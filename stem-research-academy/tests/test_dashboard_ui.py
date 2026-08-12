import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (PROJECT_ROOT / "robot_server" / "templates" / "index.html").read_text(encoding="utf-8")
STYLES = (PROJECT_ROOT / "robot_server" / "static" / "dashboard.css").read_text(encoding="utf-8")
SCRIPT = (PROJECT_ROOT / "robot_server" / "static" / "dashboard.js").read_text(encoding="utf-8")


class DashboardTabTests(unittest.TestCase):
    def test_all_three_robot_workspaces_are_visible_on_one_page(self):
        for robot in ("3tsahur", "larp-a", "larp-b"):
            self.assertIn(f'data-camera-select="{robot}"', TEMPLATE)
            self.assertIn(f'data-robot-panel="{robot}"', TEMPLATE)
        self.assertNotIn('role="tab"', TEMPLATE)
        self.assertNotIn(' hidden', TEMPLATE)

    def test_each_tab_has_its_own_video_and_controls(self):
        self.assertIn('alt="Live automatic Logitech USB camera feed from 3TSahur"', TEMPLATE)
        self.assertIn('alt="Live Inland ESP32-CAM feed from LARP Scout A"', TEMPLATE)
        self.assertIn('alt="Live Inland ESP32-CAM feed from LARP Scout B"', TEMPLATE)
        self.assertIn('aria-label="3TSahur drive controls"', TEMPLATE)
        self.assertIn('aria-label="LARP Scout A drive controls"', TEMPLATE)
        self.assertIn('aria-label="LARP Scout B drive controls"', TEMPLATE)

    def test_camera_wall_supports_one_two_or_three_selected_streams(self):
        self.assertEqual(TEMPLATE.count("data-stream-for="), 3)
        self.assertEqual(TEMPLATE.count("data-stream-src="), 3)
        self.assertIn("function activateSelectedCameras", SCRIPT)
        self.assertIn("const selectedCameras = new Set(['3tsahur'])", SCRIPT)
        self.assertIn("const rowSpan = 6 / selected.length", SCRIPT)
        self.assertIn("if (!selectedCameras.size) selectedCameras.add('3tsahur')", SCRIPT)
        self.assertIn("feed.removeAttribute('src')", SCRIPT)
        self.assertNotIn("IntersectionObserver", SCRIPT)

    def test_larp_tabs_show_the_csi_presence_indicator(self):
        self.assertEqual(TEMPLATE.count("CSI presence sensor"), 2)
        self.assertIn('id="scout-a-csi"', TEMPLATE)
        self.assertIn('id="scout-b-csi"', TEMPLATE)
        self.assertIn("function renderCsiSensor", SCRIPT)
        self.assertIn("Possible presence - check video", SCRIPT)
        self.assertIn("scoutStatusInFlight", SCRIPT)
        self.assertIn(".csi-sensor.detected", STYLES)

    def test_vision_has_a_per_camera_toggle_and_overlay(self):
        for source in ("3tsahur", "larp-a", "larp-b"):
            self.assertIn(f'data-vision-toggle="{source}"', TEMPLATE)
            self.assertIn(f'data-vision-overlay="{source}"', TEMPLATE)
        self.assertIn("key === 'c'", SCRIPT)
        self.assertIn("toggleVision(activeRobotTab)", SCRIPT)
        self.assertIn("/api/vision/${source}", SCRIPT)
        self.assertIn("Vision unavailable - robot controls remain active", SCRIPT)
        self.assertIn(".vision-overlay", STYLES)

    def test_recon_features_are_optional_and_control_aware(self):
        self.assertEqual(TEMPLATE.count('data-landmark-toggle="'), 3)
        self.assertEqual(TEMPLATE.count('data-evidence="'), 3)
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
        self.assertEqual(TEMPLATE.count('data-snapshot="'), 3)
        self.assertEqual(TEMPLATE.count('data-calibrate="'), 2)
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
        self.assertEqual(TEMPLATE.count('class="analysis-card"'), 3)
        self.assertIn('class="mission-tools"', TEMPLATE)
        self.assertIn('id="health-summary"', TEMPLATE)
        self.assertEqual(TEMPLATE.count('class="csi-sensor"'), 2)
        self.assertIn('class="actuator-card ramp-card"', TEMPLATE)
        self.assertNotIn("disclosureStorageKey", SCRIPT)
        self.assertIn("healthSummary.value", SCRIPT)
        self.assertIn("event.target.closest?.('input, select, button, summary, a')", SCRIPT)

    def test_control_interaction_selects_keyboard_context_without_hiding_controls(self):
        self.assertIn('function setActiveRobotContext', SCRIPT)
        self.assertIn("panel.addEventListener('pointerdown', selectPanel)", SCRIPT)
        self.assertIn("panel.addEventListener('focusin', selectPanel)", SCRIPT)
        self.assertNotIn("panel.hidden", SCRIPT)
        self.assertNotIn("changingTabs", SCRIPT)

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

    def test_auxiliary_scout_status_traffic_yields_to_drive_traffic(self):
        self.assertIn("if (scoutPressed[id].size) return;", SCRIPT)
        self.assertIn("}, 5000);", SCRIPT)
        self.assertIn("}, 1200);", SCRIPT)
        self.assertIn("}, 80);", SCRIPT)
        self.assertIn("controller.abort(), 140", SCRIPT)

    def test_video_and_controls_use_separate_grid_columns(self):
        self.assertIn('grid-template-columns: minmax(0, 1.08fr) minmax(520px, .92fr);', STYLES)
        self.assertIn('grid-template-rows: repeat(6, minmax(0, 1fr));', STYLES)
        self.assertIn('#panel-3tsahur .video-stage { grid-area: 1 / 1 / span 6 / 2; }', STYLES)
        self.assertIn('#panel-3tsahur .control-stage { grid-area: 1 / 2 / span 2 / 3; }', STYLES)
        self.assertNotIn('.drive-card { position: absolute', STYLES)
        self.assertNotIn('.scout-controls { position: absolute', STYLES)
        self.assertNotIn('.mission-tools { position: fixed', STYLES)

    def test_visual_refresh_remains_static_and_lightweight(self):
        self.assertIn('class="note-live"', TEMPLATE)
        self.assertIn('.dashboard-header::after', STYLES)
        self.assertNotIn('backdrop-filter:', STYLES)
        self.assertNotIn('filter: saturate(', STYLES)


if __name__ == "__main__":
    unittest.main()
