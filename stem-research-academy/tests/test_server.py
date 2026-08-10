import unittest

from robot_server.app import app, drive


class ServerTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def tearDown(self):
        drive.stop()

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

    def test_non_finite_drive_command(self):
        response = self.client.post("/api/drive", json={"forward": "NaN"})
        self.assertEqual(response.status_code, 400)

    def test_dashboard_renders_all_three_robots(self):
        response = self.client.get("/")
        self.assertIn(b"Chassis control", response.data)
        self.assertIn(b"ESP32 Scout A", response.data)
        self.assertIn(b"ESP32 Scout B", response.data)


if __name__ == "__main__":
    unittest.main()
