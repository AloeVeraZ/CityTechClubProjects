<div align="center">

# OmniBot

### Raspberry Pi controller for a three-wheel holonomic robot, positional servo, and Wi-Fi dashboard

[![Platform](https://img.shields.io/badge/Platform-Raspberry_Pi-c51a4a?style=flat-square&logo=raspberrypi&logoColor=white)](https://www.raspberrypi.com/)
[![Control](https://img.shields.io/badge/Control-Python_%2B_Pygame-3776ab?style=flat-square&logo=python&logoColor=white)](#robot-controller)
[![Drive](https://img.shields.io/badge/Drive-3_Wheel_Omni-0a7f5a?style=flat-square)](#large-robot-system)
[![License](https://img.shields.io/badge/License-CC_BY_4.0-0078d4?style=flat-square)](../LICENSE.md)

OmniBot is a three-wheel holonomic robot controlled by a Raspberry Pi. Operators can drive with a Bluetooth gamepad connected to the Pi or from a laptop, phone, or gamepad through the robot's private Wi-Fi dashboard. The runtime calculates wheel commands, drives three H-bridge motor channels, and controls a positional servo through a PCA9685 HAT.

<strong>Quick navigation:</strong><br>
[Robot System](#large-robot-system) | [Robot Controller](#robot-controller) | [Installer](installer/) | [Connect & Drive](#connect-and-drive) | [Wiring](#hardware-and-wiring) | [Back to Club](../)

</div>

---

## Large Robot System

The Raspberry Pi runs the complete robot controller. The local Pygame application combines Bluetooth or Wi-Fi input with safety arming, drive mixing, GPIO motor output, servo movement, and on-screen telemetry. A background HTTP server supplies the browser dashboard and exchanges expiring commands and live status.

<table>
  <tr>
    <td align="center"><strong>Bluetooth Controller</strong></td>
    <td align="center">&rarr;<br>BlueZ / SDL</td>
    <td align="center"><strong>Raspberry Pi</strong></td>
    <td align="center">&rarr;<br>Pygame Input</td>
    <td align="center"><strong>OmniBot Runtime</strong></td>
  </tr>
  <tr>
    <td colspan="2"></td>
    <td align="center"><strong>OmniBot Runtime</strong></td>
    <td align="center">&rarr;<br>BOARD GPIO PWM</td>
    <td align="center"><strong>H-Bridges &amp; 3 Drive Motors</strong></td>
  </tr>
  <tr>
    <td colspan="2"></td>
    <td align="center"><strong>OmniBot Runtime</strong></td>
    <td align="center">&rarr;<br>I2C / PCA9685</td>
    <td align="center"><strong>300&deg; Positional Servo</strong></td>
  </tr>
</table>

| Subsystem | Technical configuration |
| --- | --- |
| Main controller | Raspberry Pi running Raspberry Pi OS with Desktop |
| Drivetrain | Three independently driven omni wheels mounted 120 degrees apart |
| Operator input | Local Bluetooth gamepad or browser over the private OmniBot Wi-Fi network |
| Motor output | Three bidirectional H-bridge channels using BOARD-numbered GPIO PWM |
| Auxiliary actuator | goBILDA 25-2 Torque positional servo on PCA9685 channel 0 |
| User interfaces | Local 800&times;480 Pygame display and responsive browser dashboard |
| Safety behavior | Explicit enable, neutral-input arming, immediate stop, disconnect/expiry stop, session and sequence checks, and reversal dead time |

## Repository Structure

| File or folder | Purpose |
| --- | --- |
| [`omni_robot.py`](omni_robot.py) | Main Pygame application, controller mapping, GPIO motor control, safety state, and telemetry UI |
| [`wifi_control.py`](wifi_control.py) | Thread-safe remote input state, command watchdog, HTTP API, and static web server |
| [`web/`](web/) | Laptop/phone dashboard with keyboard, touch, and browser-gamepad controls |
| [`omni_kinematics.py`](omni_kinematics.py) | Hardware-independent deadzones, input shaping, servo math, and three-wheel holonomic mixing |
| [`servo_hat.py`](servo_hat.py) | PCA9685 I2C setup and calibrated positional-servo pulse output |
| [`installer/`](installer/) | Raspberry Pi deployment, hotspot configuration, Nginx proxy, launcher, and desktop auto-start |
| [`tests/`](tests/) | Hardware-independent tests for kinematics, servo limits, and Wi-Fi command safety |

## Robot Controller

`omni_robot.py` is the robot runtime. It reads the selected controller at 60 frames per second, passes movement commands through the pure functions in `omni_kinematics.py`, and writes the resulting power levels to the three motors.

The drive software includes:

- A circular deadzone and cardinal-direction lock for predictable translation.
- A gated right-stick rotation axis that rejects accidental diagonal input.
- Direction normalization so every travel direction can use the available motor range.
- A short 100% breakaway pulse, followed by shaped 75–100% drive output.
- An 80 ms coast period before reversing a motor.
- Immediate motor stop when disabled, unarmed, disconnected, or when a moving Wi-Fi command expires.

Wi-Fi control uses one active browser session, increasing command sequence numbers, and a 200 ms moving-command watchdog. Stale, conflicting, non-finite, and implausibly timed commands are rejected. Enabling from the dashboard selects Wi-Fi control; pressing `A` on the local controller takes control back.

## Raspberry Pi Installer

The [`installer/`](installer/) folder contains the automated deployment scripts. They install the graphical runtime, GPIO/I2C and Bluetooth dependencies, NetworkManager, Avahi, and Nginx; clone the current CityTechClubProjects repository and run OmniBot from `~/CityTechClubProjects/OmniBot`; validate the runtime; create the private hotspot and dashboard proxy; enable desktop auto-start; and reboot the Pi.

Run the one-command installer as the normal Raspberry Pi user, without putting `sudo` first:

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/CityTechClubProjects/main/OmniBot/installer/curl-install.sh | bash
```

See the [installer guide](installer/README.md) for prerequisites, installed components, update behavior, generated files, verification, and troubleshooting.

## Connect and Drive

After installation, OmniBot supports either control path.

### Wi-Fi dashboard

1. Join the `OmniBot` Wi-Fi network with password `omnibot1`.
2. Open `http://10.42.0.1`. If mDNS is available, `http://omnibot.local` also works; `http://10.42.0.1:8080` is the direct fallback.
3. Select **Enable**, then leave all movement controls neutral for 0.25 seconds.
4. Drive with `W/S` for forward/reverse, `A/D` for strafe, and `Q/E` for rotation. Touch controls and a gamepad connected to the browser are also supported.
5. Press Space or Escape, select **Stop**, or leave the page to disable and stop.

Use `[` and `]` or the dashboard servo buttons to move the servo, and `X` to center it. The browser refreshes moving commands every 80 ms; if updates stop for 200 ms, the Pi zeros the command, disables Wi-Fi control, and requires a fresh Enable.

### Local Bluetooth controller

1. Pair the controller in Raspberry Pi OS Bluetooth settings.
2. Power the robot and allow the Pi desktop and OmniBot application to start.
3. Connect the controller if it was not already connected during startup.
4. Press and release `A` to select local control and enable the system.
5. Hold both sticks centered for 0.25 seconds to arm the motors.
6. Drive with the controls below. Press `Y` at any time for a software stop.

| Control | Action |
| --- | --- |
| Left stick up / down | Drive forward / backward |
| Left stick left / right | Strafe left / right |
| Right stick up / down | Rotate the chassis |
| `A` | Select local control and enable, then wait for centered-stick arming |
| `Y` | Disable and stop all drive motors immediately |
| Left trigger | Move servo toward &minus;150&deg; |
| Right trigger | Move servo toward +150&deg; |
| `X` | Return the positional servo to 0&deg; |

The left stick is cardinal-locked: when driving forward or backward, small sideways drift is ignored; when strafing, small vertical drift is ignored. Rotation works only while the other right-stick axis remains near center.

## Hardware and Wiring

GPIO mode is `BOARD`, so the values below are physical Raspberry Pi header pin numbers.

| Motor | IN1 | IN2 |
| --- | ---: | ---: |
| Front | 40 | 38 |
| Left rear | 15 | 35 |
| Right rear | 12 | 16 |

Motor 2 is inverted in software to account for its mirrored wiring or mounting direction. Exact forward and backward motion intentionally leaves the front wheel stopped while the rear wheels rotate in opposite directions; the omni rollers allow the front wheel to slide laterally. Pure rotation commands all three motors in the same direction.

The supported servo interface is a Waveshare-style 16-channel PCA9685 Servo Driver HAT at I2C address `0x40`. Connect a 300-degree positional servo to channel 0. Before attaching a mechanism, test the servo unloaded and calibrate `SERVO_MIN_PULSE_US`, `SERVO_CENTER_PULSE_US`, and `SERVO_MAX_PULSE_US` in [`servo_hat.py`](servo_hat.py).

> [!CAUTION]
> Raise the chassis so every wheel can spin freely during initial testing. Do not power drive motors from the Raspberry Pi 5 V rail. Verify motor power, driver capacity, a common Pi/driver ground, servo wire orientation, and mechanical clearance before enabling motion.

## Runtime and Testing

The installer creates a launcher that starts OmniBot automatically with the desktop. To run it manually:

```bash
~/CityTechClubProjects/OmniBot/run_omnibot.sh
```

Follow the runtime log:

```bash
tail -f ~/CityTechClubProjects/OmniBot/omnibot.log
```

Run the hardware-independent tests:

```bash
cd ~/CityTechClubProjects/OmniBot
python3 -m unittest discover -s tests -v
```

---

<div align="center">

Developed through the **[City Tech AI & Automation Club](../)**

</div>
