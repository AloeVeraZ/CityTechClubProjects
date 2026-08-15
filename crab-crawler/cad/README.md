<div align="center">

# Crab Crawler CAD Collection

### Editable Fusion archives and portable STEP exports for two frame revisions

[![Status](https://img.shields.io/badge/Status-Complete-22c55e?style=flat-square)](#design-files)
[![Software](https://img.shields.io/badge/CAD-Autodesk_Fusion-6f42c1?style=flat-square)](https://www.autodesk.com/products/fusion-360/)
[![Formats](https://img.shields.io/badge/Formats-F3Z_%2B_STEP-f57c00?style=flat-square)](#file-formats)
[![License](https://img.shields.io/badge/License-CC_BY_4.0-0a7f5a?style=flat-square)](../../LICENSE.md)
[![Parent](https://img.shields.io/badge/Project-Crab_Crawler-0078d4?style=flat-square)](../)

This directory contains the original Fusion 360 project archives (`.f3z`) and neutral STEP solid models (`.step`) for the Crab Crawler walking robot.

[Design Files](#design-files) | [File Formats](#file-formats) | [Fabrication Notes](#fabrication-notes) | [Back to Crab Crawler](../)

</div>

---

## Design Files

| Revision | Fusion Archive | STEP Export | Description |
| --- | --- | --- | --- |
| 01 / Small prototype | [`small/small.f3z`](small/small.f3z) | [`small/small.step`](small/small.step) | Compact ESP32-CAM early experimental chassis |
| 02 / Final design | [`final/final.f3z`](final/final.f3z) | [`final/final.step`](final/final.step) | Reinforced final frame with thickened leg joints |

The small prototype documents the compact second-generation walker. The final design reinforces the joint and frame sections that experienced fatigue during gait testing.

## File Formats

| Format | Purpose & Compatibility |
| --- | --- |
| `.f3z` | Autodesk Fusion distributed design archive (preserves components, joints, and linked sub-assemblies) |
| `.step` | Neutral ISO 10303 solid model compatible with Onshape, SolidWorks, Inventor, FreeCAD, and slicers |

## Fabrication Notes

> [!IMPORTANT]
> Measure your specific servos, controller, battery, screws, and servo horns before printing. These models represent tested physical builds and may require tolerance offsets for your specific 3D printer calibration.

- **Print Orientation:** Orient leg pivots along the build plate to align layer lines with principal bending moments.
- **Clearance:** Confirm full range of motion for servo horns and linkages before mounting fasteners.
- **Wire Routing:** Route servo leads through designated chassis channels to prevent pinching during leg cycling.

---

<div align="center">

Designed and documented for **[Crab Crawler Walking Robot](../)** · **[City Tech Robotics](../../)**

</div>
