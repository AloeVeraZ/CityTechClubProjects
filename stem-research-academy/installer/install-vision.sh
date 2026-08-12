#!/usr/bin/env bash
# Optional pretrained YOLO11 Nano + NCNN setup for an already-installed Pi hub.
set -Eeuo pipefail

APP_DIR="${STEM_APP_DIR:-$HOME/STEMResearchAcademy}"
VISION_ROOT="${STEM_VISION_DIR:-$HOME/.local/share/stem-research-academy/vision}"
VISION_ENV="$VISION_ROOT/.vision-venv"
MODEL_NAME="yolo11n.pt"
MODEL_DIR="$VISION_ROOT/yolo11n_ncnn_model"
IMAGE_SIZE="${VISION_IMAGE_SIZE:-320}"
CONFIG_FILE="/etc/stem-research-academy/config.env"

fail() {
    printf 'Vision installation failed: %s\n' "$*" >&2
    exit 1
}

set_config_key() {
    local key="$1" value="$2" temporary
    temporary="$(mktemp)"
    if ! sudo awk -v key="$key" -v value="$value" '
        BEGIN { replaced = 0 }
        index($0, key "=") == 1 {
            if (!replaced) print key "=" value
            replaced = 1
            next
        }
        { print }
        END { if (!replaced) print key "=" value }
    ' "$CONFIG_FILE" > "$temporary"; then
        rm -f -- "$temporary"
        return 1
    fi
    if ! sudo install -o root -g root -m 0600 "$temporary" "$CONFIG_FILE"; then
        rm -f -- "$temporary"
        return 1
    fi
    rm -f -- "$temporary"
}

if [ "$(id -u)" -eq 0 ]; then
    fail "run this as the normal Raspberry Pi user, without sudo."
fi
[ -f "$APP_DIR/run.py" ] || {
    fail "3TSahur application not found at $APP_DIR. Run the base installer first."
}
[ -f "$APP_DIR/installer/start-dashboard.sh" ] || \
    fail "the installed dashboard is too old. Rerun the base one-line installer first."
command -v sudo >/dev/null 2>&1 || fail "sudo is not installed."
sudo test -f "$CONFIG_FILE" || \
    fail "$CONFIG_FILE is missing. Rerun the base one-line installer first."
[ "$(getconf LONG_BIT)" = "64" ] || \
    fail "Ultralytics on this project requires 64-bit Raspberry Pi OS."
command -v python3 >/dev/null 2>&1 || fail "python3 is not installed."

available_kb="$(df -Pk "$HOME" | awk 'END {print $4}')"
if [ -z "$available_kb" ] || [ "$available_kb" -lt 3145728 ]; then
    df -h "$HOME" || true
    fail "at least 3 GB of free storage is required before installing the export tools."
fi

echo "Creating persistent optional vision environment..."
mkdir -p "$VISION_ROOT"
python3 -m venv --system-site-packages "$VISION_ENV"
PIP_NO_CACHE_DIR=1 "$VISION_ENV/bin/python" -m pip install --upgrade pip
PIP_NO_CACHE_DIR=1 "$VISION_ENV/bin/python" -m pip install \
    "ultralytics[export]>=8.3,<9" ncnn

echo "Downloading pretrained weights and exporting NCNN at ${IMAGE_SIZE}px..."
(
    cd "$VISION_ROOT"
    MODEL_NAME="$MODEL_NAME" IMAGE_SIZE="$IMAGE_SIZE" "$VISION_ENV/bin/python" - <<'PY'
import os
from pathlib import Path

import numpy as np
from ultralytics import YOLO

model = YOLO(os.environ["MODEL_NAME"])
image_size = int(os.environ["IMAGE_SIZE"])
exported = Path(model.export(format="ncnn", imgsz=image_size, batch=1, device="cpu"))
if not exported.is_dir():
    raise RuntimeError(f"NCNN export directory was not created: {exported}")

# Load the exported runtime and perform one offline inference. This catches an
# incomplete NCNN install before the dashboard service is changed.
ncnn_model = YOLO(str(exported))
ncnn_model(np.zeros((image_size, image_size, 3), dtype=np.uint8),
           classes=[0], conf=0.45, imgsz=image_size, verbose=False)
print(f"Vision model export and synthetic inference passed: {exported.resolve()}")
PY
)

[ -d "$MODEL_DIR" ] || fail "expected NCNN model was not found at $MODEL_DIR."

echo "Connecting the persistent vision runtime to the dashboard service..."
config_backup="$(mktemp)"
sudo cat "$CONFIG_FILE" > "$config_backup"

restore_dashboard_config() {
    sudo install -o root -g root -m 0600 "$config_backup" "$CONFIG_FILE"
    sudo systemctl restart stem-robot-dashboard.service 2>/dev/null || true
    rm -f -- "$config_backup"
}

if ! set_config_key VISION_VENV "$VISION_ENV" || \
   ! set_config_key VISION_MODEL "$MODEL_DIR"; then
    restore_dashboard_config
    fail "the persistent dashboard configuration could not be updated."
fi
if ! sudo systemctl restart stem-robot-dashboard.service; then
    restore_dashboard_config
    fail "the dashboard could not start with the vision runtime; its previous config was restored."
fi

healthy=0
for _ in $(seq 1 30); do
    if curl -fsS http://127.0.0.1:8080/healthz >/dev/null 2>&1; then
        healthy=1
        break
    fi
    sleep 1
done
if [ "$healthy" != "1" ]; then
    sudo journalctl -u stem-robot-dashboard.service -n 40 --no-pager || true
    restore_dashboard_config
    fail "the dashboard failed its health check; its previous config was restored."
fi
rm -f -- "$config_backup"

echo "Optional vision setup complete and dashboard health check passed."
echo "Open a robot tab and select Vision off (or press C) to enable detection."
