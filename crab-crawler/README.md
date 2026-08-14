# Crab Crawler Walking Robot

### Three generations of servo walking, printed-frame iteration, and wireless control

[![Status](https://img.shields.io/badge/status-complete-16c784?style=flat-square)](#results)
[![Controller](https://img.shields.io/badge/controller-ESP32--CAM-00979d?style=flat-square)](#control-system)
[![Motion](https://img.shields.io/badge/motion-servo%20walking-f39c12?style=flat-square)](#control-system)
[![CAD](https://img.shields.io/badge/CAD-Fusion%20360%20%2B%20STEP-ff8a00?style=flat-square)](cad/)
[![License](https://img.shields.io/badge/license-CC%20BY%204.0-f1c40f?style=flat-square)](../LICENSE.md)

[![Crab crawler walking robot](https://assets.zyrosite.com/cdn-cgi/image/format=auto,w=1200,h=675,fit=crop/A85rnnzK6qs5qxKB/img_20260515_125209039-aa3XkdHF9OBnSOx5.jpg)](https://angelojamesny.com/crabcrawler)

This project is a compact four-leg robot that walks by sequencing hobby
servos. Three versions were built to improve the body size, frame strength,
wiring layout, and wireless control experience.

[Project overview](#project-overview) · [Development path](#development-path) · [Open the CAD](cad/) · [Watch the videos](#build-videos) · [Read before building](#before-building)

---

## Project Overview

| System | Implementation |
| --- | --- |
| Movement | Four servo-driven legs |
| First controller | Arduino Nano |
| Later controller | ESP32-CAM |
| Servo control | Multi-channel servo-driver board |
| Structure | Custom 3D-printed frames |
| Added capability | Wireless driving panel and live camera feed |
| Repository | Final and early CAD files plus project documentation |

The project began as a simple walking test and developed into a smaller
wireless robot. Each revision addressed a physical issue found in the previous
build rather than hiding the unsuccessful parts of the process.

## Development Path

### 01 / Arduino Prototype

[![Crab crawler Arduino prototype video](https://i.ytimg.com/vi_webp/WJB2is0cYr0/hqdefault.webp)](https://www.youtube.com/watch?v=WJB2is0cYr0)

The first version used an Arduino Nano, a servo driver, and a large printed
body. It proved the basic walking sequence, but the heavy frame placed too much
load on the servos.

| Prototype | Result |
| --- | --- |
| Controller | Arduino Nano |
| Frame | Large 3D-printed body |
| Main lesson | The structure was too heavy for the selected servos |

---

### 02 / Small ESP32-CAM Robot

[![Small ESP32-CAM walking robot video](https://i.ytimg.com/vi_webp/dIKoLMmPl84/hqdefault.webp)](https://www.youtube.com/watch?v=dIKoLMmPl84)

The second version reduced the frame size and added an ESP32-CAM for wireless
control and live video. The thinner structure saved weight but broke during
testing, and the smaller body made wiring difficult.

| Prototype | Result |
| --- | --- |
| Controller | ESP32-CAM |
| Added feature | Wi-Fi control and camera stream |
| Main lesson | Thin frame sections and crowded wiring reduced reliability |

---

### 03 / Stronger Final Version

[![Final crab crawler robot video](https://i.ytimg.com/vi_webp/3YAVgb8yF3U/hqdefault.webp)](https://www.youtube.com/watch?v=3YAVgb8yF3U)

The final version retained the wireless controller while thickening the frame
and cleaning up the electronics layout. It walked more consistently and
survived repeated testing better than the smaller prototype.

| Final version | Configuration |
| --- | --- |
| Controller | ESP32-CAM |
| Motion | Four servo-driven legs |
| Structure | Reinforced printed frame |
| Interface | Local wireless driving panel and video |

## Control System

The ESP32-CAM receives a movement command from the local driving panel and
sends position targets to the servo-driver board. The driver moves the leg
servos through a repeated gait sequence while the battery supplies the
controller and servos.

```mermaid
flowchart LR
    O["Operator browser"] -->|"Local Wi-Fi command"| E["ESP32-CAM"]
    E --> S["Servo-driver board"]
    S --> L["Four walking legs"]
    E -->|"Live stream"| O
```

## CAD Collection

The [`cad/`](cad/) folder contains editable Autodesk Fusion archives and STEP
exports for the smaller prototype and the stronger final design.

| Design | Fusion file | STEP file | Purpose |
| --- | --- | --- | --- |
| Final | `cad/final/final.f3z` | `cad/final/final.step` | Reinforced completed frame |
| Small | `cad/small/small.f3z` | `cad/small/small.step` | Compact early prototype |

[Open the CAD collection](cad/) · [Read the CAD guide](cad/README.md)

## Build Videos

| Arduino prototype | Small ESP32-CAM | Stronger final version |
| --- | --- | --- |
| [![Version 1](https://i.ytimg.com/vi_webp/WJB2is0cYr0/hqdefault.webp)](https://www.youtube.com/watch?v=WJB2is0cYr0) | [![Version 2](https://i.ytimg.com/vi_webp/dIKoLMmPl84/hqdefault.webp)](https://www.youtube.com/watch?v=dIKoLMmPl84) | [![Version 3](https://i.ytimg.com/vi_webp/3YAVgb8yF3U/hqdefault.webp)](https://www.youtube.com/watch?v=3YAVgb8yF3U) |

## Results

- The final robot walked with a repeatable servo sequence.
- The ESP32-CAM added wireless control and live video.
- Reinforcing the frame improved durability and consistency.
- The three versions preserve the design decisions made after real failures.

## Before Building

Check the exact servo, controller, battery, screw, and servo-arm dimensions
before printing. Confirm that every leg moves freely and that the power supply
can handle several servos moving at once.

> [!CAUTION]
> Servos can move without warning. Keep fingers away from the legs and unplug
> the battery before changing printed parts, linkages, or wiring.

---

[Project page](https://angelojamesny.com/crabcrawler) · [Club project collection](../README.md) · [City Tech AI & Automation Club](https://angelojamesny.com/club-projects)

Original project work is available under [CC BY 4.0](../LICENSE.md). Third-party
parts and models remain subject to their original terms.
