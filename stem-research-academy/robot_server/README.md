# 3TSahur Robot Server

### Python control service for the mecanum drivetrain, camera, ramp, and dashboard

[![Language](https://img.shields.io/badge/language-Python%203.11%2B-111111?style=flat-square&logo=python&logoColor=white)](#package-map)
[![Interface](https://img.shields.io/badge/interface-Flask-000000?style=flat-square&logo=flask&logoColor=white)](#runtime)
[![Safety](https://img.shields.io/badge/safety-watchdog%20protected-6b7280?style=flat-square)](#runtime)

[Project overview](../README.md) · [Package map](#package-map) · [Wiring](../docs/WIRING.md) · [Installer](../installer/)

---

`robot_server` runs on the Raspberry Pi 4. It serves the browser dashboard,
captures the Logitech USB camera, mixes mecanum commands into four PWM motor
outputs, controls the two-servo ramp, and reports system health.

## Package Map

| Module | Responsibility |
| --- | --- |
| `app.py` | Flask routes, command expiry, sequence validation, and watchdog |
| `motor.py` | Mecanum mixing, tested polarity, and motor GPIO output |
| `actuators.py` | Mirrored two-servo ramp positions |
| `camera.py` | Logitech discovery, capture recovery, and MJPEG output |
| `health.py` | Cached Pi temperature, power, storage, and camera health |
| `templates/` | Dashboard page |
| `static/` | Dashboard JavaScript and CSS |

## Runtime

Install `requirements.txt`, then run:

```bash
python -m robot_server.app
```

| Environment | Behavior |
| --- | --- |
| Raspberry Pi with GPIO | Full motor and camera service |
| Computer without `RPi.GPIO` | Safe drivetrain simulation mode |
| Missing `pigpiod` | Ramp disabled while the API and dashboard remain available |
| Lost drive heartbeat | Watchdog stops all drivetrain outputs |

Production deployment is handled by the [installer](../installer/), not by
manually launching the development server.

## Validation

```bash
python -m unittest discover -s tests -v
```

The tests cover motor mixing and polarity, reversal dead-time, watchdog
heartbeats, camera recovery, ramp behavior, dashboard controls, API expiry,
sequence rejection, and hardware-independent health checks.

> [!CAUTION]
> Simulation tests do not replace raised-wheel validation on the physical
> robot. Follow the [setup guide](../docs/SETUP.md) before a floor test.

---

Return to the [STEM Research Academy project](../README.md).
