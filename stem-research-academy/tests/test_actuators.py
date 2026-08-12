import os
import pathlib
import unittest
from unittest.mock import patch

from robot_server.actuators import ActuatorController, PCA9685ServoBoard


class FakeBus:
    def __init__(self, _bus_number):
        self.writes = []
        self.closed = False

    def read_byte_data(self, address, register):
        self.writes.append(("read", address, register))
        return 0

    def write_byte_data(self, address, register, value):
        self.writes.append(("write", address, register, value))

    def close(self):
        self.closed = True


class FakeServoBoard:
    def __init__(self):
        self.address = 0x40
        self.hardware = True
        self.error = None
        self.angles = []

    def set_angle(self, channel, angle):
        self.angles.append((channel, angle))

    def close(self):
        pass


class ServoActuatorTests(unittest.TestCase):
    def test_installer_enables_i2c_and_adds_servo_configuration(self):
        installer = (pathlib.Path(__file__).parents[1] / "installer" / "install.sh").read_text(encoding="utf-8")
        self.assertIn("python3-smbus", installer)
        self.assertIn("i2c-tools", installer)
        self.assertIn("raspi-config nonint do_i2c 0", installer)
        self.assertIn("SERVO_I2C_ADDRESS=0x40", installer)
        self.assertIn("RAMP_CHANNEL_0_OPEN_ANGLE=30", installer)
        self.assertIn("RAMP_CHANNEL_1_OPEN_ANGLE=30", installer)

    def test_pca9685_initializes_channels_zero_and_one_at_zero_degrees(self):
        bus = FakeBus(1)
        board = PCA9685ServoBoard(bus_factory=lambda _number: bus)

        self.assertTrue(board.hardware)
        # Channel 0 OFF registers start at 0x08; channel 1 starts at 0x0C.
        written_registers = [entry[2] for entry in bus.writes if entry[0] == "write"]
        self.assertIn(0x08, written_registers)
        self.assertIn(0x0C, written_registers)

    def test_open_moves_both_ramp_channels_to_their_set_positions(self):
        board = FakeServoBoard()
        with patch.dict(os.environ, {
            "RAMP_CHANNEL_0_OPEN_ANGLE": "30",
            "RAMP_CHANNEL_1_OPEN_ANGLE": "40",
        }):
            controller = ActuatorController(board=board)
        result = controller.set_ramp("open")

        self.assertEqual(board.angles, [(0, 30.0), (1, 40.0)])
        self.assertEqual(result["ramp"]["state"], "open")
        self.assertEqual(result["channels"], {"0": 30.0, "1": 40.0})

    def test_closed_returns_both_ramp_channels_to_zero(self):
        board = FakeServoBoard()
        controller = ActuatorController(board=board)
        controller.set_ramp("open")
        result = controller.set_ramp("closed")

        self.assertEqual(board.angles[-2:], [(0, 0), (1, 0)])
        self.assertEqual(result["ramp"]["state"], "closed")
        self.assertEqual(result["channels"], {"0": 0, "1": 0})


if __name__ == "__main__":
    unittest.main()
