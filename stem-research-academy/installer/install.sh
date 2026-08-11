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
AUTOSTART_DIR="$HOME/.config/autostart"
LABWC_DIR="$HOME/.config/labwc"
KIOSK_URL="http://127.0.0.1:8080"

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
if [ "${STEM_SKIP_OS_UPGRADE:-0}" != "1" ]; then
    # Keep the complete Pi OS image current, including kernel, firmware,
    # Chromium, NetworkManager, and desktop compatibility packages.
    apt_get full-upgrade -y
fi
apt_get install -y \
    avahi-daemon \
    ca-certificates \
    curl \
    git \
    libnss-mdns \
    network-manager \
    python3 \
    python3-flask \
    python3-opencv \
    python3-pip \
    python3-venv \
    util-linux \
    v4l-utils

# Package and command names differ between Raspberry Pi OS generations.
if apt-cache show chromium >/dev/null 2>&1; then
    apt_get install -y chromium
elif apt-cache show chromium-browser >/dev/null 2>&1; then
    apt_get install -y chromium-browser
else
    fail "A Chromium package was not found for this Raspberry Pi OS image."
fi

# A Pi flashed with Raspberry Pi OS Lite needs a desktop for the local kiosk.
if ! command -v labwc >/dev/null 2>&1 && \
   ! command -v startlxde-pi >/dev/null 2>&1; then
    say "No graphical desktop was found; installing the Raspberry Pi desktop..."
    if apt-cache show rpd-wayland-core >/dev/null 2>&1; then
        apt_get install -y rpd-wayland-core rpd-theme rpd-preferences lightdm
    elif apt-cache show raspberrypi-ui-mods >/dev/null 2>&1; then
        apt_get install -y raspberrypi-ui-mods lightdm
    else
        fail "Raspberry Pi desktop packages were not found. Use a current Raspberry Pi OS image."
    fi
fi

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
python3 -m compileall -q "$FRESH_SOURCE/robot_server" "$FRESH_SOURCE/run.py"

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

say "Migrating persistent robot, hotspot, and kiosk configuration..."
sudo install -d -m 0755 "$CONFIG_DIR"
if ! sudo test -f "$CONFIG_FILE"; then
    CONFIG_TEMP="$(mktemp)"
    cat > "$CONFIG_TEMP" <<'EOF'
# This file survives application upgrades. Edit it, then reboot or restart services.
HOTSPOT_SSID=EchoSwarm
HOTSPOT_PASSWORD=roboswarm1
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
KIOSK_URL=http://127.0.0.1:8080
SCOUT_A_HOST=echo-scout-a.local
SCOUT_B_HOST=echo-scout-b.local
EOF
    sudo install -m 0600 "$CONFIG_TEMP" "$CONFIG_FILE"
    rm -f "$CONFIG_TEMP"
fi

# Add keys introduced by later installer versions without discarding camera,
# ESP32, or custom hardware settings from an earlier installation.
ensure_config_key() {
    local key="$1" value="$2"
    if ! sudo grep -qE "^${key}=" "$CONFIG_FILE"; then
        printf '%s=%s\n' "$key" "$value" | sudo tee -a "$CONFIG_FILE" >/dev/null
    fi
}

ensure_config_key KIOSK_URL "$KIOSK_URL"
ensure_config_key HOTSPOT_SSID "EchoSwarm"
ensure_config_key HOTSPOT_PASSWORD "roboswarm1"
ensure_config_key WIFI_INTERFACE "wlan0"
ensure_config_key HOTSPOT_ADDRESS "10.42.0.1/24"
ensure_config_key HOTSPOT_CHANNEL "6"
ensure_config_key PORT "8080"
ensure_config_key CAMERA_DEVICE "/dev/video0"
ensure_config_key CAMERA_WIDTH "1280"
ensure_config_key CAMERA_HEIGHT "720"
ensure_config_key CAMERA_FPS "20"
ensure_config_key DRIVE_WATCHDOG_SECONDS "0.4"
ensure_config_key ESP32_ONE_STREAM_URL ""
ensure_config_key ESP32_TWO_STREAM_URL ""
ensure_config_key SCOUT_A_HOST "echo-scout-a.local"
ensure_config_key SCOUT_B_HOST "echo-scout-b.local"

