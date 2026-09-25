# 3TSahur Raspberry Pi Setup

### Installation, first boot, and raised-wheel validation for the large robot

<img alt="Platform: Raspberry Pi 4" src="https://img.shields.io/badge/platform-Raspberry%20Pi%204-C51A4A?style=flat-square&logo=raspberrypi&logoColor=white"> <img alt="Network: local 2.4 GHz hotspot" src="https://img.shields.io/badge/network-local%202.4%20GHz%20hotspot-00979d?style=flat-square">

[Project overview](../README.md) · [Wiring](WIRING.md) · [Ramp actuators](3TSAHUR_AUXILIARY_ACTUATORS.md) · [Installer](../installer/)

---

## 01 / Prepare the Hardware

> [!CAUTION]
> Keep all four wheels raised during setup. Disconnect motor power before
> changing wiring, and never power the drive motors from the Raspberry Pi 5 V
> rail.

- Install a correctly rated fuse and physical motor-power switch.
- Connect a shared ground between the Pi, both motor drivers, and motor supply.
- Wire the two drivers, the PCA9685 servo board, and the BNO055 IMU exactly as
  [WIRING.md](WIRING.md) specifies. The wheels may go on any of the four ports.
- Plug the ramp servos into servo board channels 0 and 1 and power the board's
  V+ from the regulated 5 V supply.
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
| Motor and servo I/O | `lgpio` GPIO, I2C enabled |
| Port/servo mapping | `~/.config/3tsahur/robot-settings.json` |

The installer validates the application, enables the services, and reboots.

## 03 / Connect

| Setting | Value |
| --- | --- |
| Wi-Fi name | `3TSahur-Swarm` |
| Raspberry Pi address | `10.42.0.1` |
| Driver Station | `http://10.42.0.1` |
| Debug page | `http://10.42.0.1/debug` |
| Direct service | `http://10.42.0.1:8080` |
| mDNS | `http://3tsahur.local` |

Change the default hotspot password before a public deployment.

## 04 / Map the Ports, Then Validate Without Floor Driving

The robot code is built in; there is nothing to upload. Everything that
depends on how you plugged things in is set on the Debug page.

1. Open `http://10.42.0.1/debug` and confirm Motor outputs, Servo board, and IMU
   are green.
2. Raise the wheels and tick the safety check.
3. Hold **Run** on each port and note which wheel turns. Set that port's
   **Drives wheel** to it. Choosing a wheel already on another port swaps them.
4. Tick **Invert** on any port whose wheel turns backwards at positive power.
5. Press **Save settings**, then hold each **wheel check** button: every wheel
   should roll the robot forward.
6. Check the ramp channels, press **Test closed** / **Test open** with the
   linkage clear, and leave the robot still until the gyro reports 3/3.
7. On the Driver Station (`http://10.42.0.1`), enable at low speed and test
   forward, reverse, both strafes, and both turns.
8. Verify that `Space`, `Esc`, Disable, switching tabs, and closing the page
   stop the drivetrain, and that the watchdog stops it if Wi-Fi drops.
9. Perform a floor test only after every direction and stop path is correct.

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
