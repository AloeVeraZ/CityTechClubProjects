<div align="center">

# 3TSahur Raspberry Pi Installer

### Automated deployment scripts for Wi-Fi hotspot, dashboard, GPIO services, and systemd units

[![Platform](https://img.shields.io/badge/Platform-Raspberry_Pi_OS-c51a4a?style=flat-square&logo=raspberrypi&logoColor=white)](https://www.raspberrypi.com/)
[![Services](https://img.shields.io/badge/Daemon-systemd-6f42c1?style=flat-square)](#installed-components)
[![Networking](https://img.shields.io/badge/Network-NetworkManager-0a7f5a?style=flat-square)](#installer-files)
[![License](https://img.shields.io/badge/License-CC_BY_4.0-0078d4?style=flat-square)](../../LICENSE.md)
[![Parent](https://img.shields.io/badge/Project-STEM_Research_Academy-111111?style=flat-square)](../)

This directory provides a turnkey installation pipeline to configure a stock Raspberry Pi OS system into an integrated autonomous robot server.

[Installed Components](#installed-components) | [Installation Guide](#installation-guide) | [Installer Files](#installer-files) | [Back to STEM Project](../)

</div>

---

## Installed Components

`install.sh` automates the complete provisioning and verification workflow:

| Subsystem | Resulting Configuration |
| --- | --- |
| Target location | Clean virtual environment deployed to `~/STEMResearchAcademy` |
| Python environment | Python 3 virtual environment with isolated dependency tree |
| Daemon service | `stem-robot-dashboard.service` managed via systemd |
| Wi-Fi access point | NetworkManager 2.4 GHz hotspot (`3TSahur-Swarm` @ `10.42.0.1`) |
| Local hostname | `3tsahur.local` broadcast via Avahi / mDNS |
| PWM daemon | `pigpiod.service` for accurate hardware timing on ramp servos |
| Reverse proxy | Optional Nginx proxy serving dashboard traffic on HTTP port 80 |

## Installation Guide

Run the installer from a local git checkout as the normal `pi` user (do not run as root):

```bash
cd ~/STEMResearchAcademy/installer
bash install.sh
```

> [!IMPORTANT]
> The installer automatically restarts the Raspberry Pi upon successful verification to initialize network interfaces and GPIO permissions. Complete all hardware wiring before applying high-voltage motor power.

## Installer Files

| File | Technical Responsibility |
| --- | --- |
| `install.sh` | Main idempotent installer script with automatic dependency validation |
| `curl-install.sh` | Remote bootstrap script for single-command curl installation |
| `hotspot.sh` | NetworkManager hotspot and static IP (`10.42.0.1`) configuration |
| `kiosk.sh` | Launches dedicated Chromium fullscreen UI on attached HDMI monitors |
| `start-dashboard.sh` | Service wrapper that activates venv and launches Flask daemon |
| `systemd/` | Unit files for auto-restarting services on startup |

---

<div align="center">

Designed and documented for **[STEM Research Academy](../)** · **[City Tech Robotics](../../)**

</div>
