"""Background capture and MJPEG encoding for a USB webcam."""

from __future__ import annotations

import threading
import time


class CameraStream:
    def __init__(self, device: str = "/dev/video0", width: int = 640, height: int = 480, fps: int = 10) -> None:
        self.device = device
        self.width = width
        self.height = height
        self.fps = fps
        self._condition = threading.Condition()
        self._frame: bytes | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self.error: str | None = None

    def start(self) -> None:
        with self._condition:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._capture, name="usb-camera", daemon=True)
            self._thread.start()

    def _capture(self) -> None:
        try:
            import cv2  # type: ignore

            source = int(self.device) if self.device.isdigit() else self.device
            camera = cv2.VideoCapture(source, cv2.CAP_V4L2)
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            camera.set(cv2.CAP_PROP_FPS, self.fps)
            camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            if not camera.isOpened():
                raise RuntimeError(f"Could not open camera {self.device}")

            frame_interval = 1 / max(1, self.fps)
            next_frame_at = time.monotonic()
            while self._running:
                ok, image = camera.read()
                if not ok:
                    self.error = "Camera stopped returning frames"
                    time.sleep(0.2)
                    continue
                ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 65])
                if ok:
                    with self._condition:
                        self._frame = encoded.tobytes()
                        self.error = None
                        self._condition.notify_all()
                next_frame_at += frame_interval
                delay = next_frame_at - time.monotonic()
                if delay > 0:
                    time.sleep(delay)
                else:
                    next_frame_at = time.monotonic()
            camera.release()
        except Exception as error:  # Camera errors must not take down motor control.
            self.error = str(error)
        finally:
            self._running = False

    def frames(self):
        self.start()
        last_frame = None
        while self._running:
            with self._condition:
                self._condition.wait_for(lambda: self._frame is not None and self._frame is not last_frame, timeout=2)
                frame = self._frame
            if frame is None:
                continue
            last_frame = frame
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"

    @property
    def available(self) -> bool:
        return self._frame is not None and self.error is None

    def close(self) -> None:
        self._running = False
        with self._condition:
            self._condition.notify_all()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
