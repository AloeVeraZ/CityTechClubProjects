#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="${OMNIBOT_REPO_URL:-https://github.com/AloeVeraZ/CityTechClubProjects.git}"
REPO_BRANCH="${OMNIBOT_REPO_BRANCH:-main}"
REPO_DIR="${OMNIBOT_REPO_DIR:-$HOME/CityTechClubProjects}"
APP_SUBDIR="OmniBot"
APP_DIR="$REPO_DIR/$APP_SUBDIR"
RUNNER="$APP_DIR/run_omnibot.sh"
LOG_FILE="$APP_DIR/omnibot.log"
CONFIG_DIR="/etc/omnibot"
CONFIG_FILE="$CONFIG_DIR/config.env"

say() { printf '\n\033[1;36m[OmniBot]\033[0m %s\n' "$*"; }
fail() { printf '\n\033[1;31m[OmniBot ERROR]\033[0m %s\n' "$*" >&2; exit 1; }

CURRENT_STEP="starting the installer"
APT_LOG=""
cleanup() {
    if [ -n "$APT_LOG" ]; then
        rm -f -- "$APT_LOG"
    fi
}
trap cleanup EXIT

on_error() {
    local status="$1" line="$2" command="$3"
    trap - ERR
    printf '\n\033[1;31m[OmniBot ERROR]\033[0m %s failed (line %s, exit %s).\n' \
        "$CURRENT_STEP" "$line" "$status" >&2
    printf 'Command: %s\n' "$command" >&2
    printf 'Fix the error shown above, then rerun the same installer command.\n' >&2
    exit "$status"
}
trap 'on_error "$?" "$LINENO" "$BASH_COMMAND"' ERR

if [ "$(id -u)" -eq 0 ]; then
    fail "Run this as the normal Raspberry Pi user, without sudo."
fi
command -v sudo >/dev/null 2>&1 || fail "sudo is required."
CURRENT_STEP="requesting administrator access"
sudo -v || fail "sudo authentication failed. Run the installer as your normal Pi user."
CURRENT_STEP="repairing any interrupted package configuration"
sudo env DEBIAN_FRONTEND=noninteractive dpkg --configure -a || \
    fail "dpkg could not finish an interrupted package configuration. Resolve the error above, then rerun."
APT_LOG="$(mktemp)"

apt_log_has_certificate_error() {
    grep -Eqi \
        'certificate verification failed|certificate verify failed|certificate.*(not trusted|expired|not yet valid)|issuer certificate|certificate chain|TLS.*certificate|SSL certificate' \
        "$APT_LOG"
}

apt_log_has_missing_package_error() {
    grep -Eqi \
        'unable to locate package|has no installation candidate|but it is not installable' \
        "$APT_LOG"
}

show_apt_diagnostics() {
    printf '\n===== Last apt output =====\n' >&2
    tail -n 30 "$APT_LOG" >&2 2>/dev/null || true
    printf '===== System details =====\n' >&2
    if [ -r /etc/os-release ]; then
        grep -E '^(PRETTY_NAME|VERSION_CODENAME)=' /etc/os-release >&2 || true
    fi
    printf 'Architecture: %s\n' "$(uname -m 2>/dev/null || printf 'unknown')" >&2
    printf 'Clock: %s\n' "$(date -u 2>/dev/null || printf 'unknown')" >&2
    printf '===========================\n' >&2
}

ensure_system_clock() {
    local synchronized="" year=""
    year="$(date -u +%Y 2>/dev/null || printf '0')"

    if command -v timedatectl >/dev/null 2>&1; then
        synchronized="$(timedatectl show --property=NTPSynchronized --value 2>/dev/null || true)"
        if [ "$synchronized" != "yes" ]; then
            say "Synchronizing the Pi clock before HTTPS package downloads..."
            sudo timedatectl set-ntp true 2>/dev/null || true
            sudo systemctl restart systemd-timesyncd.service 2>/dev/null || true
            for _ in 1 2 3 4 5 6 7 8 9 10; do
                synchronized="$(timedatectl show --property=NTPSynchronized --value 2>/dev/null || true)"
                [ "$synchronized" = "yes" ] && break
                sleep 2
            done
        fi
    fi

    year="$(date -u +%Y 2>/dev/null || printf '0')"
    if [ "$year" -lt 2024 ] || [ "$year" -gt 2100 ]; then
        fail "The Pi clock is $(date -u 2>/dev/null || printf 'invalid'), so HTTPS certificates cannot be verified. Connect the Pi to a network that provides time synchronization, correct the clock, and rerun."
    fi
    say "Pi clock: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
}

