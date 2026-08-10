"""Local hotspot dashboard for one mecanum and two future ESP32 robots."""

from __future__ import annotations

import atexit
import os
import socket
import threading
import time

from flask import Flask, Response, jsonify, render_template, request

from .camera import CameraStream
from .motor import MecanumDrive


WATCHDOG_SECONDS = float(os.environ.get("DRIVE_WATCHDOG_SECONDS", "0.4"))
drive = MecanumDrive()
camera = CameraStream(
    device=os.environ.get("CAMERA_DEVICE", "/dev/video0"),
    width=int(os.environ.get("CAMERA_WIDTH", "1280")),
    height=int(os.environ.get("CAMERA_HEIGHT", "720")),
    fps=int(os.environ.get("CAMERA_FPS", "20")),
)
last_drive_at = 0.0
state_lock = threading.Lock()
shutdown_event = threading.Event()


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            esp32_one_stream=os.environ.get("ESP32_ONE_STREAM_URL", ""),
            esp32_two_stream=os.environ.get("ESP32_TWO_STREAM_URL", ""),
        )

    @app.get("/camera.mjpg")
    def camera_feed():
        return Response(camera.frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.get("/api/status")
    def status():
        return jsonify(
            online=True,
            hostname=socket.gethostname(),
            gpio="hardware" if drive.is_hardware else "simulation",
            camera_available=camera.available,
            camera_error=camera.error,
            command=drive.last_command,
        )

    @app.post("/api/drive")
    def command_drive():
        global last_drive_at
        payload = request.get_json(silent=True) or {}
        try:
            forward = float(payload.get("forward", 0))
            strafe = float(payload.get("strafe", 0))
            rotate = float(payload.get("rotate", 0))
            speed = float(payload.get("speed", 0.75))
        except (TypeError, ValueError):
            return jsonify(error="Drive values must be numbers"), 400
        try:
            drive.drive(forward, strafe, rotate, speed)
        except ValueError as error:
            return jsonify(error=str(error)), 400
        with state_lock:
            last_drive_at = time.monotonic()
        return jsonify(ok=True)

    @app.post("/api/stop")
    def command_stop():
        drive.stop()
        return jsonify(ok=True)

    @app.get("/healthz")
    def health():
        return jsonify(ok=True)

    return app


def _watchdog() -> None:
    global last_drive_at
    while not shutdown_event.wait(0.05):
        with state_lock:
            expired = last_drive_at and time.monotonic() - last_drive_at > WATCHDOG_SECONDS
            if expired:
                last_drive_at = 0
        if expired:
            drive.stop()


def cleanup() -> None:
    shutdown_event.set()
    drive.close()
    camera.close()


threading.Thread(target=_watchdog, name="motor-watchdog", daemon=True).start()
atexit.register(cleanup)
app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")), threaded=True)
