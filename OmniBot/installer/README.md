<div align="center">

# OmniBot Raspberry Pi Installer

### Automated deployment for Pygame, GPIO/I2C, Bluetooth, a private Wi-Fi hotspot, and the browser dashboard

[![Platform](https://img.shields.io/badge/Platform-Raspberry_Pi_OS-c51a4a?style=flat-square&logo=raspberrypi&logoColor=white)](https://www.raspberrypi.com/)
[![Desktop](https://img.shields.io/badge/Runtime-Pygame-3776ab?style=flat-square&logo=python&logoColor=white)](#installed-components)
[![Bluetooth](https://img.shields.io/badge/Controller-BlueZ-0a7f5a?style=flat-square&logo=bluetooth&logoColor=white)](#before-installing)
[![Parent](https://img.shields.io/badge/Project-OmniBot-111111?style=flat-square)](../)

`curl-install.sh` safely downloads `install.sh` before execution. The main installer prepares a Raspberry Pi to run OmniBot automatically after the graphical desktop starts, creates a private Wi-Fi hotspot, exposes the dashboard through Nginx, and preserves local Bluetooth control.

<strong>Quick navigation:</strong><br>
[Before Installing](#before-installing) | [Quick Install](#quick-install) | [Installed Components](#installed-components) | [Updates](#existing-installations-and-updates) | [Troubleshooting](#troubleshooting) | [Back to OmniBot](../)

</div>

---

## Before Installing

Use a Raspberry Pi with:

- Raspberry Pi OS with Desktop and a normal non-root user account.
- Internet access during installation.
- A Wi-Fi adapter that supports access-point mode.
- An optional generic Bluetooth controller paired through Raspberry Pi OS.
- Three motor drivers wired to the BOARD pins documented in the [OmniBot guide](../#hardware-and-wiring).
- A shared ground between the Raspberry Pi and motor drivers.
- An optional PCA9685 servo HAT at I2C address `0x40` with a positional servo on channel 0.

> [!IMPORTANT]
> Do not run the installer by putting `sudo` before the command. It requests elevated access only for the system operations that require it. Keep motor power disabled and raise the chassis during initial setup.

## Quick Install

From a terminal on the Raspberry Pi, run:

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/CityTechClubProjects/main/OmniBot/installer/curl-install.sh | bash
```

The installer reboots the Raspberry Pi five seconds after successful validation. Existing Bluetooth pairings are preserved.

To install from an existing local checkout instead:

```bash
cd ~/CityTechClubProjects/OmniBot/installer
bash install.sh
```

Set `OMNIBOT_REPO_DIR` if the CityTechClubProjects checkout should be installed somewhere other than `~/CityTechClubProjects`. Set `OMNIBOT_REPO_BRANCH` to install a branch other than `main`:

```bash
OMNIBOT_REPO_DIR="$HOME/Robots/CityTechClubProjects" OMNIBOT_REPO_BRANCH=main bash install.sh
```

## Installed Components

| Component | Result |
| --- | --- |
| System packages | Curl, Git, Python 3, Pygame, SMBus, I2C tools, Raspberry Pi GPIO support, BlueZ, NetworkManager, Avahi, and Nginx |
| Desktop | Uses the existing Raspberry Pi desktop or installs supported desktop packages when none are detected |
| I2C | Enables the Raspberry Pi I2C interface through `raspi-config` when available |
| Application | Clones or updates CityTechClubProjects in `~/CityTechClubProjects` and runs its `OmniBot` subdirectory |
| Validation | Compiles all Python modules, checks web assets and shell syntax, imports hardware libraries, and runs the hardware-independent test suite |
| Hotspot | Creates the NetworkManager connection `omnibot-hotspot` and starts it through `omnibot-hotspot.service` |
| Local name | Sets the hostname to `omnibot` and enables Avahi for `omnibot.local` |
| Dashboard proxy | Proxies port 80 to the Python control server on port 8080 through Nginx |
| Launcher | Creates `~/CityTechClubProjects/OmniBot/run_omnibot.sh` with a single-instance lock and log redirection |
| Desktop auto-start | Creates `~/.config/autostart/omnibot.desktop` |
| Labwc auto-start | Adds an OmniBot-managed block to `~/.config/labwc/autostart` |
| Bluetooth | Enables the system Bluetooth service without erasing existing pairings |
| Boot mode | Selects graphical desktop auto-login when supported |

## Existing Installations and Updates

The installer is safe to rerun. When the application directory is a clean Git checkout on the selected branch, it fetches the latest source and resets the checkout to the matching remote branch.

If the existing folder is damaged, is not a Git checkout, contains local changes, or has local commits, the installer preserves it in a timestamped backup such as:

```text
~/CityTechClubProjects.backup.20260822-153000.1234
```

It then installs a fresh copy. Generated `run_omnibot.sh` and `omnibot.log` files do not count as local source changes. The root-owned hotspot configuration lives outside the checkout and survives application upgrades.

## Generated Files

| Path | Purpose |
| --- | --- |
| `~/CityTechClubProjects/OmniBot/run_omnibot.sh` | Single-instance launcher for `omni_robot.py` |
| `~/CityTechClubProjects/OmniBot/omnibot.log` | Combined startup and runtime output |
| `~/CityTechClubProjects/OmniBot/.omnibot.lock` | Prevents duplicate controller processes |
| `~/.config/autostart/omnibot.desktop` | Desktop-session auto-start entry |
| `~/.config/labwc/autostart` | Labwc auto-start command managed between OmniBot markers |
| `/etc/omnibot/config.env` | Root-only hotspot settings; defaults to SSID `OmniBot` and password `omnibot1` |
| `/usr/local/sbin/omnibot-hotspot` | Installed hotspot configuration helper |
| `/etc/systemd/system/omnibot-hotspot.service` | Boot-time hotspot service |
| `/etc/nginx/sites-available/omnibot-dashboard` | Port-80 dashboard reverse proxy |

## After Installation

After the Pi reboots:

1. Wait for the OmniBot Pygame window to appear.
2. Join Wi-Fi network `OmniBot` using password `omnibot1`.
3. Open `http://10.42.0.1`, select **Enable**, and keep the controls neutral for 0.25 seconds.
4. Test each direction with the robot raised off the floor, then select **Stop** and confirm every drive motor stops.
5. For local control, connect the Bluetooth controller, press and release `A`, center both sticks for 0.25 seconds, and press `Y` to test the immediate stop.

`http://omnibot.local` is the friendly mDNS address when the client supports it, and `http://10.42.0.1:8080` bypasses Nginx as a direct fallback. To change the Wi-Fi name or password, edit `/etc/omnibot/config.env` with `sudo`, then reboot. WPA-PSK passwords must contain at least eight characters.

Run OmniBot manually if the desktop auto-start did not launch it:

```bash
~/CityTechClubProjects/OmniBot/run_omnibot.sh
```

Inspect the log:

```bash
tail -n 100 ~/CityTechClubProjects/OmniBot/omnibot.log
```

Rerun the validation tests:

```bash
cd ~/CityTechClubProjects/OmniBot
python3 -m unittest discover -s tests -v
```

## Troubleshooting

| Problem | Check |
| --- | --- |
| Installer reports a certificate error | Confirm `timedatectl` shows the correct date and synchronized clock, complete any Wi-Fi captive-portal login, and remove broken HTTPS proxy/custom apt sources. The installer synchronizes time and rebuilds `/etc/ssl/certs` automatically; it never disables TLS verification |
| Installer fails during other package setup | Read the named step and command in the final error. Check internet access, then run `sudo dpkg --configure -a` and `sudo apt-get update` before rerunning |
| No `OmniBot` Wi-Fi network | Run `systemctl status omnibot-hotspot`, verify the Wi-Fi interface in `/etc/omnibot/config.env`, and confirm access-point support |
| Dashboard does not open | Try `http://10.42.0.1:8080`, inspect `omnibot.log`, then check `systemctl status nginx` |
| Dashboard stops while moving | This is the 200 ms safety watchdog; keep the page active and select **Enable** again |
| No Pygame window | Confirm the Pi booted to the graphical desktop, then inspect `omnibot.log` |
| Controller not found | Reconnect it in Bluetooth settings and restart the launcher |
| Robot remains unarmed | Enable the selected input source, then hold every movement input neutral for 0.25 seconds |
| Motors spin incorrectly | Verify the BOARD pin wiring and mirrored right-rear motor orientation |
| Servo unavailable | Confirm I2C is enabled, address `0x40` appears in `i2cdetect -y 1`, and channel 0 is wired correctly |
| Servo buzzes or hits a stop | Disconnect the load and reduce the pulse range in `servo_hat.py` |
| Installer preserves the old folder | Read the backup message; local changes or an invalid checkout caused a clean reinstall |

---

<div align="center">

Installer documentation for **[OmniBot](../)** · **[City Tech AI & Automation Club](../../)**

</div>
