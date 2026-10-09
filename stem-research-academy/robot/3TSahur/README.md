# 3TSahur robot project for MotionModule

This folder is the whole 3TSahur robot as a [MotionModule](https://github.com/AloeVeraZ/MotionModule)
robot project. The installer puts it at `~/MotionModule/robots/3TSahur` and makes it the active robot.

| File | What it does |
| --- | --- |
| `robot.py` | Driver Station drive plus the Open / Close / Toggle ramp controls |
| `hardware.py` | 3TSahur's own motor pins (unchanged from the original server) |
| `mixer.py` | The physically verified mecanum mix |
| `ramp.py` | The two GPIO ramp servos, timed by `pigpiod` |
| `dashboard.py` | Camera, ramp status, R key and controller Y button for the ramp |
| `test.py` | Debug → Drive Test with the same wiring and mix |

## Wiring (unchanged)

| Wheel | Driver | Forward GPIO | Reverse GPIO |
| --- | --- | ---: | ---: |
| `front_left` | Driver 1 · A | 5 | 6 |
| `rear_left` | Driver 1 · B | 19 | 16 |
| `front_right` | Driver 2 · A | 20 | 21 |
| `rear_right` | Driver 2 · B | 26 | 13 |

| Servo | Signal | Direction |
| --- | --- | --- |
| Ramp Servo 1 | GPIO12, physical pin 32 | normal |
| Ramp Servo 2 | GPIO18, physical pin 12 | mirrored in software |

Closed is 0° (1000 µs / 1667 µs), open is 120° (1667 µs / 1000 µs). The Logitech
USB camera is streamed by MotionModule itself. There is no PCA9685 servo board and no IMU.

## Change the code over Wi-Fi

1. Edit this folder on any computer.
2. Open `http://3tsahur.local`, go to **Code**, choose the `3TSahur` folder and press **Deploy and run**.

MotionModule validates the folder, keeps the old copy under `~/MotionModule/backups`, and restarts on
the new one. To take this folder from GitHub instead, rerun the one-line installer with
`--robot-only`.

Never move a pin to fix a direction. Change `mixer.py`, or a motor's `inverted` value in `hardware.py`.
