"""Low-rate system health telemetry collected away from request threads."""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable


class SystemHealthMonitor:
    """Cache slow host checks so dashboard/status requests stay predictable."""

    def __init__(self, camera_age: Callable[[], float], disk_path: Path) -> None:
        self._camera_age = camera_age
        self._disk_path = disk_path
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None
        self.interval = max(5.0, float(os.environ.get("HEALTH_INTERVAL_SECONDS", "10")))
        self._state = {
            "status": "starting",
            "temperature_c": None,
            "throttled_flags": None,
            "power_warning": None,
            "throttling_warning": None,
            "disk_free_mb": None,
            "disk_free_percent": None,
            "load_1m": None,
            "camera_frame_age_seconds": None,
            "collected_at_ms": None,
            "error": None,
        }

    def _ensure_started(self) -> None:
        with self._lock:
            if self._thread is None:
                self._thread = threading.Thread(target=self._run, name="system-health", daemon=True)
                self._thread.start()

    def snapshot(self) -> dict:
        self._ensure_started()
        with self._lock:
            state = dict(self._state)
        age = self._camera_age()
        state["camera_frame_age_seconds"] = round(age, 2) if age != float("inf") else None
        return state

    @staticmethod
    def _temperature() -> float | None:
        thermal = Path("/sys/class/thermal/thermal_zone0/temp")
        try:
            return round(float(thermal.read_text(encoding="ascii").strip()) / 1000, 1)
        except (OSError, ValueError):
            return None

    @staticmethod
    def _vcgencmd(argument: str) -> str | None:
        executable = shutil.which("vcgencmd")
        if not executable:
            return None
        try:
            result = subprocess.run(
                [executable, argument], capture_output=True, text=True, timeout=0.75, check=False
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            return None

    def _collect(self) -> dict:
        target = self._disk_path if self._disk_path.exists() else Path.cwd()
        usage = shutil.disk_usage(target)
        temperature = self._temperature()
        if temperature is None and (text := self._vcgencmd("measure_temp")):
            try:
                temperature = round(float(text.split("=")[-1].replace("'C", "")), 1)
            except ValueError:
                temperature = None
        flags = None
        if text := self._vcgencmd("get_throttled"):
            try:
                flags = int(text.split("=")[-1], 16)
            except ValueError:
                flags = None
        try:
            load_1m = round(os.getloadavg()[0], 2)
        except (AttributeError, OSError):
            load_1m = None
        return {
            "status": "ok",
            "temperature_c": temperature,
            "throttled_flags": flags,
            "power_warning": bool(flags & ((1 << 0) | (1 << 16))) if flags is not None else None,
            "throttling_warning": bool(flags & 0xE000E) if flags is not None else None,
            "disk_free_mb": round(usage.free / (1024 * 1024)),
            "disk_free_percent": round((usage.free / usage.total) * 100, 1),
            "load_1m": load_1m,
            "collected_at_ms": round(time.time() * 1000),
            "error": None,
        }

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                update = self._collect()
            except Exception as error:  # Telemetry can never become a control dependency.
                update = {
                    "status": "unavailable",
                    "collected_at_ms": round(time.time() * 1000),
                    "error": str(error),
                }
            with self._lock:
                self._state.update(update)
            self._wake.wait(self.interval)
            self._wake.clear()

    def close(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread:
            self._thread.join(timeout=1)
