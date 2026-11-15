# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

ROS 2 (Python 3) code for the JPL Open Source Rover (a six-wheel rocker-bogie with four steerable corners). It runs on a Raspberry Pi on the real rover and also in a Gazebo Classic simulation. This repo is Team TurtleBots' fork of `nasa-jpl/osr-rover-code`. `.github/workflows/sync_upstream.yaml` merges upstream `master` into `master` every day and fails on conflicts, so keep changes to upstream files small and easy to merge. `TTB-README.md` is the team's beginner guide for running the simulation on Windows through WSL, Docker, and rocker.

## Build, run, test

The ROS packages are built in a colcon workspace at `~/osr_ws`, with this repo cloned to `~/osr_ws/src/osr-rover-code`. Python dependencies live in a venv at `~/osr_ws/venv` (created with `--system-site-packages`, with a `COLCON_IGNORE` inside it). Activate the venv before building so colcon uses its Python:

```bash
source /opt/ros/<distro>/setup.bash && source ~/osr_ws/venv/bin/activate
cd ~/osr_ws && python3 -m colcon build --symlink-install
source install/setup.bash
```

- **Simulation (Docker, the usual dev path):** `docker build -t osr-rover-sim .`, then `rocker --x11 --name osr osr-rover-sim`. Inside the container, run `ros2 launch osr_gazebo empty_world.launch.py`. To drive it, open a second shell with `docker exec -it osr bash` and run `ros2 run teleop_twist_keyboard teleop_twist_keyboard`. The image copies the repo in at build time, so rebuild the image after changing code.
- **Hardware:** `ros2 launch osr_bringup osr_launch.py` (add `enable_odometry:=true` for wheel odometry). On the Pi, `init_scripts/launch_osr.sh` with `osr_startup.service` runs the same launch file, or a legacy `osr_mod_launch.py` copy if one exists. Stop the systemd service before you launch anything by hand.
- **Tests:** only `ROS/osr_control/test/test_kinematics.py` (pytest). `kinematics.py` has no ROS dependencies, so the tests run without ROS: `cd ROS/osr_control && python3 -m pytest test/` (`setup.cfg` sets `pythonpath = .`). Run a single test with `python3 -m pytest test/test_kinematics.py::test_straight_drive_equal_speed_opposite_sides`. Through colcon: `colcon test --packages-select osr_control`.
- **Hardware bench scripts** (Roboclaw, servo calibration, INA260, GPIO/e-stop) are in `scripts/` and run directly on the Pi.

## Architecture

There are four packages in `ROS/`:

- `osr_interfaces`: custom messages. `CommandDrive` holds 6 wheel velocities in rad/s. `CommandCorner` holds 4 corner angles in rad, with 0 meaning straight. `CommandPWM` and `Status` are the others.
- `osr_control` (ament_python): the nodes. Entry points are in `setup.py`.
- `osr_bringup`: `launch/osr_launch.py` and the parameter files in `config/`. The rover dimensions `d1`–`d4`, `wheel_radius`, and `drive_no_load_rpm` are in `osr_params.yaml`.
- `osr_gazebo` (ament_cmake): URDF/xacro, ros2_control config, and launch files. It ships with a `COLCON_IGNORE`, so a normal build skips it. The Dockerfile deletes that file so the simulation gets built.

Command flow:

```
/cmd_vel or /cmd_vel_intuitive (Twist)
  -> rover.py  (uses kinematics.py)
       -> /cmd_drive  (CommandDrive)  -> roboclaw_wrapper.py -> Roboclaw serial (roboclaw.py)   -> /drive_state, /status
       -> /cmd_corner (CommandCorner) -> servo_control.py -> /cmd_pwm -> pca_9685_interface.py  (servo_control also publishes /corner_state)
```

- **Kinematics are shared by hardware and sim.** `osr_control/kinematics.py` is pure Python and holds all the rocker-bogie math. In simulation the same `rover` node runs, and `osr_gazebo/scripts/gazebo_command_adapter.py` passes `/cmd_drive` and `/cmd_corner` on to the Gazebo `wheel_controller` and `servo_controller`. Do not reimplement the kinematics in the sim. A change to `osr_params.yaml` affects both the hardware and the simulation.
- **Twist conventions:** positive `angular.z` means a positive turning radius, which is a left turn when driving forward. Rotate-in-place uses `angular.y` with `linear.x == 0`, so `teleop_twist_keyboard` cannot command it. `/cmd_vel` is "mathematically correct" mode: steering flips when reversing, and with zero linear velocity, angular velocity does not move the corners. `/cmd_vel_intuitive` is for joysticks: the corners always turn the way the stick points. In `osr_launch.py`, `teleop_twist_joy` is remapped to publish on `/cmd_vel_intuitive`.
- **Odometry in sim is not wired up yet.** `rover` computes odometry from `/drive_state` and `/corner_state`, and Gazebo does not publish those topics. `empty_world.launch.py` sets `enable_odometry: False`.
- **ROS distro:** the Gazebo Classic simulation needs ROS 2 Humble (the Dockerfile default). The real rover's Pi runs Ubuntu 24.04. On a Pi 5, install `lgpio` with pip, not `adafruit-lgpio`, which needs Python 3.13 (see `setup/rpi.md`).

## Per-rover customization

Per-rover values go in `osr_bringup/config/{osr,roboclaw,pca9685}_params_mod.yaml`, never in the default files, so upstream merges stay clean. These files are gitignored; `setup/rpi.md` and the Dockerfile create them empty. `osr_launch.py` adds every existing mod file to every node's parameters, after the defaults and after the values written in the launch file, so the mod values win. Sections are keyed by node name, so a mod file can override any node: `servo_wrapper` for `centered_pulse_widths`, `teleop_twist_joy` and `joy` for the gamepad, `roboclaw_wrapper` for the Ryobi `velocity_qpps_to_duty_factor` (see `setup/ryobi_18v_battery.md`).

- The launch file looks for mod files next to the real path of the installed `osr_params.yaml`. With `--symlink-install` that is the source `config/` folder, so new or edited mod files work without a rebuild.
- Empty or comment-only mod files are skipped. A section with an empty `ros__parameters` stops the launch on purpose: rcl rejects such a file, and since every node gets every mod file, all nodes would crash-loop.
- The launch prints `Parameter overrides: <files>` at startup. Check that line to confirm which overrides loaded.
- To test the launch without hardware, run it in the `osr-rover-sim` image and read values with `ros2 param get --no-daemon`. `roboclaw_wrapper`, `pca9685_interface` and `ina260` crash and respawn without hardware; that's expected.

## Workflow rules

- Make every change in a git worktree on its own branch, never directly on `master`. Worktrees go in `.claude/worktrees/`, which is listed in `.git/info/exclude`.
- Merging into the fork's `master` needs at least one review by someone else. Open a PR against `Team-Turtlebots/osr-rover-code` `master` and don't merge it yourself.
- A PR against upstream (`nasa-jpl/osr-rover-code`) needs the team coaches' review and approval before it is opened.
- When this repo is opened from Windows through `\\wsl.localhost`, Windows git can't write `.git/index`. Run git inside Ubuntu (`wsl.exe -d Ubuntu -- bash -lc 'cd ~/osr-rover-code && git ...'`).
