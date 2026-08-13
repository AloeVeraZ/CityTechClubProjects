#!/usr/bin/env bash
# Start the 3TSahur dashboard runtime.
set -u

APP_DIR="${1:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
BASE_PYTHON="$APP_DIR/.venv/bin/python"
exec "$BASE_PYTHON" -m robot_server.app
