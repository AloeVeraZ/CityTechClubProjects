<div align="center">

# STEM Research Academy Robot Lab

### A six-week, full-system robotics program built around the 3TSahur mecanum robot

[![Program](https://img.shields.io/badge/Program-6_Weeks-111111?style=flat-square)](#overview)
[![Team](https://img.shields.io/badge/Team-2_Students_%2B_4_Mentors-6f42c1?style=flat-square)](#what-the-team-learned)
[![Platform](https://img.shields.io/badge/Platform-Raspberry_Pi_4-c51a4a?style=flat-square)](#robot-system)
[![Software](https://img.shields.io/badge/Software-Python_%2B_Flask-0a7f5a?style=flat-square)](robot_server/)

<strong>Quick navigation:</strong><br>
[Overview](#overview) | [Learning](#what-the-team-learned) | [Robot System](#robot-system) | [Repository Contents](#repository-contents) | [Connect and Drive](#connect-and-drive) | [Back to Club](../)

</div>

---

## Overview

The STEM Research Academy Robot Lab was a six-week program for **two high school students** supported by **four collegiate mentors**. Instead of assembling a pre-made kit, the team worked through the complete engineering process: CAD, fabrication, electrical power, custom PCB work, motors, servos, camera integration, networking, and Python software.

The main result was **3TSahur**, a Raspberry Pi 4 robot with a four-wheel mecanum drivetrain, two-servo ramp, USB camera, standalone Wi-Fi network, and browser-based driving dashboard. It is a larger and more integrated system than the club's introductory robots.

| Program | Details |
| --- | --- |
| Duration | Six weeks |
| Team | 2 student researchers and 4 mentors |
| Main platform | Custom Raspberry Pi 4 mecanum robot |
| Mechanical work | CAD/CAM, 3D printing, bandsaw work, drilling, manual milling, and CNC preparation |
| Electrical work | 5 V logic, 12 V motor power, fused distribution, buck regulation, custom PCBs, motors, servos, camera, and status-light interfaces |
| Software | Python robot server, local hotspot, camera stream, safety watchdog, and responsive web dashboard |

> [!NOTE]
> The program also produced two smaller ESP32-S3 and ESP32-CAM experimental robots that create their own local Wi-Fi networks. Their source files are not included in this repository.

## What the team learned

| Stage | Skills |
| --- | --- |
| 01 · Design | Parametric CAD, assembly clearances, component placement, and engineering drawings. |
| 02 · Prototype | 3D-printing tolerances, material choices, fit checks, and rapid revision. |
| 03 · Fabricate | Safe use of mills, bandsaws, drill presses, tapping tools, and power tools. |
| 04 · Wire | Soldering, harness routing, common grounding, fused power, buck converters, and custom PCBs. |
| 05 · Integrate | H-bridge drivers, mecanum motors, ramp servos, USB video, and status modules. |
| 06 · Program | Python services, Linux systemd, local networking, camera streaming, web controls, and safety timeouts. |

This project connects the club's foundational work to more advanced automation. The camera, network, motor-control, actuator, and software layers create the kind of complete platform that can later support computer vision and autonomous behavior.

## Robot system

| Subsystem | Implementation |
| --- | --- |
| Drive | Four independently controlled mecanum wheels for forward, reverse, strafe, and rotation |
| Controller | Raspberry Pi 4 running Raspberry Pi OS |
| Motor output | Two H-bridge drivers controlled through BCM GPIO PWM |
| Auxiliary motion | Two mirrored ramp servos driven through `pigpio` |
| Vision | Automatically detected Logitech USB camera with MJPEG streaming |
| Interface | Local Flask dashboard with keyboard controls, telemetry, and camera view |
| Networking | Standalone `3TSahur-Swarm` Wi-Fi hotspot |
| Safety | Command heartbeat, stale-sequence rejection, focus-loss stop, soft stop, and emergency kill |

The operator connects directly to the robot's hotspot. Browser commands go to the Raspberry Pi, which mixes mecanum-wheel outputs, controls the ramp servos, and streams the camera back to the dashboard. The system does not require an internet connection while driving.

## Repository contents

```text
stem-research-academy/
|-- images/         # Club, team, and completed-robot photos
|-- robot_server/   # Flask app, motors, servos, camera, health, and dashboard
|-- installer/      # Raspberry Pi deployment and systemd services
|-- docs/           # Wiring, setup, and ramp-actuator references
|-- tests/          # Hardware-independent safety and behavior tests
|-- requirements.txt
|-- run.py
`-- README.md
```

| Area | Start here |
| --- | --- |
| Robot software | [`robot_server/`](robot_server/) |
| Raspberry Pi installation | [`installer/README.md`](installer/README.md) |
| Wiring and GPIO | [`docs/WIRING.md`](docs/WIRING.md) |
| Ramp servos | [`docs/3TSAHUR_AUXILIARY_ACTUATORS.md`](docs/3TSAHUR_AUXILIARY_ACTUATORS.md) |
| Bench setup | [`docs/SETUP.md`](docs/SETUP.md) |
| Automated checks | [`tests/`](tests/) |

Run the server on a development computer with mock hardware:

```bash
python -m robot_server.app
```

Run the hardware-independent tests with:

```bash
python -m unittest discover -s tests -v
```

## Connect and drive

| Setting | Default |
| --- | --- |
| Wi-Fi network | `3TSahur-Swarm` |
| Wi-Fi password | `roboswarm1` |
| Dashboard | `http://10.42.0.1` |
| Direct API | `http://10.42.0.1:8080` |
| Local hostname | `http://3tsahur.local` |

| Key | Action |
| --- | --- |
| `W` / `S` | Drive forward / backward |
| `A` / `D` | Strafe left / right |
| `Q` / `E` | Rotate left / right |
| `R` | Open or close the ramp |
| `Space` | Soft stop |
| `Esc` | Emergency kill |

Change the default hotspot password before a public deployment.

## Safety

> [!CAUTION]
> Raise the chassis so all four wheels can spin freely during the first test. Keep the 12 V motor supply separate from the Raspberry Pi 5 V logic rail, verify a common ground, and set the servo buck converter to 5.0 V before connecting the servos.

Confirm that closing the browser, losing Wi-Fi, pressing `Space` or `Esc`, and allowing the command heartbeat to expire all stop the drivetrain.

---

[Back to the City Tech AI & Automation Club](../)
