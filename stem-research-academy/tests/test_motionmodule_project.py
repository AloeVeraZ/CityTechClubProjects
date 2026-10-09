"""The 3TSahur folder loaded by the real MotionModule runtime, in simulation.

These run where MotionModule is importable (pip install -e a MotionModule
checkout, or the Pi's release venv) and are skipped otherwise.
"""

import os
import sys
import unittest
from pathlib import Path

ROBOT = Path(__file__).resolve().parents[1] / "robot" / "3TSahur"
os.environ.setdefault("MOTIONMODULE_MOCK", "1")

try:
    from motion_module.config import load_project_config
    from motion_module.controller import MotionModule
    from motion_module.dashboard import create_app, load_project_hooks
    from motion_module.drive_test import DriveTest
    from motion_module.gpio import MockGPIO
    from motion_module.retired_wiring import on_retired_wiring
except ImportError:  # MotionModule is not installed on this computer
    MotionModule = None


def active(module):
    return {gpio for gpio, value in module.gpio.values.items() if value}


@unittest.skipIf(MotionModule is None, "MotionModule is not installed")
class MotionModuleProjectTests(unittest.TestCase):
    def setUp(self):
        self.module = MotionModule(load_project_config(ROBOT), gpio=MockGPIO())
        self.addCleanup(self.module.close)
        self.drive, self.telemetry, error = load_project_hooks(self.module, ROBOT / "robot.py")
        self.assertEqual(error, "")
        self.addCleanup(self.telemetry.close)

    def test_hardware_map_validates_and_is_not_rewritten_by_installs(self):
        config = load_project_config(ROBOT)
        self.assertEqual(config.motor_names, ("front_left", "rear_left", "front_right", "rear_right"))
        self.assertFalse(config.servos.enabled)
        # MotionModule's installer replaces pin maps that match its retired wiring.
        self.assertFalse(on_retired_wiring(ROBOT / "hardware.py"))

    def test_driver_station_drive_uses_the_3tsahur_pins(self):
        self.drive.drive(1, 0, 0, 0.5)
        self.assertEqual(active(self.module), {6, 16, 21, 13})
        self.drive.stop()
        self.assertEqual(active(self.module), set())

    def test_debug_drive_test_uses_test_py(self):
        test = DriveTest(self.module, ROBOT / "robot.py")
        test.drive(0, 0, -1, 0.4)
        self.assertEqual(active(self.module), {6, 21, 19, 26})
        test.stop()
        self.assertEqual(active(self.module), set())

    def test_dashboard_controls_and_telemetry(self):
        app = create_app(self.module, self.drive, project_name="3TSahur",
                         dashboard_telemetry=self.telemetry, project_path=ROBOT / "robot.py")
        client = app.test_client()
        token = {"X-MotionModule-Token": app.config["DASHBOARD_TOKEN"]}

        names = [item["name"] for item in client.get("/api/drive/controls").get_json()["controls"]]
        self.assertEqual(names, ["toggle_ramp", "open_ramp", "close_ramp"])

        reply = client.post("/api/drive/control", json={"name": "toggle_ramp", "value": 1}, headers=token)
        self.assertEqual(reply.get_json()["result"], {"ramp": "open"})

        telemetry = client.get("/api/drive/telemetry").get_json()
        self.assertEqual(telemetry["control_keys"], {"toggle_ramp": "r"})
        self.assertEqual(telemetry["pi_inputs"][0]["value"], "open")
        self.assertEqual(telemetry["cameras"][0]["name"], "Front camera")


if __name__ == "__main__":
    unittest.main()
