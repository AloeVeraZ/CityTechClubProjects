"""3TSahur's built-in robot code: mecanum drive, ramp, and IMU.

This replaces MotionModule's uploaded ``robot.py``. The robot is purpose-built,
so its code ships inside the server and nothing has to be dragged in from a
browser. The Driver Station sends forward / strafe / rotate; the Debug page
decides which motor port is which wheel.
"""

from __future__ import annotations

import math
import threading

from . import hardware
from .controller import MotionController
from .errors import RobotError
from .imu import BNO055, MockIMU
from .settings import RobotSettings, SettingsStore


RAMP_STATES = ("open", "closed")
DEBUG_MOTOR_LIMIT = 0.5


def _axis(value: object, label: str, low: float = -1.0, high: float = 1.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{label} must be finite")
    return max(low, min(high, value))


def mix(forward: float, strafe: float, rotate: float) -> dict[str, float]:
    """Mecanum wheel powers for one driver command.

    forward  positive drives toward the front of the robot
    strafe   positive slides the robot to the right
    rotate   positive turns the robot left (counter-clockwise, seen from above)

    Powers are scaled down together when a combined command would exceed full
    power, so the robot keeps moving in the requested direction. A wheel that
    spins the wrong way is fixed with its port's Invert switch on the Debug
    page, never here.
    """

    wheels = {
        "front_left": forward + strafe - rotate,
        "front_right": forward - strafe + rotate,
        "rear_left": forward - strafe - rotate,
        "rear_right": forward + strafe + rotate,
    }
    scale = max(1.0, *(abs(power) for power in wheels.values()))
    return {name: power / scale for name, power in wheels.items()}


class Robot:
    def __init__(self, controller: MotionController | None = None, imu=None, store: SettingsStore | None = None) -> None:
        self._lock = threading.RLock()
        self.store = store or SettingsStore()
        self.settings = self.store.load()
        self.controller = controller or MotionController(inverted=self.settings.inverted)
        for port, inverted in self.settings.inverted.items():
            if self.controller.inverted(port) != inverted:
                self.controller.set_inverted(port, inverted)
        if imu is not None:
            self.imu = imu
        else:
            self.imu = BNO055() if self.controller.is_hardware else MockIMU()
        self.command = {"forward": 0.0, "strafe": 0.0, "rotate": 0.0, "speed": 0.0}
        self.ramp_state = "released"
        self.ramp_error: str | None = None
        # Hold the ramp closed from startup, as the original robot did.
        self.set_ramp("closed", quiet=True)

    # Driving ------------------------------------------------------------------

    def drive(self, forward: object, strafe: object, rotate: object, speed: object = 0.5) -> dict:
        forward = _axis(forward, "forward")
        strafe = _axis(strafe, "strafe")
        rotate = _axis(rotate, "rotate")
        speed = _axis(speed, "speed", 0.0, 1.0)
        powers = mix(forward, strafe, rotate)
        with self._lock:
            outputs = {self.settings.port_for(wheel): powers[wheel] * speed for wheel in hardware.WHEELS}
            self.controller.set_ports(outputs)
            self.command = {"forward": forward, "strafe": strafe, "rotate": rotate, "speed": speed}
        if isinstance(self.imu, MockIMU):
            self.imu.set_rotation(rotate * speed)
        return {"wheels": {wheel: round(powers[wheel] * speed, 4) for wheel in hardware.WHEELS}, "speed": speed}

    def stop(self) -> None:
        """Soft stop: coast the drivetrain. The ramp keeps holding."""

        with self._lock:
            self.controller.stop_all()
            self.command = {**self.command, "forward": 0.0, "strafe": 0.0, "rotate": 0.0}
        if isinstance(self.imu, MockIMU):
            self.imu.set_rotation(0)

    def emergency_stop(self) -> None:
        """Kill: coast every motor, release every servo, and cut the servo outputs."""

        with self._lock:
            try:
                self.stop()
            finally:
                try:
                    self.controller.release_all_servos()
                finally:
                    self.controller.set_servo_outputs_enabled(False)
                    self.ramp_state = "released"

    # Ramp -----------------------------------------------------------------------

    def ramp_angle(self, servo: str, logical_angle: float) -> float:
        """The servo angle for one ramp servo; a reversed servo is mirrored."""

        closed, opened = self.settings.ramp_closed_angle, self.settings.ramp_open_angle
        logical_angle = max(min(closed, opened), min(max(closed, opened), float(logical_angle)))
        if self.settings.ramp_servos[servo].reversed:
            return closed + opened - logical_angle
        return logical_angle

    def ramp_pulse(self, servo: str, logical_angle: float) -> float:
        minimum, maximum = self.settings.ramp_min_pulse_us, self.settings.ramp_max_pulse_us
        return minimum + (maximum - minimum) * self.ramp_angle(servo, logical_angle) / 180.0

    def set_ramp(self, state: object, *, quiet: bool = False) -> dict:
        state = str(state).strip().lower()
        if state not in RAMP_STATES:
            raise ValueError("Ramp state must be 'open' or 'closed'")
        with self._lock:
            target = self.settings.ramp_open_angle if state == "open" else self.settings.ramp_closed_angle
            try:
                # Commanding the ramp is a deliberate operator action, so it
                # re-enables outputs that an emergency stop cut.
                if not self.controller.servo_outputs_enabled:
                    self.controller.set_servo_outputs_enabled(True)
                for servo in hardware.RAMP_SERVOS:
                    self.controller.set_servo_pulse(
                        self.settings.ramp_servos[servo].channel, self.ramp_pulse(servo, target)
                    )
            except (RobotError, OSError, ValueError) as error:
                self.ramp_error = f"Ramp servos unavailable: {error}"
                if not quiet:
                    raise RobotError(self.ramp_error) from error
            else:
                self.ramp_error = None
            self.ramp_state = state
        return self.ramp_snapshot()

    def ramp_snapshot(self) -> dict:
        board = self.controller.servos
        holding = self.ramp_state in RAMP_STATES and self.ramp_error is None and bool(board.available)
        return {
            "state": self.ramp_state,
            "holding": holding,
            "error": self.ramp_error,
            "closed_angle": self.settings.ramp_closed_angle,
            "open_angle": self.settings.ramp_open_angle,
            "servos": {
                name: {
                    "channel": servo.channel,
                    "reversed": servo.reversed,
                    "pulse_us": board.pulses.get(servo.channel),
                }
                for name, servo in self.settings.ramp_servos.items()
            },
        }

    # Settings -------------------------------------------------------------------

    def apply_settings(self, settings: RobotSettings, *, save: bool = True) -> None:
        """Stop, switch to a new port/servo map, save it, and re-hold the ramp."""

        with self._lock:
            self.stop()
            previous = self.settings
            old_channels = {servo.channel for servo in previous.ramp_servos.values()}
            new_channels = {servo.channel for servo in settings.ramp_servos.values()}
            for channel in old_channels - new_channels:
                try:
                    self.controller.release_servo(channel)
                except (RobotError, OSError, ValueError):
                    pass
            for port, inverted in settings.inverted.items():
                self.controller.set_inverted(port, inverted)
            if save:
                self.store.save(settings)
            self.settings = settings
            if self.ramp_state in RAMP_STATES:
                self.set_ramp(self.ramp_state, quiet=True)

    # Debug outputs ----------------------------------------------------------------

    def test_port(self, port: object, power: object) -> None:
        """Run one motor port directly. The watchdog stops it when commands stop."""

        if isinstance(port, bool) or not isinstance(port, int) or port not in hardware.MOTOR_PORTS:
            raise ValueError("Choose motor port 1, 2, 3 or 4")
        power = _axis(power, "power", -1.0, 1.0)
        if abs(power) > DEBUG_MOTOR_LIMIT:
            raise ValueError(f"Debug motor tests are limited to {DEBUG_MOTOR_LIMIT:.0%} power")
        self.controller.set_ports({port: power})

    def test_servo(self, channel: object, *, angle: object = None, pulse_us: object = None) -> float:
        """Hold one servo channel at an angle (0-180) or a raw pulse."""

        if isinstance(channel, bool) or not isinstance(channel, int) or not 0 <= channel < hardware.SERVO_CHANNELS:
            raise ValueError("Servo channel must be from 0 through 15")
        if pulse_us is not None:
            pulse = _axis(pulse_us, "pulse", -math.inf, math.inf)
        elif angle is not None:
            value = _axis(angle, "angle", -math.inf, math.inf)
            if not 0 <= value <= 180:
                raise ValueError("Servo angle must be from 0 through 180")
            span = hardware.SERVO_MAX_PULSE_US - hardware.SERVO_MIN_PULSE_US
            pulse = hardware.SERVO_MIN_PULSE_US + span * value / 180.0
        else:
            raise ValueError("Send an angle or a pulse")
        with self._lock:
            self.controller.set_servo_pulse(channel, pulse)
            if channel in {servo.channel for servo in self.settings.ramp_servos.values()}:
                self.ramp_state = "manual"
        return pulse

    def release_servo(self, channel: object) -> None:
        if isinstance(channel, bool) or not isinstance(channel, int) or not 0 <= channel < hardware.SERVO_CHANNELS:
            raise ValueError("Servo channel must be from 0 through 15")
        with self._lock:
            self.controller.release_servo(channel)
            if channel in {servo.channel for servo in self.settings.ramp_servos.values()}:
                self.ramp_state = "released"

    # Status -----------------------------------------------------------------------

    def snapshot(self) -> dict:
        self.controller.refresh_servo_board()
        with self._lock:
            motion = self.controller.snapshot()
            return {
                **motion,
                "command": dict(self.command),
                "wheels": {
                    wheel: {
                        "port": self.settings.port_for(wheel),
                        "power": motion["ports"][str(self.settings.port_for(wheel))]["value"],
                    }
                    for wheel in hardware.WHEELS
                },
                "ramp": self.ramp_snapshot(),
                "imu": self.imu.snapshot(),
            }

    def close(self) -> None:
        try:
            self.controller.close()
        finally:
            self.imu.close()
