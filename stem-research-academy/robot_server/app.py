"""3TSahur mecanum robot hotspot dashboard."""

from __future__ import annotations

import atexit
import logging
import os
import socket
import threading
import time
from collections import deque
from pathlib import Path
from uuid import uuid4

from flask import Flask, Response, jsonify, render_template, request, send_from_directory

from .actuators import ActuatorController
from .camera import CameraStream
from .health import SystemHealthMonitor
from .motor import MecanumDrive


# Drive heartbeats are intentionally frequent and must not flood journald.
# Warnings, tracebacks, and explicit application errors remain visible.
logging.getLogger("werkzeug").setLevel(logging.WARNING)

WATCHDOG_SECONDS = float(os.environ.get("DRIVE_WATCHDOG_SECONDS", "0.20"))
drive = MecanumDrive()
camera = CameraStream(
    device=os.environ.get("CAMERA_DEVICE", "auto"),
    width=int(os.environ.get("CAMERA_WIDTH", "640")),
    height=int(os.environ.get("CAMERA_HEIGHT", "480")),
    fps=int(os.environ.get("CAMERA_FPS", "10")),
)
last_drive_at = 0.0
state_lock = threading.Lock()
shutdown_event = threading.Event()
drive_sequences: dict[str, int] = {}


def _control_is_active() -> bool:
    return bool(last_drive_at and time.monotonic() - last_drive_at < WATCHDOG_SECONDS * 1.5)


events: deque[dict] = deque(maxlen=120)
event_lock = threading.Lock()
snapshot_dir = Path(os.environ.get("SNAPSHOT_DIR", "/tmp/3tsahur-snapshots"))
CAMERA_PROFILES = {"control": (320, 240, 6), "balanced": (640, 480, 10), "detail": (1280, 720, 12)}
camera_profile = "balanced"
actuators = ActuatorController()
system_health = SystemHealthMonitor(lambda: camera.frame_age_seconds, snapshot_dir)


def record_event(kind: str, source: str, message: str) -> dict:
    event = {"id": uuid4().hex[:10], "at_ms": round(time.time() * 1000), "kind": kind[:32], "source": source[:16], "message": message[:160]}
    with event_lock:
        events.appendleft(event)
    return event


