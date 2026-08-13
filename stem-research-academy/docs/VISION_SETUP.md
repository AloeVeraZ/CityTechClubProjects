# Offline object detection (Raspberry Pi 4)

The 3TSahur dashboard uses **YOLOv4-tiny COCO through OpenCV DNN**. Recognition
runs locally after a one-time model download. It does not require Wi-Fi or
internet during operation and does not install Ultralytics, PyTorch, NCNN, or a
second Python environment.

The compact weights are about 24 MB and recognize 80 COCO categories, including
people, bottles, chairs, backpacks, cell phones, laptops, cars, and animals.
The dashboard service has a systemd `MemoryMax=1G` hard ceiling. The detector
normally operates far below that limit because one 320x320 frame is processed
at a time.

## Install

First update the base application and let the Pi reboot:

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/CityTechClubProjects/main/stem-research-academy/installer/curl-install.sh | STEM_SKIP_OS_UPGRADE=1 bash
```

Then run the object-detector installer once, while internet is temporarily
available:

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/CityTechClubProjects/main/stem-research-academy/installer/curl-install-vision.sh | bash
```

The installer:

- downloads the 24 MB YOLOv4-tiny weights and matching configuration;
- checks SHA-256 hashes before installing either file;
- loads the model with the Pi dashboard's existing OpenCV runtime;
- verifies a real `person` detection on a local test image;
- restarts the dashboard and confirms its health endpoint responds.

After this completes, normal recognition is fully offline. Model files persist
under `~/.local/share/stem-research-academy/vision/` across application updates.
The application also includes a fallback copy under `vision_models/`, so an
empty `VISION_MODEL_CONFIG` or `VISION_MODEL_WEIGHTS` no longer disables the
detector.

## Use

When the model files are installed, detection starts automatically with the
dashboard service. Boxes show the object label and confidence percentage. Press
`C`, or select **Detection on · C**, to turn detection off; press it again to
restart detection.

Recognition runs in a background worker and pauses while drive heartbeats are
active. Motor requests, emergency stop, and the watchdog never wait for model
inference. Static people and objects are still checked continuously whenever
the robot is stopped.

## Default Pi settings

```bash
VISION_MODEL_CONFIG=$HOME/.local/share/stem-research-academy/vision/yolov4-tiny.cfg
VISION_MODEL_WEIGHTS=$HOME/.local/share/stem-research-academy/vision/yolov4-tiny.weights
VISION_AUTO_ENABLE=1
VISION_CLASSES=
VISION_CONFIDENCE=0.20
VISION_IMAGE_SIZE=320
VISION_INTERVAL_SECONDS=0.50
VISION_OBJECT_MOTION_GATE=0
VISION_CPU_THREADS=2
VISION_MAX_DETECTIONS=15
```

An empty `VISION_CLASSES` enables all 80 COCO categories. To restrict detection,
provide a comma-separated subset, for example:

```bash
VISION_CLASSES=person,bottle,chair,cell phone,backpack
```

Restart after configuration changes:

```bash
sudo systemctl restart stem-robot-dashboard.service
```

## Verify or troubleshoot

Confirm the two model files and memory limit:

```bash
grep -E '^VISION_(MODEL_CONFIG|MODEL_WEIGHTS|CONFIDENCE|IMAGE_SIZE)=' /etc/stem-research-academy/config.env
systemctl show stem-robot-dashboard.service -p MemoryCurrent -p MemoryMax
```

When detection is enabled, the UI shows one of these states:

- `DETECTED` with the object count and inference time;
- `Detection active · no objects` when the model ran but found nothing above 20%;
- `Offline object detector unavailable: ...` with the exact missing-file or runtime error.

For service errors:

```bash
sudo journalctl -u stem-robot-dashboard.service -n 80 --no-pager
```

The computer-vision output is an operator aid, not a safety sensor or identity
system. Run first hardware tests with the wheels raised.

References: [OpenCV DNN supports Darknet YOLO models](https://github.com/opencv/opencv/wiki/Deep-Learning-in-OpenCV), and the [YOLOv4-tiny COCO release](https://github.com/hank-ai/darknet).
