"""Stable, continuously held ramp-servo positions using the pigpio daemon."""

from __future__ import annotations

import os
import threading


class PigpioServoBoard:
    """Drive two hobby servos with DMA-timed pigpio pulses."""

    CLOSED_ANGLE = 0.0
    OPEN_ANGLE = 100.0

    def __init__(self, pigpio_module=None, pi_client=None) -> None:
        self.minimum_us = int(os.environ.get("RAMP_SERVO_MIN_PULSE_US", "1000"))
        self.maximum_us = int(os.environ.get("RAMP_SERVO_MAX_PULSE_US", "2000"))
        self.pins = {
            0: int(os.environ.get("RAMP_SERVO_0_GPIO_BCM", "12")),
            1: int(os.environ.get("RAMP_SERVO_1_GPIO_BCM", "18")),
        }
        self.reversed_channels = {
            channel
            for channel in self.pins
            if os.environ.get(
                f"RAMP_SERVO_{channel}_REVERSED",
                "1" if channel == 1 else "0",
            ).strip().lower()
            in {"1", "true", "yes", "on"}
        }
        self.hardware = False
        self.error: str | None = None
        self._pigpio = pigpio_module
        self._pi = pi_client
        self._lock = threading.Lock()

        try:
            if self._pigpio is None:
                import pigpio  # type: ignore

                self._pigpio = pigpio
            if self._pi is None:
                self._pi = self._pigpio.pi()
            self._validate_configuration()
            if not getattr(self._pi, "connected", False):
                raise OSError("pigpiod is not running")
            for channel, pin in self.pins.items():
                self._require_success(self._pi.set_mode(pin, self._pigpio.OUTPUT), "set GPIO mode")
                self._write_pulse(pin, self._channel_pulse_width(channel, self.CLOSED_ANGLE))
            self.hardware = True
        except (ImportError, OSError, RuntimeError, ValueError) as error:
            self.error = f"Stable servo timing unavailable: {error}"
            self.hardware = False
            self.close()

    def _validate_configuration(self) -> None:
        if not 400 <= self.minimum_us < self.maximum_us <= 3000:
            raise ValueError("Invalid ramp servo pulse-width range")
        if len(set(self.pins.values())) != 2:
            raise ValueError("Ramp servos must use two different GPIO pins")

    @staticmethod
    def _require_success(result: object, action: str) -> None:
        if isinstance(result, int) and result < 0:
            raise OSError(f"pigpio could not {action} (error {result})")

    def _pulse_width(self, angle: float) -> int:
        angle = max(0.0, min(180.0, float(angle)))
        return round(self.minimum_us + (self.maximum_us - self.minimum_us) * angle / 180.0)

    def _channel_pulse_width(self, channel: int, logical_angle: float) -> int:
        logical_angle = max(self.CLOSED_ANGLE, min(self.OPEN_ANGLE, float(logical_angle)))
        servo_angle = (
            self.OPEN_ANGLE - logical_angle
            if channel in self.reversed_channels
            else logical_angle
        )
        return self._pulse_width(servo_angle)

    def _write_pulse(self, pin: int, pulse_width_us: int) -> None:
        self._require_success(
            self._pi.set_servo_pulsewidth(pin, pulse_width_us),
            f"set GPIO{pin} servo pulse",
        )

    def set_angle(self, channel: int, angle: float) -> None:
        if channel not in self.pins:
            raise ValueError(f"Ramp servo channel {channel} is unavailable")
        with self._lock:
            self._write_pulse(self.pins[channel], self._channel_pulse_width(channel, angle))

    def close(self) -> None:
        if self._pi is None:
            return
        for pin in self.pins.values():
            try:
                self._pi.set_servo_pulsewidth(pin, 0)
            except (AttributeError, OSError, RuntimeError):
                pass
        try:
            self._pi.stop()
        except (AttributeError, OSError, RuntimeError):
            pass
        self._pi = None


class ActuatorController:
    """Hold both ramp servos at logical 0 degrees or 100 degrees."""

    RAMP_STATES = {"open", "closed"}
    CLOSED_ANGLE = PigpioServoBoard.CLOSED_ANGLE
    OPEN_ANGLE = PigpioServoBoard.OPEN_ANGLE

    def __init__(self, board: PigpioServoBoard | None = None) -> None:
        self._lock = threading.Lock()
        self._board = board or PigpioServoBoard()
        self._ramp = "closed"
        self._channel_angles = {0: self.CLOSED_ANGLE, 1: self.CLOSED_ANGLE}

    def snapshot(self) -> dict:
        with self._lock:
            configured = self._board.hardware
            return {
                "configured": configured,
                "hardware": configured,
                "reason": self._board.error or "Stable pigpio servo pulses active",
                "gpio_bcm": {str(channel): pin for channel, pin in self._board.pins.items()},
                "channels": {str(channel): angle for channel, angle in self._channel_angles.items()},
                "ramp": {
                    "state": self._ramp,
                    "closed_angle": self.CLOSED_ANGLE,
                    "open_angle": self.OPEN_ANGLE,
                    "holding": configured,
                },
            }

    def set_ramp(self, state: object) -> dict:
        state_value = str(state).lower()
        if state_value not in self.RAMP_STATES:
            raise ValueError("Ramp state must be 'open' or 'closed'")
        target_angle = self.OPEN_ANGLE if state_value == "open" else self.CLOSED_ANGLE
        if self._board.hardware:
            try:
                self._board.set_angle(0, target_angle)
                self._board.set_angle(1, target_angle)
            except (OSError, RuntimeError, ValueError) as error:
                self._board.error = f"Ramp movement failed: {error}"
                self._board.hardware = False
        with self._lock:
            self._ramp = state_value
            self._channel_angles = {0: target_angle, 1: target_angle}
        return self.snapshot()

    def close(self) -> None:
        self._board.close()
