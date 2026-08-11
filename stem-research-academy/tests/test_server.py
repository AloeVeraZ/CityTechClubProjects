import unittest
from unittest.mock import patch

from robot_server.app import app, drive, drive_sequences, scout_sequences


class ServerTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def tearDown(self):
        drive.stop()
        drive_sequences.clear()
        scout_sequences.clear()

    def test_health(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ok"])

    def test_drive_command(self):
        response = self.client.post(
            "/api/drive",
            json={"forward": 1, "strafe": 0, "rotate": 0, "speed": 0.5},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(drive.last_command["forward"], 1)
        self.assertEqual(drive.last_command["speed"], 0.5)

    def test_invalid_drive_command(self):
        response = self.client.post("/api/drive", json={"forward": "fast"})
        self.assertEqual(response.status_code, 400)

    def test_stale_big_robot_command_is_ignored(self):
        self.client.post("/api/drive", json={"forward": 0, "session": "test", "sequence": 2})
        response = self.client.post(
            "/api/drive", json={"forward": 1, "session": "test", "sequence": 1}
        )
        self.assertTrue(response.get_json()["stale"])
        self.assertEqual(drive.last_command["forward"], 0)

    def test_non_finite_drive_command(self):
        response = self.client.post("/api/drive", json={"forward": "NaN"})
        self.assertEqual(response.status_code, 400)

    def test_dashboard_renders_all_three_robots(self):
        response = self.client.get("/")
        self.assertIn(b"Chassis control", response.data)
        self.assertIn(b"ECHO Scout A", response.data)
        self.assertIn(b"ECHO Scout B", response.data)

    @patch("robot_server.app._scout_request", return_value={"id": "A", "motion": False})
    def test_scout_status_proxy(self, scout_request):
        response = self.client.get("/api/scouts/a/status")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["online"])
        scout_request.assert_called_once_with("a", "/status")

    @patch("robot_server.app._scout_request", return_value={"ok": True})
    def test_scout_drive_proxy_clamps_values(self, scout_request):
        response = self.client.post(
            "/api/scouts/b/drive",
            json={"x": 500, "y": -500, "speed": 35},
        )
        self.assertEqual(response.status_code, 200)
        scout_request.assert_called_once_with(
            "b", "/drive", {"x": 100, "y": -100, "speed": 35}
        )

    @patch("robot_server.app._scout_request", return_value={"ok": True})
    def test_stale_scout_command_is_not_forwarded(self, scout_request):
        self.client.post(
            "/api/scouts/a/drive",
            json={"x": 0, "y": 0, "session": "test", "sequence": 2},
        )
        response = self.client.post(
            "/api/scouts/a/drive",
            json={"x": 0, "y": 100, "session": "test", "sequence": 1},
        )
        self.assertTrue(response.get_json()["stale"])
        self.assertEqual(scout_request.call_count, 1)

    @patch("robot_server.app._scout_request", side_effect=OSError("offline"))
    def test_offline_scout_status_is_safe(self, _scout_request):
        response = self.client.get("/api/scouts/a/status")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()["online"])


if __name__ == "__main__":
    unittest.main()
