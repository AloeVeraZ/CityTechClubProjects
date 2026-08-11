<div align="center">

# STEM Research Academy

### One Raspberry Pi mecanum robot, two future ESP32 scout robots, and one shared control station

![Raspberry Pi](https://img.shields.io/badge/controller-Raspberry%20Pi-C51A4A?logo=raspberrypi&logoColor=white)
![Python](https://img.shields.io/badge/server-Python-3776AB?logo=python&logoColor=white)
![ESP32](https://img.shields.io/badge/scouts-2%20ESP32s-00979D)
![Status](https://img.shields.io/badge/status-mecanum%20control%20ready-b9ff38)

</div>

This research platform gives a team one browser dashboard for three robots. The Raspberry Pi creates its own Wi-Fi hotspot, hosts the website, streams a Logitech C270 webcam, and drives a four-wheel mecanum chassis. Two differential-drive ESP32 robots can join the hotspot; their camera and control panels are already reserved in the interface while their firmware is developed.

## Research team

The project is organized for **three mentors** and **two students**. Names can be added when the final roster is confirmed instead of putting guessed names in the repository.

| Role | Position | Focus |
|---|---|---|
| Mentor | Mentor 1 | Project guidance and research planning |
| Mentor | Mentor 2 | Mechanical and electrical systems |
| Mentor | Mentor 3 | Software, networking, and safety review |
| Student | Student 1 | Mecanum robot integration and testing |
| Student | Student 2 | ESP32 scout robots and camera integration |

## Current capabilities

- Creates the secured 2.4 GHz `tripletrobot` hotspot with NetworkManager.
- Serves the dashboard at `http://10.42.0.1:8080`.
- Opens the same dashboard automatically in a self-restarting fullscreen Chromium kiosk on the Pi display.
- Auto-sizes the dashboard for the attached display, phones, tablets, and laptops.
- Streams a Logitech C270 or other V4L2 webcam from `/dev/video0`.
- Drives forward/backward with W/S, strafes with A/D, and rotates with Q/E.
- Stops immediately when drive keys are released, the browser loses focus, or Space is pressed.
- Uses a server-side command watchdog to stop the motors if control messages disappear for 400 ms.
- Reserves the upper-right and lower-right quarters for two future two-motor ESP32 robots.
- Starts the hotspot and control server automatically after boot.
- Uses a clean, rerunnable installer based on the TrainUI installation workflow.

## Dashboard layout

```text
┌──────────────────────────────┬──────────────────────────────┐
│                              │ ESP32 Scout A                │
│  Mecanum robot               │ Camera + controls reserved   │
│  C270 feed + WASD controls   ├──────────────────────────────┤
│                              │ ESP32 Scout B                │
│                              │ Camera + controls reserved   │
└──────────────────────────────┴──────────────────────────────┘
             50%                           25% + 25%
```

## Raspberry Pi installation

Start with the current Raspberry Pi OS, connect the Pi to the internet, enable SSH, and attach the C270 webcam. Run the installer as the normal Pi user—not with `sudo`:

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/CityTechClubProjects/main/stem-research-academy/installer/install.sh | bash
```

The installer requests `sudo` only for packages, networking, user groups, and system services. It then reboots. Connect a phone or computer to:

```text
Wi-Fi network name (SSID): tripletrobot
Wi-Fi password:            STEMRobotics
Pi hostname:               tripletrobot
Website:                   http://10.42.0.1:8080
```

Wi-Fi uses a network name (SSID), not a username. The actual Raspberry Pi Linux login remains the normal account created in Raspberry Pi Imager; the installer does not rename that account because doing so can break its home directory, services, and SSH access.

The requested password `triplet` cannot be used with this WPA2 hotspot because it contains seven characters; WPA2 requires 8–63 characters. The installer therefore keeps the existing working password instead of breaking hotspot startup. Once an eight-character-or-longer replacement is chosen, update `HOTSPOT_PASSWORD` in `/etc/stem-research-academy/config.env` and rerun the installer.

Change the default password before demonstrations involving untrusted visitors.

### Rerunning and updating

Run the same `curl` command whenever the project should be updated. Every run:

1. Runs a complete Raspberry Pi OS upgrade, then installs current required packages.
2. Downloads a clean copy of the latest `main` branch.
3. Stops the old dashboard and preserves it as `~/STEMResearchAcademy.backup.TIMESTAMP`.
4. Replaces `~/STEMResearchAcademy` with the fresh project files.
5. Rebuilds the Python environment and upgrades its packages.
6. Reinstalls and enables the hotspot and dashboard services.
7. Installs or updates the compatible Chromium and Raspberry Pi desktop packages.
8. Recreates both current Wayland/labwc and older X11 kiosk autostart entries.
9. Reapplies auto-login, fullscreen, anti-blanking, and anti-sleep settings.
10. Compiles the Python source and verifies Flask/OpenCV imports before rebooting.

Persistent settings live outside the replaced folder at `/etc/stem-research-academy/config.env`, so hotspot credentials and future ESP32 camera URLs survive updates. If the installer is being tested without a reboot, use:

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/CityTechClubProjects/main/stem-research-academy/installer/install.sh | STEM_NO_REBOOT=1 bash
```

The Pi needs an internet path while updating. Once `wlan0` is acting as the hotspot, use Ethernet or a second Wi-Fi adapter for internet access before rerunning the installer. Every rerun downloads a clean application copy, upgrades required packages, rebuilds the Python environment, migrates configuration keys, and regenerates the system and kiosk files, so it can repair an older installation as well as update a current one.

For recovery testing only, `STEM_SKIP_OS_UPGRADE=1` can be passed to `bash` to skip the full operating-system upgrade while still refreshing the application and its configuration:

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/CityTechClubProjects/main/stem-research-academy/installer/install.sh | STEM_SKIP_OS_UPGRADE=1 bash
```

## Attached Pi screen

After installation and reboot, the Pi automatically signs in to its graphical desktop and immediately opens Chromium in fullscreen kiosk mode at `http://127.0.0.1:8080`. This is the same dashboard served to phones and laptops at `http://10.42.0.1:8080`.

The interface uses the browser viewport rather than a fixed pixel resolution. Wide screens use the mecanum panel on the left and the two ESP32 panels on the right. Narrow or portrait displays stack the panels vertically. If Chromium is closed or crashes, the kiosk launcher starts it again after two seconds.

The kiosk supports:

- Current Raspberry Pi OS using Wayland and labwc.
- Older Raspberry Pi OS desktop releases using X11/LXDE autostart.
- Raspberry Pi OS Lite, when compatible Raspberry Pi desktop packages are available.

Kiosk logs are stored at `~/.local/state/stem-robot-kiosk.log`.

## Motor wiring and first test

The pin directions come from the working four-motor test supplied with this project and use **BCM numbering**.

| Wheel assumption | Driver channel | Forward pin | Reverse pin |
|---|---|---:|---:|
| Front left | Driver 1, Motor A | GPIO 5 | GPIO 6 |
| Rear left | Driver 1, Motor B | GPIO 16 | GPIO 19 |
| Front right | Driver 2, Motor A | GPIO 20 | GPIO 21 |
| Rear right | Driver 2, Motor B (reversed wiring) | GPIO 13 | GPIO 26 |

The original test proves the electrical forward direction but does not identify which physical plug reaches each wheel. For the first test, lift the chassis so every wheel is clear of the floor, set speed to 20%, tap W, and verify all wheels push forward. If a driver channel reaches a different wheel, update only `DEFAULT_MOTOR_PINS` in `robot_server/motor.py`. Do not test strafing on the floor until the wheel mapping is confirmed.

An accessible hardware emergency stop or motor-power switch should still be used. Browser safety controls are an additional layer, not a substitute for disconnecting motor power.

## Keyboard controls

| Key | Motion |
|---|---|
| W / S | Forward / backward |
| A / D | Strafe left / right |
| Q / E | Rotate left / right |
| Space | Stop all motors immediately |

Multiple keys can be held for combined motion. The speed slider limits all four wheel outputs.

## ESP32 placeholders

Both future robots are expected to use two motors for differential drive and a camera. The Pi hotspot already supplies DHCP addresses in `10.42.0.0/24`. Once their camera firmware exists, add the stream URLs to `/etc/stem-research-academy/config.env`:

```bash
ESP32_ONE_STREAM_URL=http://10.42.0.20/stream
ESP32_TWO_STREAM_URL=http://10.42.0.21/stream
```

Then restart the dashboard:

```bash
sudo systemctl restart stem-robot-dashboard
```

Motor-control endpoints for the ESP32 robots are intentionally not implemented yet.

## Configuration and service commands

```bash
# Edit persistent settings
sudo nano /etc/stem-research-academy/config.env

# Watch server logs
sudo journalctl -u stem-robot-dashboard -f

# Check the hotspot
systemctl status stem-robot-hotspot
nmcli connection show stem-robot-hotspot

# Check the local fullscreen browser
tail -f ~/.local/state/stem-robot-kiosk.log

# Restart everything after configuration changes
sudo systemctl restart stem-robot-dashboard stem-robot-hotspot
```

## Local development

The server falls back to simulation mode when `RPi.GPIO` is unavailable, so the interface and API can be tested away from the Pi.

```bash
cd stem-research-academy
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m robot_server.app
```

## Project structure

```text
stem-research-academy/
├── installer/
│   ├── systemd/
│   │   ├── stem-robot-dashboard.service
│   │   └── stem-robot-hotspot.service
│   ├── hotspot.sh
│   └── install.sh
├── robot_server/
│   ├── static/
│   ├── templates/
│   ├── app.py
│   ├── camera.py
│   └── motor.py
├── tests/
├── requirements.txt
└── run.py
```
