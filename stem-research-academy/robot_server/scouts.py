"""UDP heartbeat discovery for ECHO scouts on the Pi hotspot."""

from __future__ import annotations

import json
import socket
import threading
import time


class ScoutRegistry:
    def __init__(self, port: int = 5006, max_age: float = 6.0) -> None:
        self.port = port
        self.max_age = max_age
        self._records: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.error: str | None = None
        self._thread = threading.Thread(target=self._listen, name="scout-heartbeats", daemon=True)
        self._thread.start()

    def _listen(self) -> None:
        listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.settimeout(0.5)
        try:
            listener.bind(("0.0.0.0", self.port))
            while not self._stop.is_set():
                try:
                    payload, address = listener.recvfrom(1024)
                    data = json.loads(payload.decode("utf-8"))
                    scout_id = str(data.get("id", "")).lower()
                    if scout_id not in ("a", "b"):
                        continue
                    with self._lock:
                        self._records[scout_id] = {
                            "id": scout_id,
                            "ip": address[0],
                            "last_seen": time.monotonic(),
                            "rssi": data.get("rssi"),
                            "uptime_ms": data.get("uptime_ms"),
                        }
                except socket.timeout:
                    continue
                except (UnicodeDecodeError, ValueError, OSError):
                    continue
        except OSError as error:
            self.error = str(error)
        finally:
            listener.close()

    def snapshot(self, scout_id: str) -> dict | None:
        with self._lock:
            record = self._records.get(scout_id)
            if not record:
                return None
            result = dict(record)
        age = time.monotonic() - result["last_seen"]
        if age > self.max_age:
            return None
        result["age_ms"] = round(age * 1000)
        return result

    def host_for(self, scout_id: str, fallback: str) -> str:
        record = self.snapshot(scout_id)
        return record["ip"] if record else fallback

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=1)

