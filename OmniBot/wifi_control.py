"""Fail-safe browser control transport for OmniBot's existing drive loop.

This module deliberately knows nothing about GPIO or wheel mixing.  It accepts
short-lived laptop commands and exposes the newest safe input to
``omni_robot.py``, where the original deadzones and three-wheel kinematics stay
in charge.
"""

from __future__ import annotations

import json
import math
import threading
import time
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


DEFAULT_PORT = 8080
DEFAULT_WATCHDOG_SECONDS = 0.20
MAX_COMMAND_FUTURE_MS = 1000
MAX_REQUEST_BYTES = 4096


def _clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _number(payload: dict[str, Any], name: str, default: float = 0.0) -> float:
    try:
        value = float(payload.get(name, default))
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a number") from error
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


@dataclass(frozen=True)
class RemoteInput:
    """One frame of normalized operator input consumed by the robot loop."""

    enabled: bool
    generation: int
    session: str
    strafe: float = 0.0
    forward: float = 0.0
    turn: float = 0.0
    left_trigger: float = 0.0
    right_trigger: float = 0.0
    center_servo: bool = False

    @property
    def moving(self) -> bool:
        return bool(self.strafe or self.forward or self.turn)


class RemoteControlState:
    """Thread-safe latest-command mailbox with expiry and session checks."""

    def __init__(self, watchdog_seconds: float = DEFAULT_WATCHDOG_SECONDS) -> None:
        if watchdog_seconds <= 0:
            raise ValueError("watchdog_seconds must be positive")
        self.watchdog_seconds = float(watchdog_seconds)
        self._lock = threading.RLock()
        self._enabled = False
        self._generation = 0
        self._session = ""
        self._sequence = -1
        self._deadline = 0.0
        self._command = {
            "strafe": 0.0,
            "forward": 0.0,
            "turn": 0.0,
            "left_trigger": 0.0,
            "right_trigger": 0.0,
        }
        self._center_servo = False
        self._runtime_status: dict[str, Any] = {
            "enabled": False,
            "armed": False,
            "source": "none",
            "telemetry": [],
            "servo": "Starting",
        }

    @staticmethod
    def _session_name(value: Any) -> str:
        session = str(value or "").strip()[:64]
        if not session:
            raise ValueError("session is required")
        return session

    def enable(self, session_value: Any) -> dict[str, Any]:
        session = self._session_name(session_value)
        with self._lock:
            self._enabled = True
            self._session = session
            self._sequence = -1
            self._deadline = 0.0
            self._center_servo = False
            self._zero_command()
            self._generation += 1
            return {
                "ok": True,
                "generation": self._generation,
                "server_time_ms": round(time.time() * 1000),
            }

    def stop(self) -> dict[str, Any]:
        with self._lock:
            self._enabled = False
            self._deadline = 0.0
            self._center_servo = False
            self._zero_command()
            self._generation += 1
            return {"ok": True, "generation": self._generation}

    def _zero_command(self) -> None:
        for name in self._command:
            self._command[name] = 0.0

    def submit(
        self,
        payload: dict[str, Any],
        *,
        wall_time_ms: int | None = None,
        monotonic_time: float | None = None,
    ) -> dict[str, Any]:
        """Accept a current input or reject stale, expired, or foreign input."""

        wall_time_ms = round(time.time() * 1000) if wall_time_ms is None else wall_time_ms
        monotonic_time = time.monotonic() if monotonic_time is None else monotonic_time
        session = self._session_name(payload.get("session"))
        try:
            sequence = int(payload.get("sequence", 0))
            expires_at_ms = int(payload["expires_at_ms"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("sequence and expires_at_ms must be integers") from error

        values = {
            "strafe": _clamp(_number(payload, "strafe")),
            "forward": _clamp(_number(payload, "forward")),
            "turn": _clamp(_number(payload, "turn")),
            "left_trigger": _clamp(_number(payload, "left_trigger"), 0.0, 1.0),
            "right_trigger": _clamp(_number(payload, "right_trigger"), 0.0, 1.0),
        }
        if expires_at_ms < wall_time_ms or expires_at_ms > wall_time_ms + MAX_COMMAND_FUTURE_MS:
            self.stop()
            return {"ok": True, "expired": True, "sequence": sequence}

        with self._lock:
            if not self._enabled:
                return {"ok": False, "disabled": True, "sequence": sequence}
            if session != self._session:
                return {"ok": False, "session_mismatch": True, "sequence": sequence}
            if sequence <= self._sequence:
                return {"ok": True, "stale": True, "sequence": sequence}

            self._sequence = sequence
            self._command.update(values)
            self._center_servo = bool(payload.get("center_servo", False))
            ttl_seconds = max(0.0, (expires_at_ms - wall_time_ms) / 1000.0)
            self._deadline = monotonic_time + min(self.watchdog_seconds, ttl_seconds)
            return {"ok": True, "sequence": sequence}

    def _expire_if_needed(self, now: float) -> None:
        if not self._enabled or not self._deadline or now <= self._deadline:
            return
        was_moving = any(self._command[name] for name in ("strafe", "forward", "turn"))
        self._deadline = 0.0
        self._center_servo = False
        self._zero_command()
        if was_moving:
            # Losing Wi-Fi while moving behaves like disconnecting the local
            # controller: disable and require an explicit new enable action.
            self._enabled = False
            self._generation += 1

    def consume(self, monotonic_time: float | None = None) -> RemoteInput:
        now = time.monotonic() if monotonic_time is None else monotonic_time
        with self._lock:
            self._expire_if_needed(now)
            result = RemoteInput(
                enabled=self._enabled,
                generation=self._generation,
                session=self._session,
                center_servo=self._center_servo,
                **self._command,
            )
            self._center_servo = False
            return result

    def report_runtime(self, **status: Any) -> None:
        with self._lock:
            self._runtime_status.update(status)

    def public_status(self) -> dict[str, Any]:
        with self._lock:
            self._expire_if_needed(time.monotonic())
            remote = RemoteInput(
                enabled=self._enabled,
                generation=self._generation,
                session=self._session,
                **self._command,
            )
            return {
                "online": True,
                "server_time_ms": round(time.time() * 1000),
                "watchdog_ms": round(self.watchdog_seconds * 1000),
                "remote": asdict(remote),
                **self._runtime_status,
            }


class _ControlHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, state: RemoteControlState, web_root: Path) -> None:
        self.control_state = state
        self.web_root = web_root
        super().__init__(address, _ControlHandler)


class _ControlHandler(BaseHTTPRequestHandler):
    server: _ControlHTTPServer

    _STATIC_FILES = {
        "/": ("index.html", "text/html; charset=utf-8"),
        "/controller.js": ("controller.js", "text/javascript; charset=utf-8"),
        "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    }

    def log_message(self, _format: str, *_args: Any) -> None:
        # The 80 ms drive heartbeat should not flood omnibot.log.
        return

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _read_json(self) -> dict[str, Any]:
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("Invalid Content-Length") from error
        if size < 0 or size > MAX_REQUEST_BYTES:
            raise ValueError("Request body is too large")
        if not size:
            return {}
        try:
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("Request body must be JSON") from error
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object")
        return payload

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        path = urlsplit(self.path).path
        if path == "/healthz":
            self._json(HTTPStatus.OK, {"ok": True})
            return
        if path == "/api/status":
            self._json(HTTPStatus.OK, self.server.control_state.public_status())
            return
        static = self._STATIC_FILES.get(path)
        if static is None:
            self._json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        name, content_type = static
        try:
            body = (self.server.web_root / name).read_bytes()
        except OSError:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Web UI unavailable"})
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        path = urlsplit(self.path).path
        try:
            payload = self._read_json()
            if path == "/api/enable":
                result = self.server.control_state.enable(payload.get("session"))
                self._json(HTTPStatus.OK, result)
            elif path == "/api/stop":
                self._json(HTTPStatus.OK, self.server.control_state.stop())
            elif path == "/api/drive":
                result = self.server.control_state.submit(payload)
                if result.get("expired") or result.get("disabled") or result.get("session_mismatch"):
                    self._json(HTTPStatus.CONFLICT, result)
                else:
                    self._json(HTTPStatus.OK, result)
            else:
                self._json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
        except ValueError as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})


class WifiControlServer:
    """Background HTTP server lifecycle wrapper."""

    def __init__(
        self,
        state: RemoteControlState,
        host: str = "0.0.0.0",
        port: int = DEFAULT_PORT,
        web_root: Path | None = None,
    ) -> None:
        root = Path(__file__).with_name("web") if web_root is None else Path(web_root)
        self._server = _ControlHTTPServer((host, port), state, root)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="omnibot-wifi-control",
            daemon=True,
        )

    @property
    def port(self) -> int:
        return int(self._server.server_address[1])

    def start(self) -> "WifiControlServer":
        self._thread.start()
        return self

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2.0)
