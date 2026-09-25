"""The only robot settings that change after wiring: port and servo mapping.

The pins themselves are fixed in ``hardware.py``. What the Debug page edits,
and what is saved here, is:

* which motor port (1-4) drives each wheel, and whether that port is inverted;
* which servo board channel (0-15) drives each half of the ramp, whether it is
  mirrored, and the ramp's closed/open angles and pulse range.

Settings are stored as JSON outside the application folder, so reinstalling
or updating the software keeps them.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from . import hardware
from .errors import ConfigurationError


DEFAULT_PATH = "~/.config/3tsahur/robot-settings.json"


def settings_path() -> Path:
    return Path(os.environ.get("STEM_ROBOT_SETTINGS", DEFAULT_PATH)).expanduser()


@dataclass(frozen=True)
class RampServo:
    channel: int
    reversed: bool = False


@dataclass(frozen=True)
class RobotSettings:
    # wheel name -> motor port. Same layout as the MotionModule Mecanum sample.
    wheels: dict[str, int] = field(default_factory=lambda: {
        "front_left": 1, "rear_left": 2, "front_right": 3, "rear_right": 4,
    })
    inverted: dict[int, bool] = field(default_factory=lambda: {port: False for port in hardware.MOTOR_PORTS})
    ramp_servos: dict[str, RampServo] = field(default_factory=lambda: {
        "ramp_left": RampServo(0, False),
        # The second ramp servo is mounted mirrored, as on the original robot.
        "ramp_right": RampServo(1, True),
    })
    ramp_closed_angle: float = 0.0
    ramp_open_angle: float = 120.0
    ramp_min_pulse_us: int = 1000
    ramp_max_pulse_us: int = 2000

    def port_for(self, wheel: str) -> int:
        return self.wheels[wheel]

    def wheel_for(self, port: int) -> str | None:
        return next((wheel for wheel, value in self.wheels.items() if value == port), None)

    def to_dict(self) -> dict:
        return {
            "wheels": dict(self.wheels),
            "inverted": {str(port): value for port, value in sorted(self.inverted.items())},
            "ramp": {
                "servos": {
                    name: {"channel": servo.channel, "reversed": servo.reversed}
                    for name, servo in self.ramp_servos.items()
                },
                "closed_angle": self.ramp_closed_angle,
                "open_angle": self.ramp_open_angle,
                "min_pulse_us": self.ramp_min_pulse_us,
                "max_pulse_us": self.ramp_max_pulse_us,
            },
        }


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool):
        raise ConfigurationError(f"{label} must be a whole number")
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, str) and value.strip().lstrip("-").isdecimal():
        value = int(value.strip())
    if not isinstance(value, int):
        raise ConfigurationError(f"{label} must be a whole number")
    return value


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{label} must be a number")
    value = float(value)
    if not math.isfinite(value):
        raise ConfigurationError(f"{label} must be finite")
    return value


def _flag(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigurationError(f"{label} must be true or false")
    return value


def from_dict(data: object) -> RobotSettings:
    """Validate a settings dictionary. Missing sections keep their defaults."""

    if not isinstance(data, dict):
        raise ConfigurationError("Settings must be a JSON object")
    defaults = RobotSettings()

    wheels_data = data.get("wheels", defaults.wheels)
    if not isinstance(wheels_data, dict):
        raise ConfigurationError("wheels must map each wheel to a motor port")
    unknown = set(wheels_data) - set(hardware.WHEELS)
    if unknown:
        raise ConfigurationError(f"Unknown wheel {sorted(unknown)[0]!r}")
    wheels = {}
    for wheel in hardware.WHEELS:
        if wheel not in wheels_data:
            raise ConfigurationError(f"Choose a motor port for {hardware.WHEEL_LABELS[wheel].lower()}")
        port = _integer(wheels_data[wheel], f"{wheel} port")
        if port not in hardware.MOTOR_PORTS:
            raise ConfigurationError(f"{hardware.WHEEL_LABELS[wheel]} must use motor port 1, 2, 3 or 4")
        wheels[wheel] = port
    for port in hardware.MOTOR_PORTS:
        using = [hardware.WHEEL_LABELS[wheel].lower() for wheel, value in wheels.items() if value == port]
        if len(using) > 1:
            raise ConfigurationError(f"Motor port {port} is assigned to both {using[0]} and {using[1]}")

    inverted_data = data.get("inverted", {})
    if not isinstance(inverted_data, dict):
        raise ConfigurationError("inverted must map motor ports to true or false")
    inverted = dict(defaults.inverted)
    for key, value in inverted_data.items():
        port = _integer(key, "Inverted motor port")
        if port not in hardware.MOTOR_PORTS:
            raise ConfigurationError(f"There is no motor port {port}")
        inverted[port] = _flag(value, f"Port {port} inverted")

    ramp = data.get("ramp", {})
    if not isinstance(ramp, dict):
        raise ConfigurationError("ramp must be an object")
    servos_data = ramp.get("servos", {})
    if not isinstance(servos_data, dict):
        raise ConfigurationError("ramp.servos must be an object")
    unknown = set(servos_data) - set(hardware.RAMP_SERVOS)
    if unknown:
        raise ConfigurationError(f"Unknown ramp servo {sorted(unknown)[0]!r}")
    ramp_servos = dict(defaults.ramp_servos)
    for name, item in servos_data.items():
        if not isinstance(item, dict):
            raise ConfigurationError(f"{name} must be an object")
        channel = _integer(item.get("channel", ramp_servos[name].channel), f"{name} channel")
        if not 0 <= channel < hardware.SERVO_CHANNELS:
            raise ConfigurationError(f"{hardware.RAMP_SERVO_LABELS[name]} must use servo channel 0-15")
        ramp_servos[name] = RampServo(channel, _flag(item.get("reversed", ramp_servos[name].reversed), f"{name} reversed"))
    channels = [servo.channel for servo in ramp_servos.values()]
    if len(set(channels)) != len(channels):
        raise ConfigurationError(f"Both ramp servos are set to servo channel {channels[0]}")

    closed = _number(ramp.get("closed_angle", defaults.ramp_closed_angle), "Ramp closed angle")
    opened = _number(ramp.get("open_angle", defaults.ramp_open_angle), "Ramp open angle")
    for label, angle in (("closed", closed), ("open", opened)):
        if not 0 <= angle <= 180:
            raise ConfigurationError(f"Ramp {label} angle must be from 0 through 180 degrees")
    if closed == opened:
        raise ConfigurationError("Ramp open and closed angles must differ")
    minimum = _integer(ramp.get("min_pulse_us", defaults.ramp_min_pulse_us), "Ramp minimum pulse")
    maximum = _integer(ramp.get("max_pulse_us", defaults.ramp_max_pulse_us), "Ramp maximum pulse")
    if not hardware.SERVO_MIN_PULSE_US <= minimum < maximum <= hardware.SERVO_MAX_PULSE_US:
        raise ConfigurationError(
            f"Ramp pulse range must be inside {hardware.SERVO_MIN_PULSE_US}-{hardware.SERVO_MAX_PULSE_US} µs "
            "with the minimum below the maximum"
        )

    return RobotSettings(
        wheels=wheels,
        inverted=inverted,
        ramp_servos=ramp_servos,
        ramp_closed_angle=closed,
        ramp_open_angle=opened,
        ramp_min_pulse_us=minimum,
        ramp_max_pulse_us=maximum,
    )


class SettingsStore:
    """Load and atomically save the settings file."""

    def __init__(self, path: str | os.PathLike[str] | None = None) -> None:
        self.path = Path(path).expanduser() if path is not None else settings_path()
        self.load_error: str | None = None

    def load(self) -> RobotSettings:
        self.load_error = None
        try:
            text = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return RobotSettings()
        except OSError as error:
            self.load_error = f"Could not read {self.path}: {error}. Using defaults."
            return RobotSettings()
        try:
            return from_dict(json.loads(text))
        except (ValueError, ConfigurationError) as error:
            self.load_error = f"{self.path} is invalid ({error}). Using defaults until you save."
            return RobotSettings()

    def save(self, settings: RobotSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(prefix=".robot-settings.", dir=self.path.parent)
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as output:
                json.dump(settings.to_dict(), output, indent=2)
                output.write("\n")
            os.replace(temporary, self.path)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
        self.load_error = None
