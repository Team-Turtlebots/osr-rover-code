"""Start the Marpy camera and phone page.

    ros2 launch osr_biodiversity biodiversity.launch.py                       # CSI camera (OV5647)
    ros2 launch osr_biodiversity biodiversity.launch.py camera:=usb \
        video_device:=/dev/v4l/by-id/usb-046d_HD_Pro_Webcam_C920_XXXX-video-index0
    ros2 launch osr_biodiversity biodiversity.launch.py camera:=test          # a photo file instead

camera:=csi   camera_ros reads the ribbon-cable camera (Arducam OV5647) through libcamera.
              Needs Raspberry Pi's libcamera and camera_ros built from source: see TTB-Camera.md
              in the repo root.
camera:=usb   usb_cam reads a UVC webcam (e.g. Logitech C920x). video_device is required.
camera:=test  image_publisher repeats test_image (default ~/test_plants/test.jpg)
camera:=none  start only the web page (camera started some other way)

Whatever the source, images arrive on image_topic (default /camera/image_raw),
so switching cameras never changes the web node.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import (EnvironmentVariable, EqualsSubstitution,
                                  LaunchConfiguration, PathJoinSubstitution)
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    camera = LaunchConfiguration('camera')
    image_topic = LaunchConfiguration('image_topic')

    args = [
        DeclareLaunchArgument('camera', default_value='csi',
                              choices=['csi', 'usb', 'test', 'none'], description='Image source'),
        DeclareLaunchArgument('image_topic', default_value='/camera/image_raw'),
        # CSI camera settings. 1296x972 is the OV5647's full view at 30 pictures per second.
        DeclareLaunchArgument('csi_width', default_value='1296'),
        DeclareLaunchArgument('csi_height', default_value='972'),
        DeclareLaunchArgument('csi_format', default_value='',
                              description='Pixel format, e.g. BGR888 or XRGB8888. Empty means '
                                          'the camera default. Try another if colors look wrong.'),
        # USB camera settings.
        DeclareLaunchArgument('video_device', default_value='',
                              description='USB camera device, required with camera:=usb. Use '
                                          'the stable name from `ls /dev/v4l/by-id/`. On a Pi 5, '
                                          '/dev/video0-7 belong to the CSI camera hardware.'),
        DeclareLaunchArgument('image_width', default_value='1920'),
        DeclareLaunchArgument('image_height', default_value='1080'),
        DeclareLaunchArgument('framerate', default_value='10.0',
                              description='Must be a decimal number, e.g. 10.0'),
        DeclareLaunchArgument('test_image', default_value=PathJoinSubstitution(
            [EnvironmentVariable('HOME'), 'test_plants', 'test.jpg'])),
        DeclareLaunchArgument('port', default_value='8000'),
    ]

    # camera_ros is built from source (TTB-Camera.md), not listed in package.xml: the apt
    # package ros-jazzy-camera-ros would pull in a second libcamera without Pi 5 support.
    # Named 'camera', it publishes /camera/image_raw and /camera/camera_info.
    csi_camera = Node(
        package='camera_ros',
        executable='camera_node',
        name='camera',
        output='screen',
        respawn=True,
        respawn_delay=3.0,
        parameters=[{
            'width': LaunchConfiguration('csi_width'),
            'height': LaunchConfiguration('csi_height'),
            # value_type=str keeps an empty format as '' instead of turning it into nothing.
            'format': ParameterValue(LaunchConfiguration('csi_format'), value_type=str),
        }],
        remappings=[('/camera/image_raw', image_topic)],
        condition=IfCondition(EqualsSubstitution(camera, 'csi')),
    )

    def check_usb_device(context):
        # /dev/video0 is the CSI hardware on a Pi 5, not the webcam, so there is no safe
        # default. Stop with a hint instead of opening the wrong device.
        if (context.perform_substitution(camera) == 'usb'
                and not context.perform_substitution(LaunchConfiguration('video_device'))):
            raise RuntimeError(
                'camera:=usb needs video_device:=..., for example '
                'video_device:=/dev/v4l/by-id/usb-046d_HD_Pro_Webcam_C920_XXXX-video-index0. '
                'Run `ls /dev/v4l/by-id/` to find your webcam.')
        return []

    usb_camera = Node(
        package='usb_cam',
        executable='usb_cam_node_exe',
        name='usb_cam',
        output='screen',
        respawn=True,
        respawn_delay=3.0,
        parameters=[{
            'video_device': LaunchConfiguration('video_device'),
            'image_width': LaunchConfiguration('image_width'),
            'image_height': LaunchConfiguration('image_height'),
            'framerate': LaunchConfiguration('framerate'),
            'pixel_format': 'mjpeg2rgb',
            'camera_name': 'marpy_camera',
            'frame_id': 'camera',
        }],
        remappings=[('image_raw', image_topic),
                    ('camera_info', '/camera/camera_info')],
        condition=IfCondition(EqualsSubstitution(camera, 'usb')),
    )

    test_camera = Node(
        package='image_publisher',
        executable='image_publisher_node',
        name='test_camera',
        output='screen',
        arguments=[LaunchConfiguration('test_image')],
        parameters=[{'publish_rate': 5.0}],
        remappings=[('image_raw', image_topic),
                    ('camera_info', '/camera/camera_info')],
        condition=IfCondition(EqualsSubstitution(camera, 'test')),
    )

    web = Node(
        package='osr_biodiversity',
        executable='web_node',
        name='biodiversity_web',
        output='screen',
        emulate_tty=True,
        respawn=True,
        respawn_delay=3.0,
        parameters=[
            PathJoinSubstitution([FindPackageShare('osr_biodiversity'), 'config',
                                  'biodiversity_params.yaml']),
            {'image_topic': image_topic, 'port': LaunchConfiguration('port')},
        ],
    )

    return LaunchDescription(args + [OpaqueFunction(function=check_usb_device),
                                     csi_camera, usb_camera, test_camera, web])
