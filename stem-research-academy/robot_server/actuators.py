"""PCA9685-backed two-position ramp controls for 3TSahur."""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable


class PCA9685ServoBoard:
    """Small dependency-free PCA9685 adapter using Raspberry Pi I2C bus 1."""

    MODE1 = 0x00
    MODE2 = 0x01
    LED0_ON_L = 0x06
    PRESCALE = 0xFE

    def __init__(self, bus_factory: Callable[[int], object] | None = None) -> None:
        self.address = int(os.environ.get("SERVO_I2C_ADDRESS", "0x40"), 0)
        self.frequency = int(os.environ.get("SERVO_FREQUENCY_HZ", "50"))
        self.minimum_us = int(os.environ.get("SERVO_MIN_PULSE_US", "1000"))
        self.maximum_us = int(os.environ.get("SERVO_MAX_PULSE_US", "2000"))
        self.hardware = False
        self.error: str | None = None
        self._bus = None
        self._lock = threading.Lock()

        try:
            if bus_factory is None:
                from smbus import SMBus  # type: ignore

                bus_factory = SMBus
            self._bus = bus_factory(1)
            self._initialize()
            self.hardware = True
            # User-requested safe startup position for the two installed ports.
            self.set_angle(0, 0)
            self.set_angle(1, 0)
        except (ImportError, OSError, ValueError) as error:
            self.error = f"PCA9685 unavailable: {error}"
            self.hardware = False

    def _write(self, register: int, value: int) -> None:
        if self._bus is None:
            raise OSError("I2C bus is not open")
        self._bus.write_byte_data(self.address, register, value & 0xFF)

    def _read(self, register: int) -> int:
        if self._bus is None:
            raise OSError("I2C bus is not open")
        return int(self._bus.read_byte_data(self.address, register))

    def _initialize(self) -> None:
        if not 40 <= self.frequency <= 1000:
            raise ValueError("SERVO_FREQUENCY_HZ must be between 40 and 1000")
        if not 400 <= self.minimum_us < self.maximum_us <= 3000:
            raise ValueError("Invalid servo pulse-width range")
        prescale = round(25_000_000 / (4096 * self.frequency)) - 1
        old_mode = self._read(self.MODE1)
        self._write(self.MODE1, (old_mode & 0x7F) | 0x10)  # sleep
        self._write(self.PRESCALE, prescale)
        self._write(self.MODE1, old_mode)
        time.sleep(0.005)
        self._write(self.MODE1, old_mode | 0xA1)  # restart, auto-increment, all-call
        self._write(self.MODE2, 0x04)  # totem-pole outputs

    def set_angle(self, channel: int, angle: float) -> None:
        if channel not in (0, 1):
            raise ValueError("Only servo channels 0 and 1 are configured")
        angle = max(0.0, min(180.0, float(angle)))
        pulse_us = self.minimum_us + (self.maximum_us - self.minimum_us) * angle / 180.0
        count = round(pulse_us * self.frequency * 4096 / 1_000_000)
        register = self.LED0_ON_L + 4 * channel
        with self._lock:
            self._write(register, 0)
            self._write(register + 1, 0)
            self._write(register + 2, count & 0xFF)
            self._write(register + 3, (count >> 8) & 0x0F)

    def close(self) -> None:
        if self._bus is not None and hasattr(self._bus, "close"):
            self._bus.close()


class ActuatorController:
    """Move both ramp servos between closed (zero) and open positions."""

    RAMP_STATES = {"open", "closed"}

    def __init__(self, board: PCA9685ServoBoard | None = None) -> None:
        self._lock = threading.Lock()
        self._board = board or PCA9685ServoBoard()
        self._ramp = "closed"
        self._channel_angles = {0: 0, 1: 0}
        self._open_angles = {
            0: self._angle_from_env("RAMP_CHANNEL_0_OPEN_ANGLE", "30"),
            1: self._angle_from_env("RAMP_CHANNEL_1_OPEN_ANGLE", "30"),
        }

    @staticmethod
    def _angle_from_env(name: str, default: str) -> float:
        angle = float(os.environ.get(name, default))
        if not 0 <= angle <= 180:
            raise ValueError(f"{name} must be between 0 and 180")
        return angle

    def snapshot(self) -> dict:
        with self._lock:
            configured = self._board.hardware
            return {
                "configured": configured,
                "hardware": configured,
                "reason": self._board.error or "PCA9685 channels 0 and 1 ready",
                "i2c_address": hex(self._board.address),
                "channels": {str(channel): angle for channel, angle in self._channel_angles.items()},
                "ramp": {
                    "state": self._ramp,
                    "closed_angle": 0,
                    "open_angles": {str(channel): angle for channel, angle in self._open_angles.items()},
                },
            }

    def set_ramp(self, state: object) -> dict:
        state_value = str(state).lower()
        if state_value not in self.RAMP_STATES:
            raise ValueError("Ramp state must be 'open' or 'closed'")
        target_angles = self._open_angles if state_value == "open" else {0: 0, 1: 0}
        if self._board.hardware:
            try:
                for channel, angle in target_angles.items():
                    self._board.set_angle(channel, angle)
            except (OSError, ValueError) as error:
                self._board.error = f"Ramp movement failed: {error}"
                self._board.hardware = False
        with self._lock:
            self._ramp = state_value
            self._channel_angles.update(target_angles)
        return self.snapshot()

    def close(self) -> None:
        self._board.close()
