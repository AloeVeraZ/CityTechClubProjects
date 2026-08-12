#!/usr/bin/env bash
# Select the optional persistent vision runtime when it has been installed.
# Falling back to the base environment keeps driving and camera streaming
# available if the optional environment is missing or incomplete.
set -u

APP_DIR="${1:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
BASE_PYTHON="$APP_DIR/.venv/bin/python"
VISION_PYTHON="${VISION_VENV:-}/bin/python"

if [ -n "${VISION_VENV:-}" ] && [ -x "$VISION_PYTHON" ]; then
    if "$VISION_PYTHON" -c \
        'import importlib.util; raise SystemExit(0 if all(importlib.util.find_spec(name) for name in ("flask", "cv2", "ultralytics", "ncnn")) else 1)' \
        >/dev/null 2>&1; then
        exec "$VISION_PYTHON" -m robot_server.app
    fi
    printf 'Optional vision environment is incomplete; starting the base dashboard runtime.\n' >&2
fi

exec "$BASE_PYTHON" -m robot_server.app
