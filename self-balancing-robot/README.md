<div align="center">

# Self Balancing Robot

### An educational platform for learning sensors, feedback control, and DC motors

[![Status](https://img.shields.io/badge/Status-Complete-22c55e?style=flat-square)](#overview)
[![Control](https://img.shields.io/badge/Control-PID-6f42c1?style=flat-square)](#how-it-works)
[![Sensor](https://img.shields.io/badge/Sensor-MPU6050-0a7f5a?style=flat-square)](#how-it-works)
[![Files](https://img.shields.io/badge/Files-CAD_%2B_Firmware-2563eb?style=flat-square)](#repository-contents)

<strong>Quick navigation:</strong><br>
[Overview](#overview) | [What Students Learn](#what-students-learn) | [Development](#development) | [How It Works](#how-it-works) | [Repository Contents](#repository-contents) | [Back to Club](../)

</div>

---

## Overview

The Self Balancing Robot was built as a practical introduction to closed-loop control. An MPU6050 measures the robot's tilt, a controller calculates how far it is from its balance point, and two geared DC motors move the wheels underneath the center of mass before the robot falls.

Three versions were used to compare controller hardware, chassis layouts, and PID settings. The project is complete, but the repository keeps the successful firmware and earlier experiments so students can see how the control system developed.

| System | What it uses |
| --- | --- |
| Motion | Two geared DC motors |
| Sensor | MPU6050 accelerometer and gyroscope |
| Controllers | Arduino Nano, Arduino Uno, and Raspberry Pi Pico |
| Motor control | Dual H-bridge driver with PWM speed and direction control |
| Mechanical design | Reused prototype chassis followed by custom 3D-printed bodies |
| Main concept | PID feedback and complementary sensor filtering |

## What students learn

| Topic | Practical lesson |
| --- | --- |
| Sensors | Read accelerometer and gyroscope data over I²C. |
| Filtering | Combine fast gyro readings with a stable accelerometer angle. |
| Feedback control | Use proportional, integral, and derivative terms to correct tilt. |
| DC motors | Control speed and direction through an H-bridge instead of driving motors directly from a microcontroller. |
| Electronics | Connect an IMU, controller, motor driver, motors, and battery with a shared ground. |
| Mechanical design | See how wheel size, frame stiffness, battery position, and center of gravity change the same control code. |

## Development

| Version | Build | What it taught | Video |
| --- | --- | --- | --- |
| 01 | Modified car chassis | Verified sensor orientation, motor direction, and the first balance corrections. | [Watch](https://www.youtube.com/watch?v=-mdpzGmiDxs) |
| 02 | Custom 3D-printed body | Improved component placement, center of gravity, and mechanical stability. | [Watch](https://www.youtube.com/watch?v=whE-oMi1N7U) |
| 03 | Raspberry Pi Pico controller | Tested faster loop timing and smoother motor response. | [Watch](https://www.youtube.com/watch?v=JzyDli07yCE) |

## How it works

| Step | Process |
| --- | --- |
| 1 | The MPU6050 measures acceleration and angular velocity. |
| 2 | A complementary filter estimates the robot's pitch angle. |
| 3 | The PID loop compares the measured angle with the target balance angle. |
| 4 | The H-bridge drives both motors forward or backward with the required PWM output. |
| 5 | Wheel motion moves the contact point back under the robot, and the loop repeats. |

## Repository contents

```text
self-balancing-robot/
|-- cad/
|   |-- pico-v1/            # Pico Fusion archive and STEP export
|   |-- arduino-uno-v2/     # Arduino Uno Fusion archive and STEP export
|   `-- final-assembly/     # Final reference assembly
|-- firmware/
|   |-- arduino-nano/       # Arduino Nano balance controller
|   |-- raspberry-pi-pico/  # Pico balance controller
|   `-- experiments/        # Motor, IMU, and earlier PID tests
`-- README.md
```

### CAD

The [`cad/`](cad/) folder contains editable Autodesk Fusion files and neutral STEP exports for the Pico, Arduino Uno, and final reference assemblies.

> [!IMPORTANT]
> The final CAD is a layout reference, not an exact digital twin of the finished robot. Some purchased wheels, the battery, an Arduino holder, and other off-the-shelf components use simplified or placeholder geometry. Measure the exact hardware before printing replacement parts.

### Firmware

The [`firmware/`](firmware/) folder contains the primary Arduino Nano and Raspberry Pi Pico balance programs plus motor, IMU, and PID experiments. Pin assignments, motor polarity, target angle, and PID values must be checked against the physical robot before use.

## Safety

> [!CAUTION]
> A balancing robot can tip or accelerate suddenly while PID gains are being tuned. Raise the chassis so the wheels are clear during the first test, keep hands away from moving parts, and verify the fall-angle motor cutoff before free-standing operation.

---

[Back to the City Tech AI & Automation Club](../)
