# CLAUDE.md: osr_biodiversity

Guidance for working in this package. See `README.md` for setup and usage.

## Project context

- **Marpy** is Team TurtleBots' FIRST LEGO League (FLL) project: a modular rover for
  biodiversity research, built on the JPL Open Source Rover in this repo.
- The team members are students. Explain things plainly, define terms, and prefer the
  simplest working approach. Keep code readable for beginners.
- This package is the biodiversity layer: camera → phone page → species ID → observation log.
  It never commands motion. Do not publish `/cmd_vel` from here without an explicit request,
  and if that comes, add a joystick-priority mux and a timeout first.

## Hardware and platform facts (learned the hard way)

- Raspberry Pi 5, Ubuntu 24.04, ROS 2 Jazzy. Python deps for the rover live in
  `~/osr_ws/venv` (created with `--system-site-packages`), so apt Python packages are visible.
- **CSI ribbon cameras don't work on this Pi.** The kernel finds an OV5647 (`rp1-cfe` registers
  `/dev/video0`-`video7`), but Ubuntu 24.04's libcamera 0.2.0 has no Pi 5 (PiSP) pipeline
  handler or IPA (`cam -l` lists nothing; its Vc4 handler looks for the Pi 4's Unicam). Fixing it
  means building Raspberry Pi's libcamera and camera_ros from source. Use a USB UVC webcam
  (the team has a Logitech C920x) with `usb_cam` instead.
- Because of those CSI nodes, the USB webcam is usually `/dev/video8+`. Prefer
  `/dev/v4l/by-id/...-video-index0`.
- The Pi is powered from the PCB's 5 V rail (Pololu D24V150F5, 15 A) through screw terminals,
  not USB-C PD, so it limits USB to 0.6 A total unless `PSU_MAX_CURRENT=5000` is set in the
  EEPROM. A single webcam fits. Heavier USB devices (e.g. Luxonis OAK-D Lite, ~5 W) need that
  setting or a powered hub.
- Internet in the field comes from a phone hotspot. Pl@ntNet identification needs it; everything
  else works offline (photos queue as `pending`).

## Architecture

```
usb_cam / image_publisher ──/camera/image_raw──► web_node (rclpy + Flask thread, port 8000)
                                                  ├─ web_app.py      routes + phone page (HTML/JS inline)
                                                  ├─ plantnet.py     Pl@ntNet API client
                                                  ├─ observations.py photos + observations.csv
                                                  └─ image_utils.py  sensor_msgs/Image → BGR numpy
```

- `launch/biodiversity.launch.py`: `camera:=usb|test|none`. Every source is remapped to
  `image_topic` (default `/camera/image_raw`), so swapping cameras never touches the web node.
- `observations.py`, `plantnet.py`, `image_utils.py`, `web_app.py` have **no ROS imports** and
  are unit-tested. Keep it that way: put ROS glue only in `web_node.py`.
- `web_app.create_app()` takes callables (`get_jpeg`, `identifier`, `get_status`,
  `normalize_upload`) so tests use fakes. Add new features the same way.
- Images are converted by hand in `image_utils.py` instead of cv_bridge, which breaks when the
  venv's numpy differs from the system's.
- Data lives outside the repo in `~/bio_data`. The API key lives in
  `~/.config/osr_biodiversity/plantnet_key`. Never put either in git.

## Conventions

- Don't modify upstream OSR files for this feature. The repo syncs `nasa-jpl/osr-rover-code`
  daily (see the root CLAUDE.md). Hook into the rover only through
  `osr_bringup/launch/osr_mod_launch.py` (the team's per-rover file); README has the snippet.
  On the Pi, that file may have uncommitted button-mapping changes, so ask before editing it.
- The phone page must keep working on iPhone Safari and Android Chrome over plain `http`
  on a LAN: no external CDNs (the hotspot may be offline), no secure-context-only APIs
  (geolocation, camera APIs; use `<input type="file" capture>` for phone photos).
- `observations.csv` is the research record. Add columns only at the end of `FIELDS` and keep
  old rows readable (`_read_rows` fills missing fields).
- User-facing messages say what happened and what to do next ("Photo saved, not identified yet.
  Check the rover has internet.").

## Tests

```bash
cd ROS/osr_biodiversity && python3 -m pytest test/     # no ROS needed; needs numpy, flask, requests
```

The Pl@ntNet endpoint and response fields in `plantnet.py` were written from memory of the v2
API. If real calls fail, check https://my.plantnet.org/doc and update `parse_response` and its
test fixture together.

## Status and next steps

Draft 1 (2026-11-25), for the FLL demo on 2026-12-05. Not yet run on the Pi. Next, roughly in order:

1. First run on the Pi with the C920x: `camera:=usb`, live view, Identify, phone upload, CSV.
2. Confirm the Pl@ntNet API call against the real service.
3. Add it to `osr_mod_launch.py` (after the demo setup is stable).
4. `capture_node`: save a photo every N seconds while driving.
5. GPS (`/fix` from a USB GPS) into `latitude`/`longitude`.
6. Animals: run MegaDetector + SpeciesNet on a laptop over saved photos; import results.
7. Darwin Core export for GBIF / iNaturalist-style sharing.
8. Optional: BirdNET on the webcam microphone.

Known limits: Flask's development server (fine on a LAN, not for the internet); no login, so
anyone on the network can use the page (keep the hotspot password private).
