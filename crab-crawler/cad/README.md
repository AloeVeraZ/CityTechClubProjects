# Crab Crawler CAD Collection

### Editable Fusion archives and portable STEP exports for two frame revisions

[![CAD](https://img.shields.io/badge/CAD-Autodesk%20Fusion-111111?style=flat-square)](#design-files)
[![Formats](https://img.shields.io/badge/formats-F3Z%20%2B%20STEP-6b7280?style=flat-square)](#file-formats)

[Project overview](../README.md) · [Final design](final/) · [Small prototype](small/)

---

## Design Files

| Revision | Fusion archive | STEP export | Purpose |
| --- | --- | --- | --- |
| 01 / Small prototype | [`small/small.f3z`](small/small.f3z) | [`small/small.step`](small/small.step) | Compact ESP32-CAM experiment |
| 02 / Final design | [`final/final.f3z`](final/final.f3z) | [`final/final.step`](final/final.step) | Reinforced completed frame |

The small design preserved the compact second-generation robot. The final
design thickened the joints and frame sections that failed during testing.

## File Formats

| Format | Use |
| --- | --- |
| `.f3z` | Opens in Autodesk Fusion and can preserve linked design components |
| `.step` | Opens in most CAD packages but does not preserve Fusion history |

## Before Printing

> [!IMPORTANT]
> Measure the exact servos, controller, battery, screws, and servo arms before
> printing. These files document the project build and may need adjustment for
> different hardware or printer tolerances.

- Check the thicker joints and choose a strong print orientation.
- Confirm that the servo arms and legs can move through the full gait.
- Leave enough clearance for wiring and connectors.
- Test one leg before printing the complete frame.

---

Return to the [Crab Crawler project](../README.md) or the
[club project collection](../../README.md).