refresh_certificate_store() {
    local fresh_option="${1:-}"
    local update_certs=""
    if command -v update-ca-certificates >/dev/null 2>&1; then
        update_certs="$(command -v update-ca-certificates)"
    elif [ -x /usr/sbin/update-ca-certificates ]; then
        update_certs=/usr/sbin/update-ca-certificates
    fi

    if [ -n "$update_certs" ]; then
        if [ -n "$fresh_option" ]; then
            sudo "$update_certs" "$fresh_option" || \
                fail "The local CA certificate store could not be rebuilt. Resolve the certificate error above, then rerun."
        else
            sudo "$update_certs" || \
                fail "The local CA certificate store could not be rebuilt. Resolve the certificate error above, then rerun."
        fi
    else
        say "The CA update utility is not installed yet; apt will install ca-certificates."
    fi
}

CURRENT_STEP="synchronizing the system clock"
ensure_system_clock
CURRENT_STEP="refreshing the trusted CA certificate store"
refresh_certificate_store

apt_get() {
    local attempt status=1
    for attempt in 1 2 3; do
        if sudo env DEBIAN_FRONTEND=noninteractive apt-get \
            -o DPkg::Lock::Timeout=120 \
            -o Acquire::Retries=3 \
            "$@" 2>&1 | tee "$APT_LOG"; then
            return 0
        else
            status="${PIPESTATUS[0]}"
        fi
        apt_log_has_certificate_error && return "$status"
        apt_log_has_missing_package_error && return "$status"
        if [ "$attempt" -lt 3 ]; then
            say "apt-get $* failed (attempt $attempt of 3). Retrying in five seconds..."
            sleep 5
        fi
    done
    return "$status"
}

apt_require() {
    if apt_get "$@"; then
        return 0
    fi
    if apt_log_has_certificate_error; then
        show_apt_diagnostics
        fail "apt-get $* could not verify an HTTPS certificate. The clock and CA store were repaired, so the remaining cause is usually a captive-portal Wi-Fi network, HTTPS-inspecting proxy, or invalid custom package source. Open the network login page or fix the source/proxy certificate; TLS verification was not disabled."
    fi
    show_apt_diagnostics
    fail "apt-get $* failed after three attempts. Check the Pi's internet connection, date/time, package sources, and any error printed above."
}

package_installed() {
    dpkg-query -W -f='${Status}' "$1" 2>/dev/null | grep -Fq 'install ok installed'
}

install_package() {
    local package="$1"
    if package_installed "$package"; then
        say "Package already installed: $package"
        return 0
    fi
    CURRENT_STEP="installing required package $package"
    say "Installing required package: $package"
    apt_require install -y "$package"
}

SELECTED_PACKAGE=""
install_one_of() {
    local purpose="$1"
    shift
    local package=""

    for package in "$@"; do
        if package_installed "$package"; then
            SELECTED_PACKAGE="$package"
            say "$purpose package already installed: $package"
            return 0
        fi
    done
    for package in "$@"; do
        if apt-cache show "$package" >/dev/null 2>&1; then
            CURRENT_STEP="installing $purpose package $package"
            say "Installing $purpose package: $package"
            if apt_get install -y "$package"; then
                SELECTED_PACKAGE="$package"
                return 0
            fi
            say "$package could not be installed; trying the next compatible package."
        fi
    done

    show_apt_diagnostics
    fail "No compatible $purpose package could be installed. Tried: $*."
}

CURRENT_STEP="refreshing Raspberry Pi package information"
say "Installing Raspberry Pi, pygame, GPIO, Bluetooth, and hotspot packages..."
if ! apt_get update; then
    if apt_log_has_certificate_error; then
        CURRENT_STEP="repairing the trusted CA certificate store"
        say "apt reported a certificate error. Rebuilding the CA store and retrying once..."
        refresh_certificate_store --fresh
        CURRENT_STEP="refreshing Raspberry Pi package information after CA repair"
        if ! apt_get update; then
            if apt_log_has_certificate_error; then
                fail "apt still cannot verify the package server certificate after clock synchronization and a fresh CA rebuild. Complete any Wi-Fi captive-portal login and remove any broken HTTPS proxy or custom apt source, then rerun. TLS verification was not disabled."
            fi
            say "Package index refresh still failed for a non-certificate reason. Continuing in case the required packages are installed or cached."
        fi
    else
        say "Package index refresh failed for a non-certificate reason. Continuing in case the required packages are already installed or cached."
    fi
fi

