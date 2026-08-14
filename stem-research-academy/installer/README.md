# 3TSahur Raspberry Pi Installer

### Repeatable deployment for the hotspot, dashboard, GPIO services, and local display

[![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi%20OS-111111?style=flat-square&logo=raspberrypi&logoColor=white)](#install)
[![Service](https://img.shields.io/badge/service-systemd-3f3f46?style=flat-square)](#installed-components)
[![Network](https://img.shields.io/badge/network-NetworkManager-6b7280?style=flat-square)](#installed-components)

[Project overview](../README.md) · [Setup guide](../docs/SETUP.md) · [Wiring](../docs/WIRING.md) · [Robot server](../robot_server/)

---

`install.sh` provisions Raspberry Pi OS for the large 3TSahur robot and safely
updates an existing installation.

## Installed Components

| Area | Result |
| --- | --- |
| Application | Validated deployment to `~/STEMResearchAcademy` |
| Python | Project virtual environment and runtime packages |
| Robot service | `stem-robot-dashboard.service` |
| Network | `3TSahur-Swarm` hotspot and fixed `10.42.0.1` address |
| Local name | `3tsahur.local` through mDNS |
| Servo timing | `pigpiod.service` |
| Display | Resizable Chromium dashboard window |
| Proxy | Nginx dashboard access on port 80 |

## Install

Run from a trusted checkout as the normal Pi user, not as root:

```bash
bash installer/install.sh
```

> [!IMPORTANT]
> The installer intentionally reboots after it validates and enables the
> deployment. Complete the wiring and raised-wheel checks in the
> [setup guide](../docs/SETUP.md) before applying drivetrain power.

## Installer Files

| File | Purpose |
| --- | --- |
| `install.sh` | Full install, update, validation, and rollback flow |
| `curl-install.sh` | Small remote bootstrap for the main installer |
| `hotspot.sh` | NetworkManager hotspot setup |
| `kiosk.sh` | Local dashboard window |
| `start-dashboard.sh` | Python service launcher |
| `systemd/` | Dashboard, hotspot, and `pigpiod` unit files |

---

Return to the [STEM Research Academy project](../README.md).
