#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="https://github.com/AloeVeraZ/OmniBot.git"
REPO_BRANCH="${OMNIBOT_REPO_BRANCH:-main}"
APP_DIR="${OMNIBOT_APP_DIR:-$HOME/OmniBot}"
RUNNER="$APP_DIR/run_omnibot.sh"
LOG_FILE="$APP_DIR/omnibot.log"
CONFIG_DIR="/etc/omnibot"
CONFIG_FILE="$CONFIG_DIR/config.env"

say() { printf '\n\033[1;36m[OmniBot]\033[0m %s\n' "$*"; }
fail() { printf '\n\033[1;31m[OmniBot ERROR]\033[0m %s\n' "$*" >&2; exit 1; }
trap 'fail "Installation stopped on line $LINENO. Fix the error above and rerun the installer."' ERR

if [ "$(id -u)" -eq 0 ]; then
    fail "Run this as the normal Raspberry Pi user, without sudo."
fi
command -v sudo >/dev/null 2>&1 || fail "sudo is required."

apt_get() {
    sudo env DEBIAN_FRONTEND=noninteractive apt-get -o DPkg::Lock::Timeout=120 "$@"
}

say "Installing Raspberry Pi, pygame, GPIO, Bluetooth, and hotspot packages..."
apt_get update

GPIO_PACKAGE="python3-rpi.gpio"
if apt-cache show python3-rpi-lgpio >/dev/null 2>&1; then
    GPIO_PACKAGE="python3-rpi-lgpio"
fi

apt_get install -y \
    ca-certificates \
    curl \
    git \
    avahi-daemon \
    libnss-mdns \
    network-manager \
    nginx-light \
    python3 \
    python3-pygame \
    python3-smbus \
    i2c-tools \
    "$GPIO_PACKAGE" \
    bluez

if ! command -v labwc >/dev/null 2>&1 && \
   ! command -v startlxde-pi >/dev/null 2>&1; then
    say "No graphical desktop detected. Installing the Raspberry Pi desktop..."
    if apt-cache show rpd-wayland-core >/dev/null 2>&1; then
        apt_get install -y rpd-wayland-core rpd-theme rpd-preferences lightdm
    elif apt-cache show raspberrypi-ui-mods >/dev/null 2>&1; then
        apt_get install -y raspberrypi-ui-mods lightdm
    else
        fail "Desktop packages were not found. Flash Raspberry Pi OS with Desktop and rerun."
    fi
fi

sudo systemctl set-default graphical.target
sudo systemctl enable lightdm 2>/dev/null || true

if command -v raspi-config >/dev/null 2>&1; then
    sudo raspi-config nonint do_i2c 0
fi

say "Downloading OmniBot..."
install_fresh_copy() {
    local reason="$1"
    local stamp="$(date +%Y%m%d-%H%M%S).$$"
    local backup="${APP_DIR}.backup.${stamp}"
    local fresh="${APP_DIR}.installing.${stamp}"
    say "$reason"
    git clone --branch "$REPO_BRANCH" --single-branch "$REPO_URL" "$fresh"
    mv "$APP_DIR" "$backup"
    mv "$fresh" "$APP_DIR"
    say "The previous folder was preserved at $backup"
}

if [ -d "$APP_DIR/.git" ]; then
    checkout_valid=true
    changes=""
    if changes="$(git -C "$APP_DIR" status --porcelain --untracked-files=all)"; then
        changes="$(printf '%s\n' "$changes" | grep -vFx '?? run_omnibot.sh' | grep -vFx '?? omnibot.log' || true)"
    else
        checkout_valid=false
    fi

    if [ "$checkout_valid" != true ]; then
        install_fresh_copy "The existing Git checkout is damaged; installing a clean copy."
    elif ! git -C "$APP_DIR" fetch --prune origin "$REPO_BRANCH"; then
        install_fresh_copy "The existing checkout could not be updated; installing a clean copy."
    elif [ -n "$changes" ]; then
        install_fresh_copy "Local changes were found; installing a clean copy."
    elif ! git -C "$APP_DIR" show-ref --verify --quiet "refs/heads/$REPO_BRANCH"; then
        install_fresh_copy "The existing checkout has no $REPO_BRANCH branch; installing a clean copy."
    elif ! git -C "$APP_DIR" merge-base --is-ancestor "$REPO_BRANCH" "origin/$REPO_BRANCH"; then
        install_fresh_copy "Local commits were found; installing a clean copy."
    else
        git -C "$APP_DIR" checkout -f "$REPO_BRANCH"
        git -C "$APP_DIR" reset --hard "origin/$REPO_BRANCH"
    fi
