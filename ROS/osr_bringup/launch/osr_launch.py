import os

import yaml
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def _empty_sections(node, path=''):
    """Return the sections of a ROS params file that hold no parameters (these make every node fail)."""
    if not isinstance(node, dict):
        return [path or '<top level>']
    if 'ros__parameters' in node:
        params = node['ros__parameters']
        return [] if isinstance(params, dict) and params else [path + '/ros__parameters']
    return [problem for key, value in node.items() for problem in _empty_sections(value, f'{path}/{key}')]


def generate_launch_description():

    roboclaw_params = os.path.join(
        get_package_share_directory('osr_bringup'),
        'config',
        'roboclaw_params.yaml'
    )
    osr_params = os.path.join(
        get_package_share_directory('osr_bringup'),
        'config',
        'osr_params.yaml'
    )
    pca_params = os.path.join(
        get_package_share_directory('osr_bringup'),
        'config',
        'pca9685_params.yaml'
    )

    # Per-rover overrides: each <name>_mod.yaml in the config folder is loaded after the defaults
    # (and after the values set in this file), so its values win. Sections are keyed by node name,
    # so a mod file can override any node launched here, e.g. `servo_wrapper:` or `teleop_twist_joy:`.
    # With `colcon build --symlink-install` the installed defaults link back to the source tree, so
    # mod files are looked up there first and new or edited ones take effect without a rebuild.
    config_dirs = dict.fromkeys([os.path.dirname(os.path.realpath(osr_params)),
                                 os.path.dirname(osr_params)])
    mod_params = []
    for name in ('osr_params', 'roboclaw_params', 'pca9685_params'):
        for config_dir in config_dirs:
            mod_file = os.path.join(config_dir, name + '_mod.yaml')
            if not os.path.isfile(mod_file):
                continue
            with open(mod_file) as f:
                content = yaml.safe_load(f)
            if content is not None:  # skip files that are empty or only hold comments
                problems = _empty_sections(content)
                if problems:
                    raise RuntimeError(
                        f"{mod_file}: no parameters under {', '.join(problems)}. "
                        "Add parameters there, or delete or comment out those lines.")
                mod_params.append(mod_file)
            break

    ld = LaunchDescription()
    ld.add_action(LogInfo(msg='Parameter overrides: ' + (', '.join(mod_params) or 'none')))
    
    ld.add_action(
        Node(
            package='osr_control',
            executable='roboclaw_wrapper',
            name='roboclaw_wrapper',
            output='screen',
            emulate_tty=True,
            respawn=True,
            parameters=[roboclaw_params, *mod_params]
        )
    )
    ld.add_action(
        DeclareLaunchArgument('enable_odometry', default_value='false')
    )
    ld.add_action(
        DeclareLaunchArgument('publish_transform', default_value='false')
    )

    pca_9685_interface_node = Node(
        package='osr_control',
        executable='pca9685_interface',
        name='pca9685_interface',
        output='screen',
        emulate_tty=True,
        respawn=True,
        parameters=[pca_params, *mod_params]
    )

    servo_control_node = Node(
        package='osr_control',
        executable='servo_control',
        name='servo_wrapper',
        output='screen',
        emulate_tty=True,
        respawn=True,
        parameters=[{'centered_pulse_widths': [148, 155, 148, 158]}, *mod_params]
    )

    ld.add_action(pca_9685_interface_node)
    ld.add_action(servo_control_node)

    ld.add_action(
        Node(
            package='osr_control',
            executable='rover',
            name='rover',
            output='screen',
            emulate_tty=True,
            respawn=True,
            parameters=[osr_params,
                        {'enable_odometry': LaunchConfiguration('enable_odometry')},
                        {'publish_transform': LaunchConfiguration('publish_transform')},
                        *mod_params]
        )
    )

    ld.add_action(
        Node(
            package='teleop_twist_joy',
            executable='teleop_node',
            name='teleop_twist_joy',
            output='screen',
            emulate_tty=True,
            respawn=True,
            parameters=[
                {"scale_linear.x": -0.4},  # scale to apply to drive speed, in m/s: drive_motor_rpm * 2pi / 60 * wheel radius * slowdown_factor
                {"axis_linear.x": 1},
                {"axis_angular.yaw": 3},  # which joystick axis to use for driving
                {"axis_angular.pitch": 0},  # axis to use for in-place rotation
                {"scale_angular.yaw": -1.25},  # scale to apply to angular speed, in rad/s: scale_linear / min_radius(=0.45m)
                {"scale_angular.pitch": 0.25},  # scale to apply to angular speed, in rad/s: scale_linear / min_radius(=0.45m)
                {"scale_angular_turbo.yaw": 3.95},  # scale to apply to angular speed, in rad/s: scale_linear_turbo / min_radius
                {"scale_linear_turbo.x": 1.78},  # scale to apply to linear speed, in m/s
                # {"enable_button": 4},  # which button to press to enable movement
                {"enable_button": 0},  # which button to press to enable movement
                # {"enable_turbo_button": 5}  # -1 to disable turbo
                {"enable_turbo_button": -1},  # -1 to disable turbo
                *mod_params
            ],
            remappings=[
                ('/cmd_vel', '/cmd_vel_intuitive')
            ]
        )
    )
    ld.add_action(
        Node(
            package='joy',
            executable='joy_node',
            name='joy',
            output='screen',
            emulate_tty=True,
            respawn=True,
            parameters=[
                {"autorepeat_rate": 5.0},
                {"device_id": 0},  # This might be different on your computer. Run `ls -l /dev/input/event*`. If you have event1, put 1.
                *mod_params
            ]
        )
    )

    ld.add_action(
        Node(
            package='osr_control',
            executable='ina260',
            name='ina260_node',
            output='screen',
            emulate_tty=True,
            parameters=[
                {"publish_rate": 1.0},
                {"sensor_address": "0x45"},
                *mod_params
            ]
        )
    )
    # ld.add_action(
    #     Node(
    #         package='osr_control',
    #         executable='joy_extras',
    #         output='screen',
    #         emulate_tty=True,
    #         parameters=[
    #             {"duty_button_index": 1}  # which button toggles duty mode on/off
    #         ]
    #     )
    # )

    return ld
