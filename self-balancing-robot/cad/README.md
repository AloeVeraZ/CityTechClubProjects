# Self Balancing Robot CAD Collection

### Three mechanical references across the Arduino and Raspberry Pi Pico builds

[![CAD](https://img.shields.io/badge/CAD-Autodesk%20Fusion-111111?style=flat-square)](#design-files)
[![Formats](https://img.shields.io/badge/formats-F3D%20%2F%20F3Z%20%2B%20STEP-6b7280?style=flat-square)](#file-formats)

[Project overview](../README.md) · [Pico V1](pico-v1/) · [Arduino Uno V2](arduino-uno-v2/) · [Final assembly](final-assembly/)

---

## Design Files

| Revision | Fusion file | STEP export | Purpose |
| --- | --- | --- | --- |
| 01 / Pico V1 | [`pico-v1/pico-cad-v1.f3z`](pico-v1/pico-cad-v1.f3z) | [`pico-v1/pico-cad-v1.step`](pico-v1/pico-cad-v1.step) | Raspberry Pi Pico layout |
| 02 / Arduino Uno V2 | [`arduino-uno-v2/arduino-uno-cad-v2.f3z`](arduino-uno-v2/arduino-uno-cad-v2.f3z) | [`arduino-uno-v2/arduino-uno-cad-v2.step`](arduino-uno-v2/arduino-uno-cad-v2.step) | Arduino Uno layout |
| 03 / Final reference | [`final-assembly/final-cad.f3d`](final-assembly/final-cad.f3d) | [`final-assembly/final-cad.step`](final-assembly/final-cad.step) | Completed design reference |

## File Formats

| Format | Use |
| --- | --- |
| `.f3d` | Native Autodesk Fusion single-design file |
| `.f3z` | Autodesk Fusion archive that may include linked components |
| `.step` | Portable solid model without the Fusion edit history |

## Final Model Note

> [!WARNING]
> The final assembly is a design reference, not an exact digital twin of every
> purchased component used on the physical robot.

Some wheels, batteries, holders, and other store-bought parts are simplified
placeholders. Measure the real motors, wheels, battery, boards, holes, and
fasteners before printing or ordering parts.

---

Return to the [Self Balancing Robot project](../README.md), open the
[firmware collection](../firmware/), or return to the
[club project collection](../../README.md).
