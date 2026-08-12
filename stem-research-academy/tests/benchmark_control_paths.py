"""Repeatable hardware-independent timing simulation for all three robots."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from robot_server.app import app, drive_sequences, scout_registry, scout_sequences


def _command(sequence: int, **values: float | int | str) -> dict:
    values.update(
        expires_at_ms=round(time.time() * 1000) + 300,
        session="integration-benchmark",
        sequence=sequence,
    )
    return values


def run_benchmark(cycles: int = 1000, warmup: int = 50) -> dict:
    if cycles < 1 or warmup < 0:
        raise ValueError("cycles must be positive and warmup cannot be negative")

    app.config.update(TESTING=True)
    client = app.test_client()
    drive_sequences.clear()
    scout_sequences.clear()
    scout_registry.record("a", "10.42.0.31")
    scout_registry.record("b", "10.42.0.32")

    def composite_cycle(sequence: int) -> None:
        responses = (
            client.post("/api/drive", json=_command(sequence, forward=1, speed=0.30)),
            client.post("/api/scouts/a/drive", json=_command(sequence, y=100, speed=30)),
            client.post("/api/scouts/b/drive", json=_command(sequence, y=100, speed=30)),
        )
        statuses = [response.status_code for response in responses]
        if any(status != 200 for status in statuses):
            raise RuntimeError(f"Composite control cycle failed: {statuses}")

    with patch("robot_server.app._scout_request", return_value={"ok": True}):
        for sequence in range(1, warmup + 1):
            composite_cycle(sequence)

        samples = []
        for sequence in range(warmup + 1, warmup + cycles + 1):
            started = time.perf_counter()
            composite_cycle(sequence)
            samples.append((time.perf_counter() - started) * 1000)

    ordered = sorted(samples)
    return {
        "cycles": cycles,
        "requests": cycles * 3,
        "average_ms_per_three_robot_cycle": round(sum(samples) / cycles, 3),
        "p95_ms": round(ordered[max(0, int(cycles * 0.95) - 1)], 3),
        "maximum_ms": round(max(samples), 3),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycles", type=int, default=1000)
    parser.add_argument("--warmup", type=int, default=50)
    arguments = parser.parse_args()
    print(json.dumps(run_benchmark(arguments.cycles, arguments.warmup), indent=2))
