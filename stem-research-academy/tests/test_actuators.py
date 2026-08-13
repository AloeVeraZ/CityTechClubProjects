import pathlib
import time
import unittest
from unittest.mock import patch

from robot_server.actuators import ActuatorController, DirectGPIOServoBoard


class FakePWM:
    def __init__(self, pin, frequency):
        self.pin = pin
        self.frequency = frequency
        self.started = []
        self.duties = []
        self.stopped = False

    def start(self, duty):
        self.started.append(duty)

    def ChangeDutyCycle(self, duty):
        self.duties.append(duty)

    def stop(self):
        self.stopped = True


class FakeGPIO:
    BCM = 11
    OUT = 1
    LOW = 0

    def __init__(self):
        self.mode = None
        self.setups = []
        self.pwms = {}
        self.cleaned = []

    def setwarnings(self, _enabled):
        pass

    def setmode(self, mode):
        self.mode = mode

    def setup(self, pin, mode, initial=None):
        self.setups.append((pin, mode, initial))

    def PWM(self, pin, frequency):
        pwm = FakePWM(pin, frequency)
        self.pwms[pin] = pwm
        return pwm

    def cleanup(self, pins):
        self.cleaned.append(tuple(pins))


class FakeServoBoard:
    def __init__(self):
        self.pins = {0: 12, 1: 18}
        self.hardware = True
        self.error = None
        self.settle_seconds = 0.6
        self.angles = []

    def set_angle(self, channel, angle):
        self.angles.append((channel, angle))

    def close(self):
        pass


class ServoActuatorTests(unittest.TestCase):
    def test_installer_has_direct_gpio_servo_configuration(self):
        installer = (pathlib.Path(__file__).parents[1] / "installer" / "install.sh").read_text(encoding="utf-8")
        self.assertIn("python3-rpi.gpio", installer)
        self.assertIn("RAMP_SERVO_0_GPIO_BCM=12", installer)
        self.assertIn("RAMP_SERVO_1_GPIO_BCM=18", installer)
        self.assertIn("RAMP_SERVO_SETTLE_SECONDS=0.6", installer)

    def test_direct_gpio_initializes_both_servos_closed_at_zero_degrees(self):
        gpio = FakeGPIO()
        board = DirectGPIOServoBoard(gpio_module=gpio)

        self.assertTrue(board.hardware)
        self.assertEqual(gpio.mode, gpio.BCM)
        self.assertEqual([item[0] for item in gpio.setups], [12, 18])
        self.assertAlmostEqual(gpio.pwms[12].started[0], 5.0)
        self.assertAlmostEqual(gpio.pwms[18].started[0], 5.0)
        board.close()

    def test_pwm_signal_is_released_after_servo_settles(self):
        gpio = FakeGPIO()
        with patch.dict("os.environ", {"RAMP_SERVO_SETTLE_SECONDS": "0.1"}):
            board = DirectGPIOServoBoard(gpio_module=gpio)
        board.set_angle(0, 30)
        self.assertGreater(gpio.pwms[12].duties[-1], 0)

        time.sleep(0.14)

        self.assertEqual(gpio.pwms[12].duties[-1], 0)
        self.assertEqual(gpio.pwms[18].duties[-1], 0)
        board.close()

    def test_open_moves_both_ramp_servos_to_30_degrees(self):
        board = FakeServoBoard()
        controller = ActuatorController(board=board)
        result = controller.set_ramp("open")

        self.assertEqual(board.angles, [(0, 30.0), (1, 30.0)])
        self.assertEqual(result["ramp"]["state"], "open")
        self.assertEqual(result["channels"], {"0": 30.0, "1": 30.0})

    def test_closed_returns_both_ramp_servos_to_zero(self):
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
