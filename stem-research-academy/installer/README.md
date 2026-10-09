<div align="center">

# 3TSahur Raspberry Pi Installer

### One command puts 3TSahur on MotionModule: browser driving, over-the-air code deploys, and dashboard updates

[![Platform](https://img.shields.io/badge/Platform-Raspberry_Pi_OS-c51a4a?style=flat-square&logo=raspberrypi&logoColor=white)](https://www.raspberrypi.com/)
[![Runtime](https://img.shields.io/badge/Runtime-MotionModule-6f42c1?style=flat-square)](https://github.com/AloeVeraZ/MotionModule)
[![License](https://img.shields.io/badge/License-CC_BY_4.0-0078d4?style=flat-square)](../../LICENSE.md)
[![Parent](https://img.shields.io/badge/Project-STEM_Research_Academy-111111?style=flat-square)](../)

<strong>Quick navigation:</strong><br>
[Install](#install) | [What It Does](#what-it-does) | [Updating](#updating) | [Options](#options) | [Back to STEM Project](../)

</div>

---

## Install

Flash Raspberry Pi OS with Raspberry Pi Imager, set the Wi-Fi network and enable SSH there, then SSH in
as the normal Pi user (not root) and run:

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/CityTechClubProjects/main/stem-research-academy/installer/curl-install.sh | bash
```

The Pi reboots when it finishes. No monitor, keyboard or mouse is needed at any point.

## What It Does

| Step | Result |
| --- | --- |
| Packages | `pigpio` for the ramp servos, `python3-opencv` and `v4l-utils` for the USB camera |
| Old server | Removes `stem-robot-dashboard`, `stem-robot-hotspot`, the old Nginx site, the kiosk and `~/STEMResearchAcademy` |
| `pigpiod.service` | DMA-timed servo pulses on GPIO12 and GPIO18, listening on this Pi only |
| GPIO18 | Parks MotionModule's IMU-bus overlay under `[none]` in `config.txt`, so GPIO18 stays free for ramp servo 2 |
| Hotspot name | `3TSahur-Swarm` / `roboswarm1` in `/etc/motionmodule/network.json` |
| Robot project | `robot/3TSahur` → `~/MotionModule/robots/3TSahur`, set as the active robot |
| MotionModule | Installs from `main`, runs its tests, sets the hostname `3tsahur` and reboots |

## Updating

| What changed | How to update |
| --- | --- |
| MotionModule (dashboard, Driver Station, runtime) | **Update** card on the dashboard. The 3TSahur folder, pins and hotspot name are kept. |
| 3TSahur robot code, from your laptop | Dashboard → **Code** → choose the `3TSahur` folder → **Deploy and run** |
| 3TSahur robot code, from GitHub | `curl -fsSL …/curl-install.sh \| bash -s -- --robot-only` over SSH |
| Everything | Rerun the install command |

## Options

| Option | Meaning |
| --- | --- |
| `--robot-only` | Replace only `~/MotionModule/robots/3TSahur` from GitHub and restart the dashboard |
| `--no-reboot` | Skip MotionModule's final reboot |
| `--motionmodule-version REF` | Install a MotionModule branch, tag or commit other than `main` |

Pass options after `bash -s --`, for example `… | bash -s -- --no-reboot`. From a checkout, run
`bash installer/install.sh` and the robot folder beside it is used instead of downloading one.

---

<div align="center">

Designed and documented for **[STEM Research Academy](../)** · **[City Tech Robotics](../../)**

</div>
