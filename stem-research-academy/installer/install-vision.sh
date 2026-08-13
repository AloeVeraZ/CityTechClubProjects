#!/usr/bin/env bash
# Install compact, fully-offline YOLOv4-tiny COCO detection for the Pi dashboard.
set -Eeuo pipefail

APP_DIR="${STEM_APP_DIR:-$HOME/STEMResearchAcademy}"
MODEL_ROOT="${STEM_VISION_DIR:-$HOME/.local/share/stem-research-academy/vision}"
MODEL_CONFIG="$MODEL_ROOT/yolov4-tiny.cfg"
MODEL_WEIGHTS="$MODEL_ROOT/yolov4-tiny.weights"
CONFIG_FILE="/etc/stem-research-academy/config.env"
MODEL_CONFIG_URL="https://raw.githubusercontent.com/hank-ai/darknet/v2.0/cfg/yolov4-tiny.cfg"
MODEL_WEIGHTS_URL="https://github.com/hank-ai/darknet/releases/download/v2.0/yolov4-tiny.weights"
TEST_IMAGE_URL="https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/images/000001.jpg"
MODEL_CONFIG_SHA256="f858e3724962eedf3ac44e3b6cb3f0c3d9ed067c306bb831f539c578b924c90e"
MODEL_WEIGHTS_SHA256="cf9fbfd0f6d4869b35762f56100f50ed05268084078805f0e7989efe5bb8ca87"
TEST_IMAGE_SHA256="3f0bdad67d01aa452929683b74a124a2926b6bce534c85f3ee0f00e20eeacab0"
MAX_MODEL_BYTES=30000000

fail() {
    printf 'Offline vision installation failed: %s\n' "$*" >&2
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
[ -f "$APP_DIR/run.py" ] || fail "3TSahur application not found at $APP_DIR. Run the base installer first."
command -v sudo >/dev/null 2>&1 || fail "sudo is not installed."
command -v curl >/dev/null 2>&1 || fail "curl is not installed."
sudo test -f "$CONFIG_FILE" || fail "$CONFIG_FILE is missing. Rerun the base installer first."
"$APP_DIR/.venv/bin/python" -c 'import cv2; assert hasattr(cv2, "dnn")' || \
    fail "OpenCV DNN is unavailable. Rerun the base installer first."

mkdir -p "$MODEL_ROOT"
temporary_config="$(mktemp)"
temporary_weights="$(mktemp)"
temporary_test_image="$(mktemp)"
config_backup="$(mktemp)"
cleanup() { rm -f -- "$temporary_config" "$temporary_weights" "$temporary_test_image" "$config_backup"; }
trap cleanup EXIT

echo "Downloading compact YOLOv4-tiny COCO weights (one-time connection only)..."
curl --fail --location --retry 3 --retry-delay 2 --silent --show-error \
    "$MODEL_CONFIG_URL" -o "$temporary_config"
curl --fail --location --retry 3 --retry-delay 2 --silent --show-error \
    "$MODEL_WEIGHTS_URL" -o "$temporary_weights"
curl --fail --location --retry 3 --retry-delay 2 --silent --show-error \
    "$TEST_IMAGE_URL" -o "$temporary_test_image"

printf '%s  %s\n' "$MODEL_CONFIG_SHA256" "$temporary_config" | sha256sum --check --status || \
    fail "model definition checksum did not match."
printf '%s  %s\n' "$MODEL_WEIGHTS_SHA256" "$temporary_weights" | sha256sum --check --status || \
    fail "model weights checksum did not match."
printf '%s  %s\n' "$TEST_IMAGE_SHA256" "$temporary_test_image" | sha256sum --check --status || \
    fail "detector test-image checksum did not match."

config_bytes="$(wc -c < "$temporary_config")"
weights_bytes="$(wc -c < "$temporary_weights")"
[ "$config_bytes" -gt 3000 ] || fail "downloaded model definition is incomplete."
[ "$weights_bytes" -gt 10000000 ] || fail "downloaded model weights are incomplete."
[ "$weights_bytes" -lt "$MAX_MODEL_BYTES" ] || fail "model exceeds the 30 MB deployment limit."
install -m 0644 "$temporary_config" "$MODEL_CONFIG"
install -m 0644 "$temporary_weights" "$MODEL_WEIGHTS"

echo "Loading the model and proving real person detection with the dashboard runtime..."
VISION_MODEL_CONFIG="$MODEL_CONFIG" VISION_MODEL_WEIGHTS="$MODEL_WEIGHTS" \
VISION_TEST_IMAGE="$temporary_test_image" \
    "$APP_DIR/.venv/bin/python" - <<'PY'
import os
import cv2

net = cv2.dnn.readNetFromDarknet(
    os.environ["VISION_MODEL_CONFIG"],
    os.environ["VISION_MODEL_WEIGHTS"],
)
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
model = cv2.dnn_DetectionModel(net)
model.setInputParams(size=(320, 320), scale=1 / 255.0, swapRB=True)
frame = cv2.imread(os.environ["VISION_TEST_IMAGE"])
if frame is None:
    raise RuntimeError("detector test image could not be decoded")
class_ids, confidences, _ = model.detect(frame, confThreshold=0.20, nmsThreshold=0.40)
people = [float(confidence) for class_id, confidence in zip(class_ids, confidences) if int(class_id) == 0]
if not people:
    raise RuntimeError("model loaded but failed its real person-detection check")
print(f"Offline YOLOv4-tiny person-detection check passed ({people[0]:.1%}).")
PY

sudo cat "$CONFIG_FILE" > "$config_backup"
restore_dashboard_config() {
    sudo install -o root -g root -m 0600 "$config_backup" "$CONFIG_FILE"
    sudo systemctl restart stem-robot-dashboard.service 2>/dev/null || true
}

if ! set_config_key VISION_MODEL_CONFIG "$MODEL_CONFIG" || \
   ! set_config_key VISION_MODEL_WEIGHTS "$MODEL_WEIGHTS" || \
   ! set_config_key VISION_AUTO_ENABLE "1" || \
   ! set_config_key VISION_CLASSES "" || \
   ! set_config_key VISION_CONFIDENCE "0.20" || \
   ! set_config_key VISION_IMAGE_SIZE "320" || \
   ! set_config_key VISION_INTERVAL_SECONDS "0.50" || \
   ! set_config_key VISION_OBJECT_MOTION_GATE "0" || \
   ! set_config_key VISION_CPU_THREADS "2" || \
   ! set_config_key VISION_MAX_DETECTIONS "15"; then
    restore_dashboard_config
    fail "the persistent dashboard configuration could not be updated."
fi
if ! sudo systemctl restart stem-robot-dashboard.service; then
    restore_dashboard_config
    fail "the dashboard could not start with the offline detector."
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

echo "Offline 80-class object detection installed. Model size: $((weights_bytes / 1024 / 1024)) MB."
echo "Internet is no longer required. Press C in the dashboard to draw object boxes."
