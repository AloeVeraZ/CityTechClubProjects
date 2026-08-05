# Crab Crawler Walking Robot

<p>
  <a href="https://angelojamesny.com/crabcrawler"><img alt="Project page" src="https://img.shields.io/badge/project-walking%20robot-6f42c1?style=flat-square"></a>
  <img alt="Controller: ESP32 CAM" src="https://img.shields.io/badge/controller-ESP32%20CAM-00979d?style=flat-square">
  <img alt="Motion: servo walking" src="https://img.shields.io/badge/motion-servo%20walking-f39c12?style=flat-square">
  <a href="../LICENSE.md"><img alt="License: CC BY 4.0" src="https://img.shields.io/badge/license-CC%20BY%204.0-f1c40f?style=flat-square"></a>
</p>

This project is a small four leg robot that walks using servos. We made three versions to improve the frame, wiring, and controls.

## Project goals

* Make a walking robot with regular hobby servos.
* Use 3D printed parts that are easy to change.
* Keep the wiring simple with a servo driver board.
* Try wireless control and live video with an ESP32 CAM.
* Use the project to practice robotics and programming.

## Main parts

| Part | What we used |
|---|---|
| Movement | Four legs moved by servos |
| First controller | Arduino Nano |
| Later controller | ESP32 CAM |
| Servo control | Servo driver board |
| Frame | Custom 3D printed parts |
| Extra features | Wireless control and live video |

## Versions

### Version 1: Arduino prototype

The first version used an Arduino Nano, a servo driver, and a large printed body. It helped us test the walking motion. The body was too big, and some servos broke under the weight.

### Version 2: Small ESP32 CAM version

The second version used an ESP32 CAM and a smaller frame. It added wireless control and live video. The frame was too thin and broke during testing, and the wiring was crowded.

### Version 3: Stronger final version

The third version kept the ESP32 CAM and made the frame thicker. It was stronger, walked more consistently, and had cleaner wiring.

## How it works

The ESP32 CAM sends commands to the servo driver. The driver moves each leg servo in a pattern so the robot can walk. A battery powers the controller and servos.

## CAD files

| Folder | Fusion file | STEP file | Description |
|---|---|---|---|
| [`cad/final/`](cad/final/) | `final.f3z` | `final.step` | Stronger final design |
| [`cad/small/`](cad/small/) | `small.f3z` | `small.step` | Smaller early design |

Read the [CAD notes](cad/README.md) before printing any parts.

## Results

* The final robot could walk using a simple servo pattern.
* The ESP32 CAM added wireless control and live video.
* The stronger frame worked better than the thin frame.
* The project gave us practice with CAD, wiring, servos, and programming.

## Before building

Check the size of your servos, controller, battery, and screws before printing. Make sure the legs move freely before turning the servos on. Printed parts may need small changes for your printer and hardware.

> [!CAUTION]
> Servos can move without warning. Keep your fingers away from the legs and unplug the power before changing parts or wires.

## Links

* [Walking robot project page](https://angelojamesny.com/crabcrawler)
* [Club projects page](https://angelojamesny.com/club-projects)
* [Repository home](../README.md)

## License

The original project work is available under [CC BY 4.0](../LICENSE.md). You can share or change it as long as you credit Angelo Demetroulakos, link to the license, and say what you changed.
