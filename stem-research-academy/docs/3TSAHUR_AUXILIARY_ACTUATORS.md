# 3TSahur Ramp Actuators

### Two servos on the PCA9685 board with fixed, mirrored open and closed positions

<img alt="Driver: PCA9685" src="https://img.shields.io/badge/driver-PCA9685-00979d?style=flat-square"> <img alt="Positions: 0 and 120 degrees" src="https://img.shields.io/badge/positions-0%C2%B0%20%2F%20120%C2%B0-f39c12?style=flat-square">

[Project overview](../README.md) · [Wiring](WIRING.md) · [Setup](SETUP.md) · [Robot code](../robot_server/robot.py)

---

The two ramp servos now plug into the MotionModule PCA9685 servo board instead
of direct Pi GPIO, so `pigpio` is no longer used. The board holds each pulse in
hardware, and its OE pin (GPIO4) can cut every servo output at once.

## 01 / Connections

| Servo | Default board channel | Power |
| --- | ---: | --- |
| Ramp servo A | 0 | Board V+ (regulated 5 V) |
| Ramp servo B | 1, mirrored | Board V+ (regulated 5 V) |

Change either channel, or which one is mirrored, on the Debug page. Both
servos always move together.

## 02 / Positions and Controls

| Position | Servo A | Servo B (mirrored) |
| --- | ---: | ---: |
| Closed / startup | 0° · 1000 µs | 120° · 1667 µs |
| Open | 120° · 1667 µs | 0° · 1000 µs |

These match the original robot: 0–180° maps onto 1000–2000 µs. The closed and
open angles and the pulse range are editable on the Debug page (within the
board's 500–2500 µs safety envelope).

| Control | Effect |
| --- | --- |
| **Open ramp** / **Close ramp**, `R`, gamepad Y / A | Move both servos (robot must be enabled) |
| `Space`, Disable, losing focus | Drive stops; the ramp keeps holding |
| `Esc`, **Stop all outputs** | Drive stops, servos released, OE cuts all outputs |

After an emergency stop the next ramp command re-enables the outputs.

## 03 / API

| API | Request |
| --- | --- |
| `GET /api/status` | `robot.ramp` shows state, holding, and each servo's pulse |
| `POST /api/ramp` | `{"state":"closed"}` or `{"state":"open"}` |

## 04 / Supply Checks

1. Set the regulator to 5.0 V before connecting either servo.
2. Confirm its continuous and peak current ratings cover both servos together.
3. Remove the ramp linkages for the first test and use Debug → **Test open**.
4. If a servo jitters, check the servo supply ground to the common ground point.

---

Return to the [STEM Research Academy project](../README.md).
