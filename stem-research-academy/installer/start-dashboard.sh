#!/usr/bin/env bash
# Start the base dashboard runtime. Optional recognition uses OpenCV DNN from
# this same environment, so there is no fragile secondary Python installation.
set -u

APP_DIR="${1:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
BASE_PYTHON="$APP_DIR/.venv/bin/python"
VISION_CPU_THREADS="${VISION_CPU_THREADS:-2}"

export OMP_NUM_THREADS="$VISION_CPU_THREADS"
export OPENBLAS_NUM_THREADS="$VISION_CPU_THREADS"
export MKL_NUM_THREADS="$VISION_CPU_THREADS"
export NUMEXPR_NUM_THREADS="$VISION_CPU_THREADS"
exec "$BASE_PYTHON" -m robot_server.app
