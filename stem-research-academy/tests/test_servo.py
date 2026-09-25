import unittest

from robot_server.errors import HardwareUnavailable
from robot_server.servo import LED0_ON_L, PCA9685Board


class FakeBus:
    def __init__(self, present=True):
        self.registers = {}
        self.blocks = []
        self.present = present
        self.writes_fail = False

    def _check(self):
        if not self.present:
            raise OSError(121, "Remote I/O error")

    def write_byte_data(self, address, register, value):
        self._check()
        self.registers[(address, register)] = value

    def read_byte_data(self, address, register):
        self._check()
        return self.registers.get((address, register), 0)

    def write_i2c_block_data(self, address, register, payload):
        self._check()
        if self.writes_fail:
            raise OSError(121, "Remote I/O error")
        self.blocks.append((address, register, list(payload)))

    def close(self):
        pass


def counts(payload):
    return payload[2] | ((payload[3] & 0x0F) << 8)


class ServoBoardTests(unittest.TestCase):
    def test_pulse_generates_pca9685_counts_on_the_right_channel(self):
        bus = FakeBus()
        board = PCA9685Board(bus=bus)
        board.set_pulse_us(3, 1500)
        address, register, payload = bus.blocks[-1]
        self.assertEqual((address, register), (0x40, LED0_ON_L + 12))
        self.assertEqual(counts(payload), round(1500 * 50 * 4096 / 1_000_000))
        self.assertEqual(board.pulses, {3: 1500})

    def test_release_sets_full_off(self):
        bus = FakeBus()
        board = PCA9685Board(bus=bus)
        board.set_pulse_us(2, 1500)
        board.release(2)
        self.assertEqual(bus.blocks[-1][2][3] & 0x10, 0x10)
        self.assertEqual(board.pulses, {})

    def test_limits_are_enforced(self):
        board = PCA9685Board(bus=FakeBus())
        with self.assertRaisesRegex(ValueError, "0 through 15"):
            board.set_pulse_us(16, 1500)
        with self.assertRaisesRegex(ValueError, "500 through 2500"):
            board.set_pulse_us(0, 3000)

    def test_unplugged_and_replugged_board_is_tracked(self):
        bus = FakeBus()
        board = PCA9685Board(bus=bus)
        self.assertTrue(board.available)
        bus.present = False
        board.probe()
        self.assertFalse(board.available)
        with self.assertRaises(HardwareUnavailable):
            board.set_pulse_us(0, 1500)
        bus.present = True
        board.probe()
        self.assertTrue(board.available)
        board.set_pulse_us(0, 1500)

    def test_write_failure_is_a_fault_not_a_disconnect(self):
        bus = FakeBus()
        board = PCA9685Board(bus=bus)
        bus.writes_fail = True
        with self.assertRaises(OSError):
            board.set_pulse_us(0, 1500)
        self.assertTrue(board.available)
        self.assertIsNotNone(board.fault)


if __name__ == "__main__":
    unittest.main()
