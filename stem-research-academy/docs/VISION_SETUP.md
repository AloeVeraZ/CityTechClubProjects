# Pretrained vision setup (Raspberry Pi 4)

This guide prepares the 3TSahur Raspberry Pi for **pretrained person detection**. It uses Ultralytics YOLO11 Nano (`yolo11n`), whose standard weights are trained on the COCO dataset. No dataset collection, labeling, or training is required.

> Current repository status: vision is optional and starts only after an operator enables it for a camera. It runs in an isolated background worker; it does not change the motor GPIO mapping, LARP firmware, or control service.

## What the model does

The included COCO weights recognize 80 common object categories. For this project, begin with COCO class `0` (`person`) only. The model returns confidence-scored bounding boxes that can be drawn onto a camera frame. Treat the output as an operator aid, not a safety decision or proof of identity.

Relevant upstream documentation:

- [YOLO11 pretrained models](https://docs.ultralytics.com/models/yolo11/)
- [Ultralytics NCNN export](https://docs.ultralytics.com/integrations/ncnn/)
- [Ultralytics Raspberry Pi deployment guidance](https://docs.ultralytics.com/guides/raspberry-pi/)

## Prerequisites

- Raspberry Pi 4 Model B (4 GB) running a current **64-bit Raspberry Pi OS**.
- The normal 3TSahur installation completed first. It provides Python 3, OpenCV, the Logitech C270 setup, and the dashboard service.
- A stable internet connection for the one-time Python package, model-weight, and NCNN export downloads. Normal driving and existing camera streaming do not need internet after setup.
- At least 3 GB of free storage and a stable Pi power supply. ML packages and model conversion use more space and CPU than the base dashboard.
- The C270 connected and visible as `/dev/video0` (or the configured camera device). Use `v4l2-ctl --list-devices` to check.

Do not run model installation as `root`, and do not install the ML packages into `/usr/lib/python3`. The separate environment below keeps the established dashboard dependencies unchanged.

## Install YOLO11 Nano and NCNN

Update the base application first and let the Pi reboot. This installs the
dashboard launcher that can select the optional runtime while retaining a safe
fallback to the base runtime:

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/CityTechClubProjects/main/stem-research-academy/installer/curl-install.sh | STEM_SKIP_OS_UPGRADE=1 bash
```

After the reboot, run the optional installer as the Pi's normal user, without
`sudo`:

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/CityTechClubProjects/main/stem-research-academy/installer/install-vision.sh | bash
```

The installer follows Ultralytics' Pi deployment pattern: it installs
`ultralytics[export]` in an isolated environment, downloads `yolo11n.pt`, and
exports NCNN for faster ARM inference. It uses `imgsz=320`, batch size 1, and
CPU export for this Pi 4 control workload. It then loads the exported model and
runs a synthetic frame through NCNN before restarting the dashboard.

The first package install and model export can take several minutes. If it
fails due to storage pressure, stop, free space, and retry—do not delete the
robot project or `/etc/stem-research-academy/config.env`.

The runtime and model are stored under
`~/.local/share/stem-research-academy/vision/`, outside the replace-on-update
application directory. The installer records their absolute paths as
`VISION_VENV` and `VISION_MODEL` in the persistent config. Normal application
updates therefore retain vision, and normal driving does not need internet.

## Enable or disable vision in the dashboard

Open a robot tab and press `C`, or select its **Vision off · C** button. The control is per camera: 3TSahur's C270, LARP Scout A, and LARP Scout B each keep their own state. When enabled, the dashboard overlays current `person` boxes and confidence scores; press `C` again to immediately stop future inference for that selected feed.

Vision is deliberately disabled after a dashboard restart. A missing model, missing `ultralytics`/`ncnn` package, unavailable camera, or unreachable LARP stream reports as **Vision unavailable** in the video pane. Those conditions do not disable driving, emergency stop, the motor watchdog, camera streaming, or CSI status.

Person inference is motion-gated by default. The worker still performs a forced
inference every five seconds so a stationary person is not ignored, but it skips
the expensive model call between those checks when the 160x120 frame-difference
score is low. The existing boxes remain visible until the next forced refresh.

The adjacent **Markers off · L** control enables lightweight 4x4 ArUco marker
recognition without loading YOLO. Press `L` on the 3TSahur or LARP A tab; on
LARP B use the button because `L` remains its right-turn key. Marker recognition
is also off after restart and reports a local warning if the installed OpenCV
package lacks `cv2.aruco`.

## Verify the Logitech C270 and create a visual preview

This one-frame check writes a labelled image to `/tmp` without touching the dashboard service or motor controls:

```bash
~/.local/share/stem-research-academy/vision/.vision-venv/bin/python - <<'PY'
import cv2
from pathlib import Path
from ultralytics import YOLO

camera = cv2.VideoCapture(0)
if not camera.isOpened():
    raise RuntimeError("C270 could not be opened. Check CAMERA_DEVICE and USB power.")

ok, frame = camera.read()
camera.release()
if not ok:
    raise RuntimeError("C270 opened but did not return a frame.")

model = YOLO(str(Path.home() / ".local/share/stem-research-academy/vision/yolo11n_ncnn_model"))
results = model(frame, classes=[0], conf=0.45, imgsz=320, verbose=False)
cv2.imwrite("/tmp/3tsahur-yolo-preview.jpg", results[0].plot())
print("Saved /tmp/3tsahur-yolo-preview.jpg")
PY
```

Open `/tmp/3tsahur-yolo-preview.jpg` on the Pi display. A person in view should have a labelled bounding box. An image with no box is valid when no person meets the confidence threshold.

## LARP ESP32-CAM feed prerequisites

Before using a LARP feed for vision:

1. Complete [ESP32_CAM_SETUP.md](ESP32_CAM_SETUP.md) for the appropriate camera.
2. Confirm the selected LARP tab plays `http://larp-a-cam.local/stream` or `http://larp-b-cam.local/stream` (or its configured static-IP fallback).
3. Keep only the selected dashboard stream open. The existing dashboard does this automatically to preserve Wi-Fi capacity for robot control.
4. Start with **one** vision source at a time. Do not run inference on both ESP32-CAM streams and the C270 simultaneously on a Pi 4.

The ESP32-CAM stream itself does not need new firmware for this model. It must simply be reachable by the Pi and produce a valid MJPEG stream.

## Performance and safe operating settings

Use these initial settings for the Pi 4:

| Setting | Start with | Why |
| --- | --- | --- |
| Model | `yolo11n_ncnn_model` | Smallest YOLO11 detection model. |
| Input size | `320` | Reduces CPU load compared with 640px inference. |
| Classes | `[0]` | Limits detection to people. |
| Confidence | `0.45` | Reasonable initial balance; tune only after observing your own space. |
| Inference rate | 2–5 FPS | Video can remain smooth while the Pi has time for controls. |
| Vision sources | One active tab/feed | Avoids competing inference, video, and Wi-Fi workloads. |
| Motion gate | enabled; `0.02` changed-pixel threshold | Avoids repeated YOLO calls in static scenes. |
| Forced refresh | every 5 seconds | Still checks for stationary people. |

The included implementation runs inference in a separate worker and never waits in a motor-command request path. If you enable more than one feed, the worker samples them in turn; for the best Pi 4 responsiveness, leave vision enabled on only the tab you are watching.

The worker also pauses before starting another analysis cycle whenever the hub
or either scout is receiving motion heartbeats. These optional environment
settings can be placed in `/etc/stem-research-academy/config.env`:

```bash
VISION_MOTION_GATE=1
VISION_MOTION_THRESHOLD=0.02
VISION_FORCE_INFERENCE_SECONDS=5
VISION_INTERVAL_SECONDS=0.5
EVIDENCE_MAX_ITEMS=100
EVIDENCE_QUEUE_SIZE=12
HEALTH_INTERVAL_SECONDS=10
```

The **Evidence** button captures the selected JPEG and queues a background
JPEG/JSON pair containing the analysis state, scout heartbeats, command state,
and cached health telemetry. The queue and retention counts are bounded; the
dashboard refuses capture while a robot is moving so it cannot compete with
control traffic.

## Benchmark before enabling it during driving

Run the repository tests first:

```bash
cd ~/STEMResearchAcademy
.venv/bin/python -m unittest discover -s tests -v
```

Then, with wheels raised, run the preview repeatedly while a second device uses the dashboard. Verify that controls stay responsive and that `Space` and `Esc` immediately stop motion. Start at 2 FPS and 320px; lower the inference rate or disable vision if control, Wi-Fi, temperature, or power stability is affected.

The existing simulation suite validates application control paths, not camera-to-model speed on physical Pi hardware. Measure final performance on the deployed Pi with the actual C270 and one actual ESP32-CAM feed.

## Optional future additions

After basic person detection is stable, the model can be connected to the currently selected dashboard tab to display its latest labelled frame and status. A tracker such as ByteTrack can be evaluated later if persistent object IDs are useful, but initial deployment should use detection alone to minimize overhead. See the [Ultralytics tracking guide](https://docs.ultralytics.com/modes/track/).
