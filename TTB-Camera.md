# TurtleBots Guide: Set Up the Arducam OV5647 Camera on the Rover

This guide gets the **Arducam OV5647** camera working on the rover's Raspberry Pi 5, so Marpy's
phone page (`osr_biodiversity`) can show a live view and identify plants.

The rover's Pi runs **Ubuntu 24.04** and **ROS 2 Jazzy**. Every command in this guide goes in a
terminal **on the Pi** (log in with SSH as in [TTB-README step 2.1](TTB-README.md#21-log-in-to-the-pi)).

> [!WARNING]
> **Draft.** Steps 1–5.2 worked on our rover (2026-11-25). Step 5.3 (the phone page) and Step 6
> haven't been tested yet. If a step doesn't work, write down the exact error message and update
> this page.

---

## Why this takes more than plugging it in

The OV5647 is a **CSI camera**: it connects with a flat ribbon cable, not USB. It sends raw
sensor data, and a program called **libcamera** turns that data into normal pictures.

On a Pi 5, Ubuntu's own libcamera doesn't include the Pi 5 support we need. So we build
**Raspberry Pi's version of libcamera** ourselves. Then a ROS node called **camera_ros**
uses it to publish the pictures as a ROS topic.

```text
OV5647 camera  ─▶  ribbon cable  ─▶  Pi 5  ─▶  libcamera  ─▶  camera_ros  ─▶  /camera/image_raw  ─▶  phone page
```

---

## Step 1: Plug in the camera

- The Pi 5 camera sockets are the small **22-pin** kind. Most Arducam OV5647 boards come with a
  wider **15-pin** cable, so you need a **15-pin to 22-pin cable**.
- **Turn the Pi off** before plugging in or unplugging the camera.
- The Pi 5 has two camera sockets, **CAM0** and **CAM1**. Write down which one you used.
- At the Pi end, the metal contacts face toward the HDMI ports.

---

## Step 2: Tell the Pi the camera is there

1. Open the Pi's startup settings file:

   ```bash
   sudo nano /boot/firmware/config.txt
   ```

2. Find the line `camera_auto_detect=1` (Ubuntu's file has one). Change the `1` to `0`, and add
   the `dtoverlay` line right after it. Use `cam0` or `cam1` to match the socket you used:

   ```ini
   camera_auto_detect=0
   dtoverlay=ov5647,cam0
   ```

   Save with **Ctrl + O**, **Enter**, then exit with **Ctrl + X**.

   Change the existing line instead of adding a second one. If the file has a setting twice, the
   Pi uses the one lower down, so a `camera_auto_detect=1` below your lines would undo them.

   > [!IMPORTANT]
   > The file is split into sections like `[pi4]`, `[cm4]` and `[all]`, and a setting only
   > applies to the boards its section names. On our Pi, `camera_auto_detect` is in the `[all]`
   > section, which is right. If your file has no `camera_auto_detect` line, add both lines at
   > the very end, with an `[all]` line above them.

3. Allow your user to use the camera, then restart:

   ```bash
   sudo usermod -aG video $USER
   sudo reboot
   ```

**Check:** after the Pi restarts, log in again and run:

```bash
sudo dmesg | grep -i ov5647
```

(`dmesg` needs `sudo` on Ubuntu.) The line that matters is the last one, ending in
**`found subdevice ... ov5647@36`**:

```text
[    4.830401] rp1-cfe 1f00110000.csi: found subdevice /axi/pcie@120000/rp1/i2c@88000/ov5647@36
```

It means the Pi's camera hardware (`rp1-cfe`) found the camera chip and its driver started. You'll
also see several `Fixed dependency cycle(s)` lines. Those are harmless. If there's no
`found subdevice` line, see [Troubleshooting](#troubleshooting).

> [!NOTE]
> Don't use `/dev/media*` as the check. A Pi 5 has `/dev/media0`, `media1`, and `media2` even
> with no camera plugged in. Those belong to the Pi's camera hardware, not to the camera.

---

## Step 3: Build Raspberry Pi's libcamera

This step downloads and compiles libcamera. It can take **15–30 minutes** on the Pi.

1. Install the tools needed to build it:

   ```bash
   sudo apt update
   sudo apt install -y git meson ninja-build pkg-config cmake python3-jinja2 python3-ply \
     python3-yaml libyaml-dev libgnutls28-dev openssl libdrm-dev libjpeg-dev libtiff-dev \
     libevent-dev libboost-dev
   ```

2. Remove the ROS copies of libcamera and camera_ros, if they're installed. Having two different
   libcameras on the Pi causes confusing errors:

   ```bash
   sudo apt remove -y ros-jazzy-libcamera ros-jazzy-camera-ros
   ```

   If apt says the packages aren't installed, that's fine.

3. Download, build, and install libcamera:

   ```bash
   cd ~
   git clone https://github.com/raspberrypi/libcamera.git
   cd libcamera
   meson setup build --buildtype=release \
     -Dpipelines=rpi/vc4,rpi/pisp -Dipas=rpi/vc4,rpi/pisp \
     -Dcam=enabled -Dv4l2=true -Dgstreamer=disabled -Dqcam=disabled \
     -Dtest=false -Dlc-compliance=disabled -Ddocumentation=disabled -Dpycamera=disabled
   ninja -C build
   sudo ninja -C build install
   sudo ldconfig
   ```

**Check:** run

```bash
cam -l
```

It should end like this:

```text
INFO IPAProxy ipa_proxy.cpp:184 Using tuning file /usr/local/share/libcamera/ipa/rpi/pisp/ov5647.json
INFO RPI pisp.cpp:1186 Registered camera ... to CFE device /dev/media0 and ISP device /dev/media1 ...
Available cameras:
1: External camera 'ov5647' (/base/axi/pcie@120000/rp1/i2c@88000/ov5647@36)
```

- `rpi/pisp` means it's using the Pi 5 support we built.
- `tuning file ... ov5647.json` means it found the color settings for this camera.
- `Available cameras: 1: ... 'ov5647'` means libcamera can use the camera.

If you see all three, the hardest part is done. 🎉

---

## Step 4: Build camera_ros

camera_ros goes in the rover's ROS workspace, next to the rover code.

```bash
source /opt/ros/jazzy/setup.bash
source ~/osr_ws/venv/bin/activate
cd ~/osr_ws/src
git clone https://github.com/christianrauch/camera_ros.git
cd ~/osr_ws
rosdep install -y --from-paths src/camera_ros --ignore-src --skip-keys=libcamera
python3 -m colcon build --symlink-install --packages-select camera_ros
source install/setup.bash
```

`--skip-keys=libcamera` stops rosdep from installing the ROS copy of libcamera again. We want
camera_ros to use the one we built in Step 3.

**Check:** the build should end with `Summary: 1 package finished`.

---

## Step 5: Start the camera

1. Start the camera node:

   ```bash
   ros2 run camera_ros camera_node --ros-args -p width:=1296 -p height:=972
   ```

   It prints some warnings about settings that aren't configured or files it can't find, plus
   one error like this:

   ```text
   [ERROR] [camera_calibration_parsers]: Unable to open camera calibration file [/home/pi/.ros/camera_info/ov5647_..._1296x972.yaml]
   ```

   **This error is harmless.** A calibration file tells ROS exactly how the lens bends the
   picture, for measuring distances in images. We haven't made one, and plant identification
   doesn't need one, so the camera works fine without it. Leave the node running.

2. In a **second** terminal on the Pi, check that pictures are arriving:

   ```bash
   source ~/osr_ws/install/setup.bash
   ros2 topic hz /camera/image_raw
   ```

   It should print a rate. On our rover it's about 30 pictures per second:

   ```text
   average rate: 29.617
           min: 0.025s max: 0.063s std dev: 0.00955s window: 31
   ```

   Press **Ctrl + C** to stop it. (This stops only the checker, not the camera.)

3. Start Marpy's phone page. `camera:=none` tells it not to start its own camera, because
   camera_ros is already running:

   ```bash
   ros2 launch osr_biodiversity biodiversity.launch.py camera:=none
   ```

   See the [osr_biodiversity README](ROS/osr_biodiversity/README.md) for how to open the page
   on a phone.

> [!TIP]
> If the colors look wrong (for example, plants look blue), stop the camera node and start it
> again with `-p format:=BGR888` or `-p format:=XRGB8888` added to the end. When the node starts,
> it prints the formats the camera supports.

---

## Step 6: Every time after the first time

Steps 1–4 happen only once. After that, one command starts **both** the camera and the phone
page.

> [!NOTE]
> **The first time only:** get the newest code onto the Pi and rebuild it, so the launch file
> has the `csi` option. Follow [TTB-README step 2.3](TTB-README.md#23-get-the-newest-code-onto-the-pi).
> Otherwise the command below fails with an error about `csi` not being a valid choice.

Stop any camera node from Step 5 first (**Ctrl + C**), then run:

```bash
source ~/osr_ws/install/setup.bash
ros2 launch osr_biodiversity biodiversity.launch.py
```

The CSI camera is the default (`camera:=csi`). If plants look blue, add
`csi_format:=BGR888` (or `csi_format:=XRGB8888`) to the end of that command. The
[osr_biodiversity README](ROS/osr_biodiversity/README.md) lists all the settings, and how to use
a USB webcam instead.

---

## Troubleshooting

| If you see… | Check this |
| --- | --- |
| `sudo dmesg \| grep -i ov5647` shows no `found subdevice` line | The cable is the wrong way round, the `cam0`/`cam1` in Step 2 doesn't match the socket, or you're using the 15-pin cable that came with the camera (the Pi 5 needs a 15-pin to 22-pin cable). |
| `cam -l` says no cameras are available | Did the build in Step 3 use `rpi/pisp`? Run `sudo ldconfig` again, then try once more. |
| The camera_ros build can't find libcamera | Run `pkg-config --modversion libcamera`. It should print a version number. If not, redo Step 3. |
| Opening `/dev/video0` directly gives garbage or errors | That's normal on a Pi 5. Those devices give raw sensor data. Use camera_ros instead. |
| `ros2: command not found` | Run `source /opt/ros/jazzy/setup.bash` and `source ~/osr_ws/install/setup.bash` first. |

---

## Notes from our setup

Write down here what was different on our rover, so the next person has an easier time.

- The camera is in the **CAM0** socket.
- Ubuntu's `config.txt` already had `camera_auto_detect=1` in the `[all]` section. We changed it
  to `0` and put `dtoverlay=ov5647,cam0` right after it.
