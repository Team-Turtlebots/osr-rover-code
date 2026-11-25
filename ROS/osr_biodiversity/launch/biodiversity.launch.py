"""Start the Marpy camera and phone page.

    ros2 launch osr_biodiversity biodiversity.launch.py                       # USB webcam
    ros2 launch osr_biodiversity biodiversity.launch.py camera:=test          # a photo file instead
    ros2 launch osr_biodiversity biodiversity.launch.py video_device:=/dev/video8

camera:=usb   usb_cam reads a UVC webcam (e.g. Logitech C920x)
camera:=test  image_publisher repeats test_image (default ~/test_plants/test.jpg)
camera:=none  start only the web page (camera started some other way)

Whatever the source, images arrive on image_topic (default /camera/image_raw),
so switching cameras never changes the web node.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import (EnvironmentVariable, EqualsSubstitution,
                                  LaunchConfiguration, PathJoinSubstitution)
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    camera = LaunchConfiguration('camera')
    image_topic = LaunchConfiguration('image_topic')

    args = [
        DeclareLaunchArgument('camera', default_value='usb', choices=['usb', 'test', 'none'],
                              description='Image source'),
        DeclareLaunchArgument('image_topic', default_value='/camera/image_raw'),
        DeclareLaunchArgument('video_device', default_value='/dev/video0',
                              description='USB camera device. On a Pi 5 with the CSI camera '
                                          'overlay enabled, the webcam is usually /dev/video8 '
                                          'or higher; run `v4l2-ctl --list-devices`.'),
        DeclareLaunchArgument('image_width', default_value='1920'),
        DeclareLaunchArgument('image_height', default_value='1080'),
        DeclareLaunchArgument('framerate', default_value='10.0',
                              description='Must be a decimal number, e.g. 10.0'),
        DeclareLaunchArgument('test_image', default_value=PathJoinSubstitution(
            [EnvironmentVariable('HOME'), 'test_plants', 'test.jpg'])),
        DeclareLaunchArgument('port', default_value='8000'),
    ]

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

    return LaunchDescription(args + [usb_camera, test_camera, web])
