import pathlib
import unittest


FIRMWARE = (
    pathlib.Path(__file__).parents[1]
    / "firmware"
    / "echo-scout"
    / "ECHO_Robot_Controller.ino"
)
INSTALLER = pathlib.Path(__file__).parents[1] / "installer" / "install.sh"


class EchoScoutFirmwareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = FIRMWARE.read_text(encoding="utf-8")
        cls.installer = INSTALLER.read_text(encoding="utf-8")

    def test_attachment_was_consolidated_to_one_sketch(self):
        self.assertEqual(self.source.count("void setup()"), 1)
        self.assertEqual(self.source.count("void loop()"), 1)

    def test_final_hotspot_credentials_match_installer(self):
        self.assertIn('WIFI_SSID[] = "EchoSwarm"', self.source)
        self.assertIn('WIFI_PASSWORD[] = "roboswarm1"', self.source)
        self.assertIn("HOTSPOT_SSID=EchoSwarm", self.installer)
        self.assertIn("HOTSPOT_PASSWORD=roboswarm1", self.installer)

    def test_echo_differential_drive_api_and_safety_are_present(self):
        self.assertIn("TankDriveTrain drivetrain", self.source)
        self.assertIn("LEFT_MOTOR_ID = 1", self.source)
        self.assertIn("RIGHT_MOTOR_ID = 6", self.source)
        self.assertIn("COMMAND_TIMEOUT_MS = 500", self.source)
        self.assertIn("motors.stopAll()", self.source)

    def test_pi_integration_endpoints_and_station_mode_are_present(self):
        self.assertIn("WiFi.mode(WIFI_STA)", self.source)
        self.assertIn("PI_HEARTBEAT_UDP_PORT = 5006", self.source)
        self.assertIn("sendHeartbeat()", self.source)
        for endpoint in ("/drive", "/stop", "/status", "/motion"):
            self.assertIn(f'"{endpoint}"', self.source)
        self.assertNotIn("192, 168, 4", self.source)

    def test_installer_schedules_reboot_outside_pipe_process(self):
        self.assertIn("systemd-run", self.installer)
        self.assertIn("--on-active=10s", self.installer)
        self.assertIn("systemctl)\" reboot", self.installer)
        self.assertNotIn("STEM_NO_REBOOT", self.installer)

    def test_installer_uses_resizable_window_and_simple_dashboard_address(self):
        self.assertIn('nginx-light', self.installer)
        self.assertIn('listen 80 default_server', self.installer)
        self.assertIn('CAMERA_FPS=10', self.installer)
        self.assertIn('DRIVE_WATCHDOG_SECONDS=0.20', self.installer)
        self.assertNotIn('fullscreen robot dashboard', self.installer)


if __name__ == "__main__":
    unittest.main()
