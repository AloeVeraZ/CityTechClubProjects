# Self Balancing Robot Firmware

### Primary balance controllers and the experiments used to bring them up

<img alt="Language: Arduino C++" src="https://img.shields.io/badge/language-Arduino%20C%2B%2B-111111?style=flat-square&logo=arduino&logoColor=white"> <img alt="Control: PID" src="https://img.shields.io/badge/control-PID-3f3f46?style=flat-square"> <img alt="Sensor: MPU6050" src="https://img.shields.io/badge/sensor-MPU6050-6b7280?style=flat-square">

[Project overview](../README.md) · [Main code](#main-code) · [Experiments](#test-code) · [CAD collection](../cad/)

---

## Main Code

| Controller | Sketch | Purpose |
| --- | --- | --- |
| Arduino Nano | [`arduino-nano/arduino-nano.ino`](arduino-nano/arduino-nano.ino) | Read the IMU, run PID control, and command both motors |
| Raspberry Pi Pico | [`raspberry-pi-pico/raspberry-pi-pico.ino`](raspberry-pi-pico/raspberry-pi-pico.ino) | Calibrate the sensor, run the balance loop, and test motor correction |

## Test Code

| Experiment | Sketch | What it isolates |
| --- | --- | --- |
| 01 / Motor test | [`experiments/motor-test/motor-test.ino`](experiments/motor-test/motor-test.ino) | Forward and reverse motor direction |
| 02 / IMU serial | [`experiments/imu-serial/imu-serial.ino`](experiments/imu-serial/imu-serial.ino) | Sensor readings in the Serial Plotter |
| 03 / Early PID | [`experiments/pid-early/pid-early.ino`](experiments/pid-early/pid-early.ino) | First balance-control implementation |
| 04 / Alternate PID | [`experiments/pid-alternate/pid-alternate.ino`](experiments/pid-alternate/pid-alternate.ino) | Second sensor and PID experiment |

Each `.ino` file is in its own Arduino sketch folder so it can be opened and
uploaded directly from the Arduino IDE.

## Before Uploading

> [!CAUTION]
> Keep the wheels raised for the first test. A reversed motor or unstable PID
> setting can move the robot immediately after startup.

- Confirm the selected board, motor driver, IMU, and pin numbers.
- Verify motor direction before enabling the balance loop.
- Keep the sensor still while it calibrates.
- Begin with a low motor-power limit.
- Tune the balance angle and PID values for the physical robot.

---

Return to the [Self Balancing Robot project](../README.md) or the
[club project collection](../../README.md).
