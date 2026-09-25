# 3TSahur Wiring Reference

### MotionModule harness: four motor ports, one PCA9685 servo board, one BNO055 IMU

<img alt="Drive: 4 mecanum motors" src="https://img.shields.io/badge/drive-4%20mecanum%20motors-6f42c1?style=flat-square"> <img alt="Servos: PCA9685" src="https://img.shields.io/badge/servos-PCA9685%20I2C-00979d?style=flat-square"> <img alt="IMU: BNO055" src="https://img.shields.io/badge/IMU-BNO055-f39c12?style=flat-square">

[Project overview](../README.md) · [Setup](SETUP.md) · [Ramp details](3TSAHUR_AUXILIARY_ACTUATORS.md) · [Pin definitions](../robot_server/hardware.py)

---

3TSahur uses the [MotionModule](https://github.com/AloeVeraZ/MotionModule)
reference wiring, cut down to what this robot has: **Drivers 1 and 2** (four
motor ports), the **PCA9685 servo board**, and a **BNO055 IMU**. MotionModule's
Drivers 3 and 4 are not fitted. Nothing is selected in software: wire it as
below and it works.

Which port drives which wheel is **not** part of the wiring. Plug the four
wheels into any of the four ports, then set the mapping and any inversions on
the Debug page (`http://10.42.0.1/debug`). All numbers below are BCM GPIO /
physical header pin.

## 01 / Motor ports (two dual H-bridge boards)

Each driver's control header reads `IN1 IN2 IN3 IN4 GND`. IN1/IN2 drive output
A; IN3/IN4 drive output B. The forward wire goes to the first input of each pair.

| Port | Driver · output | Forward input | Reverse input | Driver ground | Default wheel |
| ---: | --- | --- | --- | ---: | --- |
| 1 | Driver 1 · A | pin 37 / GPIO26 → IN1 | pin 35 / GPIO19 → IN2 | pin 39 | Front left |
| 2 | Driver 1 · B | pin 33 / GPIO13 → IN3 | pin 31 / GPIO6 → IN4 | pin 39 | Rear left |
| 3 | Driver 2 · A | pin 40 / GPIO21 → IN1 | pin 38 / GPIO20 → IN2 | pin 34 | Front right |
| 4 | Driver 2 · B | pin 36 / GPIO16 → IN3 | pin 32 / GPIO12 → IN4 | pin 34 | Rear right |

Each driver is one short bundle: Driver 1 is pins 31–39 down the left column,
Driver 2 is pins 32–40 down the right column. A wheel that spins the wrong way
is fixed with that port's **Invert** switch on the Debug page, never by moving
wires.

## 02 / Servo board (PCA9685)

Five wires in one run down the top of the left column:

| Pi header | PCA9685 |
| --- | --- |
| pin 1 / 3.3 V | VCC (chip logic only) |
| pin 3 / GPIO2 | SDA |
| pin 5 / GPIO3 | SCL |
| pin 7 / GPIO4 | OE (output enable, active low) |
| pin 9 / GND | GND |

The two ramp servos plug into the board's outputs (channels 0 and 1 by
default; change them on the Debug page). Servo **V+** comes from its own
regulated 5–6 V supply on the screw terminal. Never connect the board's V+
header pin to the Pi.

## 03 / IMU (BNO055)

The BNO055 shares the servo board's I2C bus. Chain SDA/SCL from the PCA9685
side header (or tee them at pins 3 and 5).

| Pi header | BNO055 |
| --- | --- |
| pin 17 / 3.3 V | VIN |
| pin 6 / GND | GND |
| pin 3 / GPIO2 | SDA |
| pin 5 / GPIO3 | SCL |

Leave ADR low for address `0x28`. Mount the board flat, as close to the
robot's centre as practical.

## 04 / Pins that stay free

UART (pins 8, 10), the ID EEPROM (27, 28), and MotionModule's Driver 3 and 4
pins (13, 15, 16, 18, 21, 23, 24, 26) are unused. GPIO12 and GPIO18 no longer
carry servo signals: GPIO12 is now port 4's reverse input.

## Power and First Test

> [!CAUTION]
> Motor battery power goes only to the drivers' power terminals, and servo V+
> only to its regulator. Neither ever touches a Pi header pin.

1. Set the servo regulator to 5.0 V before connecting the servos.
2. Join the motor, servo, and Pi grounds at one common point.
3. Install the correct fuse and an accessible physical power switch.
4. Raise every wheel, open **Debug**, and hold **Run** on each port at low power.
5. Assign each port to its wheel, tick **Invert** where needed, and **Save**.
6. Use the **wheel check** buttons: each wheel should roll the robot forward.

---

Return to the [STEM Research Academy project](../README.md).
