<div align="center">

# STEM Research Academy

### One Raspberry Pi mecanum robot, two ECHO differential-drive scouts, and one shared control station

![Raspberry Pi](https://img.shields.io/badge/controller-Raspberry%20Pi-C51A4A?logo=raspberrypi&logoColor=white)
![Python](https://img.shields.io/badge/server-Python-3776AB?logo=python&logoColor=white)
![ESP32](https://img.shields.io/badge/scouts-2%20ESP32s-00979D)
![Status](https://img.shields.io/badge/status-mecanum%20control%20ready-b9ff38)

</div>

This research platform gives a team one browser dashboard for three robots. The Raspberry Pi creates its own Wi-Fi hotspot, hosts the website, streams a Logitech C270 webcam, and drives a four-wheel mecanum chassis. Two identical ECHO-board differential-drive robots join the same hotspot and are controlled through the upper-right and lower-right HUD panels.

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

- Creates the secured 2.4 GHz `EchoSwarm` hotspot with NetworkManager.
- Serves the dashboard at `http://10.42.0.1`, `http://echoswarm.local`, and the fallback `http://10.42.0.1:8080`.
- Opens it automatically in a self-restarting, resizable Chromium application window on the Pi display.
- Auto-sizes the dashboard for the attached display, phones, tablets, and laptops.
- Streams a Logitech C270 or other V4L2 webcam from `/dev/video0`.
- Drives forward/backward with W/S, strafes with A/D, and rotates with Q/E.
- Stops immediately when drive keys are released, the browser loses focus, or a kill switch is pressed.
- Uses a latest-command-only channel, 300 ms command expiration, sequence checks, and a 200 ms server watchdog. Delayed commands are discarded instead of replayed.
- Proxies status, CSI disturbance data, and fail-safe drive commands to both ECHO scouts.
- Starts the hotspot and control server automatically after boot.
- Uses a clean, rerunnable installer based on the TrainUI installation workflow.

## Dashboard layout

```text
┌──────────────────────────────┬──────────────────────────────┐
│                              │ ECHO Scout A                 │
│  Mecanum robot               │ Camera + drive controls      │
│  C270 feed + WASD controls   ├──────────────────────────────┤
│                              │ ECHO Scout B                 │
│                              │ Camera + drive controls      │
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
Wi-Fi network name (SSID): EchoSwarm
Wi-Fi password:            roboswarm1
Pi hostname:               echoswarm
Website:                   http://10.42.0.1
Named address:             http://echoswarm.local
Direct fallback:           http://10.42.0.1:8080
```

Wi-Fi uses a network name (SSID), not a username. The actual Raspberry Pi Linux login remains the normal account created in Raspberry Pi Imager; the installer does not rename that account because doing so can break its home directory, services, and SSH access.

Change the default password before demonstrations involving untrusted visitors.

### Rerunning and updating

Run the same `curl` command whenever the project should be updated. Every run:

1. Runs a complete Raspberry Pi OS upgrade, then installs current required packages.
2. Downloads a clean copy of the latest `main` branch.
3. Removes stale installer backups, cleans the APT cache, checks free space, and stops the old dashboard.
4. Replaces `~/STEMResearchAcademy` with fresh project files while avoiding a duplicate virtual environment.
5. Rebuilds the Python environment and upgrades its packages.
6. Reinstalls and enables the hotspot and dashboard services.
7. Installs or updates the compatible Chromium and Raspberry Pi desktop packages.
8. Recreates both current Wayland/labwc and older X11 dashboard autostart entries.
9. Reapplies auto-login, resizable-window, anti-blanking, and anti-sleep settings.
10. Compiles the Python source and verifies Flask/OpenCV imports before rebooting.

Persistent hardware and camera settings live outside the replaced folder at `/etc/stem-research-academy/config.env`. The installer deliberately reapplies the documented `EchoSwarm` credentials on every update so the Pi and both flashed scouts cannot drift onto different network settings.

The Pi needs an internet path while updating. Once `wlan0` is acting as the hotspot, use Ethernet or a second Wi-Fi adapter for internet access before rerunning the installer. Every rerun downloads a clean application copy, upgrades required packages, rebuilds the Python environment, migrates configuration keys, and regenerates the system and kiosk files, so it can repair an older installation as well as update a current one. At the end, a transient systemd timer schedules the reboot independently of the `curl | bash` process, making automatic reboot reliable after the terminal command exits.

For recovery testing only, `STEM_SKIP_OS_UPGRADE=1` can be passed to `bash` to skip the full operating-system upgrade while still refreshing the application and its configuration:

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/CityTechClubProjects/main/stem-research-academy/installer/install.sh | STEM_SKIP_OS_UPGRADE=1 bash
```

## Attached Pi screen

After installation and reboot, the Pi signs in to its graphical desktop and opens Chromium as a normal application window at `http://127.0.0.1:8080`. It can be resized or minimized, leaving the desktop and Terminal available. Closing it causes the launcher to reopen it after two seconds, so the control station cannot remain accidentally closed. Phones and laptops on `EchoSwarm` use `http://10.42.0.1` or `http://echoswarm.local`.

The interface uses the browser viewport rather than a fixed pixel resolution. Wide screens use the mecanum panel on the left and the two ESP32 panels on the right. Narrow or portrait displays stack the panels vertically.

The kiosk supports:

- Current Raspberry Pi OS using Wayland and labwc.
- Older Raspberry Pi OS desktop releases using X11/LXDE autostart.
- Raspberry Pi OS Lite, when compatible Raspberry Pi desktop packages are available.

Dashboard-window logs are stored at `~/.local/state/stem-robot-kiosk.log`.

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

| Robot | Key | Motion |
|---|---|---|
| Big mecanum | W / S | Forward / backward |
| Big mecanum | A / D | Strafe left / right |
| Big mecanum | Q / E | Rotate left / right |
| Big mecanum | Space | Kill all four big-robot motors |
| ECHO Scout A | Arrow keys | Differential drive |
| ECHO Scout B | I / J / K / L | Forward / left / backward / right |
| All robots | Escape | Kill every robot immediately |

Multiple keys can be held for combined motion. The speed slider limits all four wheel outputs.

Each keyboard group is routed to a different API endpoint: WASD/QE cannot issue Scout commands, Arrow keys cannot issue mecanum commands, and IJKL cannot issue commands to either of the other robots. The browser keeps at most one request in flight per robot and overwrites pending input with the newest state, preventing a slow connection from building a motor-command backlog.

If the header says `GPIO unavailable - motors disabled`, the keyboard and web server are working but the Raspberry Pi GPIO backend did not load. Rerun the installer and check `sudo journalctl -u stem-robot-dashboard -n 100` rather than continuing a motor test.

## ECHO Scout firmware

The shared Arduino sketch is [`firmware/echo-scout/ECHO_Robot_Controller.ino`](firmware/echo-scout/ECHO_Robot_Controller.ino). Flash one board with `ROBOT_ID = 'A'` and the other with `ROBOT_ID = 'B'`. Both join `EchoSwarm` in Wi-Fi station mode, start with their motors stopped, use ECHO motor channels 1 and 6 through EchoLib's `TankDrive`, and advertise these addresses:

```text
http://echo-scout-a.local
http://echo-scout-b.local
```

The Pi calls the scouts through same-origin proxy endpoints, so a phone only needs to open the main Pi dashboard. Each scout sends a UDP heartbeat to the Pi once per second, allowing the HUD to confirm `Connected` even before cameras are fitted. Each scout also serves a small independent touch UI for bench testing. Both layers use a 500 ms firmware watchdog; if commands stop arriving, the affected scout stops itself.

The sketch exposes `/drive`, `/stop`, `/status`, and `/motion`. `/status` includes connection strength, stopped/running state, uptime, and the coarse CSI disturbance reading. Read the [firmware-specific guide](firmware/echo-scout/README.md) before the first wheels-up motor test.

If separate ESP32-CAM boards are installed, the HUD expects:

```text
http://echo-scout-a-cam.local/stream
http://echo-scout-b-cam.local/stream
```

Those URLs can be overridden with `ESP32_ONE_STREAM_URL` and `ESP32_TWO_STREAM_URL` in `/etc/stem-research-academy/config.env`.

## Configuration and service commands

```bash
# Edit persistent settings
sudo nano /etc/stem-research-academy/config.env

# Watch server logs
sudo journalctl -u stem-robot-dashboard -f

# Check the hotspot
systemctl status stem-robot-hotspot
nmcli connection show stem-robot-hotspot

# Check the local dashboard window
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