def _snapshot_bytes(source: str) -> bytes | None:
    if source == "3tsahur":
        return camera.latest_jpeg()
    return None


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    @app.after_request
    def prevent_stale_dashboard(response):
        if request.endpoint != "camera_feed":
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
        return response

    @app.get("/")
    def index():
        return render_template("index.html", server_time_ms=round(time.time() * 1000))

    @app.get("/camera.mjpg")
    def camera_feed():
        return Response(camera.frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.get("/api/status")
    def status():
        frame_age = camera.frame_age_seconds
        return jsonify(
            online=True,
            name="3TSahur",
            hostname=socket.gethostname(),
            gpio="hardware" if drive.is_hardware else "simulation",
            camera_available=camera.available,
            camera_error=camera.error,
            camera_device=camera.selected_device,
            camera_name=camera.camera_name,
            camera_mode="automatic",
            camera_profile=camera_profile,
            camera_width=camera.capture_width or camera.width,
            camera_height=camera.capture_height or camera.height,
            camera_fps=camera.capture_fps or camera.fps,
            camera_frame_age_seconds=None if frame_age == float("inf") else round(frame_age, 2),
            camera_restart_count=camera.restart_count,
            uptime_seconds=round(time.monotonic(), 1),
            command=drive.last_command,
            actuators=actuators.snapshot(),
            system_health=system_health.snapshot(),
            server_time_ms=round(time.time() * 1000),
        )

    @app.post("/api/camera/profile")
    def set_camera_profile():
        global camera_profile
        if _control_is_active():
            return jsonify(error="Stop all robots before changing the camera profile", control_active=True), 409
        profile = str((request.get_json(silent=True) or {}).get("profile", ""))
        if profile not in CAMERA_PROFILES:
            return jsonify(error="Unknown camera profile"), 400
        width, height, fps = CAMERA_PROFILES[profile]
        try:
            camera.configure(width, height, fps)
            camera_profile = profile
            return jsonify(ok=True, profile=profile, width=width, height=height, fps=fps)
        except ValueError as error:
            return jsonify(error=str(error)), 400

    @app.post("/api/actuators/ramp")
    def set_ramp():
        payload = request.get_json(silent=True) or {}
        try:
            result = actuators.set_ramp(payload.get("state"))
            record_event("ramp", "3tsahur", f"Ramp target {result['ramp']['state']}")
            return jsonify(ok=True, **result)
        except ValueError as error:
            return jsonify(error=str(error)), 400

    @app.get("/api/events")
    def event_list():
        with event_lock:
            return jsonify(events=list(events))

    @app.post("/api/events")
    def add_event():
        payload = request.get_json(silent=True) or {}
        return jsonify(record_event(str(payload.get("kind", "note")), str(payload.get("source", "dashboard")), str(payload.get("message", "Operator event"))))

    @app.post("/api/snapshots/<source>")
    def snapshot(source: str):
        if source != "3tsahur":
            return jsonify(error="Unknown snapshot source"), 404
        if _control_is_active():
            return jsonify(error="Stop all robots before taking a snapshot", control_active=True), 409
        try:
            image = _snapshot_bytes(source)
            if not image:
                raise RuntimeError("No JPEG frame received")
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            name = f"{round(time.time() * 1000)}-{source}.jpg"
            (snapshot_dir / name).write_bytes(image)
            event = record_event("snapshot", source, f"Saved {source} camera snapshot")
            return jsonify(ok=True, url=f"/snapshots/{name}", event=event)
        except Exception as error:
            return jsonify(error=f"Snapshot unavailable: {error}"), 503

    @app.get("/snapshots/<path:name>")
    def serve_snapshot(name: str):
        return send_from_directory(snapshot_dir, name)

    @app.post("/api/drive")
    def command_drive():
        global last_drive_at
        payload = request.get_json(silent=True) or {}
        try:
            forward = float(payload.get("forward", 0))
            strafe = float(payload.get("strafe", 0))
            rotate = float(payload.get("rotate", 0))
            speed = float(payload.get("speed", 0.75))
            sequence = int(payload.get("sequence", 0))
            session = str(payload.get("session", "legacy"))[:64]
            expires_at_ms = int(payload["expires_at_ms"])
        except (TypeError, ValueError):
            return jsonify(error="Drive values must be numbers"), 400
        except KeyError:
            return jsonify(error="Current control protocol required", expired=True), 409
        server_now_ms = round(time.time() * 1000)
        if expires_at_ms < server_now_ms or expires_at_ms > server_now_ms + 1000:
            with state_lock:
                drive.stop()
                last_drive_at = 0
            return jsonify(ok=True, expired=True, sequence=sequence), 409
        with state_lock:
            if sequence and sequence <= drive_sequences.get(session, -1):
                return jsonify(ok=True, stale=True, sequence=sequence)
            if sequence:
                drive_sequences[session] = sequence
                if len(drive_sequences) > 64:
                    drive_sequences.pop(next(iter(drive_sequences)))
            try:
                drive.drive(forward, strafe, rotate, speed)
            except ValueError as error:
                return jsonify(error=str(error)), 400
            last_drive_at = time.monotonic() if speed > 0 and (forward or strafe or rotate) else 0.0
        return jsonify(ok=True, sequence=sequence)

    @app.post("/api/stop")
    def command_stop():
        global last_drive_at
        with state_lock:
            drive.stop()
            last_drive_at = 0
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
                drive.stop()


def cleanup() -> None:
    shutdown_event.set()
    actuators.close()
    drive.close()
    camera.close()
    system_health.close()


threading.Thread(target=_watchdog, name="motor-watchdog", daemon=True).start()
atexit.register(cleanup)
app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")), threaded=True)
