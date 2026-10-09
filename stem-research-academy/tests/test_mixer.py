"""3TSahur's drive mix, checked at the GPIO pins listed in docs/WIRING.md."""

import ast
import sys
import unittest
from pathlib import Path

ROBOT = Path(__file__).resolve().parents[1] / "robot" / "3TSahur"
sys.path.insert(0, str(ROBOT))

from mixer import WHEELS, mix, outputs  # noqa: E402


def hardware():
    tree = ast.parse((ROBOT / "hardware.py").read_text(encoding="utf-8"))
    node = next(item for item in tree.body if isinstance(item, ast.Assign) and item.targets[0].id == "HARDWARE")
    return ast.literal_eval(node.value)


MOTORS = {motor["name"]: motor for motor in hardware()["motors"].values()}


def active_pins(forward, strafe, rotate):
    """The GPIO each wheel's PWM is on, as the MotionModule H-bridge drives it."""

    pins = set()
    for name, power in mix(forward, strafe, rotate).items():
        motor = MOTORS[name]
        if motor["inverted"]:
            power = -power
        if power > 0:
            pins.add(motor["forward_gpio"])
        elif power < 0:
            pins.add(motor["reverse_gpio"])
    return pins


class WiringTests(unittest.TestCase):
    def test_pins_match_the_original_3tsahur_wiring(self):
        self.assertEqual(
            {name: (motor["forward_gpio"], motor["reverse_gpio"], motor["inverted"]) for name, motor in MOTORS.items()},
            {
                "front_left": (5, 6, False),
                "rear_left": (19, 16, False),
                "front_right": (20, 21, False),
                "rear_right": (26, 13, False),
            },
        )
        self.assertEqual(set(WHEELS), set(MOTORS))

    def test_no_motor_pin_is_a_ramp_servo_pin(self):
        used = {pin for motor in MOTORS.values() for pin in (motor["forward_gpio"], motor["reverse_gpio"])}
        self.assertFalse(used & {12, 18})

    def test_servo_board_is_disabled(self):
        self.assertFalse(hardware()["servos"]["enabled"])


class DirectionTests(unittest.TestCase):
    def test_w_drives_the_documented_pins(self):
        self.assertEqual(active_pins(1, 0, 0), {6, 16, 21, 13})

    def test_s_drives_the_documented_pins(self):
        self.assertEqual(active_pins(-1, 0, 0), {5, 19, 20, 26})

    def test_e_rotates_on_the_documented_pins(self):
        # MotionModule sends -rotate for E (turn right).
        self.assertEqual(active_pins(0, 0, -1), {6, 21, 19, 26})

    def test_q_is_the_exact_inverse_of_e(self):
        self.assertEqual(active_pins(0, 0, 1), {5, 20, 16, 13})

    def test_a_and_d_keep_the_original_strafe_directions(self):
        # The original dashboard sent +strafe for A; MotionModule sends -strafe.
        self.assertEqual(
            mix(0, -1, 0),
            {"front_left": 1, "rear_left": -1, "front_right": -1, "rear_right": 1},
        )
        self.assertEqual(active_pins(0, 1, 0), active_pins(0, -1, 0) ^ {5, 6, 19, 16, 20, 21, 26, 13})

    def test_combined_commands_stay_within_full_power(self):
        for command in ((1, 1, 1), (-1, 1, -1), (1, -1, 1)):
            self.assertLessEqual(max(abs(power) for power in mix(*command).values()), 1)

    def test_speed_limit_scales_every_wheel(self):
        self.assertEqual(set(outputs(1, 0, 0, 0.4).values()), {-0.4})
        self.assertEqual(set(outputs(1, 0, 0, 5).values()), {-1.0})

    def test_bad_values_are_refused(self):
        for value in (float("nan"), float("inf"), "1", True):
            with self.assertRaises(ValueError):
                mix(value, 0, 0)


if __name__ == "__main__":
    unittest.main()