# Hotspot credentials are installer-managed so firmware and Pi stay in sync.
sudo sed -i -E \
    -e 's/^HOTSPOT_SSID=.*/HOTSPOT_SSID=EchoSwarm/' \
    -e 's/^HOTSPOT_PASSWORD=.*/HOTSPOT_PASSWORD=roboswarm1/' \
    "$CONFIG_FILE"
sudo chmod 0600 "$CONFIG_FILE"
sudo hostnamectl set-hostname echoswarm

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
sudo systemctl enable avahi-daemon.service
sudo systemctl set-default graphical.target
sudo systemctl enable lightdm.service 2>/dev/null || true
sudo systemctl daemon-reload
sudo systemctl enable stem-robot-hotspot.service stem-robot-dashboard.service

say "Configuring the attached screen as a fullscreen robot dashboard..."
chmod +x "$APP_DIR/installer/kiosk.sh"
mkdir -p "$AUTOSTART_DIR" "$LABWC_DIR"

cat > "$AUTOSTART_DIR/stem-robot-kiosk.desktop" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=Triple T Robot Dashboard
Comment=Fullscreen STEM Research Academy robot controls
Exec=$APP_DIR/installer/kiosk.sh
Path=$APP_DIR
Terminal=false
StartupNotify=false
X-GNOME-Autostart-enabled=true
EOF

# Current Pi OS uses labwc; older releases use the XDG desktop entry above.
touch "$LABWC_DIR/autostart"
sed -i '/# STEM ROBOT KIOSK START/,/# STEM ROBOT KIOSK END/d' "$LABWC_DIR/autostart"
cat >> "$LABWC_DIR/autostart" <<EOF
# STEM ROBOT KIOSK START
$APP_DIR/installer/kiosk.sh &
# STEM ROBOT KIOSK END
EOF

if command -v raspi-config >/dev/null 2>&1; then
    sudo raspi-config nonint do_boot_behaviour B4 || true
    sudo raspi-config nonint do_blanking 1 || true
fi

# Keep the dashboard visible across old X11 and current Wayland Pi desktops.
sudo install -d -m 0755 /etc/systemd/logind.conf.d
sudo tee /etc/systemd/logind.conf.d/90-stem-robot.conf >/dev/null <<'EOF'
[Login]
IdleAction=ignore
EOF

if [ -d /etc/lightdm ] || command -v lightdm >/dev/null 2>&1; then
    sudo install -d -m 0755 /etc/lightdm/lightdm.conf.d
    sudo tee /etc/lightdm/lightdm.conf.d/90-stem-robot.conf >/dev/null <<'EOF'
[Seat:*]
xserver-command=X -s 0 -dpms
EOF
fi

sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target 2>/dev/null || true

CMDLINE_FILE="/boot/firmware/cmdline.txt"
[ -f "$CMDLINE_FILE" ] || CMDLINE_FILE="/boot/cmdline.txt"
if [ -f "$CMDLINE_FILE" ]; then
    if grep -qE '(^| )consoleblank=[^ ]+' "$CMDLINE_FILE"; then
        sudo sed -i -E 's/(^| )consoleblank=[^ ]+/ consoleblank=0/g; s/^ //' "$CMDLINE_FILE"
    else
        sudo sed -i 's/$/ consoleblank=0/' "$CMDLINE_FILE"
    fi
fi

say "Validating the server before enabling it..."
"$VENV_DIR/bin/python" -m compileall -q "$APP_DIR/robot_server" "$APP_DIR/run.py"
"$VENV_DIR/bin/python" -c 'import flask; import cv2; print("Flask and OpenCV imports passed.")'
sudo systemctl restart stem-robot-dashboard.service

say "Installation complete."
echo "Pi name: echoswarm"
echo "Hotspot name: EchoSwarm"
echo "Hotspot password: roboswarm1"
echo "Dashboard: http://10.42.0.1:8080"
echo "The hotspot starts at boot and can accept both ESP32 robots."
echo "The attached Pi screen opens the same dashboard automatically in fullscreen mode."
echo "The Pi will reboot automatically in 10 seconds."

# A transient systemd timer survives this piped installer process exiting.
# This is more reliable than sleeping inside `curl | bash` and then rebooting.
sync
if command -v systemd-run >/dev/null 2>&1; then
    REBOOT_UNIT="stem-robot-installer-reboot-$(date +%s)"
    sudo systemd-run \
        --unit="$REBOOT_UNIT" \
        --on-active=10s \
        --timer-property=AccuracySec=1s \
        "$(command -v systemctl)" reboot
else
    sudo shutdown -r +1 "STEM robot installation complete"
fi
