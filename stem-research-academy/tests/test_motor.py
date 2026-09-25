import time
import unittest
from unittest.mock import patch

from robot_server import hardware
from robot_server.controller import MotionController
from robot_server.errors import RobotError
from robot_server.gpio import MockGPIO
from robot_server.servo import MockServoBoard


class WiringTests(unittest.TestCase):
    def test_ports_use_the_locked_motionmodule_driver_1_and_2_pins(self):
        pins = {port: (item.forward_gpio, item.reverse_gpio) for port, item in hardware.MOTOR_PORTS.items()}
        self.assertEqual(pins, {1: (26, 19), 2: (13, 6), 3: (21, 20), 4: (16, 12)})
        self.assertEqual(hardware.SERVO_OE_GPIO, 4)
        self.assertEqual(hardware.SERVO_ADDRESS, 0x40)

    def test_only_four_ports_exist_and_no_gpio_is_shared(self):
        self.assertEqual(sorted(hardware.MOTOR_PORTS), [1, 2, 3, 4])
        used = [gpio for item in hardware.MOTOR_PORTS.values() for gpio in (item.forward_gpio, item.reverse_gpio)]
        used.append(hardware.SERVO_OE_GPIO)
        self.assertEqual(len(used), len(set(used)))
        self.assertFalse({2, 3} & set(used), "I2C pins must stay free for the servo board and IMU")


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.gpio = MockGPIO()
        self.controller = MotionController(self.gpio, MockServoBoard())

    def tearDown(self):
        self.controller.close()

    def test_positive_drives_only_the_forward_input(self):
        self.controller.set_ports({1: 0.5, 2: 0.5, 3: 0.5, 4: 0.5})
        for pin in (26, 13, 21, 16):
            self.assertEqual(self.gpio.values[pin], 0.5)
        for pin in (19, 6, 20, 12):
            self.assertEqual(self.gpio.values[pin], 0)

    def test_inversion_swaps_the_driven_input(self):
        self.controller.set_inverted(1, True)
        self.controller.set_ports({1: 0.4})
        self.assertEqual(self.gpio.values[19], 0.4)
        self.assertEqual(self.gpio.values[26], 0)

    def test_reversal_uses_one_shared_deadtime(self):
        self.controller.set_ports({port: 0.4 for port in range(1, 5)})
        with patch("robot_server.controller.time.sleep") as sleep:
            self.controller.set_ports({port: -0.4 for port in range(1, 5)})
        sleep.assert_called_once_with(0.015)

    def test_values_are_clamped_and_validated(self):
        self.controller.set_ports({2: 3})
        self.assertEqual(self.controller.motor_values[2], 1.0)
        with self.assertRaises(ValueError):
            self.controller.set_ports({5: 0.2})
        with self.assertRaises(ValueError):
            self.controller.set_ports({1: float("nan")})

    def test_watchdog_stops_stale_outputs(self):
        self.controller.close()
        self.gpio = MockGPIO()
        self.controller = MotionController(self.gpio, MockServoBoard(), watchdog_ms=50)
        self.controller.set_ports({3: 0.3})
        time.sleep(0.15)
        self.assertEqual(self.controller.motor_values[3], 0)
        self.assertTrue(self.controller.snapshot()["watchdog_tripped"])

    def test_oe_is_active_low_and_blocks_servo_commands_when_cut(self):
        self.assertEqual(self.gpio.values[4], 0)
        self.controller.set_servo_outputs_enabled(False)
        self.assertEqual(self.gpio.values[4], 1)
        with self.assertRaises(RobotError):
            self.controller.set_servo_pulse(0, 1500)

    def test_close_stops_motors_and_cuts_servo_outputs(self):
        self.controller.set_ports({1: 0.5})
        self.controller.close()
        self.assertTrue(self.gpio.closed)
        self.assertEqual(self.gpio.values[26], 0)


if __name__ == "__main__":
    unittest.main()
