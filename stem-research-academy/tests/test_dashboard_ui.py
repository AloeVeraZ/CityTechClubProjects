import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (PROJECT_ROOT / "robot_server" / "templates" / "index.html").read_text(encoding="utf-8")
STYLES = (PROJECT_ROOT / "robot_server" / "static" / "dashboard.css").read_text(encoding="utf-8")
SCRIPT = (PROJECT_ROOT / "robot_server" / "static" / "dashboard.js").read_text(encoding="utf-8")


class DashboardTests(unittest.TestCase):
    def test_large_robot_workspace_has_video_and_controls(self):
        self.assertEqual(TEMPLATE.count('data-robot-panel="'), 1)
        self.assertIn('data-robot-panel="3tsahur"', TEMPLATE)
        self.assertIn('alt="Live automatic Logitech USB camera feed from 3TSahur"', TEMPLATE)
        self.assertIn('aria-label="3TSahur drive controls"', TEMPLATE)

    def test_only_one_camera_stream_is_active(self):
        self.assertEqual(TEMPLATE.count("data-stream-for="), 1)
        self.assertEqual(TEMPLATE.count("data-stream-src="), 1)
        self.assertIn("const selectedCameras = new Set(['3tsahur'])", SCRIPT)
        self.assertIn("feed.removeAttribute('src')", SCRIPT)

    def test_camera_snapshot_and_health_are_available(self):
        self.assertIn('class="camera-auto"', TEMPLATE)
        self.assertIn('id="hub-camera-model"', TEMPLATE)
        self.assertIn('data-snapshot="3tsahur"', TEMPLATE)
        self.assertIn('id="health-panel"', TEMPLATE)
        self.assertIn("/api/snapshots/${source}", SCRIPT)
        self.assertIn("healthSummary.value", SCRIPT)

    def test_safety_and_gamepad_controls_remain(self):
        self.assertIn('id="deadman"', TEMPLATE)
        self.assertIn('id="auto-priority"', TEMPLATE)
        self.assertIn("function recordControlTiming", SCRIPT)
        self.assertIn("function anyRobotMoving", SCRIPT)
        self.assertIn("navigator.getGamepads", SCRIPT)
        self.assertIn("now - lastGamepadSentAt >= 80", SCRIPT)

    def test_ramp_has_two_position_controls(self):
        self.assertIn('id="ramp-toggle"', TEMPLATE)
        self.assertIn('id="ramp-readout"', TEMPLATE)
        self.assertIn("key === 'r'", SCRIPT)
        self.assertIn("/api/actuators/ramp", SCRIPT)
        self.assertIn('state: "closed"', SCRIPT)
        self.assertIn('state === "open"', SCRIPT)
        self.assertIn("Servo GPIO unavailable", SCRIPT)
        self.assertIn(".actuator-card", STYLES)

    def test_q_and_e_are_pure_four_wheel_rotations_at_75_percent(self):
        self.assertIn("const rotate = Number(bigPressed.has('q')) - Number(bigPressed.has('e'))", SCRIPT)
        self.assertIn("if (rotate) return {forward: 0, strafe: 0, rotate, speed: 0.75};", SCRIPT)
        self.assertIn("Q/E four-wheel rotate at 75%", TEMPLATE)

    def test_drive_heartbeat_and_stop_timeout_remain(self):
        self.assertIn("if (bigPressed.size) sendBig(true)", SCRIPT)
        self.assertIn("}, 80);", SCRIPT)
        self.assertIn("controller.abort(), 140", SCRIPT)
        self.assertIn("window.addEventListener('blur', () => killAll())", SCRIPT)

    def test_video_and_controls_use_separate_columns(self):
        self.assertIn('grid-template-columns: minmax(0, 1.08fr) minmax(520px, .92fr);', STYLES)
        self.assertIn('#panel-3tsahur .video-stage { grid-area: 1 / 1 / 2 / 2; }', STYLES)
        self.assertIn('#panel-3tsahur .control-stage { grid-area: 1 / 2 / 2 / 3; }', STYLES)


if __name__ == "__main__":
    unittest.main()
