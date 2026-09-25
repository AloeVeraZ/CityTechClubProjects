import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "robot_server"
STATION = (ROOT / "templates" / "driver_station.html").read_text(encoding="utf-8")
STATION_JS = (ROOT / "static" / "driver_station.js").read_text(encoding="utf-8")
DEBUG = (ROOT / "templates" / "debug.html").read_text(encoding="utf-8")
DEBUG_JS = (ROOT / "static" / "debug.js").read_text(encoding="utf-8")


class DriverStationTests(unittest.TestCase):
    def test_documented_keys_are_bound(self):
        for key in ("'w', 'a', 's', 'd', 'q', 'e'", "key === 'r'", "key === ' '", "key === 'Escape'"):
            self.assertIn(key, STATION_JS)

    def test_losing_focus_or_connection_disables(self):
        self.assertIn("addEventListener('blur', () => setEnabled(false))", STATION_JS)
        self.assertIn("document.hidden) setEnabled(false)", STATION_JS)
        self.assertIn("setInterval(sendDrive, 80)", STATION_JS)
        self.assertIn('id="killButton"', STATION)

    def test_camera_ramp_imu_and_debug_link(self):
        for marker in ('id="cameraFeed"', 'data-ramp="open"', 'id="headingDial"', 'href="/debug"', 'data-wheel="front_left"'):
            self.assertIn(marker, STATION)

    def test_no_code_upload(self):
        for page in (STATION, STATION_JS, DEBUG, DEBUG_JS):
            self.assertNotIn("deploy", page.lower())


class DebugPageTests(unittest.TestCase):
    def test_port_mapping_and_tests(self):
        self.assertIn('id="portGrid"', DEBUG)
        self.assertIn("function assignWheel", DEBUG_JS)
        self.assertIn("/api/debug/motor", DEBUG_JS)
        self.assertIn("/api/settings", DEBUG_JS)

    def test_servo_imu_and_wiring(self):
        for marker in ('id="channelGrid"', 'id="rampGrid"', 'id="oeToggle"', 'id="zeroHeading"', 'id="wiringTable"'):
            self.assertIn(marker, DEBUG)
        self.assertIn("/api/debug/servo", DEBUG_JS)

    def test_holds_stop_when_released(self):
        self.assertIn("['pointerup', 'pointerleave', 'pointercancel']", DEBUG_JS)
        self.assertIn("addEventListener('blur', stopHold)", DEBUG_JS)


if __name__ == "__main__":
    unittest.main()