elif [ -e "$APP_DIR" ]; then
    install_fresh_copy "A non-Git OmniBot folder was found; installing a clean copy."
else
    git clone --branch "$REPO_BRANCH" --single-branch "$REPO_URL" "$APP_DIR"
fi

python3 -m py_compile \
    "$APP_DIR/omni_kinematics.py" \
    "$APP_DIR/omni_robot.py" \
    "$APP_DIR/servo_hat.py" \
    "$APP_DIR/wifi_control.py"
test -s "$APP_DIR/web/index.html"
test -s "$APP_DIR/web/controller.js"
test -s "$APP_DIR/web/styles.css"
bash -n "$APP_DIR/installer/hotspot.sh"
bash -n "$APP_DIR/installer/curl-install.sh"
python3 -c 'import pygame; import RPi.GPIO; import smbus; print("pygame, GPIO, and SMBus imports passed.")'
PYTHONPATH="$APP_DIR" python3 -m unittest discover -s "$APP_DIR/tests" -v

say "Configuring the private OmniBot Wi-Fi hotspot..."
sudo install -d -m 0755 "$CONFIG_DIR"
if ! sudo test -f "$CONFIG_FILE"; then
    CONFIG_TEMP="$(mktemp)"
    cat > "$CONFIG_TEMP" <<'EOF'
# This root-owned file survives application upgrades. Edit it, then reboot.
HOTSPOT_SSID=OmniBot
HOTSPOT_PASSWORD=omnibot1
WIFI_INTERFACE=wlan0
HOTSPOT_ADDRESS=10.42.0.1/24
HOTSPOT_CHANNEL=6
EOF
    sudo install -o root -g root -m 0600 "$CONFIG_TEMP" "$CONFIG_FILE"
    rm -f "$CONFIG_TEMP"
fi

ensure_config_key() {
    local key="$1" value="$2"
    if ! sudo grep -qE "^${key}=" "$CONFIG_FILE"; then
        printf '%s=%s\n' "$key" "$value" | sudo tee -a "$CONFIG_FILE" >/dev/null
    fi
}
ensure_config_key HOTSPOT_SSID "OmniBot"
ensure_config_key HOTSPOT_PASSWORD "omnibot1"
ensure_config_key WIFI_INTERFACE "wlan0"
ensure_config_key HOTSPOT_ADDRESS "10.42.0.1/24"
ensure_config_key HOTSPOT_CHANNEL "6"
sudo chmod 0600 "$CONFIG_FILE"

sudo install -m 0755 "$APP_DIR/installer/hotspot.sh" /usr/local/sbin/omnibot-hotspot
sudo install -m 0644 \
    "$APP_DIR/installer/systemd/omnibot-hotspot.service" \
    /etc/systemd/system/omnibot-hotspot.service

# Use a stable local name while preserving unrelated /etc/hosts aliases.
HOSTS_TEMP="$(mktemp)"
HOSTS_BACKUP="/etc/hosts.before-omnibot-$(date +%Y%m%d-%H%M%S)"
python3 - /etc/hosts "$HOSTS_TEMP" <<'PY'
from pathlib import Path
import sys

source, destination = map(Path, sys.argv[1:])
lines = source.read_text(encoding="utf-8").splitlines() if source.exists() else []
result = []
replaced = False
for line in lines:
    fields = line.split()
    if fields and fields[0] == "127.0.1.1":
        if not replaced:
            result.append("127.0.1.1\tomnibot")
            replaced = True
        continue
    result.append(line)
if not any(line.split()[:1] == ["127.0.0.1"] for line in result):
    result.insert(0, "127.0.0.1\tlocalhost")
if not replaced:
    result.append("127.0.1.1\tomnibot")
destination.write_text("\n".join(result) + "\n", encoding="utf-8")
PY
sudo cp -a -- /etc/hosts "$HOSTS_BACKUP"
sudo install -o root -g root -m 0644 "$HOSTS_TEMP" /etc/hosts
rm -f "$HOSTS_TEMP"
sudo hostnamectl set-hostname omnibot

