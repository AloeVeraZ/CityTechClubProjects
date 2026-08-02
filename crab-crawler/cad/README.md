# Walking robot CAD

Two design sets are included:

| Design | Native archive | Neutral export |
|---|---|---|
| Final reinforced design | `final/final.f3z` | `final/final.step` |
| Small compact design | `small/small.f3z` | `small/small.step` |

## Formats

- `.f3z` is an Autodesk Fusion distributed-design archive and may include linked components.
- `.step` is a neutral solid-model format for opening the design in other CAD software. It does not preserve the original Fusion timeline or parametric feature history.

## Before printing or manufacturing

- Confirm all servo, controller, fastener, and battery dimensions against your actual hardware.
- Inspect high-load joints and consider print orientation, additional walls, or local reinforcement.
- Check servo horns and linkages for free movement throughout the full gait range.
- Expect to adjust tolerances for your printer, material, and hardware variation.

The smaller design documents an earlier compact iteration. The final design uses a thicker, reinforced structure to address the frame failures observed during development.

