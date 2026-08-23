<div align="center">

# Self Balancing Robot

### Three controller generations of sensor feedback, PID tuning, and mechanical iteration

[![Status](https://img.shields.io/badge/Status-Complete-22c55e?style=flat-square)](#project-overview)
[![Control](https://img.shields.io/badge/Control-PID_Balance_Loop-6f42c1?style=flat-square)](#control-system)
[![Sensor](https://img.shields.io/badge/Sensor-MPU6050_IMU-0a7f5a?style=flat-square)](#control-system)
[![CAD](https://img.shields.io/badge/CAD-Fusion_360_%2B_STEP-f57c00?style=flat-square)](cad/)
[![Firmware](https://img.shields.io/badge/Firmware-Arduino_%2B_Pico-0078d4?style=flat-square)](firmware/)
[![License](https://img.shields.io/badge/License-CC_BY_4.0-111111?style=flat-square)](../LICENSE.md)

<picture>
  <img src="https://assets.zyrosite.com/cdn-cgi/image/format=auto,w=1200,h=675,fit=crop/A85rnnzK6qs5qxKB/img_20260514_162917008-GuGOQgTeFhg8mCtz.jpg" alt="Self balancing robot" width="820" draggable="false">
</picture>

A two-wheel robot that uses an MPU6050 and a PID loop to catch itself before it falls.

<strong>Quick navigation:</strong><br>
[Project Overview](#project-overview) | [Development Path](#development-path) | [CAD Collection](cad/) | [Firmware](firmware/) | [Build Videos](#build-videos) | [Back to Club](../)

</div>

---

## Project Overview

I used this robot to learn IMU filtering, PID tuning, and how weight placement changes the result. It went through three controller and frame revisions before reaching the final version.

| System | Implementation |
| --- | --- |
| Dynamic control | Closed-loop PID balance algorithm |
| Inertial sensing | MPU6050 6-DOF IMU (Accelerometer + Gyroscope) |
| Microcontrollers | Arduino Nano, Arduino Uno, and Raspberry Pi Pico (RP2040) |
| Actuation | Twin geared DC motors with dual H-bridge motor driver |
| Chassis structure | Custom 3D-printed tiered body with standard M3/M4 hardware |
| Project repository | Complete CAD models, active firmware sketches, and diagnostic test code |

## Development Path

### 01 / First Prototype (Car Chassis)

[![Play Self balancing robot first prototype video](https://i.ytimg.com/vi_webp/-mdpzGmiDxs/hqdefault.webp)](https://www.youtube.com/watch?v=-mdpzGmiDxs)

> **Click the preview to watch the first prototype.** Validated the MPU6050 sensor orientation and initial PID motor correction on a modified car chassis.

| Stage | Configuration & Result |
| --- | --- |
| Frame | Repurposed commercial car chassis |
| Objective | Sensor calibration and sign convention verification for motor drive |
| Outcome | Confirmed foundational closed-loop stabilization logic |

---

### 02 / Custom 3D-Printed Body

[![Play Self balancing robot printed body video](https://i.ytimg.com/vi_webp/whE-oMi1N7U/hqdefault.webp)](https://www.youtube.com/watch?v=whE-oMi1N7U)

> **Click the preview to watch the custom printed body.** Refined component placement, center of gravity, and wheel track width.

| Stage | Configuration & Result |
| --- | --- |
| Frame | Custom tiered 3D-printed modular chassis |
| Objective | Center of gravity optimization and battery isolation |
| Outcome | Dramatically reduced mechanical vibration and stabilized sensor readings |

---

### 03 / Raspberry Pi Pico Controller

[![Play Self balancing robot Pico controller video](https://i.ytimg.com/vi_webp/JzyDli07yCE/hqdefault.webp)](https://www.youtube.com/watch?v=JzyDli07yCE)

> **Click the preview to watch the Raspberry Pi Pico version.** Faster loop timing and responsive motor control.

| Stage | Configuration & Result |
| --- | --- |
| Controller | Raspberry Pi Pico (RP2040 dual-core @ 133 MHz) |
| Sensor | MPU6050 over high-speed I²C |
| Outcome | Higher loop frequencies produced smoother recovery and superior disturbance rejection |

## Control System

The MPU6050 measures pitch angle and angular velocity. The onboard controller executes a PID algorithm to compute corrective motor voltage, driving the wheel contact patch beneath the center of gravity.

<table>
  <tr>
    <td align="center"><strong>MPU6050</strong><br>Tilt and rate</td>
    <td align="center">&rarr;</td>
    <td align="center"><strong>PID Controller</strong></td>
    <td align="center">&rarr;</td>
    <td align="center"><strong>H-Bridge Driver</strong></td>
    <td align="center">&rarr;</td>
    <td align="center"><strong>Left and Right Motors</strong></td>
    <td align="center">&rarr;</td>
    <td align="center"><strong>Chassis Correction</strong></td>
    <td align="center">&rarr; feedback</td>
    <td align="center"><strong>MPU6050</strong></td>
  </tr>
</table>

## Project Files

### CAD Collection

The [`cad/`](cad/) directory contains editable Autodesk Fusion files (`.f3d`, `.f3z`) and vendor-neutral STEP exports (`.step`).

| Revision | Fusion Archive | STEP Model | Purpose |
| --- | --- | --- | --- |
| 01 / Pico V1 | [`cad/pico-v1/pico-cad-v1.f3z`](cad/pico-v1/pico-cad-v1.f3z) | [`cad/pico-v1/pico-cad-v1.step`](cad/pico-v1/pico-cad-v1.step) | Raspberry Pi Pico chassis |
| 02 / Arduino Uno V2 | [`cad/arduino-uno-v2/arduino-uno-cad-v2.f3z`](cad/arduino-uno-v2/arduino-uno-cad-v2.f3z) | [`cad/arduino-uno-v2/arduino-uno-cad-v2.step`](cad/arduino-uno-v2/arduino-uno-cad-v2.step) | Arduino Uno chassis |
| 03 / Final reference | [`cad/final-assembly/final-cad.f3d`](cad/final-assembly/final-cad.f3d) | [`cad/final-assembly/final-cad.step`](cad/final-assembly/final-cad.step) | Completed master assembly |

[Browse CAD Collection](cad/) | [Read CAD Guide](cad/README.md)

### Firmware Collection

The [`firmware/`](firmware/) directory contains primary balance controllers along with diagnostic test sketches.

| Directory | Controller / Target | Function |
| --- | --- | --- |
| [`arduino-nano/`](firmware/arduino-nano/) | Arduino Nano | Primary 8-bit PID balance sketch |
| [`raspberry-pi-pico/`](firmware/raspberry-pi-pico/) | Raspberry Pi Pico (RP2040) | 32-bit high-rate PID balance sketch |
| [`experiments/motor-test/`](firmware/experiments/motor-test/) | Diagnostic | Motor direction and PWM linearity test |
| [`experiments/imu-serial/`](firmware/experiments/imu-serial/) | Diagnostic | MPU6050 raw and filtered telemetry |
| [`experiments/pid-early/`](firmware/experiments/pid-early/) | Diagnostic | Early proportional-only test loop |

[Browse Firmware Collection](firmware/) | [Read Firmware Guide](firmware/README.md)

## Build Videos

| Prototype 1 (Car Chassis) | Prototype 2 (Printed Body) | Final Version (Pico Controller) |
| :---: | :---: | :---: |
| [![Version 1](https://i.ytimg.com/vi_webp/-mdpzGmiDxs/hqdefault.webp)](https://www.youtube.com/watch?v=-mdpzGmiDxs) | [![Version 2](https://i.ytimg.com/vi_webp/whE-oMi1N7U/hqdefault.webp)](https://www.youtube.com/watch?v=whE-oMi1N7U) | [![Version 3](https://i.ytimg.com/vi_webp/JzyDli07yCE/hqdefault.webp)](https://www.youtube.com/watch?v=JzyDli07yCE) |

## Safety & Commissioning

> [!CAUTION]
> The robot can tip rapidly or accelerate abruptly when tuning PID gains. Perform initial bring-up on a raised stand and keep hands clear of the spinning wheels.

1. **Raised Bench Test:** Keep wheels suspended off the table during first upload to verify motor polarity against tilt direction.
2. **Sensor Calibration:** Keep the robot stationary during startup gyro bias calculation.
3. **Gain Tuning:** Begin with low $K_p$, zero $K_d$, and zero $K_i$. Increase $K_p$ until oscillation begins, then introduce $K_d$ to dampen movement.
