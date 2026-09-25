import unittest

from robot_server.robot import mix
from robot_server.settings import RobotSettings, from_dict

from helpers import make_robot


class MixTests(unittest.TestCase):
    def test_forward_strafe_and_turn(self):
        self.assertEqual(set(mix(1, 0, 0).values()), {1.0})
        self.assertEqual(mix(0, 1, 0), {"front_left": 1, "front_right": -1, "rear_left": -1, "rear_right": 1})
        # Positive rotate turns left: left wheels back, right wheels forward.
        self.assertEqual(mix(0, 0, 1), {"front_left": -1, "front_right": 1, "rear_left": -1, "rear_right": 1})

    def test_combined_commands_are_scaled_together(self):
        powers = mix(1, 1, 0)
        self.assertEqual(max(abs(value) for value in powers.values()), 1.0)
        self.assertEqual(powers["front_right"], 0.0)


class RobotTests(unittest.TestCase):
    def setUp(self):
        self.robot, self.gpio = make_robot(self)

    def test_drive_reaches_the_mapped_ports(self):
        self.robot.drive(0, 1, 0, 0.5)   # strafe right
        values = self.robot.controller.motor_values
        self.assertEqual(values, {1: 0.5, 2: -0.5, 3: -0.5, 4: 0.5})

    def test_remapping_moves_a_wheel_to_another_port(self):
        data = RobotSettings().to_dict()
        data["wheels"].update(front_left=2, rear_left=1)
        self.robot.apply_settings(from_dict(data))
        self.robot.drive(0, 1, 0, 0.5)
        self.assertEqual(self.robot.controller.motor_values[2], 0.5)   # front left now on port 2
        self.assertEqual(self.robot.controller.motor_values[1], -0.5)  # rear left now on port 1
        self.assertEqual(self.robot.store.load().port_for("front_left"), 2)

    def test_inversion_from_settings_reaches_the_gpio(self):
        data = RobotSettings().to_dict()
        data["inverted"]["3"] = True
        self.robot.apply_settings(from_dict(data))
        self.robot.drive(1, 0, 0, 0.4)
        self.assertEqual(self.gpio.values[20], 0.4)   # port 3 reverse input
        self.assertEqual(self.gpio.values[21], 0)

    def test_ramp_starts_closed_and_mirrors_the_second_servo(self):
        pulses = self.robot.controller.servos.pulses
        self.assertEqual(self.robot.ramp_state, "closed")
        self.assertEqual(round(pulses[0]), 1000)
        self.assertEqual(round(pulses[1]), 1667)
        self.robot.set_ramp("open")
        self.assertEqual(round(pulses[0]), 1667)
        self.assertEqual(round(pulses[1]), 1000)
        with self.assertRaises(ValueError):
            self.robot.set_ramp("sideways")

    def test_ramp_follows_a_new_channel(self):
        data = RobotSettings().to_dict()
        data["ramp"]["servos"]["ramp_right"]["channel"] = 7
        self.robot.apply_settings(from_dict(data))
        pulses = self.robot.controller.servos.pulses
        self.assertNotIn(1, pulses)
        self.assertEqual(round(pulses[7]), 1667)

    def test_soft_stop_keeps_the_ramp_and_emergency_releases_it(self):
        self.robot.drive(1, 0, 0, 0.5)
        self.robot.stop()
        self.assertEqual(set(self.robot.controller.motor_values.values()), {0.0})
        self.assertTrue(self.robot.controller.servos.pulses)
        self.robot.emergency_stop()
        self.assertEqual(self.robot.controller.servos.pulses, {})
        self.assertFalse(self.robot.controller.servo_outputs_enabled)
        # Commanding the ramp again is deliberate and re-enables the outputs.
        self.robot.set_ramp("closed")
        self.assertTrue(self.robot.controller.servo_outputs_enabled)

    def test_debug_port_and_servo_tests_are_limited(self):
        self.robot.test_port(4, -0.3)
        self.assertEqual(self.robot.controller.motor_values[4], -0.3)
        with self.assertRaises(ValueError):
            self.robot.test_port(4, 0.9)
        with self.assertRaises(ValueError):
            self.robot.test_port(5, 0.1)
        self.assertEqual(self.robot.test_servo(9, angle=90), 1500)
        self.robot.release_servo(9)
        self.assertNotIn(9, self.robot.controller.servos.pulses)
        with self.assertRaises(ValueError):
            self.robot.test_servo(9, angle=200)


if __name__ == "__main__":
    unittest.main()
