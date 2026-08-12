import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from robot_server.evidence import EvidenceStore
from robot_server.health import SystemHealthMonitor
from robot_server.vision import VisionManager


class _Frame:
    shape = (480, 640, 3)


class VisionEfficiencyTests(unittest.TestCase):
    def test_motion_gate_skips_yolo_until_periodic_refresh(self):
        manager = VisionManager({"camera": lambda: _Frame()})
        manager._last_inference_at["camera"] = time.monotonic()
        with patch.dict("sys.modules", {"cv2": object()}), patch.object(
            manager, "_motion_score", return_value=0.001
        ), patch.object(manager, "_detect_people") as detect:
            manager._run_one("camera", people_enabled=True, landmarks_enabled=False)

        state = manager.snapshot("camera")
        self.assertTrue(state["available"])
        self.assertTrue(state["inference_skipped"])
        detect.assert_not_called()

    def test_motion_gate_forces_periodic_static_scene_inference(self):
        manager = VisionManager({"camera": lambda: _Frame()})
        manager._last_inference_at["camera"] = 0
        with patch.dict("sys.modules", {"cv2": object()}), patch.object(
            manager, "_motion_score", return_value=0.001
        ), patch.object(manager, "_detect_people", return_value=[]) as detect:
            manager._run_one("camera", people_enabled=True, landmarks_enabled=False)

        detect.assert_called_once()
        self.assertFalse(manager.snapshot("camera")["inference_skipped"])

    def test_static_scene_also_gates_lightweight_landmark_checks(self):
        manager = VisionManager({"camera": lambda: _Frame()})
        manager._last_landmark_at["camera"] = time.monotonic()
        with patch.dict("sys.modules", {"cv2": object()}), patch.object(
            manager, "_motion_score", return_value=0.001
        ), patch.object(manager, "_detect_landmarks") as detect:
            manager._run_one("camera", people_enabled=False, landmarks_enabled=True)

        state = manager.snapshot("camera")
        self.assertTrue(state["landmarks_available"])
        self.assertTrue(state["landmark_skipped"])
        detect.assert_not_called()


class EvidenceTests(unittest.TestCase):
    def test_evidence_bundle_writes_image_and_metadata_pair(self):
        with TemporaryDirectory() as directory:
            store = EvidenceStore(Path(directory))
            store._write(
                "bundle-1",
                b"\xff\xd8test\xff\xd9",
                {"source": "3tsahur", "at_ms": 1, "note": "test evidence"},
            )
            self.assertTrue((Path(directory) / "bundle-1.jpg").is_file())
            self.assertTrue((Path(directory) / "bundle-1.json").is_file())
            item = store.snapshot()["items"][0]
            self.assertEqual(item["status"], "saved")
            self.assertEqual(item["source"], "3tsahur")
            store.close()


class HealthTests(unittest.TestCase):
    def test_health_snapshot_is_cached_and_camera_age_is_cheap(self):
        monitor = SystemHealthMonitor(lambda: 0.25, Path.cwd())
        with patch.object(monitor, "_ensure_started"):
            state = monitor.snapshot()
        self.assertEqual(state["status"], "starting")
        self.assertEqual(state["camera_frame_age_seconds"], 0.25)


if __name__ == "__main__":
    unittest.main()
