<div align="center">

# Crab Crawler Walking Robot

### Three generations of servo walking, printed-frame iteration, and wireless control

[![Status](https://img.shields.io/badge/Status-Complete-22c55e?style=flat-square)](#project-overview)
[![Controller](https://img.shields.io/badge/Controller-ESP32--CAM-6f42c1?style=flat-square)](#control-system)
[![Motion](https://img.shields.io/badge/Motion-Servo_Walking-0a7f5a?style=flat-square)](#control-system)
[![CAD](https://img.shields.io/badge/CAD-Fusion_360_%2B_STEP-f57c00?style=flat-square)](cad/)
[![License](https://img.shields.io/badge/License-CC_BY_4.0-0078d4?style=flat-square)](../LICENSE.md)
[![Parent](https://img.shields.io/badge/Club-City_Tech_Robotics-111111?style=flat-square)](../)

<picture>
  <img src="https://assets.zyrosite.com/cdn-cgi/image/format=auto,w=1200,h=675,fit=crop/A85rnnzK6qs5qxKB/img_20260515_125209039-aa3XkdHF9OBnSOx5.jpg" alt="Crab crawler walking robot" width="820" draggable="false">
</picture>

A compact four-leg walking robot built through iterative frame design, gait sequencing, and wireless ESP32-CAM control.

<strong>Quick navigation:</strong><br>
[Project Overview](#project-overview) | [Development Path](#development-path) | [CAD Collection](cad/) | [Build Videos](#build-videos) | [Back to Club](../)

</div>

---

## Project Overview

The Crab Crawler project explores multi-servo legged locomotion on a compact desktop footprint. Across three distinct iterations, the robot evolved from an overweight tethered prototype into a reinforced wireless walker with a live video feed.

| System | Implementation |
| --- | --- |
| Locomotion | Four servo-driven articulated legs |
| Early controller | Arduino Nano with external servo driver |
| Final controller | ESP32-CAM (Wi-Fi access point + video streaming) |
| Servo control | Dedicated multi-channel PCA9685 PWM driver |
| Mechanical frame | Custom 3D-printed modular chassis |
| User interface | Browser-based directional control panel |
| Development stages | 3 physical revisions documented |

## Development Path

### 01 / Arduino Prototype

[![Play Crab crawler Arduino prototype video](https://i.ytimg.com/vi_webp/WJB2is0cYr0/hqdefault.webp)](https://www.youtube.com/watch?v=WJB2is0cYr0)

> **Click the preview to watch the first prototype.** Tested the fundamental gait sequence on an Arduino Nano.

| Parameter | Configuration & Result |
| --- | --- |
| Controller | Arduino Nano |
| Structure | Large single-piece 3D-printed body |
| Failure mode | Frame mass placed excessive torque demand on the micro-servos |

---

### 02 / Small ESP32-CAM Robot

[![Play Small ESP32-CAM walking robot video](https://i.ytimg.com/vi_webp/dIKoLMmPl84/hqdefault.webp)](https://www.youtube.com/watch?v=dIKoLMmPl84)

> **Click the preview to watch the compact ESP32-CAM version.** Added wireless control and camera streaming.

| Parameter | Configuration & Result |
| --- | --- |
| Controller | ESP32-CAM |
| Structure | Scaled-down lightweight skeleton |
| Failure mode | Thin leg pivots cracked under lateral load; internal electronics space was too restricted |

---

### 03 / Stronger Final Version

[![Play Final crab crawler robot video](https://i.ytimg.com/vi_webp/3YAVgb8yF3U/hqdefault.webp)](https://www.youtube.com/watch?v=3YAVgb8yF3U)

> **Click the preview to watch the final reinforced walker.** Demonstrates stable gait and robust joints.

| Parameter | Configuration & Result |
| --- | --- |
| Controller | ESP32-CAM |
| Structure | Reinforced ribbing, thickened joint geometry, and organized wire channels |
| Outcome | Reliable, repeatable walking with onboard wireless telemetry |

## Control System

The ESP32-CAM hosts a local Wi-Fi web server. The operator interface sends directional commands over HTTP/WebSockets, which the microcontroller translates into coordinated multi-servo gait steps.

<table>
  <tr>
    <td align="center"><strong>Operator Browser</strong><br>Directional commands</td>
    <td align="center">&rarr;</td>
    <td align="center"><strong>ESP32-CAM</strong><br>Local Wi-Fi server</td>
    <td align="center">&rarr;</td>
    <td align="center"><strong>PCA9685 Driver</strong></td>
    <td align="center">&rarr;</td>
    <td align="center"><strong>Four Articulated Legs</strong></td>
  </tr>
  <tr>
    <td align="center"><strong>Operator Browser</strong></td>
    <td align="center">&larr;</td>
    <td align="center"><strong>ESP32-CAM</strong><br>MJPEG video stream</td>
    <td colspan="4"></td>
  </tr>
</table>

## CAD Collection

The [`cad/`](cad/) directory contains source Autodesk Fusion archives (`.f3z`) and neutral STEP exports (`.step`) for the prototype and production revisions.

| Revision | Fusion Archive | STEP Export | Purpose |
| --- | --- | --- | --- |
| 01 / Small prototype | [`cad/small/small.f3z`](cad/small/small.f3z) | [`cad/small/small.step`](cad/small/small.step) | Lightweight early test chassis |
| 02 / Final reinforced | [`cad/final/final.f3z`](cad/final/final.f3z) | [`cad/final/final.step`](cad/final/final.step) | Thickened production frame |

[Browse the CAD folder](cad/) | [Read the CAD Guide](cad/README.md)

## Build Videos

| Prototype 1 (Arduino) | Prototype 2 (ESP32-CAM) | Final Version (Reinforced) |
| :---: | :---: | :---: |
| [![Version 1](https://i.ytimg.com/vi_webp/WJB2is0cYr0/hqdefault.webp)](https://www.youtube.com/watch?v=WJB2is0cYr0) | [![Version 2](https://i.ytimg.com/vi_webp/dIKoLMmPl84/hqdefault.webp)](https://www.youtube.com/watch?v=dIKoLMmPl84) | [![Version 3](https://i.ytimg.com/vi_webp/3YAVgb8yF3U/hqdefault.webp)](https://www.youtube.com/watch?v=3YAVgb8yF3U) |

## Assembly & Safety

> [!CAUTION]
> Servos can rotate abruptly upon power application. Keep fingers clear of linkages and disconnect the battery before making mechanical or electrical adjustments.

- Confirm servo arm zero positions before installing leg linkages.
- Use high-infill settings (≥40% PETG/ABS) on the leg pivots for structural rigidity.
- Ensure the external battery pack can supply peak concurrent servo stall currents without browning out the ESP32-CAM.
