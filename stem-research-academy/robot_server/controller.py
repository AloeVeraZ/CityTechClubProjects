"""MotionModule-style safety controller for 3TSahur's four ports and servo board.

Every motor write goes through one lock. Reversing any motor first coasts all
of them for the deadtime, and a watchdog coasts everything if commands stop
arriving. The servo board's OE pin is a plain Pi output owned here, so cutting
the servo outputs still works if the I2C bus stops answering.
"""

from __future__ import annotations

import math
import threading
import time

from . import hardware
from .errors import RobotError
from .gpio import MockGPIO, create_gpio_backend
from .motor import HBridgeMotor
from .servo import MockServoBoard, PCA9685Board


class MotionController:
    def __init__(
        self,
        gpio=None,
        servo_board=None,
        inverted: dict[int, bool] | None = None,
        watchdog_ms: int = hardware.WATCHDOG_MS,
    ) -> None:
        self.gpio = gpio or create_gpio_backend()
        self.watchdog_ms = watchdog_ms
        self._lock = threading.RLock()
        self._closed = False
        self._watchdog_armed = False
        self._watchdog_tripped = False
        self._last_feed = time.monotonic()
        self._last_servo_probe = time.monotonic()
        self._stop_event = threading.Event()
        inverted = inverted or {}
        self._motors = {
            number: HBridgeMotor(self.gpio, port, hardware.PWM_HZ, inverted.get(number, False))
            for number, port in hardware.MOTOR_PORTS.items()
        }
        self.motor_values = {number: 0.0 for number in self._motors}
        if servo_board is not None:
            self.servos = servo_board
        elif isinstance(self.gpio, MockGPIO):
            self.servos = MockServoBoard()
        else:
            self.servos = PCA9685Board()
        self.gpio.claim_output(hardware.SERVO_OE_GPIO)
        self._write_output_enable(True)
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop, name="motor-watchdog", daemon=True
        )
        self._watchdog_thread.start()

    @property
    def is_hardware(self) -> bool:
        return bool(getattr(self.gpio, "is_hardware", False))

    # Motors -------------------------------------------------------------------

    def set_ports(self, outputs: dict[int, float]) -> None:
        """Set several motor ports at once. Values are clamped to -1..1."""

        clean: dict[int, float] = {}
        for port, value in outputs.items():
            if isinstance(port, bool) or port not in self._motors:
                raise ValueError(f"There is no motor port {port}")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("Motor values must be numbers")
            value = float(value)
            if not math.isfinite(value):
                raise ValueError("Motor values must be finite")
            clean[port] = max(-1.0, min(1.0, value))
        with self._lock:
            if self._closed:
                return
            if any(self._motors[port].would_reverse(value) for port, value in clean.items()):
                # One shared coast before a direction change, not one per motor.
                self._apply_all_zero()
                time.sleep(hardware.DEADTIME_MS / 1000.0)
            for port, value in clean.items():
                self._motors[port].set(value)
                self.motor_values[port] = value
            self._last_feed = time.monotonic()
            self._watchdog_armed = any(value != 0 for value in self.motor_values.values())
            self._watchdog_tripped = False

    def inverted(self, port: int) -> bool:
        return self._motors[port].inverted

    def set_inverted(self, port: int, inverted: bool) -> None:
        """Change a port's direction. Stops every motor first."""

        with self._lock:
            if self._closed:
                return
            self._apply_all_zero()
            self._watchdog_armed = False
            self._motors[port].inverted = bool(inverted)

    def stop_all(self) -> None:
        """Coast every motor now. Servos keep holding."""

        with self._lock:
            if self._closed:
                return
            self._apply_all_zero()
            self._watchdog_armed = False

    def _apply_all_zero(self) -> None:
        for port, motor in self._motors.items():
            motor.set(0)
            self.motor_values[port] = 0.0

    def _watchdog_loop(self) -> None:
        interval = max(0.01, self.watchdog_ms / 4000.0)
        timeout = self.watchdog_ms / 1000.0
        while not self._stop_event.wait(interval):
            with self._lock:
                if self._watchdog_armed and time.monotonic() - self._last_feed > timeout:
                    self._apply_all_zero()
                    self._watchdog_armed = False
                    self._watchdog_tripped = True

    # Servos -------------------------------------------------------------------

    def set_servo_pulse(self, channel: int, pulse_us: float) -> None:
        with self._lock:
            if self._closed:
                return
            if not self._servo_outputs_enabled:
                raise RobotError("Servo outputs are disabled at the board's OE pin. Enable them first.")
            self.servos.set_pulse_us(channel, pulse_us)

    def release_servo(self, channel: int) -> None:
        with self._lock:
            if self._closed:
                return
            self.servos.release(channel)

    def release_all_servos(self) -> None:
        """Stop driving every servo. A loaded mechanism can then move freely."""

        with self._lock:
            if self._closed:
                return
            for channel in sorted(self.servos.pulses):
                try:
                    self.servos.release(channel)
                except (RobotError, ValueError, OSError):
                    continue

    @property
    def servo_outputs_enabled(self) -> bool:
        return self._servo_outputs_enabled

    def set_servo_outputs_enabled(self, enabled: bool) -> None:
        with self._lock:
            if self._closed:
                return
            self._write_output_enable(bool(enabled))

    def _write_output_enable(self, enabled: bool) -> None:
        # OE is active low: low enables all 16 outputs, high cuts them.
        self.gpio.write(hardware.SERVO_OE_GPIO, not enabled)
        self._servo_outputs_enabled = enabled

    def refresh_servo_board(self, *, interval: float = 2.0) -> None:
        """Re-probe the servo board at most every ``interval`` seconds."""

        with self._lock:
            if self._closed:
                return
            now = time.monotonic()
            if now - self._last_servo_probe < interval:
                return
            self._last_servo_probe = now
        try:
            self.servos.probe()
        except OSError:
            pass

    # Status -------------------------------------------------------------------

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "hardware": self.is_hardware,
                "ports": {
                    str(port): {
                        "value": self.motor_values[port],
                        "inverted": motor.inverted,
                    }
                    for port, motor in self._motors.items()
                },
                "watchdog_ms": self.watchdog_ms,
                "watchdog_armed": self._watchdog_armed,
                "watchdog_tripped": self._watchdog_tripped,
                "servo_board": {
                    "address": f"0x{self.servos.address:02x}",
                    "available": bool(self.servos.available),
                    "error": self.servos.error,
                    "fault": self.servos.fault,
                    "outputs_enabled": self._servo_outputs_enabled,
                    "oe_gpio": hardware.SERVO_OE_GPIO,
                    "pulses": {str(channel): round(pulse, 1) for channel, pulse in sorted(self.servos.pulses.items())},
                },
            }

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._watchdog_armed = False
            self._apply_all_zero()
            try:
                self._write_output_enable(False)
            except RobotError:
                pass
            self.servos.close()
            self.gpio.close()
        self._stop_event.set()
        self._watchdog_thread.join(timeout=1)

