<p align="center">
  <a href="https://angelojamesny.com/selfbalancing"><img alt="Project status: complete" src="https://img.shields.io/badge/status-complete-16c784?style=flat-square"></a>
  <img alt="Control: PID" src="https://img.shields.io/badge/control-PID-7c5cff?style=flat-square">
  <img alt="Sensor: MPU6050" src="https://img.shields.io/badge/sensor-MPU6050-00a8e8?style=flat-square">
  <a href="../LICENSE.md"><img alt="License: CC BY 4.0" src="https://img.shields.io/badge/license-CC%20BY%204.0-f1c40f?style=flat-square"></a>
</p>

# Self Balancing Robot

This is a two wheel robot that uses a sensor and motors to stay standing. We built it to learn how PID control works and to practice robotics.

The project uses common parts, so it was easier to test and change as we worked on it.

## Main parts

| Part | What we used |
|---|---|
| Control | PID balance control |
| Sensor | MPU6050 motion sensor |
| Controllers | Arduino Nano, Arduino Uno, and Raspberry Pi Pico |
| Motors | Two DC motors and a motor driver |
| Frame | Custom 3D printed body and regular hardware |
| Status | Finished, with early code kept for reference |

## How it works

The MPU6050 checks which way the robot is leaning. The controller uses that information to decide how fast and which way the wheels should move. Moving the wheels under the robot helps it stay upright.

## Versions

* **Version 1: First prototype.** We used an Elegoo car frame to test the balancing code and see how the robot reacted.
* **Version 2: Printed body.** We made a smaller custom frame and spent more time adjusting the PID values.
* **Version 3: Pico controller.** We used a Raspberry Pi Pico to make the controls react faster and move more smoothly.

The folder also includes Arduino Nano and Arduino Uno code from other tests.

## Project files

The `cad` folder has the 3D models. The `firmware` folder has the main Arduino and Pico code, plus a few experiments. Read the [CAD guide](cad/README.md) before printing and the [firmware guide](firmware/README.md) before uploading code.

## CAD note

> [!WARNING]
> The final CAD model is only a general reference. It is not an exact copy of every part on the real robot.

Some wheels, batteries, holders, and other parts are simple placeholders. Measure your own parts before printing or buying anything. Check the holes, wheel hubs, battery space, board space, and screws.

## Uploading the code

1. Install the Arduino IDE.
2. Install the board support for your controller.
3. Open the `.ino` file from its folder.
4. Check every wire and pin before connecting motor power.
5. Keep the wheels off the table for the first test.
6. Adjust the target angle and PID values for your robot.

> [!CAUTION]
> The robot can move quickly or fall over. Keep your fingers away from the wheels and test it in a clear area.

## Results

* The robot was able to balance and move using sensor feedback.
* We tested the same basic idea with different controllers.
* Adjusting the PID values made the balancing smoother.
* Reusing parts helped keep the project affordable.

## Links

* [Self balancing robot project page](https://angelojamesny.com/selfbalancing)
* [Club projects page](https://angelojamesny.com/club-projects)
* [Repository home](../README.md)
* [Angelo's GitHub profile](https://github.com/TheTheAloe)

## License

The original project work is available under [CC BY 4.0](../LICENSE.md). You can share or change it as long as you credit Angelo Demetroulakos, link to the license, and say what you changed.

Parts made by other companies or creators still follow their original rules.
