import importlib
import time
import unittest
from unittest.mock import patch

from robot_server.app import app, drive, drive_sequences

app_module = importlib.import_module("robot_server.app")


class ServerTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def tearDown(self):
        drive.stop()
        app_module.last_drive_at = 0
        drive_sequences.clear()

    @staticmethod
    def current_command(**values):
        values["expires_at_ms"] = round(time.time() * 1000) + 1000
        return values

    def test_health(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ok"])

    def test_status_exposes_big_robot_hardware(self):
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["name"], "3TSahur")
        self.assertIn(data["camera_profile"], {"control", "balanced", "detail"})
        self.assertEqual(data["camera_mode"], "automatic")
        self.assertIn("camera_name", data)
        self.assertIn("system_health", data)
        self.assertIn("actuators", data)

    def test_drive_command(self):
        response = self.client.post(
            "/api/drive",
            json=self.current_command(forward=1, strafe=0, rotate=0, speed=0.5),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(drive.last_command["forward"], 1)
        self.assertEqual(drive.last_command["speed"], 0.5)

    def test_invalid_drive_command(self):
        response = self.client.post("/api/drive", json=self.current_command(forward="fast"))
        self.assertEqual(response.status_code, 400)

    def test_non_finite_drive_command(self):
        response = self.client.post("/api/drive", json=self.current_command(forward="NaN"))
        self.assertEqual(response.status_code, 400)

    def test_stale_command_is_ignored(self):
        self.client.post(
            "/api/drive",
            json=self.current_command(forward=0, session="test", sequence=2),
        )
        response = self.client.post(
            "/api/drive",
            json=self.current_command(forward=1, session="test", sequence=1),
        )
        self.assertTrue(response.get_json()["stale"])
        self.assertEqual(drive.last_command["forward"], 0)

    def test_expired_command_cannot_replay(self):
        drive.drive(1, 0, 0, 0.5)
        response = self.client.post("/api/drive", json={"forward": 1, "expires_at_ms": 1})
        self.assertEqual(response.status_code, 409)
        self.assertTrue(response.get_json()["expired"])
        self.assertEqual(drive.last_command["forward"], 0)

    def test_implausible_future_command_is_rejected(self):
        response = self.client.post(
            "/api/drive",
            json={"forward": 1, "expires_at_ms": round(time.time() * 1000) + 60_000},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(drive.last_command["forward"], 0)

    def test_dashboard_renders_only_the_large_robot(self):
        response = self.client.get("/")
        self.assertIn(b'data-robot-panel="3tsahur"', response.data)
        self.assertIn(b'data-stream-for="3tsahur"', response.data)
        self.assertIn(b"3TSahur", response.data)

    def test_ramp_accepts_two_positions_without_drive_changes(self):
        ramp = self.client.post("/api/actuators/ramp", json={"state": "open"})
        self.assertEqual(ramp.status_code, 200)
        self.assertEqual(ramp.get_json()["ramp"]["state"], "open")
        self.assertEqual(drive.last_command["forward"], 0)

    def test_ramp_rejects_invalid_values(self):
        response = self.client.post("/api/actuators/ramp", json={"state": "sideways"})
        self.assertEqual(response.status_code, 400)

    @patch("robot_server.app.camera.configure")
    def test_camera_profile_isolated_from_drive(self, configure):
        response = self.client.post("/api/camera/profile", json={"profile": "control"})
        self.assertEqual(response.status_code, 200)
        configure.assert_called_once_with(320, 240, 6)
        drive_response = self.client.post("/api/drive", json=self.current_command(forward=1))
        self.assertEqual(drive_response.status_code, 200)
        self.assertEqual(drive.last_command["forward"], 1)

    def test_invalid_camera_profile_is_rejected(self):
        response = self.client.post("/api/camera/profile", json={"profile": "unsafe"})
        self.assertEqual(response.status_code, 400)

    def test_activity_log_is_bounded_and_hardware_independent(self):
        created = self.client.post(
            "/api/events",
            json={"kind": "test", "source": "test", "message": "activity ok"},
        )
        self.assertEqual(created.status_code, 200)
        listed = self.client.get("/api/events")
        self.assertTrue(any(event["message"] == "activity ok" for event in listed.get_json()["events"]))

    @patch("robot_server.app._snapshot_bytes", return_value=None)
    def test_unavailable_snapshot_does_not_affect_drive(self, snapshot):
        response = self.client.post("/api/snapshots/3tsahur")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(drive.last_command["forward"], 0)

    def test_snapshot_accepts_only_the_large_robot_camera(self):
        self.assertEqual(self.client.post("/api/snapshots/other").status_code, 404)


if __name__ == "__main__":
    unittest.main()
