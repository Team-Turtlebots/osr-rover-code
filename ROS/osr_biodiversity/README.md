# osr_biodiversity: Marpy's field station

Marpy is Team TurtleBots' FIRST LEGO League project: a modular rover for biodiversity research.
This package turns the rover's camera into a field station you use from a phone:

- **Live view** of the rover camera in the phone's browser
- **Identify** a plant from the rover camera, or from a photo taken with the phone, using the
  [Pl@ntNet](https://my.plantnet.org) API
- **Observation log**: every photo is saved on the rover with a row in `observations.csv`
  (time, species, confidence, plant part, reviewed yes/no)

It does not drive the rover. Driving stays on the controller.

## One-time setup (on the Pi)

```bash
sudo apt install ros-jazzy-usb-cam ros-jazzy-image-publisher \
                 python3-flask python3-requests python3-opencv v4l-utils
cd ~/osr_ws && source venv/bin/activate
python3 -m colcon build --symlink-install --packages-select osr_biodiversity
source install/setup.bash
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

1. Find the webcam:
   ```bash
   v4l2-ctl --list-devices
   ls /dev/v4l/by-id/           # stable names, e.g. usb-046d_HD_Pro_Webcam_C920_...-video-index0
   ```
   On a Pi 5 the CSI camera hardware uses `/dev/video0`-`video7`, so a USB webcam is
   usually `/dev/video8` or higher. The `/dev/v4l/by-id/...-video-index0` name never changes,
   so prefer it.
2. Start the camera and the page:
   ```bash
   ros2 launch osr_biodiversity biodiversity.launch.py \
     video_device:=/dev/v4l/by-id/usb-046d_HD_Pro_Webcam_C920_XXXX-video-index0
   ```
   No camera yet? Put a plant photo at `~/test_plants/test.jpg` and run
   `ros2 launch osr_biodiversity biodiversity.launch.py camera:=test`.
3. On a phone on the same network (home Wi-Fi or the phone's hotspot), open
   **http://TurtleBots.local:8000**. If that doesn't load, use the Pi's IP instead,
   e.g. http://192.168.68.80:8000 (`hostname -I` on the Pi shows it).

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
Identify photo so autofocus can settle.

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
        'camera': 'usb',
        'video_device': '/dev/v4l/by-id/usb-046d_HD_Pro_Webcam_C920_XXXX-video-index0',
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

They need `numpy`, `flask`, and `requests` (`sudo apt install python3-numpy python3-flask python3-requests`).

## Troubleshooting

| Problem | Fix |
|---|---|
| Page says "No camera image" | Is the camera node running? `ros2 topic hz /camera/image_raw`. Check `video_device`. |
| `usb_cam` can't open the device | Wrong `/dev/video` number, or the node isn't allowed to open it (is `pi` in the `video` group? `groups`). |
| `framerate` type error at launch | Pass a decimal: `framerate:=10.0`, not `10`. |
| `cv2` import fails mentioning numpy | The venv has its own numpy that doesn't match the system OpenCV. In the venv: `python3 -m pip uninstall numpy`. |
| "Pl@ntNet rejected the API key" | Check the key file has only the key, no spaces or quotes. |
| "Couldn't reach Pl@ntNet" | No internet. Photos stay pending; tap **Retry waiting** later. |
| Phone can't open `TurtleBots.local` | Some Android phones and school networks don't support `.local`. Use the IP. |
