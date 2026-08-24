"""Hardware-independent checks for USB-camera discovery and stream status."""

import time
import unittest
from unittest.mock import patch

from camera_stream import CameraStream


class CameraStreamTests(unittest.TestCase):
    def test_auto_discovery_prefers_persistent_path_and_deduplicates_nodes(self):
        camera = CameraStream()
        persistent = "/dev/v4l/by-id/usb-Acme_Camera-video-index0"
        with patch(
            "camera_stream.glob.glob",
            side_effect=[[persistent], ["/dev/video2", "/dev/video0"]],
        ), patch(
            "camera_stream.os.path.realpath",
            side_effect=lambda path: "/dev/video0" if path == persistent else path,
        ):
            self.assertEqual(camera._candidate_devices(), [persistent, "/dev/video2"])

    def test_explicit_numeric_and_path_devices_are_supported(self):
        self.assertEqual(CameraStream(device="2")._candidate_devices(), [2])
        self.assertEqual(
            CameraStream(device="/dev/video8")._candidate_devices(), ["/dev/video8"]
        )

    def test_persistent_camera_name_is_readable_and_vendor_neutral(self):
        self.assertEqual(
            CameraStream._device_name(
                "/dev/v4l/by-id/usb-Generic_HD_Webcam_123-video-index0"
            ),
            "Generic HD Webcam 123",
        )

    def test_status_reports_a_recent_frame_as_available(self):
        camera = CameraStream(width=320, height=240, fps=8)
        camera._frame = b"jpeg"
        camera._frame_time = time.monotonic()
        camera._camera_name = "Test Camera"
        status = camera.public_status()
        self.assertTrue(status["available"])
        self.assertEqual(status["name"], "Test Camera")
        self.assertEqual((status["width"], status["height"], status["fps"]), (320, 240, 8))

    def test_mjpeg_frames_include_boundary_and_content_length(self):
        camera = CameraStream()
        camera._running = True
        camera._frame = b"jpeg-data"
        frame = next(camera.frames())
        self.assertIn(b"--frame\r\n", frame)
        self.assertIn(b"Content-Type: image/jpeg", frame)
        self.assertIn(b"Content-Length: 9", frame)
        self.assertTrue(frame.endswith(b"jpeg-data\r\n"))


class CameraWebLayoutTests(unittest.TestCase):
    def test_camera_panel_is_below_control_helper(self):
        from pathlib import Path

        project = Path(__file__).resolve().parents[1]
        html = (project / "web" / "index.html").read_text(encoding="utf-8")
        self.assertGreater(html.index('class="camera-card"'), html.index("Keyboard, touch"))
        self.assertIn('src="/camera.mjpg"', html)


if __name__ == "__main__":
    unittest.main()