sudo systemctl daemon-reload
sudo systemctl enable NetworkManager.service
sudo systemctl enable avahi-daemon.service
sudo systemctl enable omnibot-hotspot.service

say "Adding the friendly http://10.42.0.1 dashboard address..."
NGINX_TEMP="$(mktemp)"
NGINX_TEST_CONFIG="$(mktemp)"
NGINX_BIN="$(command -v nginx 2>/dev/null || true)"
if [ -z "$NGINX_BIN" ] && [ -x /usr/sbin/nginx ]; then
    NGINX_BIN=/usr/sbin/nginx
fi
[ -n "$NGINX_BIN" ] && [ -x "$NGINX_BIN" ] || \
    fail "Nginx was installed but its executable was not found."
cat > "$NGINX_TEMP" <<'EOF'
server {
    listen 80;
    server_name 10.42.0.1 omnibot.local localhost _;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_buffering off;
        proxy_read_timeout 1h;
    }
}
EOF
cat > "$NGINX_TEST_CONFIG" <<EOF
pid /tmp/omnibot-nginx-test.pid;
error_log stderr;
events {}
http {
    include /etc/nginx/mime.types;
    include $NGINX_TEMP;
}
EOF
if ! sudo "$NGINX_BIN" -t -c "$NGINX_TEST_CONFIG"; then
    rm -f "$NGINX_TEMP" "$NGINX_TEST_CONFIG"
    fail "The generated dashboard proxy is not compatible with this Nginx installation."
fi
rm -f "$NGINX_TEST_CONFIG"
sudo install -d -m 0755 /etc/nginx/sites-available /etc/nginx/sites-enabled
sudo install -m 0644 "$NGINX_TEMP" /etc/nginx/sites-available/omnibot-dashboard
rm -f "$NGINX_TEMP"
sudo ln -sfn /etc/nginx/sites-available/omnibot-dashboard /etc/nginx/sites-enabled/omnibot-dashboard
if ! sudo "$NGINX_BIN" -t; then
    sudo rm -f /etc/nginx/sites-enabled/omnibot-dashboard
    fail "The generated dashboard proxy conflicted with the existing Nginx configuration."
fi
sudo rm -f /etc/nginx/sites-enabled/default
sudo "$NGINX_BIN" -t
sudo systemctl enable nginx.service
sudo systemctl restart nginx.service

say "Creating the launcher and desktop auto-start..."
cat > "$RUNNER" <<EOF
#!/usr/bin/env bash
set -u
cd "$APP_DIR"
exec 9>"$APP_DIR/.omnibot.lock"
flock -n 9 || exit 0
printf '\n===== OmniBot startup: %s =====\n' "\$(date)" >> "$LOG_FILE"
exec python3 "$APP_DIR/omni_robot.py" >> "$LOG_FILE" 2>&1
EOF
chmod +x "$RUNNER"

mkdir -p "$HOME/.config/autostart" "$HOME/.config/labwc"
cat > "$HOME/.config/autostart/omnibot.desktop" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=OmniBot
Comment=Three-wheel omni robot controller
Exec=$RUNNER
Path=$APP_DIR
Terminal=false
StartupNotify=false
X-GNOME-Autostart-enabled=true
EOF

touch "$HOME/.config/labwc/autostart"
sed -i '/# OMNIBOT START/,/# OMNIBOT END/d' "$HOME/.config/labwc/autostart"
cat >> "$HOME/.config/labwc/autostart" <<EOF
# OMNIBOT START
$RUNNER &
# OMNIBOT END
EOF

if command -v raspi-config >/dev/null 2>&1; then
    sudo raspi-config nonint do_boot_behaviour B4 || true
fi
sudo systemctl enable bluetooth 2>/dev/null || true

say "Installation complete. The Pi will reboot in five seconds."
echo "Your existing Bluetooth pairing is preserved."
echo "Wi-Fi name: $(sudo sed -n 's/^HOTSPOT_SSID=//p' "$CONFIG_FILE" | tail -n 1)"
echo "Wi-Fi password: $(sudo sed -n 's/^HOTSPOT_PASSWORD=//p' "$CONFIG_FILE" | tail -n 1)"
echo "Laptop controller: http://10.42.0.1"
echo "Friendly address (when supported): http://omnibot.local"
echo "Direct fallback: http://10.42.0.1:8080"
echo "Runtime log: $LOG_FILE"
sync
sleep 5
sudo reboot
