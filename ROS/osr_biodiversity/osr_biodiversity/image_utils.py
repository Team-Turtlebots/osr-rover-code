"""Convert sensor_msgs/Image data to an OpenCV-style BGR numpy array.

We do this by hand instead of using cv_bridge: cv_bridge is compiled against the
system numpy and tends to break when the rover's venv has a different numpy.
Takes the message fields (not the message) so it can be tested without ROS.
"""
import numpy as np


def ros_image_to_bgr(encoding, height, width, step, data):
    """Return an (height, width, 3) uint8 BGR array. Raises ValueError for
    encodings we don't handle."""
    enc = encoding.lower()
    buf = np.frombuffer(bytes(data), dtype=np.uint8)
    if buf.size < height * step:
        raise ValueError(f'image data too short: {buf.size} bytes for {height} rows of {step}')
    rows = buf[:height * step].reshape(height, step)

    if enc in ('rgb8', 'bgr8'):
        img = rows[:, :width * 3].reshape(height, width, 3)
        if enc == 'rgb8':
            img = img[:, :, ::-1]
    elif enc in ('rgba8', 'bgra8'):
        img = rows[:, :width * 4].reshape(height, width, 4)[:, :, :3]
        if enc == 'rgba8':
            img = img[:, :, ::-1]
    elif enc == 'mono8':
        gray = rows[:, :width]
        img = np.repeat(gray[:, :, None], 3, axis=2)
    elif enc in ('yuv422_yuy2', 'yuyv'):
        import cv2
        yuyv = rows[:, :width * 2].reshape(height, width, 2)
        img = cv2.cvtColor(yuyv, cv2.COLOR_YUV2BGR_YUY2)
    else:
        raise ValueError(f'unsupported image encoding: {encoding}')
    return np.ascontiguousarray(img)
