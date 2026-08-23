<div align="center">

# OmniBot

### Raspberry Pi controller for a three-wheel holonomic robot and positional servo

[![Platform](https://img.shields.io/badge/Platform-Raspberry_Pi-c51a4a?style=flat-square&logo=raspberrypi&logoColor=white)](https://www.raspberrypi.com/)
[![Control](https://img.shields.io/badge/Control-Python_%2B_Pygame-3776ab?style=flat-square&logo=python&logoColor=white)](#robot-controller)
[![Drive](https://img.shields.io/badge/Drive-3_Wheel_Omni-0a7f5a?style=flat-square)](#large-robot-system)
[![License](https://img.shields.io/badge/License-CC_BY_4.0-0078d4?style=flat-square)](../LICENSE.md)

OmniBot is a controller-driven robot with three omni wheels spaced 120 degrees apart. A Raspberry Pi reads a Bluetooth gamepad, calculates holonomic wheel commands, drives three H-bridge motor channels, and controls a 300-degree positional servo through a PCA9685 HAT.

<strong>Quick navigation:</strong><br>
[Robot System](#large-robot-system) | [Robot Controller](#robot-controller) | [Installer](installer/) | [Connect & Drive](#connect-and-drive) | [Wiring](#hardware-and-wiring) | [Back to Club](../)

</div>

---

## Large Robot System

The Raspberry Pi is the complete robot controller. Unlike the STEM Research Academy robot, OmniBot does not host a web server or Wi-Fi dashboard. The operator pairs a Bluetooth controller directly to the Pi, and the local Pygame application handles controller input, safety arming, drive mixing, GPIO motor output, servo movement, and on-screen telemetry.

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
| Operator input | Generic Bluetooth controller read through Pygame/SDL |
| Motor output | Three bidirectional H-bridge channels using BOARD-numbered GPIO PWM |
| Auxiliary actuator | goBILDA 25-2 Torque positional servo on PCA9685 channel 0 |
| User interface | Local 800&times;480 Pygame status and telemetry display |
| Safety behavior | A-to-enable, neutral-stick arming, Y-to-disable, disconnect stop, and reversal dead time |

## Repository Structure

| File or folder | Purpose |
| --- | --- |
| [`omni_robot.py`](omni_robot.py) | Main Pygame application, controller mapping, GPIO motor control, safety state, and telemetry UI |
| [`omni_kinematics.py`](omni_kinematics.py) | Hardware-independent deadzones, input shaping, servo math, and three-wheel holonomic mixing |
| [`servo_hat.py`](servo_hat.py) | PCA9685 I2C setup and calibrated positional-servo pulse output |
| [`installer/`](installer/) | Raspberry Pi package installation, deployment, launcher creation, and desktop auto-start |
| [`tests/`](tests/) | Hardware-independent tests for controller mapping, power shaping, kinematics, and servo limits |

## Robot Controller

`omni_robot.py` is the robot runtime. It reads the gamepad at 60 frames per second, passes movement commands through the pure functions in `omni_kinematics.py`, and writes the resulting power levels to the three motors.

The drive software includes:

- A circular deadzone and cardinal-direction lock for predictable translation.
- A gated right-stick rotation axis that rejects accidental diagonal input.
- Direction normalization so every travel direction can use the available motor range.
- A short 100% breakaway pulse, followed by shaped 75–100% drive output.
- An 80 ms coast period before reversing a motor.
- Immediate motor stop when disabled, unarmed, or disconnected.

There is no remote server to start or browser address to open. The controller and runtime both operate locally on the Raspberry Pi.

## Raspberry Pi Installer

The [`installer/`](installer/) folder contains the automated Raspberry Pi deployment script. It installs the graphical runtime, GPIO/I2C and Bluetooth dependencies, deploys OmniBot to `~/OmniBot`, validates the Python files and drive math, creates `run_omnibot.sh`, enables desktop auto-start, and reboots the Pi.

Run the one-command installer as the normal Raspberry Pi user, without putting `sudo` first:

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/OmniBot/main/installer/install.sh | bash
```

See the [installer guide](installer/README.md) for prerequisites, installed components, update behavior, generated files, verification, and troubleshooting.

## Connect and Drive

OmniBot uses a Bluetooth gamepad rather than a web dashboard:

1. Pair the controller in Raspberry Pi OS Bluetooth settings.
2. Power the robot and allow the Pi desktop and OmniBot application to start.
3. Connect the controller if it was not already connected during startup.
4. Press and release `A` to enable the control system.
5. Hold both sticks centered for 0.25 seconds to arm the motors.
6. Drive with the controls below. Press `Y` at any time for a software stop.

| Control | Action |
| --- | --- |
| Left stick up / down | Drive forward / backward |
| Left stick left / right | Strafe left / right |
| Right stick up / down | Rotate the chassis |
| `A` | Enable, then wait for centered-stick arming |
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
~/OmniBot/run_omnibot.sh
```

Follow the runtime log:

```bash
tail -f ~/OmniBot/omnibot.log
```

Run the hardware-independent tests:

```bash
cd ~/OmniBot
python3 -m unittest discover -s tests -v
```

---

<div align="center">

Developed through the **[City Tech AI & Automation Club](../)**

</div>
