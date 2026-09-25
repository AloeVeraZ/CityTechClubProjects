import json
import tempfile
import unittest
from pathlib import Path

from robot_server.errors import ConfigurationError
from robot_server.settings import RobotSettings, SettingsStore, from_dict


class SettingsTests(unittest.TestCase):
    def test_defaults_match_the_motionmodule_mecanum_layout(self):
        settings = RobotSettings()
        self.assertEqual(settings.wheels, {"front_left": 1, "rear_left": 2, "front_right": 3, "rear_right": 4})
        self.assertEqual(from_dict(settings.to_dict()), settings)

    def test_a_port_cannot_drive_two_wheels(self):
        data = RobotSettings().to_dict()
        data["wheels"]["front_left"] = 3
        with self.assertRaisesRegex(ConfigurationError, "port 3"):
            from_dict(data)

    def test_ports_and_channels_are_range_checked(self):
        data = RobotSettings().to_dict()
        data["wheels"]["front_left"] = 5
        with self.assertRaises(ConfigurationError):
            from_dict(data)
        data = RobotSettings().to_dict()
        data["ramp"]["servos"]["ramp_left"]["channel"] = 1
        with self.assertRaisesRegex(ConfigurationError, "Both ramp servos"):
            from_dict(data)
        data = RobotSettings().to_dict()
        data["ramp"]["min_pulse_us"] = 300
        with self.assertRaises(ConfigurationError):
            from_dict(data)

    def test_swapped_map_round_trips_through_the_file(self):
        with tempfile.TemporaryDirectory() as folder:
            store = SettingsStore(Path(folder) / "nested" / "robot.json")
            data = RobotSettings().to_dict()
            data["wheels"].update(front_left=2, rear_left=1)
            data["inverted"]["2"] = True
            store.save(from_dict(data))
            loaded = SettingsStore(store.path).load()
            self.assertEqual(loaded.port_for("front_left"), 2)
            self.assertTrue(loaded.inverted[2])

    def test_corrupt_file_falls_back_to_defaults_with_a_message(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "robot.json"
            path.write_text(json.dumps({"wheels": {"front_left": 9}}))
            store = SettingsStore(path)
            self.assertEqual(store.load(), RobotSettings())
            self.assertIn("invalid", store.load_error)


if __name__ == "__main__":
    unittest.main()
