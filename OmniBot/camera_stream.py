"""Shared, reconnecting USB camera stream for OmniBot.

One capture thread owns the camera.  The local pygame display and every web
client consume the same JPEG frames so opening the dashboard never tries to
claim the video device a second time.
"""

from __future__ import annotations

import glob
import os
import threading
import time
from pathlib import Path
from typing import Any, Iterator


class CameraStream:
    """Discover a V4L2 camera, encode MJPEG frames, and reconnect on failure."""

    def __init__(
        self,
        device: str = "auto",
        width: int = 640,
        height: int = 480,
        fps: int = 10,
    ) -> None:
        self.device = str(device or "auto")
        self.width = max(160, int(width))
        self.height = max(120, int(height))
        self.fps = max(1, min(30, int(fps)))
        self._condition = threading.Condition()
        self._frame: bytes | None = None
        self._frame_time = 0.0
        self._running = False
        self._thread: threading.Thread | None = None
        self._capture: Any = None
        self._active_device = ""
        self._camera_name = ""
        self._error = "Looking for a USB camera"
        self._restart_count = 0

    @classmethod
    def from_environment(cls) -> "CameraStream":
        def number(name: str, default: int) -> int:
            try:
                return int(os.environ.get(name, str(default)))
            except ValueError:
                return default

        return cls(
            device=os.environ.get("OMNIBOT_CAMERA_DEVICE", "auto"),
            width=number("OMNIBOT_CAMERA_WIDTH", 640),
            height=number("OMNIBOT_CAMERA_HEIGHT", 480),
            fps=number("OMNIBOT_CAMERA_FPS", 10),
        )

    def _candidate_devices(self) -> list[str | int]:
        if self.device.lower() != "auto":
            return [int(self.device)] if self.device.isdigit() else [self.device]

        candidates: list[str | int] = []
        # Persistent index-0 paths represent the image stream and remain stable
        # when multiple USB cameras are plugged in or their /dev/videoN order changes.
        candidates.extend(sorted(glob.glob("/dev/v4l/by-id/*-video-index0")))
        candidates.extend(
            sorted(
                glob.glob("/dev/video[0-9]*"),
                key=lambda value: int(Path(value).name.removeprefix("video")),
            )
        )

        unique: list[str | int] = []
        real_devices: set[str] = set()
        for candidate in candidates:
            real_device = os.path.realpath(str(candidate))
            if real_device in real_devices:
                continue
            real_devices.add(real_device)
            unique.append(candidate)
        return unique

    @staticmethod
    def _device_name(device: str | int) -> str:
        path = Path(str(device))
        if "/dev/v4l/by-id/" in path.as_posix():
            name = path.name.removesuffix("-video-index0")
            for prefix in ("usb-",):
                name = name.removeprefix(prefix)
            return name.replace("_", " ").strip() or "USB camera"
        node = Path(os.path.realpath(str(device))).name
        try:
            return Path(f"/sys/class/video4linux/{node}/name").read_text(
                encoding="utf-8"
            ).strip()
        except OSError:
            return f"USB camera ({path.name})"

    def start(self) -> "CameraStream":
        with self._condition:
            if self._running:
                return self
            self._running = True
            self._thread = threading.Thread(
                target=self._supervise,
                name="omnibot-camera",
                daemon=True,
            )
            self._thread.start()
        return self

    def _open_capture(self):
        import cv2

        for source in self._candidate_devices():
            capture = cv2.VideoCapture(source, cv2.CAP_V4L2)
            if not capture.isOpened():
                capture.release()
                continue
            capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            capture.set(cv2.CAP_PROP_FPS, self.fps)
            ok, frame = capture.read()
            if ok and frame is not None:
                return capture, source, frame
            capture.release()
        return None, None, None

    def _set_unavailable(self, message: str) -> None:
        with self._condition:
            self._frame = None
            self._frame_time = 0.0
            self._active_device = ""
            self._camera_name = ""
            self._error = message
            self._condition.notify_all()

    def _supervise(self) -> None:
        try:
            import cv2
        except ImportError:
            self._set_unavailable("Camera support is not installed (python3-opencv)")
            return

        delay = 1.0
        while self._running:
            capture = None
            try:
                capture, source, first_frame = self._open_capture()
                if capture is None:
                    self._set_unavailable("No working USB camera detected")
                    if self._wait(delay):
                        break
                    delay = min(delay * 1.6, 8.0)
                    continue

                self._capture = capture
                with self._condition:
                    self._active_device = str(source)
                    self._camera_name = self._device_name(source)
                    self._error = ""
                delay = 1.0
                frame = first_frame
                while self._running:
                    if frame is None:
                        ok, frame = capture.read()
                        if not ok or frame is None:
                            raise RuntimeError("Camera stopped returning frames")
                    ok, encoded = cv2.imencode(
                        ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 68]
                    )
                    if not ok:
                        raise RuntimeError("Camera frame could not be encoded")
                    with self._condition:
                        self._frame = encoded.tobytes()
                        self._frame_time = time.monotonic()
                        self._error = ""
                        self._condition.notify_all()
                    frame = None
            except Exception as error:  # Camera drivers surface several exception types.
                self._restart_count += 1
                self._set_unavailable(f"USB camera reconnecting: {error}")
                if self._wait(delay):
                    break
                delay = min(delay * 1.6, 8.0)
            finally:
                self._capture = None
                if capture is not None:
                    capture.release()

    def _wait(self, seconds: float) -> bool:
        deadline = time.monotonic() + seconds
        with self._condition:
            while self._running and time.monotonic() < deadline:
                self._condition.wait(timeout=max(0.0, deadline - time.monotonic()))
            return not self._running

    def latest_jpeg(self) -> bytes | None:
        with self._condition:
            return self._frame

    def public_status(self) -> dict[str, Any]:
        with self._condition:
            age = (
                round(time.monotonic() - self._frame_time, 2)
                if self._frame_time
                else None
            )
            return {
                "available": self._frame is not None and age is not None and age < 3.0,
                "name": self._camera_name,
                "device": self._active_device,
                "error": self._error,
                "width": self.width,
                "height": self.height,
                "fps": self.fps,
                "frame_age_seconds": age,
                "restart_count": self._restart_count,
            }

    def frames(self) -> Iterator[bytes]:
        last_frame: bytes | None = None
        while True:
            with self._condition:
                self._condition.wait_for(
                    lambda: not self._running or (
                        self._frame is not None and self._frame is not last_frame
                    ),
                    timeout=2.0,
                )
                if not self._running:
                    return
                frame = self._frame
            if frame is None or frame is last_frame:
                continue
            last_frame = frame
            yield (
                b"--frame\r\nContent-Type: image/jpeg\r\n"
                + f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii")
                + frame
                + b"\r\n"
            )

    def close(self) -> None:
        with self._condition:
            if not self._running:
                return
            self._running = False
            self._condition.notify_all()
        capture = self._capture
        if capture is not None:
            capture.release()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
