<div align="center">

# OmniBot Raspberry Pi Installer

### Automated deployment for the Pygame controller, GPIO/I2C support, Bluetooth, and desktop auto-start

[![Platform](https://img.shields.io/badge/Platform-Raspberry_Pi_OS-c51a4a?style=flat-square&logo=raspberrypi&logoColor=white)](https://www.raspberrypi.com/)
[![Desktop](https://img.shields.io/badge/Runtime-Pygame-3776ab?style=flat-square&logo=python&logoColor=white)](#installed-components)
[![Bluetooth](https://img.shields.io/badge/Controller-BlueZ-0a7f5a?style=flat-square&logo=bluetooth&logoColor=white)](#before-installing)
[![Parent](https://img.shields.io/badge/Project-OmniBot-111111?style=flat-square)](../)

`install.sh` prepares a Raspberry Pi to run OmniBot automatically after the graphical desktop starts. It installs system packages, enables I2C and Bluetooth, downloads or updates the application, validates the runtime, and creates the local launcher and auto-start entries.

<strong>Quick navigation:</strong><br>
[Before Installing](#before-installing) | [Quick Install](#quick-install) | [Installed Components](#installed-components) | [Updates](#existing-installations-and-updates) | [Troubleshooting](#troubleshooting) | [Back to OmniBot](../)

</div>

---

## Before Installing

Use a Raspberry Pi with:

- Raspberry Pi OS with Desktop and a normal non-root user account.
- Internet access during installation.
- A generic Bluetooth controller paired through Raspberry Pi OS.
- Three motor drivers wired to the BOARD pins documented in the [OmniBot guide](../#hardware-and-wiring).
- A shared ground between the Raspberry Pi and motor drivers.
- An optional PCA9685 servo HAT at I2C address `0x40` with a positional servo on channel 0.

> [!IMPORTANT]
> Do not run the installer by putting `sudo` before the command. It requests elevated access only for the system operations that require it. Keep motor power disabled and raise the chassis during initial setup.

## Quick Install

From a terminal on the Raspberry Pi, run:

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/OmniBot/main/installer/install.sh | bash
```

The installer reboots the Raspberry Pi five seconds after successful validation. Existing Bluetooth pairings are preserved.

To install from an existing local checkout instead:

```bash
cd ~/OmniBot/installer
bash install.sh
```

Set `OMNIBOT_APP_DIR` before running the script if the application should be installed somewhere other than `~/OmniBot`:

```bash
OMNIBOT_APP_DIR="$HOME/Robots/OmniBot" bash install.sh
```

## Installed Components

| Component | Result |
| --- | --- |
| System packages | Git, Python 3, Pygame, SMBus, I2C tools, Raspberry Pi GPIO support, and BlueZ |
| Desktop | Uses the existing Raspberry Pi desktop or installs supported desktop packages when none are detected |
| I2C | Enables the Raspberry Pi I2C interface through `raspi-config` when available |
| Application | Clones or updates OmniBot in `~/OmniBot` by default |
| Validation | Compiles the Python modules, imports hardware libraries, and runs the hardware-independent test suite |
| Launcher | Creates `~/OmniBot/run_omnibot.sh` with a single-instance lock and log redirection |
| Desktop auto-start | Creates `~/.config/autostart/omnibot.desktop` |
| Labwc auto-start | Adds an OmniBot-managed block to `~/.config/labwc/autostart` |
| Bluetooth | Enables the system Bluetooth service without erasing existing pairings |
| Boot mode | Selects graphical desktop auto-login when supported |

## Existing Installations and Updates

The installer is safe to rerun. When `~/OmniBot` is a clean Git checkout on `main`, it fetches the latest source and resets the checkout to `origin/main`.

If the existing folder is damaged, is not a Git checkout, contains local changes, or has local commits, the installer preserves it in a timestamped backup such as:

```text
~/OmniBot.backup.20260822-153000.1234
```

It then installs a fresh copy. Generated `run_omnibot.sh` and `omnibot.log` files do not count as local source changes.

## Generated Files

| Path | Purpose |
| --- | --- |
| `~/OmniBot/run_omnibot.sh` | Single-instance launcher for `omni_robot.py` |
| `~/OmniBot/omnibot.log` | Combined startup and runtime output |
| `~/OmniBot/.omnibot.lock` | Prevents duplicate controller processes |
| `~/.config/autostart/omnibot.desktop` | Desktop-session auto-start entry |
| `~/.config/labwc/autostart` | Labwc auto-start command managed between OmniBot markers |

## After Installation

After the Pi reboots:

1. Confirm the Bluetooth controller is connected.
2. Wait for the OmniBot Pygame window to appear.
3. Press and release `A`.
4. Center both sticks for 0.25 seconds to arm the drivetrain.
5. Test each direction with the robot raised off the floor.
6. Press `Y` and confirm that all drive motors stop immediately.

Run OmniBot manually if the desktop auto-start did not launch it:

```bash
~/OmniBot/run_omnibot.sh
```

Inspect the log:

```bash
tail -n 100 ~/OmniBot/omnibot.log
```

Rerun the validation tests:

```bash
cd ~/OmniBot
python3 -m unittest discover -s tests -v
```

## Troubleshooting

| Problem | Check |
| --- | --- |
| No Pygame window | Confirm the Pi booted to the graphical desktop, then inspect `omnibot.log` |
| Controller not found | Reconnect it in Bluetooth settings and restart the launcher |
| Robot remains unarmed | Press and release `A`, then hold both sticks at neutral for 0.25 seconds |
| Motors spin incorrectly | Verify the BOARD pin wiring and mirrored right-rear motor orientation |
| Servo unavailable | Confirm I2C is enabled, address `0x40` appears in `i2cdetect -y 1`, and channel 0 is wired correctly |
| Servo buzzes or hits a stop | Disconnect the load and reduce the pulse range in `servo_hat.py` |
| Installer preserves the old folder | Read the backup message; local changes or an invalid checkout caused a clean reinstall |

---

<div align="center">

Installer documentation for **[OmniBot](../)** · **[City Tech AI & Automation Club](../../)**

</div>
