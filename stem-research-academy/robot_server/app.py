"""Local hotspot dashboard for one mecanum robot and two ECHO scouts."""

from __future__ import annotations

import atexit
import json
import math
import os
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

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
SCOUTS = {
    "a": {
        "name": "ECHO Scout A",
        "host": os.environ.get("SCOUT_A_HOST", "echo-scout-a.local"),
        "camera": os.environ.get("ESP32_ONE_STREAM_URL") or "http://echo-scout-a-cam.local/stream",
    },
    "b": {
        "name": "ECHO Scout B",
        "host": os.environ.get("SCOUT_B_HOST", "echo-scout-b.local"),
        "camera": os.environ.get("ESP32_TWO_STREAM_URL") or "http://echo-scout-b-cam.local/stream",
    },
}


def _scout_request(scout_id: str, path: str, query: dict | None = None) -> dict:
    scout = SCOUTS.get(scout_id)
    if scout is None:
        raise KeyError(scout_id)
    suffix = f"?{urllib.parse.urlencode(query)}" if query else ""
    url = f"http://{scout['host']}{path}{suffix}"
    with urllib.request.urlopen(url, timeout=0.45) as response:
        body = response.read(8192).decode("utf-8")
    return json.loads(body) if body else {"ok": True}


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            esp32_one_stream=SCOUTS["a"]["camera"],
            esp32_two_stream=SCOUTS["b"]["camera"],
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

    @app.get("/api/scouts/<scout_id>/status")
    def scout_status(scout_id: str):
        if scout_id not in SCOUTS:
            return jsonify(error="Unknown scout"), 404
        try:
            status_data = _scout_request(scout_id, "/status")
            status_data["online"] = True
            status_data["host"] = SCOUTS[scout_id]["host"]
            return jsonify(status_data)
        except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as error:
            return jsonify(
                online=False,
                name=SCOUTS[scout_id]["name"],
                host=SCOUTS[scout_id]["host"],
                error=str(error),
            )

    @app.post("/api/scouts/<scout_id>/drive")
    def scout_drive(scout_id: str):
        if scout_id not in SCOUTS:
            return jsonify(error="Unknown scout"), 404
        payload = request.get_json(silent=True) or {}
        try:
            x = float(payload.get("x", 0))
            y = float(payload.get("y", 0))
            speed = float(payload.get("speed", 35))
            if not all(math.isfinite(value) for value in (x, y, speed)):
                raise ValueError
        except (TypeError, ValueError):
            return jsonify(error="Scout drive values must be finite numbers"), 400
        query = {
            "x": round(max(-100, min(100, x))),
            "y": round(max(-100, min(100, y))),
            "speed": round(max(0, min(100, speed))),
        }
        try:
            result = _scout_request(scout_id, "/drive", query)
            return jsonify(result)
        except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as error:
            return jsonify(error=f"{SCOUTS[scout_id]['name']} is unreachable: {error}"), 502

    @app.post("/api/scouts/<scout_id>/stop")
    def scout_stop(scout_id: str):
        if scout_id not in SCOUTS:
            return jsonify(error="Unknown scout"), 404
        try:
            result = _scout_request(scout_id, "/stop")
            return jsonify(result)
        except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as error:
            return jsonify(error=f"{SCOUTS[scout_id]['name']} is unreachable: {error}"), 502

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
