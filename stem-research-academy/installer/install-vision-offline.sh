#!/usr/bin/env bash
# Install the bundled OpenCV YOLOv4-tiny model without any network connection.
set -Eeuo pipefail

APP_DIR="${STEM_APP_DIR:-$HOME/STEMResearchAcademy}"
CONFIG_FILE="/etc/stem-research-academy/config.env"
MODEL_ROOT="${STEM_VISION_DIR:-$APP_DIR/vision_models}"
BUNDLE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_CONFIG="$BUNDLE_DIR/yolov4-tiny.cfg"
SOURCE_WEIGHTS="$BUNDLE_DIR/yolov4-tiny.weights"
TEST_IMAGE="$BUNDLE_DIR/person-test.jpg"
MODEL_CONFIG="$MODEL_ROOT/yolov4-tiny.cfg"
MODEL_WEIGHTS="$MODEL_ROOT/yolov4-tiny.weights"
MODEL_CONFIG_SHA256="f858e3724962eedf3ac44e3b6cb3f0c3d9ed067c306bb831f539c578b924c90e"
MODEL_WEIGHTS_SHA256="cf9fbfd0f6d4869b35762f56100f50ed05268084078805f0e7989efe5bb8ca87"
TEST_IMAGE_SHA256="3f0bdad67d01aa452929683b74a124a2926b6bce534c85f3ee0f00e20eeacab0"

fail() { printf 'Offline vision installation failed: %s\n' "$*" >&2; exit 1; }

set_config_key() {
    local key="$1" value="$2" temporary
    temporary="$(mktemp)"
    sudo awk -v key="$key" -v value="$value" '
        BEGIN { replaced = 0 }
        index($0, key "=") == 1 {
            if (!replaced) print key "=" value
            replaced = 1
            next
        }
        { print }
        END { if (!replaced) print key "=" value }
    ' "$CONFIG_FILE" > "$temporary"
    sudo install -o root -g root -m 0600 "$temporary" "$CONFIG_FILE"
    rm -f -- "$temporary"
}

[ "$(id -u)" -ne 0 ] || fail "run this as the normal Pi user, without sudo."
[ -x "$APP_DIR/.venv/bin/python" ] || fail "dashboard runtime not found at $APP_DIR."
sudo test -f "$CONFIG_FILE" || fail "$CONFIG_FILE is missing."
for file in "$SOURCE_CONFIG" "$SOURCE_WEIGHTS" "$TEST_IMAGE"; do
    [ -f "$file" ] || fail "bundle file is missing: $file"
done
printf '%s  %s\n' "$MODEL_CONFIG_SHA256" "$SOURCE_CONFIG" | sha256sum --check --status || fail "model config checksum failed."
printf '%s  %s\n' "$MODEL_WEIGHTS_SHA256" "$SOURCE_WEIGHTS" | sha256sum --check --status || fail "model weights checksum failed."
printf '%s  %s\n' "$TEST_IMAGE_SHA256" "$TEST_IMAGE" | sha256sum --check --status || fail "test image checksum failed."

mkdir -p "$MODEL_ROOT"
install -m 0644 "$SOURCE_CONFIG" "$MODEL_CONFIG"
install -m 0644 "$SOURCE_WEIGHTS" "$MODEL_WEIGHTS"

VISION_MODEL_CONFIG="$MODEL_CONFIG" VISION_MODEL_WEIGHTS="$MODEL_WEIGHTS" VISION_TEST_IMAGE="$TEST_IMAGE" \
    "$APP_DIR/.venv/bin/python" - <<'PY'
import os
import cv2

network = cv2.dnn.readNetFromDarknet(os.environ["VISION_MODEL_CONFIG"], os.environ["VISION_MODEL_WEIGHTS"])
network.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
network.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
model = cv2.dnn_DetectionModel(network)
model.setInputParams(size=(320, 320), scale=1 / 255.0, swapRB=True)
frame = cv2.imread(os.environ["VISION_TEST_IMAGE"])
class_ids, confidences, _ = model.detect(frame, confThreshold=0.20, nmsThreshold=0.40)
if not any(int(class_id) == 0 for class_id in class_ids):
    raise RuntimeError("model loaded but did not detect the test person")
print("Model verification passed.")
PY

set_config_key VISION_MODEL_CONFIG "$MODEL_CONFIG"
set_config_key VISION_MODEL_WEIGHTS "$MODEL_WEIGHTS"
set_config_key VISION_AUTO_ENABLE "1"
set_config_key VISION_CLASSES ""
set_config_key VISION_CONFIDENCE "0.20"
set_config_key VISION_IMAGE_SIZE "320"
set_config_key VISION_INTERVAL_SECONDS "0.50"
set_config_key VISION_OBJECT_MOTION_GATE "0"
set_config_key VISION_CPU_THREADS "2"
set_config_key VISION_MAX_DETECTIONS "15"

sudo systemctl restart stem-robot-dashboard.service
sleep 3
curl --fail --silent --show-error http://127.0.0.1:8080/healthz >/dev/null || fail "dashboard did not become healthy."
printf 'Offline detection installed and enabled. Reload the dashboard; boxes start automatically.\n'
