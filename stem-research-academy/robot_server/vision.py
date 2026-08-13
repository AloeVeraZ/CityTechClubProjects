"""Offline, failure-isolated object recognition for the dashboard.

The detector uses OpenCV's native DNN engine with a small YOLOv4-tiny model.
It has no cloud dependency and shares the OpenCV installation already used by
the USB camera. One daemon worker keeps inference out of motor request paths.
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Callable


COCO_CLASSES = (
    "person",
    "bicycle",
    "car",
    "motorbike",
    "aeroplane",
    "bus",
    "train",
    "truck",
    "boat",
    "traffic light",
    "fire hydrant",
    "stop sign",
    "parking meter",
    "bench",
    "bird",
    "cat",
    "dog",
    "horse",
    "sheep",
    "cow",
    "elephant",
    "bear",
    "zebra",
    "giraffe",
    "backpack",
    "umbrella",
    "handbag",
    "tie",
    "suitcase",
    "frisbee",
    "skis",
    "snowboard",
    "sports ball",
    "kite",
    "baseball bat",
    "baseball glove",
    "skateboard",
    "surfboard",
    "tennis racket",
    "bottle",
    "wine glass",
    "cup",
    "fork",
    "knife",
    "spoon",
    "bowl",
    "banana",
    "apple",
    "sandwich",
    "orange",
    "broccoli",
    "carrot",
    "hot dog",
    "pizza",
    "donut",
    "cake",
    "chair",
    "sofa",
    "pottedplant",
    "bed",
    "diningtable",
    "toilet",
    "tvmonitor",
    "laptop",
    "mouse",
    "remote",
    "keyboard",
    "cell phone",
    "microwave",
    "oven",
    "toaster",
    "sink",
    "refrigerator",
    "book",
    "clock",
    "vase",
    "scissors",
    "teddy bear",
    "hair drier",
    "toothbrush",
)


def _environment_flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    return default if value is None else value.strip().lower() not in {"0", "false", "no", "off"}


class VisionManager:
    """Run optional reconnaissance analysis without making control depend on it."""

    def __init__(
        self,
        sources: dict[str, Callable[[], object | None]],
        should_pause: Callable[[], bool] | None = None,
    ) -> None:
        self._sources = sources
        self._should_pause = should_pause or (lambda: False)
        self.interval = max(0.25, float(os.environ.get("VISION_INTERVAL_SECONDS", "0.50")))
        self.confidence = min(0.95, max(0.05, float(os.environ.get("VISION_CONFIDENCE", "0.20"))))
        bundled_models = Path(__file__).resolve().parents[1] / "vision_models"
        configured_model = os.environ.get("VISION_MODEL_CONFIG", "").strip()
        configured_weights = os.environ.get("VISION_MODEL_WEIGHTS", "").strip()
        self.model_config = os.path.expanduser(configured_model) if configured_model else str(
            bundled_models / "yolov4-tiny.cfg"
        )
        self.model_weights = os.path.expanduser(configured_weights) if configured_weights else str(
            bundled_models / "yolov4-tiny.weights"
        )
        self.auto_enable = _environment_flag("VISION_AUTO_ENABLE", True)
        self.image_size = max(224, min(416, int(os.environ.get("VISION_IMAGE_SIZE", "320"))))
        self.cpu_threads = max(1, min(4, int(os.environ.get("VISION_CPU_THREADS", "2"))))
        self.max_detections = max(1, min(30, int(os.environ.get("VISION_MAX_DETECTIONS", "15"))))
        selected_classes = {
            value.strip().lower()
            for value in os.environ.get("VISION_CLASSES", "").split(",")
            if value.strip()
        }
        self.detected_classes = selected_classes or set(COCO_CLASSES)
        self.motion_gate = _environment_flag("VISION_MOTION_GATE", True)
        self.object_motion_gate = _environment_flag("VISION_OBJECT_MOTION_GATE", False)
        self.motion_threshold = max(0.001, float(os.environ.get("VISION_MOTION_THRESHOLD", "0.02")))
        self.force_inference_seconds = max(
            1.0, float(os.environ.get("VISION_FORCE_INFERENCE_SECONDS", "5"))
        )
        self._enabled = {source: False for source in sources}
        self._landmarks_enabled = {source: False for source in sources}
        self._states = {source: self._new_state() for source in sources}
        self._previous_gray: dict[str, object] = {}
        self._last_inference_at = {source: 0.0 for source in sources}
        self._last_landmark_at = {source: 0.0 for source in sources}
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._model = None
        self._model_error: str | None = None
        if self.auto_enable and self._model_files_installed():
            auto_source = next(iter(self._sources), None)
            if auto_source is not None:
                self.set_enabled(auto_source, True)

    def _model_files_installed(self) -> bool:
        return all(
            path and os.path.isfile(path) and os.path.getsize(path) > 0
            for path in (self.model_config, self.model_weights)
        )

    def _new_state(self) -> dict:
        return {
            "enabled": False,
            "available": None,
            "error": None,
            "detections": [],
            "landmarks_enabled": False,
            "landmarks_available": None,
            "landmark_error": None,
            "landmarks": [],
            "landmark_skipped": False,
            "backend": "opencv-yolov4-tiny",
            "model_name": "YOLOv4-tiny (COCO 80)",
            "motion_gate": self.object_motion_gate,
            "confidence_threshold": self.confidence,
            "motion_score": None,
            "inference_skipped": False,
            "inference_ms": None,
            "updated_at_ms": None,
            "frame_width": 0,
            "frame_height": 0,
        }

    def snapshot(self, source: str) -> dict:
        with self._lock:
            if source not in self._states:
                raise KeyError(source)
            state = self._states[source]
            return dict(state, detections=list(state["detections"]), landmarks=list(state["landmarks"]))

    def _ensure_thread_locked(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="optional-vision", daemon=True)
            self._thread.start()

    def set_enabled(self, source: str, enabled: bool) -> dict:
        with self._lock:
            if source not in self._states:
                raise KeyError(source)
            if enabled:
                # The Pi control hub runs at most one detector source. Enabling a
                # new camera disables the previous one before the worker wakes.
                for other_source in self._sources:
                    if other_source == source:
                        continue
                    self._enabled[other_source] = False
                    self._states[other_source].update(
                        enabled=False, available=None, error=None, detections=[],
                        motion_score=None, inference_skipped=False, inference_ms=None,
                    )
                    self._previous_gray.pop(other_source, None)
            self._enabled[source] = enabled
            state = self._states[source]
            state["enabled"] = enabled
            if not enabled:
                state.update(
                    available=None, error=None, detections=[], motion_score=None,
                    inference_skipped=False, inference_ms=None,
                )
                self._previous_gray.pop(source, None)
            if enabled:
                self._ensure_thread_locked()
        if self._thread is not None:
            self._wake.set()
        return self.snapshot(source)

    def set_landmarks_enabled(self, source: str, enabled: bool) -> dict:
        with self._lock:
            if source not in self._states:
                raise KeyError(source)
            self._landmarks_enabled[source] = enabled
            state = self._states[source]
            state["landmarks_enabled"] = enabled
            if not enabled:
                state.update(
                    landmarks_available=None, landmark_error=None, landmarks=[], landmark_skipped=False
                )
            self._ensure_thread_locked()
        self._wake.set()
        return self.snapshot(source)

    def _load_model(self, cv2):
        if self._model is not None:
            return self._model
        if self._model_error:
            raise RuntimeError(self._model_error)
        try:
            if not self.model_config or not os.path.isfile(self.model_config):
                raise RuntimeError(f"model definition is missing: {self.model_config or 'VISION_MODEL_CONFIG is unset'}")
            if not self.model_weights or not os.path.isfile(self.model_weights):
                raise RuntimeError(f"model weights are missing: {self.model_weights or 'VISION_MODEL_WEIGHTS is unset'}")
            cv2.setNumThreads(self.cpu_threads)
            network = cv2.dnn.readNetFromDarknet(self.model_config, self.model_weights)
            network.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            network.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            self._model = cv2.dnn_DetectionModel(network)
            self._model.setInputParams(
                size=(self.image_size, self.image_size), scale=1 / 255.0, swapRB=True
            )
            return self._model
        except Exception as error:
            self._model_error = f"Offline object detector unavailable: {error}"
            raise RuntimeError(self._model_error) from error

    @staticmethod
    def _decode_frame(frame, cv2):
        if isinstance(frame, bytes):
            import numpy  # type: ignore

            frame = cv2.imdecode(numpy.frombuffer(frame, dtype="uint8"), cv2.IMREAD_COLOR)
        if frame is None:
            raise RuntimeError("Camera frame could not be decoded")
        return frame

    def _motion_score(self, source: str, frame, cv2) -> float:
        gray = cv2.cvtColor(cv2.resize(frame, (160, 120)), cv2.COLOR_BGR2GRAY)
        previous = self._previous_gray.get(source)
        self._previous_gray[source] = gray
        if previous is None:
            return 1.0
        difference = cv2.absdiff(previous, gray)
        changed = cv2.countNonZero(cv2.threshold(difference, 18, 255, cv2.THRESH_BINARY)[1])
        return changed / float(gray.shape[0] * gray.shape[1])

    def _detect_objects(self, frame, cv2) -> list[dict]:
        model = self._load_model(cv2)
        class_ids, confidences, boxes = model.detect(
            frame, confThreshold=self.confidence, nmsThreshold=0.40
        )
        height, width = frame.shape[:2]
        detections = []
        for raw_class_id, raw_confidence, raw_box in zip(class_ids, confidences, boxes):
            confidence = float(raw_confidence)
            class_id = int(raw_class_id)
            if confidence < self.confidence or not (0 <= class_id < len(COCO_CLASSES)):
                continue
            label = COCO_CLASSES[class_id]
            if label not in self.detected_classes:
                continue
            raw_x, raw_y, raw_width, raw_height = (float(value) for value in raw_box)
            x1 = max(0.0, min(float(width), raw_x))
            y1 = max(0.0, min(float(height), raw_y))
            x2 = max(0.0, min(float(width), raw_x + raw_width))
            y2 = max(0.0, min(float(height), raw_y + raw_height))
            if x2 - x1 < 3 or y2 - y1 < 3:
                continue
            detections.append(
                {
                    "label": label,
                    "confidence": round(confidence, 3),
                    "x1": round(x1, 1),
                    "y1": round(y1, 1),
                    "x2": round(x2, 1),
                    "y2": round(y2, 1),
                }
            )
            if len(detections) >= self.max_detections:
                break
        return sorted(detections, key=lambda item: item["confidence"], reverse=True)

    @staticmethod
    def _detect_landmarks(frame, cv2) -> list[dict]:
        if not hasattr(cv2, "aruco"):
            raise RuntimeError("OpenCV ArUco support is not installed")
        dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        if hasattr(cv2.aruco, "ArucoDetector"):
            detector = cv2.aruco.ArucoDetector(dictionary, cv2.aruco.DetectorParameters())
            corners, identifiers, _ = detector.detectMarkers(frame)
        else:
            corners, identifiers, _ = cv2.aruco.detectMarkers(frame, dictionary)
        if identifiers is None:
            return []
        landmarks = []
        for marker_id, marker_corners in zip(identifiers.flatten().tolist(), corners):
            points = marker_corners.reshape(4, 2)
            xs = [float(point[0]) for point in points]
            ys = [float(point[1]) for point in points]
            landmarks.append(
                {
                    "id": int(marker_id),
                    "x1": round(min(xs), 1),
                    "y1": round(min(ys), 1),
                    "x2": round(max(xs), 1),
                    "y2": round(max(ys), 1),
                    "center_x": round(sum(xs) / 4, 1),
                    "center_y": round(sum(ys) / 4, 1),
                }
            )
        return landmarks

    def _run_one(self, source: str, objects_enabled: bool, landmarks_enabled: bool) -> None:
        now_ms = round(time.time() * 1000)
        try:
            import cv2  # type: ignore

            frame = self._sources[source]()
            if frame is None:
                raise RuntimeError("No camera frame available")
            frame = self._decode_frame(frame, cv2)
            height, width = frame.shape[:2]
        except Exception as error:
            with self._lock:
                update = {"updated_at_ms": now_ms}
                if objects_enabled:
                    update.update(available=False, error=str(error), detections=[])
                if landmarks_enabled:
                    update.update(landmarks_available=False, landmark_error=str(error), landmarks=[])
                self._states[source].update(update)
            return

        update = {"updated_at_ms": now_ms, "frame_width": width, "frame_height": height}
        score = None
        if objects_enabled:
            started_at = time.monotonic()
            try:
                score = self._motion_score(source, frame, cv2) if self.object_motion_gate else 1.0
                force = started_at - self._last_inference_at[source] >= self.force_inference_seconds
                skip = self.object_motion_gate and score < self.motion_threshold and not force
                update.update(
                    motion_gate=self.object_motion_gate,
                    confidence_threshold=self.confidence,
                    motion_score=round(score, 4),
                    inference_skipped=skip,
                )
                if not skip:
                    update["detections"] = self._detect_objects(frame, cv2)
                    self._last_inference_at[source] = time.monotonic()
                update.update(
                    available=True,
                    error=None,
                    inference_ms=round((time.monotonic() - started_at) * 1000, 1),
                )
            except Exception as error:
                update.update(
                    available=False, error=str(error), detections=[], inference_skipped=False,
                    inference_ms=round((time.monotonic() - started_at) * 1000, 1),
                )

        if landmarks_enabled:
            try:
                started_at = time.monotonic()
                if score is None:
                    score = self._motion_score(source, frame, cv2) if self.motion_gate else 1.0
                    update["motion_score"] = round(score, 4)
                force = started_at - self._last_landmark_at[source] >= self.force_inference_seconds
                skip = self.motion_gate and score < self.motion_threshold and not force
                landmarks = None if skip else self._detect_landmarks(frame, cv2)
                if not skip:
                    self._last_landmark_at[source] = time.monotonic()
                update.update(
                    landmarks_available=True,
                    landmark_error=None,
                    landmark_skipped=skip,
                )
                if landmarks is not None:
                    update["landmarks"] = landmarks
            except Exception as error:
                update.update(
                    landmarks_available=False, landmark_error=str(error), landmarks=[],
                    landmark_skipped=False,
                )

        with self._lock:
            self._states[source].update(update)

    def _run(self) -> None:
        while not self._stop.is_set():
            with self._lock:
                active = [
                    (source, self._enabled[source], self._landmarks_enabled[source])
                    for source in self._sources
                    if self._enabled[source] or self._landmarks_enabled[source]
                ]
            if not active:
                self._wake.wait(timeout=1)
                self._wake.clear()
                continue
            if self._should_pause():
                self._wake.wait(timeout=0.1)
                self._wake.clear()
                continue
            for source, objects_enabled, landmarks_enabled in active:
                if self._stop.is_set() or self._should_pause():
                    break
                self._run_one(source, objects_enabled, landmarks_enabled)
            self._wake.wait(timeout=self.interval)
            self._wake.clear()

    def close(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread:
            self._thread.join(timeout=1)
