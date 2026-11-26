# osr_biodiversity: Marpy's field station

Marpy is Team TurtleBots' FIRST LEGO League project: a modular rover for biodiversity research.
This package turns the rover's camera into a field station you use from a phone:

- **Live view** of the rover camera in the phone's browser
- **Identify** a plant from the rover camera, or from a photo taken with the phone, using the
  [Pl@ntNet](https://my.plantnet.org) API
- **Observation log**: every photo is saved on the rover with a row in `observations.csv`
  (time, species, confidence, plant part, reviewed yes/no)

It does not drive the rover. Driving stays on the controller.

## Pick a camera

The page works with either kind of camera. Set it up once, then pick it with `camera:=` when
you start the page.

| Camera | `camera:=` | Status |
|---|---|---|
| **Arducam OV5647** ribbon-cable (CSI) camera | `csi` (the default) | ✅ Camera tested on our rover |
| **USB webcam**, e.g. Logitech C920x | `usb` | 🚧 We'll set this up later |
| A photo file, for testing without a camera | `test` | ✅ |
| Nothing: start only the page | `none` | For when you start a camera yourself |

## One-time setup (on the Pi)

1. Install what the page needs, then build it:

   ```bash
   sudo apt install ros-jazzy-image-publisher python3-flask python3-requests python3-opencv
   cd ~/osr_ws && source venv/bin/activate
   python3 -m colcon build --symlink-install --packages-select osr_biodiversity
   source install/setup.bash
   ```

2. Set up your camera:
   - **CSI camera (OV5647):** follow the [camera guide](../../TTB-Camera.md) through Step 5.2.
     It builds libcamera and camera_ros. Don't install `ros-jazzy-camera-ros` with apt: it
     brings a second libcamera that can't use the Pi 5's camera hardware.
   - **USB webcam (later):** `ros2 launch` needs `usb_cam`. If you ran `rosdep install` as in
     [TTB-README step 2.3](../../TTB-README.md#23-get-the-newest-code-onto-the-pi), it's already
     installed. Otherwise, or to get `v4l2-ctl` for finding the webcam, run:

     ```bash
     sudo apt install ros-jazzy-usb-cam v4l-utils
     ```

**Pl@ntNet API key.** Make a free account at https://my.plantnet.org, create an API key, then
save it on the Pi (never commit it to the repo):

```bash
mkdir -p ~/.config/osr_biodiversity
nano ~/.config/osr_biodiversity/plantnet_key      # paste the key, save
chmod 600 ~/.config/osr_biodiversity/plantnet_key
```

Without a key everything still works, but photos are saved as **pending**. Tap
**Retry waiting** after adding the key.

## Run it

1. Start the camera and the page. Use the line for your camera:

   ```bash
   # CSI camera (OV5647)
   ros2 launch osr_biodiversity biodiversity.launch.py

   # USB webcam (see "Finding the USB webcam" below for the video_device name)
   ros2 launch osr_biodiversity biodiversity.launch.py camera:=usb \
     video_device:=/dev/v4l/by-id/usb-046d_HD_Pro_Webcam_C920_XXXX-video-index0

   # No camera: put a plant photo at ~/test_plants/test.jpg first
   ros2 launch osr_biodiversity biodiversity.launch.py camera:=test
   ```

   With the CSI camera, a `camera_calibration_parsers` error about a missing calibration file
   is normal and harmless (see the [camera guide](../../TTB-Camera.md#step-5-start-the-camera)).

2. On a phone on the same network (home Wi-Fi or the phone's hotspot), open
   **http://TurtleBots.local:8000**. If that doesn't load, use the Pi's IP instead,
   e.g. http://192.168.68.80:8000 (`hostname -I` on the Pi shows it).

### CSI camera settings

| Setting | Default | What it does |
|---|---|---|
| `csi_width`, `csi_height` | `1296`, `972` | Picture size. This is the OV5647's full view at 30 pictures per second. `2592`×`1944` is sharper but slower. |
| `csi_format` | empty (camera default) | If plants look blue, try `csi_format:=BGR888` or `csi_format:=XRGB8888`. |

### Finding the USB webcam

```bash
v4l2-ctl --list-devices
ls /dev/v4l/by-id/           # stable names, e.g. usb-046d_HD_Pro_Webcam_C920_...-video-index0
```

On a Pi 5 the CSI camera hardware uses `/dev/video0`-`video7`, so a USB webcam is
usually `/dev/video8` or higher. The `/dev/v4l/by-id/...-video-index0` name never changes,
so prefer it. `video_device` has no default: with `camera:=usb`, the launch stops and asks
for it. Other USB settings: `image_width` (`1920`), `image_height` (`1080`), and `framerate`
(`10.0`).

Identify needs internet (Pl@ntNet runs online). In the field, the Pi joins the phone's
hotspot, and the hotspot provides the internet.

## Using the page

| Control | What it does |
|---|---|
| Plant part chips | Tell Pl@ntNet what's in the photo (leaf, flower, fruit, bark). "Not sure" sends `auto`. |
| **Identify from rover** | Saves the current full-resolution camera frame and identifies it |
| **Use phone photo** | Opens the phone camera; the photo is saved on the rover and identified |
| **Save photo to phone** | Downloads the observation photo |
| **Retry waiting** | Identifies photos saved while offline or without a key |
| **Download CSV** | The whole observation log |

Hold the camera still and 10-30 cm from the plant. Stop the rover before taking an
Identify photo so the picture isn't blurry. (The C920x also needs a moment to autofocus. The
OV5647 has fixed focus, so plants very close to it can look soft.)

## Data

```
~/bio_data/
├── observations.csv
└── 2026-12-05/img_00001.jpg ...
```

`observations.csv` columns: `id, time, photo, source, organ, status, scientific_name,
common_name, score, alternatives, latitude, longitude, reviewed, notes`.
AI identifications can be wrong, so have a person check them and set `reviewed` to `yes`.

## Start it with the rover (optional)

Add this to `osr_bringup/launch/osr_mod_launch.py`, inside `generate_launch_description()`
before `return ld`. The rover's startup service runs that file.

```python
from launch.actions import IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

ld.add_action(DeclareLaunchArgument('enable_biodiversity', default_value='true'))
ld.add_action(IncludeLaunchDescription(
    PythonLaunchDescriptionSource(PathJoinSubstitution(
        [FindPackageShare('osr_biodiversity'), 'launch', 'biodiversity.launch.py'])),
    launch_arguments={
        'camera': 'csi',
        # For a USB webcam instead:
        # 'camera': 'usb',
        # 'video_device': '/dev/v4l/by-id/usb-046d_HD_Pro_Webcam_C920_XXXX-video-index0',
    }.items(),
    condition=IfCondition(LaunchConfiguration('enable_biodiversity')),
))
```

Turn it off for a run with `enable_biodiversity:=false`.

## Tests

The tests don't need ROS:

```bash
cd ROS/osr_biodiversity && python3 -m pytest test/
```

They need `pytest`, `numpy`, `flask`, `requests`, and OpenCV. On a PC, install them into a
virtual environment from the repo root:

```bash
cd ~/osr-rover-code
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
```

On the Pi, use apt instead: `sudo apt install python3-pytest python3-numpy python3-flask
python3-requests python3-opencv`.

## Troubleshooting

| Problem | Fix |
|---|---|
| Page says "No camera image" | Is the camera node running? `ros2 topic hz /camera/image_raw`. With `usb`, check `video_device`. |
| `package 'camera_ros' not found` | camera_ros isn't built, or the workspace isn't sourced. Follow the [camera guide](../../TTB-Camera.md) Step 4, then `source ~/osr_ws/install/setup.bash`. |
| camera_ros says no cameras found | Run `cam -l`. If it lists nothing, go back to the [camera guide](../../TTB-Camera.md) Steps 2-3. |
| Plants look blue (CSI) | Red and blue are swapped. Try `csi_format:=BGR888` or `csi_format:=XRGB8888`. |
| `usb_cam` can't open the device | Wrong `/dev/video` number, or the node isn't allowed to open it (is `pi` in the `video` group? `groups`). |
| `framerate` type error at launch | Pass a decimal: `framerate:=10.0`, not `10`. |
| `cv2` import fails mentioning numpy | The venv has its own numpy that doesn't match the system OpenCV. In the venv: `python3 -m pip uninstall numpy`. |
| "Pl@ntNet rejected the API key" | Check the key file has only the key, no spaces or quotes. |
| "Couldn't reach Pl@ntNet" | No internet. Photos stay pending; tap **Retry waiting** later. |
| Phone can't open `TurtleBots.local` | Some Android phones and school networks don't support `.local`. Use the IP. |
