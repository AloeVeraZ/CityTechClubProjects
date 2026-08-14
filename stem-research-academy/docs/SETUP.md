# 3TSahur Raspberry Pi Setup

### Installation, first boot, and raised-wheel validation for the large robot

[![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi%204-C51A4A?style=flat-square&logo=raspberrypi&logoColor=white)](#02--install-on-the-raspberry-pi)
[![Network](https://img.shields.io/badge/network-local%202.4%20GHz%20hotspot-00979d?style=flat-square)](#03--connect)

[Project overview](../README.md) · [Wiring](WIRING.md) · [Ramp actuators](3TSAHUR_AUXILIARY_ACTUATORS.md) · [Installer](../installer/)

---

## 01 / Prepare the Hardware

> [!CAUTION]
> Keep all four wheels raised during setup. Disconnect motor power before
> changing wiring, and never power the drive motors from the Raspberry Pi 5 V
> rail.

- Install a correctly rated fuse and physical motor-power switch.
- Connect a shared ground between the Pi, both motor drivers, and motor supply.
- Wire the drivetrain exactly as [WIRING.md](WIRING.md) specifies.
- Connect the ramp servos to their regulated 5 V supply and common ground.
- Attach the Logitech USB camera.

## 02 / Install on the Raspberry Pi

Use a current Raspberry Pi OS image with internet access. Run the installer as
the normal Pi user, not as root:

```bash
git clone https://github.com/AloeVeraZ/CityTechClubProjects.git
cd CityTechClubProjects/stem-research-academy
bash installer/install.sh
```

| Installer result | Value |
| --- | --- |
| Application directory | `~/STEMResearchAcademy` |
| Hostname | `3tsahur` |
| Hotspot | `3TSahur-Swarm` |
| Dashboard service | `stem-robot-dashboard.service` |
| Hotspot service | `stem-robot-hotspot.service` |
| Servo timing service | `pigpiod.service` |

The installer validates the application, enables the services, and reboots.

## 03 / Connect

| Setting | Value |
| --- | --- |
| Wi-Fi name | `3TSahur-Swarm` |
| Raspberry Pi address | `10.42.0.1` |
| Dashboard | `http://10.42.0.1` |
| Direct service | `http://10.42.0.1:8080` |
| mDNS | `http://3tsahur.local` |

Change the default hotspot password before a public deployment.

## 04 / Validate Without Floor Driving

1. Confirm that the dashboard loads and the Logitech camera stream appears.
2. Confirm that GPIO, camera, and servo status appear in the system panel.
3. Keep the wheels raised and select a low speed.
4. Test forward, reverse, both strafes, and both rotations.
5. Release each input and verify that all four motors stop.
6. Test the ramp with its linkage disconnected or clear of obstructions.
7. Verify that `Space`, `Esc`, focus loss, and the watchdog stop the drivetrain.
8. Perform a floor test only after every direction and stop path is correct.

## Nginx Validation During an Update

The installer resolves Nginx at `/usr/sbin/nginx` when it is not in the normal
user's `PATH`. It validates the generated proxy before changing active sites
and avoids declarations that conflict with the Raspberry Pi OS default site.

If validation fails, the installer prints the diagnostic and removes the new
site link. Repair the reported site or reinstall Nginx, then rerun the same
installer command:

```bash
sudo apt-get install --reinstall nginx-light
```

---

Return to the [STEM Research Academy project](../README.md).
