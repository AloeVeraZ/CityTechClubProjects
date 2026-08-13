import pathlib
import unittest

from robot_server.actuators import ActuatorController, PigpioServoBoard


class FakePigpioModule:
    OUTPUT = 1


class FakePi:
    def __init__(self, connected=True):
        self.connected = connected
        self.modes = []
        self.pulses = []
        self.stopped = False

    def set_mode(self, pin, mode):
        self.modes.append((pin, mode))
        return 0

    def set_servo_pulsewidth(self, pin, pulse_width):
        self.pulses.append((pin, pulse_width))
        return 0

    def stop(self):
        self.stopped = True


class FakeServoBoard:
    def __init__(self):
        self.pins = {0: 12, 1: 18}
        self.hardware = True
        self.error = None
        self.angles = []

    def set_angle(self, channel, angle):
        self.angles.append((channel, angle))

    def close(self):
        pass


class ServoActuatorTests(unittest.TestCase):
    def test_installer_has_pigpio_servo_timing(self):
        root = pathlib.Path(__file__).parents[1]
        installer = (root / "installer" / "install.sh").read_text(encoding="utf-8")
        service = (root / "installer" / "systemd" / "stem-robot-dashboard.service").read_text(encoding="utf-8")
        daemon_service = (root / "installer" / "systemd" / "pigpiod.service").read_text(encoding="utf-8")
        self.assertIn("apt_has_candidate pigpio", installer)
        self.assertIn("pigpio is already installed; skipping its download and build", installer)
        self.assertIn("joan2937/pigpio/archive/refs/tags/v79.tar.gz", installer)
        self.assertIn("sudo make -C", installer)
        self.assertIn('sudo rm -rf -- "$PIGPIO_BUILD_DIR"', installer)
        self.assertIn("systemctl enable pigpiod.service", installer)
        self.assertIn("RAMP_SERVO_0_GPIO_BCM=12", installer)
        self.assertIn("RAMP_SERVO_1_GPIO_BCM=18", installer)
        self.assertIn("RAMP_SERVO_0_REVERSED=0", installer)
        self.assertIn("RAMP_SERVO_1_REVERSED=1", installer)
        self.assertIn("pigpiod.service", service)
        self.assertIn("ExecStart=@PIGPIOD_BIN@", daemon_service)

    def test_pigpio_is_not_in_the_mandatory_apt_batch(self):
        installer = (pathlib.Path(__file__).parents[1] / "installer" / "install.sh").read_text(encoding="utf-8")
        mandatory_batch = installer.split("apt_get install -y \\", 1)[1].split("\n\n", 1)[0]
        self.assertNotIn("pigpio", mandatory_batch)

    def test_pigpio_initializes_both_servos_closed_with_pin_12_reversed(self):
        pi = FakePi()
        board = PigpioServoBoard(pigpio_module=FakePigpioModule(), pi_client=pi)

        self.assertTrue(board.hardware)
        self.assertEqual(pi.modes, [(12, 1), (18, 1)])
        self.assertEqual(pi.pulses, [(12, 1000), (18, 1556)])
        board.close()

    def test_open_maps_to_100_degrees_with_pin_12_reversed(self):
        pi = FakePi()
        board = PigpioServoBoard(pigpio_module=FakePigpioModule(), pi_client=pi)
        board.set_angle(0, 100)
        board.set_angle(1, 100)

        self.assertEqual(pi.pulses[-2:], [(12, 1556), (18, 1000)])
        board.close()

    def test_missing_pigpio_daemon_disables_hardware_safely(self):
        pi = FakePi(connected=False)
        board = PigpioServoBoard(pigpio_module=FakePigpioModule(), pi_client=pi)

        self.assertFalse(board.hardware)
        self.assertIn("pigpiod is not running", board.error)
        self.assertTrue(pi.stopped)

    def test_open_holds_both_ramp_servos_at_logical_100_degrees(self):
        board = FakeServoBoard()
        controller = ActuatorController(board=board)
        result = controller.set_ramp("open")

        self.assertEqual(board.angles, [(0, 100.0), (1, 100.0)])
        self.assertEqual(result["ramp"]["state"], "open")
        self.assertEqual(result["channels"], {"0": 100.0, "1": 100.0})

    def test_closed_holds_both_ramp_servos_at_absolute_zero(self):
        board = FakeServoBoard()
        controller = ActuatorController(board=board)
        controller.set_ramp("open")
        result = controller.set_ramp("closed")

        self.assertEqual(board.angles[-2:], [(0, 0.0), (1, 0.0)])
        self.assertEqual(result["ramp"]["state"], "closed")
        self.assertEqual(result["channels"], {"0": 0.0, "1": 0.0})

    def test_invalid_ramp_state_is_rejected(self):
        controller = ActuatorController(board=FakeServoBoard())
        with self.assertRaisesRegex(ValueError, "open.*closed"):
            controller.set_ramp("halfway")


if __name__ == "__main__":
    unittest.main()
