import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (PROJECT_ROOT / "robot_server" / "templates" / "index.html").read_text(encoding="utf-8")
STYLES = (PROJECT_ROOT / "robot_server" / "static" / "dashboard.css").read_text(encoding="utf-8")
SCRIPT = (PROJECT_ROOT / "robot_server" / "static" / "dashboard.js").read_text(encoding="utf-8")


class DashboardTabTests(unittest.TestCase):
    def test_only_the_3tsahur_workspace_is_visible(self):
        self.assertIn('data-robot-panel="3tsahur"', TEMPLATE)
        self.assertNotIn('data-camera-select=', TEMPLATE)
        self.assertNotIn('LARP Scout', TEMPLATE)
        self.assertNotIn('data-scout-panel=', TEMPLATE)

    def test_3tsahur_has_its_video_and_controls(self):
        self.assertIn('alt="Live automatic Logitech USB camera feed from 3TSahur"', TEMPLATE)
        self.assertIn('aria-label="3TSahur drive controls"', TEMPLATE)

    def test_only_the_hub_camera_stream_is_active(self):
        self.assertEqual(TEMPLATE.count("data-stream-for="), 1)
        self.assertEqual(TEMPLATE.count("data-stream-src="), 1)
        self.assertIn("function activateSelectedCameras", SCRIPT)
        self.assertIn("const selectedCameras = new Set(['3tsahur'])", SCRIPT)
        self.assertIn("feed.removeAttribute('src')", SCRIPT)

    def test_scout_controls_and_polling_are_absent(self):
        self.assertNotIn("CSI presence sensor", TEMPLATE)
        self.assertNotIn("refreshScout", SCRIPT)
        self.assertNotIn("queueScouts", SCRIPT)
        self.assertNotIn("/api/scouts/", SCRIPT)

    def test_vision_has_a_per_camera_toggle_and_overlay(self):
        self.assertEqual(TEMPLATE.count('data-vision-toggle="'), 1)
        self.assertIn('data-vision-toggle="3tsahur"', TEMPLATE)
        self.assertIn('data-vision-overlay="3tsahur"', TEMPLATE)
        self.assertIn("key === 'c'", SCRIPT)
        self.assertIn("toggleVision(activeRobotTab)", SCRIPT)
        self.assertIn("/api/vision/${source}", SCRIPT)
        self.assertIn("Vision unavailable - robot controls remain active", SCRIPT)
        self.assertIn(".vision-overlay", STYLES)

    def test_recon_features_are_optional_and_control_aware(self):
        self.assertEqual(TEMPLATE.count('data-landmark-toggle="'), 1)
        self.assertEqual(TEMPLATE.count('data-evidence="'), 1)
        self.assertIn('id="auto-priority"', TEMPLATE)
        self.assertIn("/api/landmarks/${source}", SCRIPT)
        self.assertIn("/api/evidence/${source}", SCRIPT)
        self.assertIn("function recordControlTiming", SCRIPT)
        self.assertIn("function anyRobotMoving", SCRIPT)
        self.assertIn("if (anyRobotMoving()) return;", SCRIPT)
        self.assertIn("cameraFeeds.forEach(feed => feed.removeAttribute('src'))", SCRIPT)

    def test_mission_tools_automatic_camera_and_health_are_dashboard_features(self):
        self.assertNotIn('id="camera-profile"', TEMPLATE)
        self.assertIn('class="camera-auto"', TEMPLATE)
        self.assertIn('id="hub-camera-model"', TEMPLATE)
        self.assertIn('id="hub-camera-mode"', TEMPLATE)
        self.assertIn('id="health-panel"', TEMPLATE)
        self.assertEqual(TEMPLATE.count('data-snapshot="'), 1)
        self.assertNotIn('data-calibrate="', TEMPLATE)
        self.assertIn('id="deadman"', TEMPLATE)
        self.assertIn('id="event-list"', TEMPLATE)
        self.assertNotIn("/api/camera/profile", SCRIPT)
        self.assertIn("/api/snapshots/${source}", SCRIPT)
        self.assertIn("navigator.getGamepads", SCRIPT)
        self.assertIn("lastGamepadSignature", SCRIPT)
        self.assertIn("lastGamepadSentAt", SCRIPT)
        self.assertIn("now - lastGamepadSentAt >= 80", SCRIPT)

    def test_all_tools_are_exposed_without_overlays_or_disclosures(self):
        self.assertNotIn('<details', TEMPLATE)
        self.assertEqual(TEMPLATE.count('class="analysis-card"'), 1)
        self.assertIn('class="mission-tools"', TEMPLATE)
        self.assertIn('id="health-summary"', TEMPLATE)
        self.assertNotIn('class="csi-sensor"', TEMPLATE)
        self.assertIn('class="actuator-card ramp-card"', TEMPLATE)
        self.assertNotIn("disclosureStorageKey", SCRIPT)
        self.assertIn("healthSummary.value", SCRIPT)
        self.assertIn("event.target.closest?.('input, select, button, summary, a')", SCRIPT)

    def test_keyboard_context_is_fixed_to_3tsahur(self):
        self.assertNotIn('activeRobotTab', SCRIPT)
        self.assertIn("toggleVision('3tsahur')", SCRIPT)
        self.assertIn("toggleLandmarks('3tsahur')", SCRIPT)

    def test_3tsahur_has_only_two_position_ramp_controls(self):
        self.assertIn('id="ramp-toggle"', TEMPLATE)
        self.assertIn('id="ramp-readout"', TEMPLATE)
        self.assertIn("key === 'r'", SCRIPT)
        self.assertIn("/api/actuators/ramp", SCRIPT)
        self.assertIn('state: "closed"', SCRIPT)
        self.assertIn('state === "open"', SCRIPT)
        self.assertIn("Servo GPIO unavailable", SCRIPT)
        self.assertIn(".actuator-card", STYLES)
        self.assertIn("grid-template-rows: auto minmax(0, 1fr) minmax(0, 1fr) auto;", STYLES)

    def test_q_and_e_are_pure_four_wheel_rotations_at_75_percent(self):
        self.assertIn("const rotate = Number(bigPressed.has('q')) - Number(bigPressed.has('e'))", SCRIPT)
        self.assertIn("if (rotate) return {forward: 0, strafe: 0, rotate, speed: 0.75};", SCRIPT)
        self.assertIn("Q/E four-wheel rotate at 75%", TEMPLATE)

    def test_yolo_state_has_only_the_hub_source(self):
        self.assertIn("const visionEnabled = {'3tsahur': false};", SCRIPT)
        self.assertNotIn("'larp-a'", SCRIPT)
        self.assertNotIn("'larp-b'", SCRIPT)

    def test_only_mecanum_drive_heartbeat_remains(self):
        self.assertIn("if (bigPressed.size) sendBig(true)", SCRIPT)
        self.assertNotIn("scoutPressed", SCRIPT)
        self.assertIn("}, 80);", SCRIPT)
        self.assertIn("controller.abort(), 140", SCRIPT)

    def test_video_and_controls_use_separate_grid_columns(self):
        self.assertIn('grid-template-columns: minmax(0, 1.08fr) minmax(520px, .92fr);', STYLES)
        self.assertIn('grid-template-rows: minmax(610px, 1fr);', STYLES)
        self.assertIn('#panel-3tsahur .video-stage { grid-area: 1 / 1 / 2 / 2; }', STYLES)
        self.assertIn('#panel-3tsahur .control-stage { grid-area: 1 / 2 / 2 / 3; }', STYLES)
        self.assertNotIn('.drive-card { position: absolute', STYLES)
        self.assertNotIn('.scout-controls { position: absolute', STYLES)
        self.assertNotIn('.mission-tools { position: fixed', STYLES)

    def test_mission_systems_use_the_freed_screen_space(self):
        self.assertIn('.mission-tools { gap: 14px; min-height: 220px; padding: 20px; }', STYLES)
        self.assertIn('.mission-header h2 { font-size: 28px; }', STYLES)
        self.assertIn('.mission-tools ol { max-height: 145px; }', STYLES)

    def test_visual_refresh_remains_static_and_lightweight(self):
        self.assertIn('class="note-live"', TEMPLATE)
        self.assertIn('.dashboard-header::after', STYLES)
        self.assertNotIn('backdrop-filter:', STYLES)
        self.assertNotIn('filter: saturate(', STYLES)


if __name__ == "__main__":
    unittest.main()
