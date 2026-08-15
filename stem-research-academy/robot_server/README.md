<div align="center">

# 3TSahur Robot Server

### Python control service for mecanum kinematics, USB camera streaming, ramp actuation, and telemetry

[![Language](https://img.shields.io/badge/Language-Python_3.11%2B-3776ab?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Web Framework](https://img.shields.io/badge/Framework-Flask-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Safety](https://img.shields.io/badge/Safety-Watchdog_Protected-0a7f5a?style=flat-square)](#runtime--safety)
[![License](https://img.shields.io/badge/License-CC_BY_4.0-0078d4?style=flat-square)](../../LICENSE.md)
[![Parent](https://img.shields.io/badge/Project-STEM_Research_Academy-111111?style=flat-square)](../)

This package implements the asynchronous hardware control daemon and browser dashboard serving the 3TSahur mecanum robot on Raspberry Pi 4.

[Package Map](#package-map) | [Runtime & Safety](#runtime--safety) | [Automated Validation](#automated-validation) | [Back to STEM Project](../)

</div>

---

## Package Map

`robot_server` coordinates communication between the browser front-end, hardware PWM drivers, camera pipeline, and health telemetry:

| Module | Core Responsibility |
| --- | --- |
| `app.py` | Flask HTTP & WebSocket endpoints, command timestamp validation, and hardware watchdog |
| `motor.py` | Holonomic mecanum kinematics mixing, polarity mapping, deadband compensation, and GPIO PWM |
| `actuators.py` | Mirrored dual-servo ramp position sequencing via `pigpio` socket |
| `camera.py` | Dynamic USB V4L2 camera discovery, auto-reconnect capture loop, and MJPEG encoder |
| `health.py` | Asynchronous caching of CPU temperature, core voltage, RAM, and disk utilization |
| `templates/` & `static/` | Responsive HTML5/CSS/JavaScript driving dashboard with touch/keyboard/gamepad support |

## Runtime & Safety

To start the service in local development mode:

```bash
python -m robot_server.app
```

| Operating Mode | Behavior & Fail-Safe Response |
| --- | --- |
| Raspberry Pi Hardware | Full GPIO PWM motor switching, camera streaming, and servo control |
| Host PC / Simulation | Automatic mock mode for dry-run testing without physical GPIO pins |
| `pigpiod` Unavailable | Ramp servos safely disabled while motor API and telemetry remain operational |
| Lost Heartbeat (>500ms) | Watchdog immediately zeros all four motor PWM channels |

> [!CAUTION]
> Simulation tests confirm API routes and mixing mathematics, but do not replace raised-wheel physical bench testing. Follow the [setup guide](../docs/SETUP.md) before conducting untethered floor maneuvers.

## Automated Validation

Execute the test suite to verify kinematics, safety timeouts, and health caching:

```bash
python -m unittest discover -s tests -v
```

---

<div align="center">

Designed and documented for **[STEM Research Academy](../)** · **[City Tech Robotics](../../)**

</div>
