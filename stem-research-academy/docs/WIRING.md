# 3TSahur Wiring Reference

### Mecanum motor-driver mapping, ramp-servo signals, and power boundaries

[![Drive](https://img.shields.io/badge/drive-4%20mecanum%20motors-6f42c1?style=flat-square)](#01--mecanum-drivetrain)
[![Motor Power](https://img.shields.io/badge/motor%20power-external%20supply-f39c12?style=flat-square)](#power-and-first-test)
[![Servo Power](https://img.shields.io/badge/servo%20power-regulated%205%20V-00979d?style=flat-square)](#02--direct-ramp-servos)

[Project overview](../README.md) · [Setup](SETUP.md) · [Ramp details](3TSAHUR_AUXILIARY_ACTUATORS.md) · [Motor code](../robot_server/motor.py)

---

## 01 / Mecanum Drivetrain

The chassis uses two DC 3–18 V, 10 A dual H-bridge motor drivers. All numbers
below are Raspberry Pi **BCM GPIO** numbers and intentionally retain the tested
mecanum assignment.

| Wheel | Driver input pair | Positive PWM leg | Negative PWM leg |
| --- | --- | ---: | ---: |
| Front left | Driver 1 IN1 / IN2 | GPIO 5 | GPIO 6 |
| Rear left | Driver 1 IN3 / IN4 | GPIO 19 | GPIO 16 |
| Front right | Driver 2 IN1 / IN2 | GPIO 20 | GPIO 21 |
| Rear right | Driver 2 IN3 / IN4 | GPIO 26 | GPIO 13 |

This mapping is implemented in [`robot_server/motor.py`](../robot_server/motor.py)
and checked by [`tests/test_motor.py`](../tests/test_motor.py).

The installed chassis uses inverted longitudinal polarity: `W` drives GPIO 6,
16, 21, and 13, while `S` drives GPIO 5, 19, 20, and 26. Strafe polarity is
unchanged. `Q` and `E` rotate about the robot center with all four wheels at
75% magnitude.

| Rotation | Active PWM legs |
| --- | --- |
| `E` | FL GPIO6, FR GPIO21, RL GPIO19, RR GPIO26 |
| `Q` | Opposite leg of each motor pair |

> [!WARNING]
> Never connect one GPIO output to more than one driver input. If one physical
> wheel is reversed, swap only that motor's leads or only its `MotorPins` pair.

## 02 / Direct Ramp Servos

The two ramp servos use `pigpio`-timed signals from otherwise unused Pi pins.
The code uses BCM numbering; physical header numbers are included below.

| Servo | Wire | Raspberry Pi connection |
| --- | --- | --- |
| Ramp Servo 1 | Signal | BCM GPIO12, physical pin 32 |
| Ramp Servo 1 | +5 V | Buck-converter +5 V output |
| Ramp Servo 1 | Ground | Buck-converter ground |
| Ramp Servo 2 | Signal | BCM GPIO18, physical pin 12 |
| Ramp Servo 2 | +5 V | Buck-converter +5 V output |
| Ramp Servo 2 | Ground | Buck-converter ground |
| Common reference | Ground jumper | Buck ground to Pi ground, physical pin 6 or 14 |

GPIO12 and GPIO18 are 3.3 V signal outputs. Never connect a servo's red 5 V
wire to either GPIO signal pin.

| Logical position | Servo 1 | Servo 2 |
| --- | ---: | ---: |
| Closed / startup | 0° | 0° |
| Open | 120° | 120° |

Servo 2 on physical pin 12 is reversed in software so the mechanism moves in
the correct direction. Servo 1 on physical pin 32 keeps the normal direction.

## Power and First Test

> [!CAUTION]
> Power the motors from their rated external supply and the servos from a
> regulated 5 V supply. Do not use the Raspberry Pi logic rail as the motor or
> servo power source.

1. Set the servo buck converter to 5.0 V before connecting the servos.
2. Connect all required logic, motor, servo, and Pi grounds.
3. Install the correct fuse and an accessible physical power switch.
4. Raise every wheel before applying motor power.
5. Test one direction at a time at low speed.
6. Confirm the common ground first if the servos jitter.

---

Return to the [STEM Research Academy project](../README.md).
