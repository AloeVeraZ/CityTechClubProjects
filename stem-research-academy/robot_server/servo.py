"""The robot's one PCA9685 servo board on the Raspberry Pi I2C bus.

Adapted from MotionModule's PCA9685 driver for a single board at 0x40.
"""

from __future__ import annotations

import math
import time
from threading import RLock

from . import hardware
from .errors import HardwareUnavailable


MODE1 = 0x00
MODE2 = 0x01
LED0_ON_L = 0x06
PRESCALE = 0xFE
RESTART = 0x80
SLEEP = 0x10
OUTDRV = 0x04


def open_i2c_bus(number: int):
    """smbus2 when installed, otherwise Raspberry Pi OS' python3-smbus."""

    try:
        from smbus2 import SMBus  # type: ignore
    except ImportError:
        from smbus import SMBus  # type: ignore
    return SMBus(number)


def _check_channel(channel: int) -> None:
    if isinstance(channel, bool) or not isinstance(channel, int) or not 0 <= channel < hardware.SERVO_CHANNELS:
        raise ValueError("Servo channel must be from 0 through 15")


def _check_pulse(pulse_us: float) -> float:
    pulse_us = float(pulse_us)
    if not math.isfinite(pulse_us) or not (
        hardware.SERVO_MIN_PULSE_US <= pulse_us <= hardware.SERVO_MAX_PULSE_US
    ):
        raise ValueError(
            "Servo pulse must be a finite value from "
            f"{hardware.SERVO_MIN_PULSE_US} through {hardware.SERVO_MAX_PULSE_US} microseconds"
        )
    return pulse_us


def angle_to_pulse(angle: float) -> float:
    """Generic 0-180 degree servo over the board's full pulse envelope."""

    angle = float(angle)
    if not math.isfinite(angle) or not 0 <= angle <= 180:
        raise ValueError("Servo angle must be a finite value from 0 through 180")
    span = hardware.SERVO_MAX_PULSE_US - hardware.SERVO_MIN_PULSE_US
    return hardware.SERVO_MIN_PULSE_US + span * angle / 180.0


class PCA9685Board:
    """Initialize and drive the 16 outputs of one PCA9685."""

    is_hardware = True

    def __init__(self, bus=None, address: int = hardware.SERVO_ADDRESS) -> None:
        self.address = address
        self._lock = RLock()
        self._owns_bus = bus is None
        self._bus = bus
        self.available = False
        self.error: str | None = None
        # Answered the probe but rejected a real write: the chip is on the bus,
        # something about the wiring or the command is not.
        self.fault: str | None = None
        self.pulses: dict[int, float] = {}
        self._open_bus()
        self.probe()

    def _open_bus(self) -> bool:
        if self._bus is not None:
            return True
        try:
            self._bus = open_i2c_bus(hardware.SERVO_I2C_BUS)
        except (ImportError, OSError) as error:
            self.error = str(error)
            return False
        return True

    def probe(self) -> None:
        """Re-check the board, so an unplugged or late-plugged board is noticed."""

        if not self._open_bus():
            return
        with self._lock:
            try:
                self._bus.read_byte_data(self.address, MODE1)
            except OSError as error:
                self.available = False
                self.error = str(error)
                self.fault = None
                return
            if self.available:
                self.error = None
                return
            try:
                self._initialize()
            except OSError as error:
                self.error = str(error)
                self.fault = None
                return
            self.available = True
            self.error = None
            self.fault = None

    def _initialize(self) -> None:
        bus, address = self._bus, self.address
        bus.write_byte_data(address, MODE1, 0x00)
        bus.write_byte_data(address, MODE2, OUTDRV)
        old_mode = bus.read_byte_data(address, MODE1)
        prescale = round(25_000_000 / (4096 * hardware.SERVO_FREQUENCY_HZ) - 1)
        bus.write_byte_data(address, MODE1, (old_mode & 0x7F) | SLEEP)
        bus.write_byte_data(address, PRESCALE, prescale)
        bus.write_byte_data(address, MODE1, old_mode)
        time.sleep(0.005)
        bus.write_byte_data(address, MODE1, old_mode | RESTART)
        for channel in range(hardware.SERVO_CHANNELS):
            self._write_counts(channel, 0, full_off=True)
        self.pulses.clear()

    def _require(self) -> None:
        if not self.available:
            reason = self.error or "no I2C response"
            raise HardwareUnavailable(f"Servo board at 0x{self.address:02x} is unavailable: {reason}")

    def _write_counts(self, channel: int, off: int, *, full_off: bool = False) -> None:
        register = LED0_ON_L + 4 * channel
        payload = [0, 0, off & 0xFF, ((off >> 8) & 0x0F) | (0x10 if full_off else 0)]
        try:
            self._bus.write_i2c_block_data(self.address, register, payload)
        except OSError as error:
            self.fault = str(error)
            raise
        self.fault = None

    def set_pulse_us(self, channel: int, pulse_us: float) -> None:
        _check_channel(channel)
        pulse_us = _check_pulse(pulse_us)
        self._require()
        counts = round(pulse_us * hardware.SERVO_FREQUENCY_HZ * 4096 / 1_000_000)
        with self._lock:
            self._write_counts(channel, min(4095, counts))
            self.pulses[channel] = pulse_us

    def release(self, channel: int) -> None:
        _check_channel(channel)
        self._require()
        with self._lock:
            self._write_counts(channel, 0, full_off=True)
            self.pulses.pop(channel, None)

    def close(self) -> None:
        if self._bus is None:
            return
        if self.available:
            for channel in range(hardware.SERVO_CHANNELS):
                try:
                    self._write_counts(channel, 0, full_off=True)
                except OSError:
                    break
        self.pulses.clear()
        if self._owns_bus:
            try:
                self._bus.close()
            except OSError:
                pass


class MockServoBoard:
    """Simulated board: always present, remembers what it was told."""

    is_hardware = False

    def __init__(self, address: int = hardware.SERVO_ADDRESS) -> None:
        self.address = address
        self.available = True
        self.error: str | None = None
        self.fault: str | None = None
        self.pulses: dict[int, float] = {}

    def probe(self) -> None:
        pass

    def set_pulse_us(self, channel: int, pulse_us: float) -> None:
        _check_channel(channel)
        self.pulses[channel] = _check_pulse(pulse_us)

    def release(self, channel: int) -> None:
        _check_channel(channel)
        self.pulses.pop(channel, None)

    def close(self) -> None:
        self.pulses.clear()
