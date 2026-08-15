# 3TSahur Ramp Actuators

### Two direct-GPIO servos with fixed, mirrored open and closed positions

<img alt="Timing: pigpio" src="https://img.shields.io/badge/timing-pigpio-00979d?style=flat-square"> <img alt="Positions: 0 and 120 degrees" src="https://img.shields.io/badge/positions-0%C2%B0%20%2F%20120%C2%B0-f39c12?style=flat-square">

[Project overview](../README.md) · [Wiring](WIRING.md) · [Setup](SETUP.md) · [Actuator code](../robot_server/actuators.py)

---

The Logitech camera is fixed and has no actuator controls. Two hobby servos
operate the robot's ramp directly from Raspberry Pi GPIO signals.

## 01 / Pinout

| Servo | Signal | Power | Ground |
| --- | --- | --- | --- |
| Ramp Servo 1 | BCM GPIO12, physical pin 32 | Buck +5 V | Buck ground |
| Ramp Servo 2 | BCM GPIO18, physical pin 12 | Buck +5 V | Buck ground |

Connect the buck-converter ground to a Pi ground such as physical pin 6 or 14.
Typical servo colors are red for power, brown/black for ground, and
orange/white/yellow for signal; verify the exact servo before applying power.

> [!CAUTION]
> GPIO12 and GPIO18 are 3.3 V signal pins. Never connect a servo's red 5 V wire
> to either signal pin.

## 02 / Positions and Controls

| Position | Servo 1 | Servo 2 |
| --- | ---: | ---: |
| Closed / startup | 0° logical | 0° logical |
| Open | 120° logical | 120° logical |

Servo 2 on physical pin 12 is mirrored in software: logical 0° uses its 120°
electrical position, while logical 120° uses its 0° electrical position. Servo
1 retains normal direction.

Use **Open ramp** / **Close ramp** in the dashboard or press `R`. There is no
intermediate position and no camera movement mode.

## 03 / Runtime and Configuration

Persistent settings in `/etc/stem-research-academy/config.env`:

```text
RAMP_SERVO_0_GPIO_BCM=12
RAMP_SERVO_1_GPIO_BCM=18
RAMP_SERVO_0_REVERSED=0
RAMP_SERVO_1_REVERSED=1
RAMP_SERVO_MIN_PULSE_US=1000
RAMP_SERVO_MAX_PULSE_US=2000
```

| Servo state | Normal servo pulse | Reversed servo pulse |
| --- | ---: | ---: |
| Closed | 1000 µs | 1667 µs |
| Open | 1667 µs | 1000 µs |

The installer starts `pigpiod` before the dashboard. `pigpio` continuously
holds the selected pulse, while the server serializes commands and suppresses
duplicate writes.

| API | Request |
| --- | --- |
| `GET /api/status` | Read actuator state and availability |
| `POST /api/actuators/ramp` | `{"state":"closed"}` or `{"state":"open"}` |

## 04 / Buck-Converter Checks

1. Set the converter to 5.0 V before connecting either servo.
2. Confirm its continuous and peak current ratings cover both servos together.
3. Disconnect drivetrain power and remove the ramp linkages for the first test.
4. If jitter remains, verify the buck-to-Pi common ground.
5. Measure voltage while both servos move to identify supply sag.

A noisy supply or mechanically stalled servo cannot be corrected in software.

---

Return to the [STEM Research Academy project](../README.md).
