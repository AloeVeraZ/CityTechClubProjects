<div align="center">

# Crab Crawler Walking Robot

### An educational platform for learning servos, gait sequencing, and wireless modules

[![Status](https://img.shields.io/badge/Status-Complete-22c55e?style=flat-square)](#overview)
[![Controller](https://img.shields.io/badge/Controller-ESP32--CAM-6f42c1?style=flat-square)](#how-it-works)
[![Motion](https://img.shields.io/badge/Motion-Servo_Gait-0a7f5a?style=flat-square)](#how-it-works)
[![Files](https://img.shields.io/badge/Files-Fusion_%2B_STEP-2563eb?style=flat-square)](#repository-contents)

<strong>Quick navigation:</strong><br>
[Overview](#overview) | [What Students Learn](#what-students-learn) | [Development](#development) | [How It Works](#how-it-works) | [Repository Contents](#repository-contents) | [Back to Club](../)

</div>

---

## Overview

Crab Crawler is a four-leg walking robot built to teach a different kind of motion control from the Self Balancing Robot. Instead of continuously adjusting DC motors from sensor feedback, it moves positional servos through a timed gait sequence.

The robot developed from a large Arduino Nano prototype into smaller ESP32-CAM versions with wireless commands and live video. Each physical version exposed a new mechanical problem, giving students a direct example of how software, electronics, and frame design affect one another.

| System | What it uses |
| --- | --- |
| Motion | Four servo-driven articulated legs |
| Early controller | Arduino Nano |
| Later controller | ESP32-CAM with local Wi-Fi and camera streaming |
| Servo module | PCA9685 multi-channel PWM driver |
| Interface | Browser-based directional controls |
| Mechanical design | Three generations of custom 3D-printed frames |

## What students learn

| Topic | Practical lesson |
| --- | --- |
| Servos | Command repeatable positions instead of raw motor speed and direction. |
| Gaits | Coordinate several joints into a stable walking sequence. |
| Modules | Connect an ESP32-CAM, PCA9685 driver, servos, display hardware, and power system. |
| Wireless control | Host a local network and send movement commands from a browser. |
| Camera streaming | Use the ESP32-CAM for live visual feedback. |
| Mechanical iteration | Improve torque distribution, joint strength, frame size, and wire routing after real walking tests. |

## Development

| Version | Build | What it taught | Video |
| --- | --- | --- | --- |
| 01 | Large Arduino Nano prototype | Validated the first gait, but the heavy body overloaded and stripped servos. | [Watch](https://www.youtube.com/watch?v=WJB2is0cYr0) |
| 02 | Small ESP32-CAM robot | Added wireless control and video, but the thin frame cracked and the wiring space was too tight. | [Watch](https://www.youtube.com/watch?v=dIKoLMmPl84) |
| 03 | Reinforced ESP32-CAM robot | Thickened the high-stress areas and cleaned up the wiring for more reliable walking. | [Watch](https://www.youtube.com/watch?v=3YAVgb8yF3U) |

## How it works

| Step | Process |
| --- | --- |
| 1 | A phone or computer connects to the robot's local Wi-Fi interface. |
| 2 | The operator sends a directional command from the browser. |
| 3 | The ESP32-CAM selects the matching gait sequence. |
| 4 | The PCA9685 produces stable PWM signals for the leg servos. |
| 5 | The servos move through coordinated positions while the camera returns live video. |

## Repository contents

```text
crab-crawler/
|-- cad/
|   |-- small/   # Compact design Fusion archive and STEP export
|   `-- final/   # Reinforced final Fusion archive and STEP export
`-- README.md
```

The [`cad/`](cad/) folder contains Autodesk Fusion archives (`.f3z`) and STEP exports (`.step`) for the compact and reinforced designs. The smaller model documents the earlier lightweight iteration; the final model thickens the structure where development testing showed failures.

Before printing, confirm the dimensions of the exact servos, horns, controller, battery, and fasteners being used. Check linkage clearance through the full gait and reinforce high-load joints for the chosen material and print orientation.

## Safety

> [!CAUTION]
> Servos can move unexpectedly when power is applied and can draw high current when stalled. Keep fingers clear of the linkages, use a properly rated servo power supply, and disconnect power before changing wiring or mechanical parts.

---

[Back to the City Tech AI & Automation Club](../)
