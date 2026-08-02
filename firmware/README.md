# Firmware

These sketches preserve the working builds and the major test iterations from the original [`AloeVeraZ/self-balance-robot`](https://github.com/AloeVeraZ/self-balance-robot) repository.

## Controller sketches

| Sketch | Target | Notes |
|---|---|---|
| `arduino-nano/arduino-nano.ino` | Arduino Nano | MPU6050 complementary filter, PID balance control, dual motor output, and fall cutoff |
| `raspberry-pi-pico/raspberry-pi-pico.ino` | Raspberry Pi Pico | RP2040/Mbed I2C setup, MPU6050 calibration, PID control, and asymmetric correction experiment |

## Development sketches

| Sketch | Purpose |
|---|---|
| `experiments/motor-test/motor-test.ino` | Forward, stop, and reverse test for both motors |
| `experiments/imu-serial/imu-serial.ino` | MPU6050 roll, pitch, and yaw output for the Serial Plotter |
| `experiments/pid-early/pid-early.ino` | Early full balancing-controller iteration |
| `experiments/pid-alternate/pid-alternate.ino` | Alternate fixed-rate PID and gyro-calibration iteration |

Each `.ino` file is inside a same-named sketch folder so it can be opened directly in the Arduino IDE. Experimental files are retained for learning and comparison; they are not presented as production-ready firmware.

## Before uploading

- Confirm the board, motor-driver, and MPU6050 pinout against the sketch.
- Test motor direction with the chassis supported and wheels clear of the workbench.
- Calibrate the sensor while the robot is still.
- Start with conservative power limits.
- Retune the balance angle and PID gains after any mechanical, battery, wheel, or motor change.

