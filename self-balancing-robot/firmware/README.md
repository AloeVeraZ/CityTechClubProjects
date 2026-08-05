# Firmware

This folder has the main robot code and a few early tests.

## Main code

| Sketch | Board | What it does |
|---|---|---|
| `arduino-nano/arduino-nano.ino` | Arduino Nano | Reads the sensor, runs PID control, and moves both motors |
| `raspberry-pi-pico/raspberry-pi-pico.ino` | Raspberry Pi Pico | Calibrates the sensor, runs PID control, and tests motor correction |

## Test code

| Sketch | What it tests |
|---|---|
| `experiments/motor-test/motor-test.ino` | Runs both motors forward and backward |
| `experiments/imu-serial/imu-serial.ino` | Shows the sensor readings in the Serial Plotter |
| `experiments/pid-early/pid-early.ino` | An early version of the balancing code |
| `experiments/pid-alternate/pid-alternate.ino` | Another PID and sensor test |

Each `.ino` file is inside its own sketch folder so it can open in the Arduino IDE. The experiment files are included to show some of the testing process.

## Before uploading

* Check the board, motor driver, sensor, and pin numbers.
* Test the motor direction with the wheels off the table.
* Keep the sensor still while it calibrates.
* Start with a low motor power limit.
* Adjust the balance angle and PID values for your own robot.
