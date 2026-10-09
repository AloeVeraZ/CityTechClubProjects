# 3TSahur Raspberry Pi Setup

### Installation, first boot, and raised-wheel validation for the large robot

<img alt="Platform: Raspberry Pi 4" src="https://img.shields.io/badge/platform-Raspberry%20Pi%204-C51A4A?style=flat-square&logo=raspberrypi&logoColor=white"> <img alt="Runtime: MotionModule" src="https://img.shields.io/badge/runtime-MotionModule-6f42c1?style=flat-square">

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

Flash a current Raspberry Pi OS image with Raspberry Pi Imager and set the Wi-Fi
network and SSH there. Then SSH in as the normal Pi user, not as root:

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/CityTechClubProjects/main/stem-research-academy/installer/curl-install.sh | bash
```

| Installer result | Value |
| --- | --- |
| Runtime | MotionModule, `~/.local/share/motionmodule` |
| Robot project | `~/MotionModule/robots/3TSahur` (active) |
| Hostname | `3tsahur` |
| Fallback hotspot | `3TSahur-Swarm` |
| Dashboard service | `motionmodule.service` |
| Servo timing service | `pigpiod.service` |

The installer removes the original 3TSahur server, tests the MotionModule
release, and reboots. See the [installer README](../installer/README.md).

## 03 / Connect

The Pi joins the Wi-Fi saved by Raspberry Pi Imager. If no saved network
connects within 30 seconds of boot, it starts its own hotspot.

| Setting | On saved Wi-Fi | On the hotspot |
| --- | --- | --- |
| Wi-Fi name | your network | `3TSahur-Swarm` |
| Password | your network | `roboswarm1` |
| Dashboard | `http://3tsahur.local` | `http://10.42.0.1` |
| Driver Station | Dashboard → **Open Driver Station** | same |

Change Wi-Fi networks, the hotspot and the hostname from the dashboard. Change
the default hotspot password before a public deployment.

## 04 / Validate Without Floor Driving

1. Open the dashboard and run the **Debug** checks. The IMU check reports no
   IMU bus; that is expected on 3TSahur.
2. Open the Driver Station and confirm the Logitech camera stream appears.
3. Confirm that the Ramp line under Raspberry Pi Inputs reads `closed`, not an error.
4. Keep the wheels raised, enable the Driver Station and set a low drive output.
5. Test forward, reverse, both strafes, and both rotations.
6. Release each key and verify that all four motors stop.
7. Test the ramp with its linkage disconnected or clear of obstructions.
8. Verify that Space, **STOP ALL OUTPUTS**, closing the page and losing Wi-Fi stop the drivetrain.
9. Perform a floor test only after every direction and stop path is correct.

## 05 / Change Code and Update, Over Wi-Fi

| Task | Where |
| --- | --- |
| Deploy edited robot code | Dashboard → **Code** → choose the `3TSahur` folder → **Deploy and run** |
| Update MotionModule | Dashboard → **Update** |
| Take the robot folder from GitHub | Rerun the install command with `bash -s -- --robot-only` |

---

Return to the [STEM Research Academy project](../README.md).
