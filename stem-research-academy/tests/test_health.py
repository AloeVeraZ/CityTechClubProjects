import unittest
from pathlib import Path
from unittest.mock import patch

from robot_server.health import SystemHealthMonitor


class HealthTests(unittest.TestCase):
    def test_health_snapshot_is_cached_and_camera_age_is_cheap(self):
        monitor = SystemHealthMonitor(lambda: 0.25, Path.cwd())
        with patch.object(monitor, "_ensure_started"):
            state = monitor.snapshot()
        self.assertEqual(state["status"], "starting")
        self.assertEqual(state["camera_frame_age_seconds"], 0.25)


if __name__ == "__main__":
    unittest.main()
