"""3TSahur web server: one Driver Station and one Debug page.

The robot's code is built in (``robot.py``), so there is nothing to upload.
``/`` is the Driver Station; ``/debug`` maps motor ports and servo channels,
runs single outputs, and shows the wiring, servo board, and IMU.
"""

from __future__ import annotations

import atexit
import logging
import os
import secrets
import signal
import socket
import threading
import time
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request

from . import hardware
from .camera import CameraStream
from .errors import ConfigurationError, RobotError
from .health import SystemHealthMonitor
from .robot import DEBUG_MOTOR_LIMIT, Robot
from .settings import RobotSettings, from_dict


# Drive heartbeats arrive every 80 ms and must not flood journald.
logging.getLogger("werkzeug").setLevel(logging.WARNING)

CAMERA_PROFILES = {"control": (320, 240, 6), "balanced": (640, 480, 10), "detail": (1280, 720, 12)}


def create_app(robot: Robot, camera: CameraStream | None = None, health: SystemHealthMonitor | None = None) -> Flask:
    app = Flask(__name__)
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    camera = camera or CameraStream(
        device=os.environ.get("CAMERA_DEVICE", "auto"),
        width=int(os.environ.get("CAMERA_WIDTH", "640")),
        height=int(os.environ.get("CAMERA_HEIGHT", "480")),
        fps=int(os.environ.get("CAMERA_FPS", "10")),
    )
    health = health or SystemHealthMonitor(lambda: camera.frame_age_seconds, Path.home())
    token = secrets.token_urlsafe(32)
    command_lock = threading.Lock()
    state = {"sequence": -1, "camera_profile": "balanced", "last_drive": 0.0}
    app.config.update(ROBOT=robot, CAMERA=camera, HEALTH=health, ROBOT_TOKEN=token)

    def authorized() -> bool:
        provided = request.headers.get("X-Robot-Token", "")
        return bool(provided) and secrets.compare_digest(provided, token)

    def refused():
        return jsonify(ok=False, error="This page is out of date. Reload it."), 403

    def failed(error: Exception, status: int = 400):
        return jsonify(ok=False, error=str(error)), status

    def driving() -> bool:
        return time.monotonic() - state["last_drive"] < 0.5

    @app.after_request
    def no_stale_pages(response):
        if request.endpoint != "camera_feed":
            response.headers["Cache-Control"] = "no-store, max-age=0"
        return response

    # Pages ----------------------------------------------------------------------

    @app.get("/")
    def driver_station():
        return render_template("driver_station.html", token=token, hostname=socket.gethostname())

    @app.get("/debug")
    def debug_page():
        return render_template("debug.html", token=token, hostname=socket.gethostname())

    @app.get("/healthz")
    def healthz():
        return jsonify(ok=True)

    @app.get("/camera.mjpg")
    def camera_feed():
        return Response(camera.frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

    # Status ---------------------------------------------------------------------

    @app.get("/api/status")
    def status():
        frame_age = camera.frame_age_seconds
        return jsonify(
            ok=True,
            name="3TSahur",
            hostname=socket.gethostname(),
            uptime_seconds=round(time.monotonic(), 1),
            robot=robot.snapshot(),
            camera={
                "available": camera.available,
                "error": camera.error,
                "name": camera.camera_name,
                "device": camera.selected_device,
                "profile": state["camera_profile"],
                "width": camera.capture_width or camera.width,
                "height": camera.capture_height or camera.height,
                "fps": camera.capture_fps or camera.fps,
                "frame_age_seconds": None if frame_age == float("inf") else round(frame_age, 2),
            },
            system=health.snapshot(),
        )

    @app.get("/api/config")
    def configuration():
        return jsonify(
            ok=True,
            settings=robot.settings.to_dict(),
            settings_path=str(robot.store.path),
            settings_error=robot.store.load_error,
            defaults=RobotSettings().to_dict(),
            ports=hardware.port_rows(),
            wheels=[{"id": wheel, "label": hardware.WHEEL_LABELS[wheel]} for wheel in hardware.WHEELS],
            ramp_servos=[{"id": name, "label": hardware.RAMP_SERVO_LABELS[name]} for name in hardware.RAMP_SERVOS],
            header=hardware.header_rows(),
            servo={
                "address": f"0x{hardware.SERVO_ADDRESS:02x}",
                "channels": hardware.SERVO_CHANNELS,
                "min_pulse_us": hardware.SERVO_MIN_PULSE_US,
                "max_pulse_us": hardware.SERVO_MAX_PULSE_US,
                "oe_gpio": hardware.SERVO_OE_GPIO,
            },
            imu={"model": "BNO055", "address": f"0x{hardware.IMU_ADDRESS:02x}"},
            debug_motor_limit=DEBUG_MOTOR_LIMIT,
            watchdog_ms=hardware.WATCHDOG_MS,
        )

    # Driving --------------------------------------------------------------------

    @app.post("/api/drive")
    def drive():
        if not authorized():
            return refused()
        body = request.get_json(silent=True) or {}
        try:
            sequence = int(body.get("sequence", -1))
        except (TypeError, ValueError):
            return failed(ValueError("sequence must be a number"))
        with command_lock:
            if sequence <= state["sequence"]:
                return jsonify(ok=True, ignored="stale sequence")
            state["sequence"] = sequence
            try:
                result = robot.drive(
                    body.get("forward", 0), body.get("strafe", 0), body.get("rotate", 0), body.get("speed", 0.5)
                )
            except (RobotError, ValueError) as error:
                robot.stop()
                return failed(error)
            state["last_drive"] = time.monotonic()
        return jsonify(ok=True, **result)

    @app.post("/api/stop")
    def stop():
        # Deliberately unauthenticated: any open page may always stop the robot.
        emergency = bool((request.get_json(silent=True) or {}).get("emergency"))
        with command_lock:
            state["last_drive"] = 0.0
            try:
                robot.emergency_stop() if emergency else robot.stop()
            except Exception:
                app.logger.exception("Stop failed")
                robot.controller.stop_all()
                return jsonify(ok=False, error="A stop step failed. Use the physical power cutoff."), 500
        return jsonify(ok=True, emergency=emergency)

    @app.post("/api/ramp")
    def ramp():
        if not authorized():
            return refused()
        with command_lock:
            try:
                return jsonify(ok=True, ramp=robot.set_ramp((request.get_json(silent=True) or {}).get("state")))
            except ValueError as error:
                return failed(error)
            except RobotError as error:
                return failed(error, 503)

    @app.post("/api/imu/zero")
    def zero_imu():
        if not authorized():
            return refused()
        robot.imu.zero_heading()
        return jsonify(ok=True, imu=robot.imu.snapshot())

    @app.post("/api/camera/profile")
    def camera_profile():
        if not authorized():
            return refused()
        if driving():
            return failed(RobotError("Stop driving before changing the camera quality"), 409)
        profile = str((request.get_json(silent=True) or {}).get("profile", ""))
        if profile not in CAMERA_PROFILES:
            return failed(ValueError("Unknown camera profile"))
        camera.configure(*CAMERA_PROFILES[profile])
        state["camera_profile"] = profile
        return jsonify(ok=True, profile=profile)

    # Debug ----------------------------------------------------------------------

    @app.post("/api/settings")
    def save_settings():
        if not authorized():
            return refused()
        try:
            settings = from_dict(request.get_json(silent=True))
        except ConfigurationError as error:
            return failed(error)
        with command_lock:
            state["last_drive"] = 0.0
            try:
                robot.apply_settings(settings)
            except OSError as error:
                return failed(RobotError(f"Could not save settings: {error}"), 500)
        return jsonify(ok=True, settings=robot.settings.to_dict())

    @app.post("/api/debug/motor")
    def debug_motor():
        if not authorized():
            return refused()
        body = request.get_json(silent=True) or {}
        if body.get("confirmed") is not True:
            return failed(RobotError("Raise the wheels and tick the safety check first"))
        if driving():
            return failed(RobotError("The Driver Station is driving. Disable it first."), 409)
        with command_lock:
            try:
                robot.test_port(body.get("port"), body.get("power", 0))
            except (RobotError, ValueError) as error:
                robot.stop()
                return failed(error)
        return jsonify(ok=True)

    @app.post("/api/debug/servo")
    def debug_servo():
        if not authorized():
            return refused()
        body = request.get_json(silent=True) or {}
        if body.get("confirmed") is not True:
            return failed(RobotError("Confirm the mechanism is clear first"))
        with command_lock:
            try:
                pulse = robot.test_servo(body.get("channel"), angle=body.get("angle"), pulse_us=body.get("pulse_us"))
            except (RobotError, ValueError) as error:
                return failed(error)
        return jsonify(ok=True, pulse_us=round(pulse, 1))

    @app.post("/api/debug/servo/release")
    def debug_servo_release():
        if not authorized():
            return refused()
        body = request.get_json(silent=True) or {}
        with command_lock:
            try:
                if body.get("all") is True:
                    robot.controller.release_all_servos()
                    robot.ramp_state = "released"
                else:
                    robot.release_servo(body.get("channel"))
            except (RobotError, ValueError) as error:
                return failed(error)
        return jsonify(ok=True)

    @app.post("/api/servos/output-enable")
    def servo_output_enable():
        if not authorized():
            return refused()
        enabled = (request.get_json(silent=True) or {}).get("enabled")
        if not isinstance(enabled, bool):
            return failed(ValueError("Send enabled: true or false"))
        with command_lock:
            if not enabled:
                robot.controller.release_all_servos()
                robot.ramp_state = "released"
            robot.controller.set_servo_outputs_enabled(enabled)
        return jsonify(ok=True, enabled=robot.controller.servo_outputs_enabled)

    return app


def main() -> int:
    robot = Robot()
    app = create_app(robot)
    camera, health = app.config["CAMERA"], app.config["HEALTH"]

    def cleanup() -> None:
        for close in (robot.close, camera.close, health.close):
            try:
                close()
            except Exception:
                pass

    def terminate(_signum, _frame) -> None:
        # systemd stops the service with SIGTERM; exit through atexit cleanup.
        raise SystemExit(0)

    atexit.register(cleanup)
    signal.signal(signal.SIGTERM, terminate)
    mode = "Raspberry Pi GPIO" if robot.controller.is_hardware else "simulation (no GPIO found)"
    print(f"3TSahur driver station on port {os.environ.get('PORT', '8080')} using {mode}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")), threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
