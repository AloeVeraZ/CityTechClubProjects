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
    def test_installed_model_auto_enables_detection_at_startup(self):
        with TemporaryDirectory() as directory:
            config = Path(directory) / "model.cfg"
            weights = Path(directory) / "model.weights"
            config.write_text("model", encoding="utf-8")
            weights.write_bytes(b"weights")
            environment = {
                "VISION_MODEL_CONFIG": str(config),
                "VISION_MODEL_WEIGHTS": str(weights),
                "VISION_AUTO_ENABLE": "1",
            }
            with patch.dict("os.environ", environment, clear=True), patch.object(
                VisionManager, "_ensure_thread_locked"
            ) as ensure_worker:
                manager = VisionManager({"camera": lambda: _Frame()})

        self.assertTrue(manager.snapshot("camera")["enabled"])
        ensure_worker.assert_called_once()

    def test_missing_model_stays_disabled_at_startup(self):
        with patch.dict("os.environ", {"VISION_AUTO_ENABLE": "1"}, clear=True):
            manager = VisionManager({"camera": lambda: _Frame()})

        self.assertFalse(manager.snapshot("camera")["enabled"])
        self.assertIsNone(manager._thread)

    def test_object_detection_defaults_to_low_threshold_without_motion_gating(self):
        with patch.dict("os.environ", {}, clear=True):
            manager = VisionManager({"camera": lambda: _Frame()})

        self.assertEqual(manager.confidence, 0.20)
        self.assertFalse(manager.object_motion_gate)
        self.assertIn("person", manager.detected_classes)
        self.assertIn("cell phone", manager.detected_classes)

    def test_stationary_person_frames_are_inferred_continuously(self):
        manager = VisionManager({"camera": lambda: _Frame()})
        manager._last_inference_at["camera"] = time.monotonic()
        with patch.dict("sys.modules", {"cv2": object()}), patch.object(
            manager, "_motion_score", return_value=0.0
        ), patch.object(manager, "_detect_objects", return_value=[]) as detect:
            manager._run_one("camera", objects_enabled=True, landmarks_enabled=False)

        detect.assert_called_once()
        self.assertFalse(manager.snapshot("camera")["inference_skipped"])

    def test_disabling_never_starts_the_optional_worker(self):
        manager = VisionManager({"camera": lambda: _Frame()})
        state = manager.set_enabled("camera", False)

        self.assertIsNone(manager._thread)
        self.assertFalse(state["enabled"])

    def test_enabling_one_yolo_source_disables_the_previous_source(self):
        manager = VisionManager({"one": lambda: _Frame(), "two": lambda: _Frame()})
        with patch.object(manager, "_ensure_thread_locked"):
            manager.set_enabled("one", True)
            manager.set_enabled("two", True)

        self.assertFalse(manager.snapshot("one")["enabled"])
        self.assertTrue(manager.snapshot("two")["enabled"])

    def test_motion_gate_skips_yolo_until_periodic_refresh(self):
        manager = VisionManager({"camera": lambda: _Frame()})
        manager.object_motion_gate = True
        manager._last_inference_at["camera"] = time.monotonic()
        with patch.dict("sys.modules", {"cv2": object()}), patch.object(
            manager, "_motion_score", return_value=0.001
        ), patch.object(manager, "_detect_objects") as detect:
            manager._run_one("camera", objects_enabled=True, landmarks_enabled=False)

        state = manager.snapshot("camera")
        self.assertTrue(state["available"])
        self.assertTrue(state["inference_skipped"])
        detect.assert_not_called()

    def test_motion_gate_forces_periodic_static_scene_inference(self):
        manager = VisionManager({"camera": lambda: _Frame()})
        manager.object_motion_gate = True
        manager._last_inference_at["camera"] = 0
        with patch.dict("sys.modules", {"cv2": object()}), patch.object(
            manager, "_motion_score", return_value=0.001
        ), patch.object(manager, "_detect_objects", return_value=[]) as detect:
            manager._run_one("camera", objects_enabled=True, landmarks_enabled=False)

        detect.assert_called_once()
        self.assertFalse(manager.snapshot("camera")["inference_skipped"])

    def test_static_scene_also_gates_lightweight_landmark_checks(self):
        manager = VisionManager({"camera": lambda: _Frame()})
        manager._last_landmark_at["camera"] = time.monotonic()
        with patch.dict("sys.modules", {"cv2": object()}), patch.object(
            manager, "_motion_score", return_value=0.001
        ), patch.object(manager, "_detect_landmarks") as detect:
            manager._run_one("camera", objects_enabled=False, landmarks_enabled=True)

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


class VisionInstallerTests(unittest.TestCase):
    def test_one_command_installer_selects_offline_yolov4_tiny_coco(self):
        root = Path(__file__).parents[1]
        bootstrap = (root / "installer" / "curl-install-vision.sh").read_text(encoding="utf-8")
        installer = (root / "installer" / "install-vision.sh").read_text(encoding="utf-8")

        self.assertIn("installer/install-vision.sh", bootstrap)
        self.assertIn("yolov4-tiny.weights", installer)
        self.assertIn("readNetFromDarknet", installer)
        self.assertIn("sha256sum --check --status", installer)
        self.assertIn("person-detection check passed", installer)
        self.assertIn('set_config_key VISION_AUTO_ENABLE "1"', installer)
        self.assertNotIn("ultralytics", installer.lower())

    def test_launcher_bounds_native_runtime_threads_without_second_venv(self):
        root = Path(__file__).parents[1]
        launcher = (root / "installer" / "start-dashboard.sh").read_text(encoding="utf-8")

        self.assertIn('VISION_CPU_THREADS="${VISION_CPU_THREADS:-2}"', launcher)
        self.assertIn('export OMP_NUM_THREADS="$VISION_CPU_THREADS"', launcher)
        self.assertIn('exec "$BASE_PYTHON" -m robot_server.app', launcher)
        self.assertNotIn("VISION_VENV", launcher)

    def test_dashboard_service_has_one_gigabyte_hard_limit(self):
        root = Path(__file__).parents[1]
        service = (root / "installer" / "systemd" / "stem-robot-dashboard.service").read_text(encoding="utf-8")
        self.assertIn("MemoryMax=1G", service)


if __name__ == "__main__":
    unittest.main()
