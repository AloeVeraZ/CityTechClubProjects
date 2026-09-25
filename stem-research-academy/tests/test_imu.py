import unittest
from unittest.mock import patch

from robot_server import imu


class FakeBNO055:
    def __init__(self, heading=90.0, rate=-10.0, chip=imu.CHIP_ID):
        self.writes = []
        self.chip = chip
        self.present = True
        self.set(heading, rate)

    def set(self, heading, rate):
        def raw(value):
            number = round(value * 16) & 0xFFFF
            return [number & 0xFF, number >> 8]
        self.euler = raw(heading) + raw(5.0) + raw(-2.5)
        self.gyro = raw(0) + raw(0) + raw(rate)

    def _check(self):
        if not self.present:
            raise OSError(121, "Remote I/O error")

    def read_byte_data(self, address, register):
        self._check()
        if register == imu.REG_CHIP_ID:
            return self.chip
        if register == imu.REG_CALIB_STAT:
            return 0b11110000
        return 0

    def write_byte_data(self, address, register, value):
        self._check()
        self.writes.append((register, value))

    def read_i2c_block_data(self, address, register, length):
        self._check()
        return self.euler if register == imu.REG_EULER else self.gyro

    def close(self):
        pass


@patch("robot_server.imu.time.sleep")
class BNO055Tests(unittest.TestCase):
    def test_connects_in_imu_fusion_mode_and_reports_ftc_style_angles(self, _sleep):
        bus = FakeBNO055(heading=90.0, rate=-10.0)
        sensor = imu.BNO055(bus=bus)
        reading = sensor.snapshot()
        self.assertIn((imu.REG_OPR_MODE, imu.MODE_IMUPLUS), bus.writes)
        self.assertTrue(reading["connected"])
        # 90 degrees clockwise on the chip is a right turn: yaw -90.
        self.assertEqual(reading["yaw"], -90.0)
        self.assertEqual(reading["roll"], 5.0)
        self.assertEqual(reading["pitch"], -2.5)
        self.assertEqual(reading["rate"], -10.0)
        self.assertTrue(reading["calibrated"])

    def test_zero_heading(self, _sleep):
        bus = FakeBNO055(heading=30.0)
        sensor = imu.BNO055(bus=bus)
        sensor.snapshot()
        sensor.zero_heading()
        self.assertEqual(sensor.snapshot()["yaw"], 0.0)
        bus.set(40.0, 0)
        sensor._last_read = 0
        self.assertEqual(sensor.snapshot()["yaw"], -10.0)

    def test_missing_or_wrong_device_reports_offline(self, _sleep):
        bus = FakeBNO055(chip=0x12)
        reading = imu.BNO055(bus=bus).snapshot()
        self.assertFalse(reading["connected"])
        self.assertIn("not a BNO055", reading["error"])
        bus = FakeBNO055()
        bus.present = False
        self.assertFalse(imu.BNO055(bus=bus).snapshot()["connected"])

    def test_wrap_keeps_yaw_in_range(self, _sleep):
        self.assertEqual(imu._wrap(190), -170)
        self.assertEqual(imu._wrap(-180), 180)


if __name__ == "__main__":
    unittest.main()
