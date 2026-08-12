"""Bounded background storage for reconnaissance evidence bundles."""

from __future__ import annotations

import json
import os
import queue
import threading
import time
from collections import deque
from pathlib import Path
from uuid import uuid4


class EvidenceStore:
    """Write JPEG + metadata pairs asynchronously with bounded memory/disk use."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.max_items = max(10, int(os.environ.get("EVIDENCE_MAX_ITEMS", "100")))
        self._queue: queue.Queue[tuple[str, bytes, dict]] = queue.Queue(
            maxsize=max(2, int(os.environ.get("EVIDENCE_QUEUE_SIZE", "12")))
        )
        self._items: deque[dict] = deque(maxlen=self.max_items)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._dropped = 0
        self._error: str | None = None

    def _ensure_started(self) -> None:
        with self._lock:
            if self._thread is None:
                self._thread = threading.Thread(target=self._run, name="evidence-writer", daemon=True)
                self._thread.start()

    def submit(self, source: str, image: bytes, metadata: dict) -> dict:
        self._ensure_started()
        identifier = f"{round(time.time() * 1000)}-{source}-{uuid4().hex[:8]}"
        item = {
            "id": identifier,
            "source": source,
            "at_ms": int(metadata.get("at_ms", round(time.time() * 1000))),
            "status": "queued",
        }
        try:
            self._queue.put_nowait((identifier, bytes(image), dict(metadata)))
        except queue.Full as error:
            with self._lock:
                self._dropped += 1
            raise RuntimeError("Evidence queue is full; try again after the robot stops") from error
        return item

    def snapshot(self) -> dict:
        self._ensure_started()
        with self._lock:
            items = [dict(item) for item in self._items]
            dropped = self._dropped
            error = self._error
        return {"items": items, "queue_depth": self._queue.qsize(), "dropped": dropped, "error": error}

    def _load_existing(self) -> None:
        """Restore the newest index and prune old bundles after a restart."""
        self.root.mkdir(parents=True, exist_ok=True)
        metadata_files = sorted(
            self.root.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True
        )
        restored = []
        for index, path in enumerate(metadata_files):
            identifier = path.stem
            if index >= self.max_items:
                path.unlink(missing_ok=True)
                (self.root / f"{identifier}.jpg").unlink(missing_ok=True)
                continue
            try:
                metadata = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(metadata, dict):
                    continue
                if not (self.root / f"{identifier}.jpg").is_file():
                    continue
                restored.append(
                    {
                        "id": identifier,
                        "source": metadata.get("source"),
                        "at_ms": metadata.get("at_ms"),
                        "note": metadata.get("note", ""),
                        "image_url": f"/evidence/{identifier}.jpg",
                        "metadata_url": f"/evidence/{identifier}.json",
                        "status": "saved",
                    }
                )
            except (OSError, ValueError, TypeError):
                continue
        with self._lock:
            self._items.clear()
            self._items.extend(restored)

    def _write(self, identifier: str, image: bytes, metadata: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        metadata.update(id=identifier, image_url=f"/evidence/{identifier}.jpg")
        image_path = self.root / f"{identifier}.jpg"
        metadata_path = self.root / f"{identifier}.json"
        image_temp = self.root / f".{identifier}.jpg.tmp"
        metadata_temp = self.root / f".{identifier}.json.tmp"
        image_temp.write_bytes(image)
        metadata_temp.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
        image_temp.replace(image_path)
        metadata_temp.replace(metadata_path)
        item = {
            "id": identifier,
            "source": metadata.get("source"),
            "at_ms": metadata.get("at_ms"),
            "note": metadata.get("note", ""),
            "image_url": metadata["image_url"],
            "metadata_url": f"/evidence/{identifier}.json",
            "status": "saved",
        }
        stale = None
        with self._lock:
            # deque(maxlen) silently drops the oldest item, so remove its files first.
            if len(self._items) == self._items.maxlen:
                stale = self._items[-1]
            self._items.appendleft(item)
            self._error = None
        if stale:
            for suffix in (".jpg", ".json"):
                try:
                    (self.root / f"{stale['id']}{suffix}").unlink(missing_ok=True)
                except OSError:
                    pass

    def _run(self) -> None:
        try:
            self._load_existing()
        except Exception as error:
            with self._lock:
                self._error = str(error)
        while not self._stop.is_set() or not self._queue.empty():
            try:
                item = self._queue.get(timeout=0.25)
            except queue.Empty:
                continue
            try:
                self._write(*item)
            except Exception as error:  # Disk faults must remain outside control paths.
                with self._lock:
                    self._error = str(error)
            finally:
                self._queue.task_done()

    def close(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
