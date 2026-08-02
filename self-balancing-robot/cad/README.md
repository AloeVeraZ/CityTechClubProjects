# CAD files

The CAD is supplied in both editable Autodesk Fusion formats and broadly compatible STEP exports.

| Folder | Native file | Exchange file | Purpose |
|---|---|---|---|
| `pico-v1/` | `pico-cad-v1.f3z` | `pico-cad-v1.step` | Raspberry Pi Pico controller layout |
| `arduino-uno-v2/` | `arduino-uno-cad-v2.f3z` | `arduino-uno-cad-v2.step` | Arduino Uno controller layout |
| `final-assembly/` | `final-cad.f3d` | `final-cad.step` | Composite final design reference |

## Format notes

- `.f3d` is a single Autodesk Fusion design archive.
- `.f3z` is an Autodesk Fusion distributed-design archive and may contain linked components.
- `.step` is the best starting point for other CAD applications, but it does not preserve the full Fusion feature history.

## Final assembly limitations

The final assembly is **not an exact as-built model**. The physical robot used several purchased components that were represented with convenient placeholder geometry during layout work.

Known or likely approximations include:

- wheels used as visual or envelope placeholders;
- a simplified battery placeholder;
- a placeholder 3D-printed holder surrounding one Arduino board;
- other off-the-shelf parts whose exact vendor geometry was unavailable.

Do not manufacture directly from assumed clearances in the assembly. Measure your actual wheels, battery, controller boards, motors, hubs, and fasteners, then update mating printed parts before fabrication.

