import unittest

from robot_server.app import create_app

from helpers import make_robot


class FakeCamera:
    available = False
    error = None
    camera_name = "USB camera"
    selected_device = None
    width, height, fps = 640, 480, 10
    capture_width = capture_height = capture_fps = None
    frame_age_seconds = float("inf")

    def configure(self, *args):
        self.configured = args


class FakeHealth:
    def snapshot(self):
        return {"status": "ok"}


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.robot, self.gpio = make_robot(self)
        self.app = create_app(self.robot, FakeCamera(), FakeHealth())
        self.client = self.app.test_client()
        self.headers = {"X-Robot-Token": self.app.config["ROBOT_TOKEN"]}

    def post(self, url, body, headers=True):
        return self.client.post(url, json=body, headers=self.headers if headers else {})

    def test_only_the_driver_station_and_debug_pages_exist(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/debug").status_code, 200)
        self.assertEqual(self.client.get("/code").status_code, 404)
        self.assertEqual(self.client.post("/api/projects/deploy").status_code, 404)

    def test_commands_need_the_page_token_but_stop_never_does(self):
        self.assertEqual(self.post("/api/drive", {"sequence": 1, "forward": 1}, headers=False).status_code, 403)
        self.assertEqual(self.post("/api/settings", {}, headers=False).status_code, 403)
        self.assertEqual(self.post("/api/stop", {}, headers=False).status_code, 200)

    def test_drive_and_stale_sequences(self):
        response = self.post("/api/drive", {"sequence": 5, "forward": 1, "speed": 0.5})
        self.assertEqual(response.json["wheels"]["front_left"], 0.5)
        self.assertEqual(self.robot.controller.motor_values[1], 0.5)
        stale = self.post("/api/drive", {"sequence": 4, "forward": 0})
        self.assertEqual(stale.json["ignored"], "stale sequence")
        self.assertEqual(self.robot.controller.motor_values[1], 0.5)
        bad = self.post("/api/drive", {"sequence": 6, "forward": "fast"})
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(self.robot.controller.motor_values[1], 0)

    def test_status_reports_wheels_ramp_imu_and_servo_board(self):
        robot = self.client.get("/api/status").json["robot"]
        self.assertEqual(robot["wheels"]["front_right"]["port"], 3)
        self.assertEqual(robot["ramp"]["state"], "closed")
        self.assertTrue(robot["imu"]["connected"])
        self.assertTrue(robot["servo_board"]["available"])
        self.assertEqual(sorted(robot["ports"]), ["1", "2", "3", "4"])

    def test_settings_remap_from_the_debug_page(self):
        settings = self.client.get("/api/config").json["settings"]
        settings["wheels"].update(front_left=2, rear_left=1)
        self.assertEqual(self.post("/api/settings", settings).status_code, 200)
        self.assertEqual(self.robot.settings.port_for("front_left"), 2)
        settings["wheels"]["rear_left"] = 2
        response = self.post("/api/settings", settings)
        self.assertEqual(response.status_code, 400)
        self.assertIn("port 2", response.json["error"])

    def test_debug_outputs_require_confirmation(self):
        self.assertEqual(self.post("/api/debug/motor", {"port": 1, "power": 0.2}).status_code, 400)
        self.assertEqual(self.post("/api/debug/motor", {"port": 1, "power": 0.2, "confirmed": True}).status_code, 200)
        self.assertEqual(self.robot.controller.motor_values[1], 0.2)
        self.assertEqual(self.post("/api/debug/motor", {"port": 1, "power": 0.8, "confirmed": True}).status_code, 400)
        response = self.post("/api/debug/servo", {"channel": 5, "angle": 45, "confirmed": True})
        self.assertEqual(response.json["pulse_us"], 1000.0)
        self.post("/api/debug/servo/release", {"channel": 5})
        self.assertNotIn(5, self.robot.controller.servos.pulses)

    def test_debug_motor_refused_while_driving(self):
        self.post("/api/drive", {"sequence": 1, "forward": 0.5})
        response = self.post("/api/debug/motor", {"port": 1, "power": 0.2, "confirmed": True})
        self.assertEqual(response.status_code, 409)

    def test_ramp_emergency_stop_and_output_enable(self):
        self.assertEqual(self.post("/api/ramp", {"state": "open"}).json["ramp"]["state"], "open")
        self.post("/api/stop", {"emergency": True})
        self.assertEqual(self.robot.ramp_state, "released")
        self.assertFalse(self.robot.controller.servo_outputs_enabled)
        self.assertTrue(self.post("/api/servos/output-enable", {"enabled": True}).json["enabled"])

    def test_zero_heading(self):
        self.assertEqual(self.post("/api/imu/zero", {}).json["imu"]["yaw"], 0.0)


if __name__ == "__main__":
    unittest.main()
