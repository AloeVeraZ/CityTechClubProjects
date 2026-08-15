<div align="center">

# City Tech AI & Automation Club

### Three student robotics projects built through design, fabrication, electronics, and code

<img alt="Projects: 3" src="https://img.shields.io/badge/projects-3-8B5CF6?style=for-the-badge&labelColor=6D28D9"> <img alt="Workflow: CAD to hardware" src="https://img.shields.io/badge/workflow-CAD%20to%20hardware-00979D?style=for-the-badge&labelColor=006A70"> <img alt="STEM team: 2 students and 4 mentors" src="https://img.shields.io/badge/STEM%20team-2%20students%20%2B%204%20mentors-16C784?style=for-the-badge&labelColor=0E8A5F"> <img alt="License: CC BY 4.0" src="https://img.shields.io/badge/license-CC%20BY%204.0-F1C40F?style=for-the-badge&labelColor=B7950B">

This repository collects three hands-on robotics projects from the City Tech
AI & Automation Club. Each project keeps its design files, code, build history,
and practical notes together so the finished robot and the process behind it
can be explored from one place.

[Explore the projects](#project-collection) · [See the STEM team](#stem-research-academy-team) · [Open the repository map](#repository-map) · [Visit the club page](https://angelojamesny.com/club-projects)

</div>

[![City Tech AI and Automation Club at the Experimental Learning Symposium](stem-research-academy/images/club-cover.jpg)](https://www.instagram.com/p/DYOBZRNFmqn/?img_index=6)

---

## Club Overview

The collection covers three different robotics problems: balancing on two
wheels, walking with servo-driven legs, and integrating a full Raspberry Pi
mecanum platform. Together they show how mechanical design, electronics, and
software evolve through repeated physical testing.

| Project | Main engineering focus | Repository content |
| --- | --- | --- |
| Self Balancing Robot | IMU feedback, PID control, controller iteration | Arduino/Pico firmware and CAD |
| Crab Crawler Walking Robot | Servo gait design, frame strength, wireless control | Fusion and STEP CAD plus build history |
| STEM Research Academy Robot Lab | Full-system integration across manufacturing, electronics, and Python | Robot server, Pi installer, documentation, and tests |

## Project Collection

### 01 / Self Balancing Robot

<img src="https://assets.zyrosite.com/cdn-cgi/image/format=auto,w=1200,h=675,fit=crop/A85rnnzK6qs5qxKB/img_20260514_162917008-GuGOQgTeFhg8mCtz.jpg" alt="Self balancing robot">

A two-wheel robot that uses an MPU6050 and PID feedback to move its wheels
under its center of mass. Three versions were built with Arduino and Raspberry
Pi Pico controllers.

| System | Configuration |
| --- | --- |
| Sensor | MPU6050 IMU |
| Control | PID balance loop |
| Controllers | Arduino Nano, Arduino Uno, Raspberry Pi Pico |
| Drive | Two DC motors |
| Files | Fusion/STEP CAD, main firmware, and experiments |

[Open the project](self-balancing-robot/README.md) · [Browse the CAD](self-balancing-robot/cad/) · [Browse the firmware](self-balancing-robot/firmware/) · [View the portfolio page](https://angelojamesny.com/selfbalancing)

<table>
  <tr>
    <td width="33%" align="center"><a href="https://www.youtube.com/watch?v=-mdpzGmiDxs"><img src="https://i.ytimg.com/vi_webp/-mdpzGmiDxs/hqdefault.webp" width="100%" alt="Self balancing robot first prototype video"><br><strong>First prototype</strong></a></td>
    <td width="33%" align="center"><a href="https://www.youtube.com/watch?v=whE-oMi1N7U"><img src="https://i.ytimg.com/vi_webp/whE-oMi1N7U/hqdefault.webp" width="100%" alt="Self balancing robot printed body video"><br><strong>Printed body</strong></a></td>
    <td width="33%" align="center"><a href="https://www.youtube.com/watch?v=JzyDli07yCE"><img src="https://i.ytimg.com/vi_webp/JzyDli07yCE/hqdefault.webp" width="100%" alt="Self balancing robot Pico controller video"><br><strong>Pico controller</strong></a></td>
  </tr>
</table>

---

### 02 / Crab Crawler Walking Robot

<img src="https://assets.zyrosite.com/cdn-cgi/image/format=auto,w=1200,h=675,fit=crop/A85rnnzK6qs5qxKB/img_20260515_125209039-aa3XkdHF9OBnSOx5.jpg" alt="Crab crawler walking robot">

A four-leg robot that walks through a servo gait sequence. The project moved
from a large Arduino prototype to smaller ESP32-CAM versions with local Wi-Fi
control and live video.

| System | Configuration |
| --- | --- |
| Motion | Four servo-driven legs |
| Controllers | Arduino Nano, then ESP32-CAM |
| Interface | Local wireless driving panel |
| Structure | Two documented 3D-printed frame revisions |
| Files | Fusion archives and STEP exports |

[Open the project](crab-crawler/README.md) · [Browse the CAD](crab-crawler/cad/) · [View the portfolio page](https://angelojamesny.com/crabcrawler)

<table>
  <tr>
    <td width="33%" align="center"><a href="https://www.youtube.com/watch?v=WJB2is0cYr0"><img src="https://i.ytimg.com/vi_webp/WJB2is0cYr0/hqdefault.webp" width="100%" alt="Crab crawler Arduino prototype video"><br><strong>Arduino prototype</strong></a></td>
    <td width="33%" align="center"><a href="https://www.youtube.com/watch?v=dIKoLMmPl84"><img src="https://i.ytimg.com/vi_webp/dIKoLMmPl84/hqdefault.webp" width="100%" alt="Small ESP32-CAM walking robot video"><br><strong>Small ESP32-CAM</strong></a></td>
    <td width="33%" align="center"><a href="https://www.youtube.com/watch?v=3YAVgb8yF3U"><img src="https://i.ytimg.com/vi_webp/3YAVgb8yF3U/hqdefault.webp" width="100%" alt="Final crab crawler robot video"><br><strong>Stronger final version</strong></a></td>
  </tr>
</table>

---

### 03 / STEM Research Academy Robot Lab

<img src="stem-research-academy/images/final-robot.jpg" alt="Completed 3TSahur Raspberry Pi mecanum robot">

A six-week, full-system robotics build completed by **two students** with
support from **four mentors**. The students worked through CAD/CAM, 3D printing,
manual and CNC-oriented manufacturing, custom PCB and low-voltage electrical
work, sensors, servos, motors, and Python integration.

| Program | Configuration |
| --- | --- |
| Team | 2 students and 4 mentors |
| Duration | 6 weeks |
| Main platform | Raspberry Pi 4 mecanum robot |
| Mechanical work | CAD/CAM, printing, bandsaw, power tools, manual milling, CNC preparation |
| Electrical work | 5 V logic, 12 V power, custom PCBs, motors, servos, cameras, LiDAR-ready interfaces, LEDs |
| Software | Python robot server and local browser dashboard |

[Open the STEM project](stem-research-academy/README.md) · [Browse the robot server](stem-research-academy/robot_server/) · [Read the wiring guide](stem-research-academy/docs/WIRING.md)

## STEM Research Academy Team

<table>
  <tr>
    <td width="33%" align="center" valign="top">
      <img src="stem-research-academy/images/final-robot.jpg" width="100%" alt="Completed 3TSahur Raspberry Pi mecanum robot">
      <br><strong>Completed Robot</strong><br>
      <sub>The final Raspberry Pi mecanum robot built during the Academy.</sub>
    </td>
    <td width="33%" align="center" valign="top">
      <img src="stem-research-academy/images/group-photo-01.png" width="100%" alt="STEM Research Academy team presenting certificates with the completed robot">
      <br><strong>Group Photo 01</strong><br>
      <sub>The team presenting its research and completed robot.</sub>
    </td>
    <td width="33%" align="center" valign="top">
      <img src="stem-research-academy/images/group-photo-02.jpg" width="100%" alt="STEM Research Academy students and mentors with the robot in the lab">
      <br><strong>Group Photo 02</strong><br>
      <sub>The students and mentors with the robot in the lab.</sub>
    </td>
  </tr>
</table>

The STEM team also built two smaller ESP32-S3-based robots locally. Those
robots create their own Wi-Fi networks and use separate driving panels; their
source files are not part of this repository.

---

## Learning Workflow

| Stage | Practice across the collection |
| --- | --- |
| 01 / Define | Choose a movement problem and identify the control constraints |
| 02 / Design | Model frames, assemblies, and component layouts in CAD |
| 03 / Prototype | Print parts, assemble hardware, and expose physical problems |
| 04 / Wire | Build safe power, motor, sensor, and controller connections |
| 05 / Program | Create feedback loops, gait sequences, dashboards, and safety controls |
| 06 / Test | Validate one subsystem at a time and preserve unsuccessful iterations |
| 07 / Improve | Revise the mechanical design and software from measured behavior |

## Repository Map

```text
CityTechClubProjects/
|-- self-balancing-robot/
|   |-- cad/                 Fusion and STEP mechanical files
|   `-- firmware/            Arduino and Pico control programs
|-- crab-crawler/
|   `-- cad/                 Small and final walking-robot designs
|-- stem-research-academy/
|   |-- images/              Club, team, and final-robot media
|   |-- robot_server/        Python dashboard and hardware control
|   |-- installer/           Raspberry Pi deployment
|   |-- docs/                Wiring, setup, and ramp documentation
|   `-- tests/               Hardware-independent validation
|-- CITATION.cff
|-- LICENSE.md
`-- README.md
```

## More Information

| Destination | Link |
| --- | --- |
| Club page | [City Tech AI & Automation Club](https://angelojamesny.com/club-projects) |
| Self Balancing Robot portfolio | [angelojamesny.com/selfbalancing](https://angelojamesny.com/selfbalancing) |
| Crab Crawler portfolio | [angelojamesny.com/crabcrawler](https://angelojamesny.com/crabcrawler) |
| Citation information | [`CITATION.cff`](CITATION.cff) |

## License

Original project work is available under the
[Creative Commons Attribution 4.0 International License](LICENSE.md). You may
share or adapt it with credit to **Angelo Demetroulakos**, a link to the
license, and a note describing your changes. Third-party models and components
remain subject to their original terms.

---

Built through the City Tech AI & Automation Club as an iterative
design-to-hardware robotics collection.
