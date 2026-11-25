"""ROS node that serves the Marpy phone page.

Subscribes to a camera image topic, keeps the latest frame, and runs the Flask
app from web_app.py in a background thread. Open http://<rover>:8000 on a phone.

Parameters (defaults in config/biodiversity_params.yaml):
    image_topic         sensor_msgs/Image topic to show and photograph
    data_dir            where photos and observations.csv are saved
    host, port          web server address (0.0.0.0 = reachable from the network)
    stream_width        live view width in pixels (full-res frames are used for Identify)
    stream_fps          live view frame rate
    jpeg_quality        quality of saved photos (1-100)
    plantnet_key_file   file holding the Pl@ntNet API key (never put the key in the repo)
    plantnet_lang       language for common names, e.g. en
    plantnet_project    Pl@ntNet flora; 'all' covers every region
"""
import threading
import time

import cv2
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image

from .image_utils import ros_image_to_bgr
from .observations import ObservationStore
from .plantnet import identify, load_api_key
from .web_app import create_app

STALE_AFTER_S = 3.0


class BiodiversityWebNode(Node):

    def __init__(self):
        super().__init__('biodiversity_web')
        p = self.declare_parameter
        self.image_topic = p('image_topic', '/camera/image_raw').value
        data_dir = p('data_dir', '~/bio_data').value
        host = p('host', '0.0.0.0').value
        port = p('port', 8000).value
        stream_width = p('stream_width', 640).value
        stream_fps = p('stream_fps', 10.0).value
        self.jpeg_quality = p('jpeg_quality', 90).value
        key_file = p('plantnet_key_file', '~/.config/osr_biodiversity/plantnet_key').value
        lang = p('plantnet_lang', 'en').value
        project = p('plantnet_project', 'all').value

        self._frame_lock = threading.Lock()
        self._frame = None
        self._frame_time = 0.0
        self._warned_encoding = False

        self.create_subscription(Image, self.image_topic, self._on_image, qos_profile_sensor_data)

        self.store = ObservationStore(data_dir)
        api_key = load_api_key(key_file)
        if api_key:
            identifier = lambda jpeg, organ: identify(jpeg, organ, api_key, lang=lang, project=project)
        else:
            identifier = None
            self.get_logger().warn(
                f'No Pl@ntNet API key in {key_file}. Photos will be saved as "pending" '
                'and can be identified later with "Retry waiting".')

        app = create_app(self.latest_jpeg, self.store, identifier=identifier,
                         get_status=self.status, stream_width=stream_width,
                         stream_fps=stream_fps)
        self._server = threading.Thread(
            target=app.run,
            kwargs=dict(host=host, port=port, threaded=True, use_reloader=False),
            daemon=True)
        self._server.start()
        self.get_logger().info(
            f'Marpy page on http://<rover-ip>:{port} (camera topic {self.image_topic}, '
            f'saving to {self.store.data_dir})')

    def _on_image(self, msg):
        try:
            bgr = ros_image_to_bgr(msg.encoding, msg.height, msg.width, msg.step, msg.data)
        except ValueError as e:
            if not self._warned_encoding:
                self.get_logger().error(f'Cannot show camera images: {e}')
                self._warned_encoding = True
            return
        with self._frame_lock:
            self._frame = bgr
            self._frame_time = time.monotonic()

    def latest_jpeg(self, max_width=None, quality=None):
        """Latest frame as JPEG bytes, or None if there is no recent frame."""
        with self._frame_lock:
            frame = self._frame
            age = time.monotonic() - self._frame_time
        if frame is None or age > STALE_AFTER_S:
            return None
        h, w = frame.shape[:2]
        if max_width and w > max_width:
            frame = cv2.resize(frame, (max_width, round(h * max_width / w)),
                               interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode('.jpg', frame,
                               [cv2.IMWRITE_JPEG_QUALITY, int(quality or self.jpeg_quality)])
        return buf.tobytes() if ok else None

    def status(self):
        with self._frame_lock:
            has_frame = self._frame is not None
            age = time.monotonic() - self._frame_time
        return {'camera_ok': has_frame and age <= STALE_AFTER_S,
                'camera_age_s': round(age, 1) if has_frame else None,
                'image_topic': self.image_topic}


def main(args=None):
    rclpy.init(args=args)
    node = BiodiversityWebNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
