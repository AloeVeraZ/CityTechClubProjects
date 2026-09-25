"""BNO055 orientation sensor on the shared I2C bus.

The BNO055 runs in IMU (IMUPLUS) fusion mode: accelerometer plus gyroscope,
no magnetometer. That is the FTC choice for drivetrains, because four motors
next to the sensor make a compass heading unreliable. Heading therefore starts
at zero where the robot is powered on, and "Zero heading" resets it.

Angles are reported the FTC way: yaw is counter-clockwise positive in
(-180, 180], and the yaw rate is degrees per second, counter-clockwise positive.
"""

from __future__ import annotations

import threading
import time

from . import hardware
from .servo import open_i2c_bus


CHIP_ID = 0xA0
REG_CHIP_ID = 0x00
REG_GYRO_DATA = 0x14      # x, y, z; 16 LSB per degree/second
REG_EULER = 0x1A          # heading, roll, pitch; 16 LSB per degree
REG_CALIB_STAT = 0x35
REG_UNIT_SEL = 0x3B
REG_OPR_MODE = 0x3D
REG_PWR_MODE = 0x3E
REG_SYS_TRIGGER = 0x3F
MODE_CONFIG = 0x00
MODE_IMUPLUS = 0x08


def _int16(low: int, high: int) -> int:
    value = low | (high << 8)
    return value - 0x10000 if value & 0x8000 else value


def _wrap(angle: float) -> float:
    angle = (angle + 180.0) % 360.0 - 180.0
    return 180.0 if angle == -180.0 else angle


class BNO055:
    """Poll the BNO055 on demand, re-detecting it if it drops off the bus."""

    is_hardware = True
    RETRY_SECONDS = 2.0
    CACHE_SECONDS = 0.04

    def __init__(self, bus=None, address: int = hardware.IMU_ADDRESS) -> None:
        self.address = address
        self._bus = bus
        self._owns_bus = bus is None
        self._lock = threading.Lock()
        self.connected = False
        self.error: str | None = "Not detected yet"
        self._next_attempt = 0.0
        self._last_read = 0.0
        self._yaw_offset = 0.0
        self._raw_yaw: float | None = None
        self._reading = self._empty()

    @staticmethod
    def _empty() -> dict:
        return {"yaw": None, "pitch": None, "roll": None, "rate": None, "calibrated": False, "calibration": None}

    def _connect(self) -> None:
        if self._bus is None:
            self._bus = open_i2c_bus(hardware.IMU_I2C_BUS)
        chip = self._bus.read_byte_data(self.address, REG_CHIP_ID)
        if chip != CHIP_ID:
            raise OSError(f"device at 0x{self.address:02x} is not a BNO055 (chip id 0x{chip:02x})")
        self._bus.write_byte_data(self.address, REG_OPR_MODE, MODE_CONFIG)
        time.sleep(0.025)
        self._bus.write_byte_data(self.address, REG_PWR_MODE, 0x00)
        self._bus.write_byte_data(self.address, REG_SYS_TRIGGER, 0x00)
        # Degrees, degrees/second, m/s², Celsius, default (Windows) orientation.
        self._bus.write_byte_data(self.address, REG_UNIT_SEL, 0x00)
        self._bus.write_byte_data(self.address, REG_OPR_MODE, MODE_IMUPLUS)
        time.sleep(0.02)
        self.connected = True
        self.error = None

    def _read(self) -> None:
        euler = self._bus.read_i2c_block_data(self.address, REG_EULER, 6)
        gyro = self._bus.read_i2c_block_data(self.address, REG_GYRO_DATA, 6)
        calibration = self._bus.read_byte_data(self.address, REG_CALIB_STAT)
        # The BNO055 heading grows clockwise; FTC-style yaw grows counter-clockwise.
        heading = _int16(euler[0], euler[1]) / 16.0
        self._raw_yaw = _wrap(-heading)
        gyro_level = (calibration >> 4) & 0x03
        self._reading = {
            "yaw": round(_wrap(self._raw_yaw - self._yaw_offset), 2),
            "roll": round(_int16(euler[2], euler[3]) / 16.0, 2),
            "pitch": round(_int16(euler[4], euler[5]) / 16.0, 2),
            "rate": round(_int16(gyro[4], gyro[5]) / 16.0, 2),
            "calibrated": gyro_level == 3,
            "calibration": {
                "system": (calibration >> 6) & 0x03,
                "gyro": gyro_level,
                "accel": (calibration >> 2) & 0x03,
            },
        }

    def poll(self) -> None:
        now = time.monotonic()
        with self._lock:
            if self.connected and now - self._last_read < self.CACHE_SECONDS:
                return
            if not self.connected and now < self._next_attempt:
                return
            try:
                if not self.connected:
                    self._connect()
                self._read()
                self._last_read = now
            except (ImportError, OSError) as error:
                self.connected = False
                self.error = str(error)
                self._reading = self._empty()
                self._next_attempt = now + self.RETRY_SECONDS

    def zero_heading(self) -> None:
        with self._lock:
            if self._raw_yaw is not None:
                self._yaw_offset = self._raw_yaw
                self._last_read = 0.0

    def snapshot(self) -> dict:
        self.poll()
        with self._lock:
            return {
                "name": "BNO055",
                "address": f"0x{self.address:02x}",
                "connected": self.connected,
                "error": self.error,
                "simulated": False,
                **self._reading,
            }

    def close(self) -> None:
        if self._owns_bus and self._bus is not None:
            try:
                self._bus.close()
            except OSError:
                pass
            self._bus = None


class MockIMU:
    """Simulated IMU that integrates the commanded rotation into a heading."""

    is_hardware = False

    def __init__(self) -> None:
        self.address = hardware.IMU_ADDRESS
        self._yaw = 0.0
        self._rate = 0.0
        self._updated = time.monotonic()
        self._lock = threading.Lock()

    def set_rotation(self, rotate: float) -> None:
        """Called with each drive command so the simulator has something to show."""

        with self._lock:
            self._advance()
            self._rate = max(-1.0, min(1.0, float(rotate))) * 90.0

    def _advance(self) -> None:
        now = time.monotonic()
        self._yaw = _wrap(self._yaw + self._rate * (now - self._updated))
        self._updated = now

    def zero_heading(self) -> None:
        with self._lock:
            self._advance()
            self._yaw = 0.0

    def snapshot(self) -> dict:
        with self._lock:
            self._advance()
            return {
                "name": "BNO055",
                "address": f"0x{self.address:02x}",
                "connected": True,
                "error": None,
                "simulated": True,
                "yaw": round(self._yaw, 2),
                "pitch": 0.0,
                "roll": 0.0,
                "rate": round(self._rate, 2),
                "calibrated": True,
                "calibration": {"system": 3, "gyro": 3, "accel": 3},
            }

    def close(self) -> None:
        pass
