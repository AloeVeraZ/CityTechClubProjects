# City Tech Club Robotics Projects

Open CAD, firmware, and build notes from hands-on robotics projects developed for City Tech club activities. Each project has its own folder, documentation, design history, and downloadable files.

## Projects

| Self-Balancing Robot | Crab Crawler / Walking Robot |
|---|---|
| Two-wheel balancing platform using real-time IMU feedback and PID control. | Four-leg servo walker developed through three mechanical and electronics revisions. |
| **Controllers:** Arduino Nano, Arduino Uno, Raspberry Pi Pico | **Controllers:** Arduino Nano, ESP32-CAM |
| **Included:** firmware, experiments, Fusion CAD, STEP exports, build notes | **Included:** Fusion CAD, STEP exports, design history, build notes |
| [Open the self-balancing robot project →](self-balancing-robot/README.md) | [Open the crab crawler project →](crab-crawler/README.md) |

## Repository structure

```text
.
├── self-balancing-robot/
│   ├── cad/                 Fusion and STEP design files
│   ├── firmware/            Controller and experimental sketches
│   └── README.md            Project story, setup, and safety notes
├── crab-crawler/
│   ├── cad/                 Final and compact design files
│   └── README.md            Project story, revisions, and build notes
├── CITATION.cff             Creator and citation information
└── LICENSE.md               CC BY 4.0 terms
```

## About the collection

Both projects use iterative prototyping to turn control concepts into physical robots. The repository preserves successful builds as well as useful development history: controller experiments, mechanical failures, compact redesigns, and the changes that made later versions more reliable.

The project folders explain what each file represents and call out important limitations before fabrication or hardware testing.

## Project pages

- [City Tech club projects overview](https://angelojamesny.com/club-projects)
- [Self-balancing robot website](https://angelojamesny.com/selfbalancing)
- [Crab crawler / walking robot website](https://angelojamesny.com/crabcrawler)

## License

Except where otherwise noted, original materials are licensed under the [Creative Commons Attribution 4.0 International License](LICENSE.md). You may share and adapt them, including commercially, provided you credit **Angelo Demetroulakos**, link to the license, and indicate whether changes were made.

Third-party and off-the-shelf component models remain subject to their respective owners' rights.

