<div align="center">

# Self Balancing Robot CAD Collection

### Three mechanical references across the Arduino and Raspberry Pi Pico builds

[![Status](https://img.shields.io/badge/Status-Complete-22c55e?style=flat-square)](#design-files)
[![Software](https://img.shields.io/badge/CAD-Autodesk_Fusion-6f42c1?style=flat-square)](https://www.autodesk.com/products/fusion-360/)
[![Formats](https://img.shields.io/badge/Formats-F3D_%2F_F3Z_%2B_STEP-f57c00?style=flat-square)](#file-formats)
[![License](https://img.shields.io/badge/License-CC_BY_4.0-0a7f5a?style=flat-square)](../../LICENSE.md)
[![Parent](https://img.shields.io/badge/Project-Self_Balancing_Robot-0078d4?style=flat-square)](../)

This directory contains the original Autodesk Fusion designs and neutral STEP solid models for the Self Balancing Robot platform.

<strong>Quick navigation:</strong><br>
[Design Files](#design-files) | [File Formats](#file-formats) | [Component Validation](#component-validation) | [Back to Self Balancing Robot](../)

</div>

---

## Design Files

| Revision | Fusion Archive | STEP Model | Description |
| --- | --- | --- | --- |
| 01 / Pico V1 | [`pico-v1/pico-cad-v1.f3z`](pico-v1/pico-cad-v1.f3z) | [`pico-v1/pico-cad-v1.step`](pico-v1/pico-cad-v1.step) | Raspberry Pi Pico (RP2040) tiered frame layout |
| 02 / Arduino Uno V2 | [`arduino-uno-v2/arduino-uno-cad-v2.f3z`](arduino-uno-v2/arduino-uno-cad-v2.f3z) | [`arduino-uno-v2/arduino-uno-cad-v2.step`](arduino-uno-v2/arduino-uno-cad-v2.step) | Arduino Uno / Nano shield bracket layout |
| 03 / Final reference | [`final-assembly/final-cad.f3d`](final-assembly/final-cad.f3d) | [`final-assembly/final-cad.step`](final-assembly/final-cad.step) | Integrated full robot reference assembly |

## File Formats

| Format | Purpose & Compatibility |
| --- | --- |
| `.f3d` | Native Autodesk Fusion single-design file (preserves full sketch and timeline parametric history) |
| `.f3z` | Autodesk Fusion archive bundle (contains linked subcomponents and joint definitions) |
| `.step` | Neutral ISO 10303 solid model compatible with modern CAD systems and slicers |

## Component Validation

> [!WARNING]
> The final CAD assembly serves as a dimensional reference. Off-the-shelf components (batteries, motor brackets, and fasteners) may vary across manufacturing batches.

- Verify motor mounting hole spacing and D-shaft diameter before 3D printing wheel hubs.
- Ensure standoffs provide adequate vertical clearance for the MPU6050 breakout header pins.
- Mount the battery tray as low as possible to reduce unwanted pendulum inertia.

---

<div align="center">

Designed and documented for **[Self Balancing Robot](../)** · **[City Tech Robotics](../../)**

</div>
