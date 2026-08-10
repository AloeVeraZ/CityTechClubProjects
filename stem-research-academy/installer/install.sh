#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="${STEM_REPO_URL:-https://github.com/AloeVeraZ/CityTechClubProjects.git}"
REPO_BRANCH="${STEM_REPO_BRANCH:-main}"
SOURCE_SUBDIR="stem-research-academy"
APP_DIR="${STEM_APP_DIR:-$HOME/STEMResearchAcademy}"
VENV_DIR="$APP_DIR/.venv"
CONFIG_DIR="/etc/stem-research-academy"
CONFIG_FILE="$CONFIG_DIR/config.env"
APP_USER="$(id -un)"
TEMP_CHECKOUT=""

say() { printf '\n\033[1;36m[STEM Robot Lab]\033[0m %s\n' "$*"; }
fail() { printf '\n\033[1;31m[INSTALL ERROR]\033[0m %s\n' "$*" >&2; exit 1; }

cleanup() {
    if [ -n "$TEMP_CHECKOUT" ] && [ -d "$TEMP_CHECKOUT" ]; then
        rm -rf -- "$TEMP_CHECKOUT"
    fi
}

trap cleanup EXIT
trap 'fail "Installation stopped on line $LINENO. Fix the error above and rerun the same command."' ERR

apt_get() {
    local attempt=1 output
    output="$(mktemp)"
    while true; do
        if sudo env DEBIAN_FRONTEND=noninteractive apt-get -o DPkg::Lock::Timeout=60 "$@" 2>&1 | tee "$output"; then
            rm -f "$output"
            return 0
        fi
        if ! grep -Eq 'Could not get lock|Unable to (acquire|lock)|is another process using it' "$output"; then
            rm -f "$output"
            return 1
        fi
        if [ "$attempt" -ge 20 ]; then
            rm -f "$output"
            fail "APT stayed busy. Wait for Raspberry Pi OS updates to finish, then rerun the installer."
        fi
        say "APT is busy; retrying in 15 seconds ($attempt/20)..."
        sleep 15
        attempt=$((attempt + 1))
        : > "$output"
    done
}

if [ "$(id -u)" -eq 0 ]; then
    fail "Run this as the normal Raspberry Pi user, without sudo."
fi
command -v sudo >/dev/null 2>&1 || fail "sudo is required."

say "Installing current Raspberry Pi OS packages..."
apt_get update
apt_get install -y \
    ca-certificates \
    curl \
    git \
    network-manager \
    python3 \
    python3-flask \
    python3-opencv \
    python3-pip \
    python3-venv \
    v4l-utils

if apt-cache show python3-rpi-lgpio >/dev/null 2>&1; then
    apt_get install -y python3-rpi-lgpio
else
    apt_get install -y python3-rpi.gpio
fi

say "Downloading a clean copy of the latest project..."
TEMP_CHECKOUT="$(mktemp -d)"
git clone --depth 1 --branch "$REPO_BRANCH" --single-branch "$REPO_URL" "$TEMP_CHECKOUT/repository"
FRESH_SOURCE="$TEMP_CHECKOUT/repository/$SOURCE_SUBDIR"
[ -f "$FRESH_SOURCE/run.py" ] || fail "$SOURCE_SUBDIR was not found in the downloaded repository."

sudo systemctl stop stem-robot-dashboard.service 2>/dev/null || true

if [ -e "$APP_DIR" ]; then
    BACKUP_DIR="${APP_DIR}.backup.$(date +%Y%m%d-%H%M%S).$$"
    say "Preserving the previous installation at $BACKUP_DIR"
    mv "$APP_DIR" "$BACKUP_DIR"
fi

mkdir -p "$APP_DIR"
cp -a "$FRESH_SOURCE/." "$APP_DIR/"

say "Rebuilding the isolated Python environment..."
python3 -m venv --system-site-packages "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel
"$VENV_DIR/bin/python" -m pip install --upgrade -r "$APP_DIR/requirements.txt"

say "Creating persistent robot and hotspot configuration..."
sudo install -d -m 0755 "$CONFIG_DIR"
if ! sudo test -f "$CONFIG_FILE"; then
    CONFIG_TEMP="$(mktemp)"
    cat > "$CONFIG_TEMP" <<'EOF'
# This file survives application upgrades. Edit it, then reboot or restart services.
HOTSPOT_SSID=STEM-Robot-Lab
HOTSPOT_PASSWORD=STEMRobotics
WIFI_INTERFACE=wlan0
HOTSPOT_ADDRESS=10.42.0.1/24
HOTSPOT_CHANNEL=6
PORT=8080
CAMERA_DEVICE=/dev/video0
CAMERA_WIDTH=1280
CAMERA_HEIGHT=720
CAMERA_FPS=20
DRIVE_WATCHDOG_SECONDS=0.4
ESP32_ONE_STREAM_URL=
ESP32_TWO_STREAM_URL=
EOF
    sudo install -m 0600 "$CONFIG_TEMP" "$CONFIG_FILE"
    rm -f "$CONFIG_TEMP"
fi

say "Installing the hotspot and dashboard services..."
sudo install -m 0755 "$APP_DIR/installer/hotspot.sh" /usr/local/sbin/stem-robot-hotspot

SERVICE_TEMP="$(mktemp)"
sed -e "s|@APP_USER@|$APP_USER|g" -e "s|@APP_DIR@|$APP_DIR|g" \
    "$APP_DIR/installer/systemd/stem-robot-dashboard.service" > "$SERVICE_TEMP"
sudo install -m 0644 "$SERVICE_TEMP" /etc/systemd/system/stem-robot-dashboard.service
rm -f "$SERVICE_TEMP"
sudo install -m 0644 \
    "$APP_DIR/installer/systemd/stem-robot-hotspot.service" \
    /etc/systemd/system/stem-robot-hotspot.service

getent group gpio >/dev/null && sudo usermod -aG gpio "$APP_USER" || true
getent group video >/dev/null && sudo usermod -aG video "$APP_USER" || true
sudo systemctl enable NetworkManager.service
sudo systemctl daemon-reload
sudo systemctl enable stem-robot-hotspot.service stem-robot-dashboard.service

say "Validating the server before enabling it..."
"$VENV_DIR/bin/python" -m compileall -q "$APP_DIR/robot_server" "$APP_DIR/run.py"
"$VENV_DIR/bin/python" -c 'import flask; import cv2; print("Flask and OpenCV imports passed.")'
sudo systemctl restart stem-robot-dashboard.service

say "Installation complete."
echo "Hotspot name: STEM-Robot-Lab (change it in $CONFIG_FILE if needed)"
echo "Dashboard: http://10.42.0.1:8080"
echo "The hotspot starts at boot and can accept both ESP32 robots."
echo "The Pi will reboot in 10 seconds so group and network changes take effect."
echo "Set STEM_NO_REBOOT=1 before running the installer to skip the automatic reboot."

if [ "${STEM_NO_REBOOT:-0}" = "1" ]; then
    say "Automatic reboot skipped. Run: sudo reboot"
else
    sync
    sleep 10
    sudo reboot
fi