install_package ca-certificates
CURRENT_STEP="refreshing the trusted CA certificate store after package validation"
refresh_certificate_store
install_package curl
install_package git
install_package avahi-daemon
install_package libnss-mdns
install_package python3
install_package python3-pygame
install_package python3-smbus
install_package i2c-tools
install_package bluez

install_one_of "Raspberry Pi GPIO" python3-rpi-lgpio python3-rpi.gpio
GPIO_PACKAGE="$SELECTED_PACKAGE"
install_one_of "Nginx" nginx-light nginx
NGINX_PACKAGE="$SELECTED_PACKAGE"

# Install NetworkManager last because changing network managers can briefly
# interrupt the active connection on older Raspberry Pi OS images.
install_package network-manager

if ! command -v labwc >/dev/null 2>&1 && \
   ! command -v startlxde-pi >/dev/null 2>&1; then
    say "No graphical desktop detected. Installing the Raspberry Pi desktop..."
    if apt-cache show rpd-wayland-core >/dev/null 2>&1; then
        CURRENT_STEP="installing the Raspberry Pi Wayland desktop"
        apt_require install -y rpd-wayland-core rpd-theme rpd-preferences lightdm
    elif apt-cache show raspberrypi-ui-mods >/dev/null 2>&1; then
        CURRENT_STEP="installing the Raspberry Pi desktop"
        apt_require install -y raspberrypi-ui-mods lightdm
    else
        fail "Desktop packages were not found. Flash Raspberry Pi OS with Desktop and rerun."
    fi
fi

sudo systemctl set-default graphical.target
sudo systemctl enable lightdm 2>/dev/null || true

if command -v raspi-config >/dev/null 2>&1; then
    sudo raspi-config nonint do_i2c 0
fi

CURRENT_STEP="downloading the CityTechClubProjects repository"
say "Downloading OmniBot..."
install_fresh_copy() {
    local reason="$1"
    local stamp="$(date +%Y%m%d-%H%M%S).$$"
    local backup="${REPO_DIR}.backup.${stamp}"
    local fresh="${REPO_DIR}.installing.${stamp}"
    say "$reason"
    git clone --branch "$REPO_BRANCH" --single-branch "$REPO_URL" "$fresh"
    test -f "$fresh/$APP_SUBDIR/omni_robot.py" || \
        fail "The selected repository branch does not contain $APP_SUBDIR/omni_robot.py."
    mv "$REPO_DIR" "$backup"
    mv "$fresh" "$REPO_DIR"
    say "The previous repository checkout was preserved at $backup"
}

if [ -d "$REPO_DIR/.git" ]; then
    checkout_valid=true
    changes=""
    if changes="$(git -C "$REPO_DIR" status --porcelain --untracked-files=all)"; then
        changes="$(printf '%s\n' "$changes" | grep -vFx "?? $APP_SUBDIR/run_omnibot.sh" | grep -vFx "?? $APP_SUBDIR/omnibot.log" || true)"
    else
        checkout_valid=false
    fi

    if [ "$checkout_valid" != true ]; then
        install_fresh_copy "The existing Git checkout is damaged; installing a clean copy."
    elif ! git -C "$REPO_DIR" fetch --prune origin "$REPO_BRANCH"; then
        install_fresh_copy "The existing checkout could not be updated; installing a clean copy."
    elif [ -n "$changes" ]; then
        install_fresh_copy "Local changes were found; installing a clean copy."
    elif ! git -C "$REPO_DIR" show-ref --verify --quiet "refs/heads/$REPO_BRANCH"; then
        install_fresh_copy "The existing checkout has no $REPO_BRANCH branch; installing a clean copy."
    elif ! git -C "$REPO_DIR" merge-base --is-ancestor "$REPO_BRANCH" "origin/$REPO_BRANCH"; then
        install_fresh_copy "Local commits were found; installing a clean copy."
    else
        git -C "$REPO_DIR" checkout -f "$REPO_BRANCH"
        git -C "$REPO_DIR" reset --hard "origin/$REPO_BRANCH"
    fi
elif [ -e "$REPO_DIR" ]; then
    install_fresh_copy "A non-Git CityTechClubProjects folder was found; installing a clean copy."
else
    git clone --branch "$REPO_BRANCH" --single-branch "$REPO_URL" "$REPO_DIR"
fi

test -f "$APP_DIR/omni_robot.py" || \
    fail "The repository checkout does not contain $APP_SUBDIR/omni_robot.py."

CURRENT_STEP="validating the OmniBot application"
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

CURRENT_STEP="configuring the private OmniBot Wi-Fi hotspot"
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

CURRENT_STEP="configuring the OmniBot dashboard proxy"
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

CURRENT_STEP="creating the OmniBot launcher and desktop auto-start"
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
