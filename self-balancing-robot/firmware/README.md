<div align="center">

# Self Balancing Robot Firmware

### Arduino C++ and Raspberry Pi Pico PID balance routines and bring-up experiments

[![Language](https://img.shields.io/badge/Language-Arduino_C%2B%2B-6f42c1?style=flat-square&logo=arduino&logoColor=white)](https://www.arduino.cc/)
[![Control](https://img.shields.io/badge/Control-PID_Loop-0a7f5a?style=flat-square)](#main-code)
[![Sensor](https://img.shields.io/badge/Sensor-MPU6050_I2C-f57c00?style=flat-square)](#test-code)
[![License](https://img.shields.io/badge/License-CC_BY_4.0-0078d4?style=flat-square)](../../LICENSE.md)
[![Parent](https://img.shields.io/badge/Project-Self_Balancing_Robot-111111?style=flat-square)](../)

This directory contains the primary closed-loop balance control firmware alongside modular bring-up sketches for sensor calibration and motor verification.

[Main Code](#main-code) | [Test Code](#test-code) | [Commissioning & Safety](#commissioning--safety) | [Back to Self Balancing Robot](../)

</div>

---

## Main Code

| Controller | Sketch Path | Architecture & Function |
| --- | --- | --- |
| Arduino Nano / Uno | [`arduino-nano/arduino-nano.ino`](arduino-nano/arduino-nano.ino) | ATmega328P 8-bit PID balance loop with complementary filtered IMU telemetry |
| Raspberry Pi Pico | [`raspberry-pi-pico/raspberry-pi-pico.ino`](raspberry-pi-pico/raspberry-pi-pico.ino) | RP2040 32-bit dual-core high-frequency PID balance loop |

## Test Code

| Experiment | Sketch Path | Isolated Subsystem |
| --- | --- | --- |
| 01 / Motor test | [`experiments/motor-test/motor-test.ino`](experiments/motor-test/motor-test.ino) | Verifies left/right forward and reverse wiring polarity |
| 02 / IMU serial | [`experiments/imu-serial/imu-serial.ino`](experiments/imu-serial/imu-serial.ino) | Streams real-time raw accelerometer and gyro data to Arduino Serial Plotter |
| 03 / Early PID | [`experiments/pid-early/pid-early.ino`](experiments/pid-early/pid-early.ino) | Early proportional-only balance response baseline |
| 04 / Alternate PID | [`experiments/pid-alternate/pid-alternate.ino`](experiments/pid-alternate/pid-alternate.ino) | Alternative integral anti-windup implementation |

Each `.ino` sketch is isolated in its own directory for one-click upload in Arduino IDE.

## Commissioning & Safety

> [!CAUTION]
> Always suspend the wheels above the work surface before powering the motor driver for initial testing. Incorrect motor polarity will cause runaway acceleration.

1. **Verify IMU Polarity:** Ensure tilting the robot forward registers a positive angle, and tilting backward registers a negative angle.
2. **Verify Motor Reaction:** When tilting forward, the wheels must spin forward to drive underneath the robot.
3. **Calibrate Gyro Bias:** Allow the microcontroller 3–5 seconds of complete stillness upon boot to zero the gyroscope offsets.

---

<div align="center">

Designed and documented for **[Self Balancing Robot](../)** · **[City Tech Robotics](../../)**

</div>
