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
INSTALL_MODE="fresh"
CODE_CHANGED=1
REPO_COMMIT_BEFORE=""
REPO_COMMIT_AFTER=""
SYSTEM_CHANGED=0
REPO_BACKUP=""
REPO_REPLACED=0
REPO_UPDATED=0
INSTALL_SUCCESS=0

say() { printf '\n\033[1;36m[OmniBot]\033[0m %s\n' "$*"; }
fail() { printf '\n\033[1;31m[OmniBot ERROR]\033[0m %s\n' "$*" >&2; exit 1; }

CURRENT_STEP="starting the installer"
APT_LOG=""
cleanup() {
    local status=$? failed_checkout=""
    if [ -n "$APT_LOG" ]; then
        rm -f -- "$APT_LOG"
    fi
    if [ "$status" -ne 0 ] && [ "$INSTALL_SUCCESS" != "1" ]; then
        if [ "$REPO_REPLACED" = "1" ] && [ -d "$REPO_BACKUP" ]; then
            say "Restoring the previous repository after the failed installation..."
            failed_checkout="${REPO_DIR}.failed.$$.${RANDOM}"
            if [ -e "$REPO_DIR" ]; then
                mv "$REPO_DIR" "$failed_checkout" || true
                say "The failed replacement was preserved at $failed_checkout"
            fi
            mv "$REPO_BACKUP" "$REPO_DIR" || true
        elif [ "$REPO_UPDATED" = "1" ] && [ -n "$REPO_COMMIT_BEFORE" ] && \
             [ -d "$REPO_DIR/.git" ]; then
            say "Rolling the repository back to the previously working revision..."
            git -C "$REPO_DIR" reset --hard "$REPO_COMMIT_BEFORE" || true
        fi
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
CURRENT_STEP="checking passwordless administrator access"
command sudo -n true || \
    fail "This account does not have passwordless sudo. Enable the standard Raspberry Pi OS passwordless sudo policy for this admin user, then rerun; the OmniBot installer never prompts for a password."
# Never let any later package or system command pause at an unseen password
# prompt (especially when the bootstrap is piped from curl).
sudo() { command sudo -n "$@"; }
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

all_packages_ready() {
    local package=""
    for package in \
        ca-certificates curl git avahi-daemon libnss-mdns network-manager \
        python3 python3-pygame python3-opencv python3-smbus i2c-tools \
        v4l-utils bluez; do
        package_installed "$package" || return 1
    done
    if ! package_installed python3-rpi-lgpio && ! package_installed python3-rpi.gpio; then
        return 1
    fi
    if ! package_installed nginx-light && ! package_installed nginx; then
        return 1
    fi
    if ! command -v labwc >/dev/null 2>&1 && \
       ! command -v startlxde-pi >/dev/null 2>&1; then
        return 1
    fi
    return 0
}

PACKAGES_CHANGED=0
if all_packages_ready; then
    say "All required Raspberry Pi packages are already installed; skipping apt."
else
    PACKAGES_CHANGED=1
    CURRENT_STEP="synchronizing the system clock"
    ensure_system_clock
    CURRENT_STEP="refreshing the trusted CA certificate store"
    refresh_certificate_store
    CURRENT_STEP="refreshing Raspberry Pi package information"
    say "Installing missing Raspberry Pi, pygame, GPIO, Bluetooth, and hotspot packages..."
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
    install_package python3-opencv
    install_package python3-smbus
    install_package i2c-tools
    install_package v4l-utils
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
fi

if [ "$(systemctl get-default 2>/dev/null || true)" != "graphical.target" ]; then
    sudo systemctl set-default graphical.target
    SYSTEM_CHANGED=1
else
    say "Graphical boot is already configured; skipping."
fi
if ! systemctl is-enabled --quiet lightdm.service 2>/dev/null; then
    sudo systemctl enable lightdm.service 2>/dev/null || true
    SYSTEM_CHANGED=1
else
    say "LightDM is already enabled; skipping."
fi

if command -v raspi-config >/dev/null 2>&1; then
    if raspi-config nonint get_i2c 2>/dev/null | grep -Fxq '0'; then
        say "I2C is already enabled; skipping."
    else
        sudo raspi-config nonint do_i2c 0
        SYSTEM_CHANGED=1
    fi
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
    REPO_BACKUP="$backup"
    REPO_REPLACED=1
    mv "$fresh" "$REPO_DIR"
    INSTALL_MODE="repair"
    CODE_CHANGED=1
    say "The previous repository checkout was preserved at $backup"
}

if [ -d "$REPO_DIR/.git" ]; then
    INSTALL_MODE="update"
    REPO_COMMIT_BEFORE="$(git -C "$REPO_DIR" rev-parse HEAD 2>/dev/null || true)"
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
        REPO_COMMIT_AFTER="$(git -C "$REPO_DIR" rev-parse "origin/$REPO_BRANCH")"
        if [ "$REPO_COMMIT_BEFORE" = "$REPO_COMMIT_AFTER" ]; then
            CODE_CHANGED=0
            say "OmniBot source is already current; skipping the code update."
        else
            if git -C "$REPO_DIR" diff --quiet \
                "$REPO_COMMIT_BEFORE" "$REPO_COMMIT_AFTER" -- "$APP_SUBDIR"; then
                CODE_CHANGED=0
                say "Only other CityTechClubProjects changed; OmniBot files are unchanged."
            else
                CODE_CHANGED=1
                say "A newer OmniBot revision is available; updating the code."
            fi
            REPO_UPDATED=1
            git -C "$REPO_DIR" checkout -f "$REPO_BRANCH"
            git -C "$REPO_DIR" reset --hard "$REPO_COMMIT_AFTER"
        fi
    fi
elif [ -e "$REPO_DIR" ]; then
    install_fresh_copy "A non-Git CityTechClubProjects folder was found; installing a clean copy."
else
    git clone --branch "$REPO_BRANCH" --single-branch "$REPO_URL" "$REPO_DIR"
    INSTALL_MODE="fresh"
    CODE_CHANGED=1
fi

test -f "$APP_DIR/omni_robot.py" || \
    fail "The repository checkout does not contain $APP_SUBDIR/omni_robot.py."

if [ "$CODE_CHANGED" = "1" ] || [ "$PACKAGES_CHANGED" = "1" ]; then
    CURRENT_STEP="validating the OmniBot application"
    python3 -m py_compile \
        "$APP_DIR/camera_stream.py" \
        "$APP_DIR/omni_kinematics.py" \
        "$APP_DIR/omni_robot.py" \
        "$APP_DIR/servo_hat.py" \
        "$APP_DIR/wifi_control.py"
    test -s "$APP_DIR/web/index.html"
    test -s "$APP_DIR/web/controller.js"
    test -s "$APP_DIR/web/styles.css"
    bash -n "$APP_DIR/installer/hotspot.sh"
    bash -n "$APP_DIR/installer/curl-install.sh"
    python3 -c 'import cv2; import pygame; import RPi.GPIO; import smbus; print("OpenCV, pygame, GPIO, and SMBus imports passed.")'
    PYTHONPATH="$APP_DIR" python3 -m unittest discover -s "$APP_DIR/tests" -v
else
    say "Code and dependencies are unchanged; skipping application validation."
fi

HOTSPOT_CHANGED=0
NGINX_CHANGED=0
LAUNCHER_CHANGED=0
LAST_INSTALL_CHANGED=0

install_root_file_if_changed() {
    local source="$1" destination="$2" mode="$3" current_mode=""
    LAST_INSTALL_CHANGED=0
    current_mode="$(sudo stat -c '%a' "$destination" 2>/dev/null || true)"
    if sudo test -f "$destination" && \
       sudo cmp -s -- "$source" "$destination" && \
       [ "$current_mode" = "${mode#0}" ]; then
        say "Unchanged: $destination"
        return 0
    fi
    sudo install -o root -g root -m "$mode" "$source" "$destination"
    LAST_INSTALL_CHANGED=1
    SYSTEM_CHANGED=1
    say "Updated: $destination"
}

install_user_file_if_changed() {
    local source="$1" destination="$2" mode="$3" current_mode=""
    LAST_INSTALL_CHANGED=0
    current_mode="$(stat -c '%a' "$destination" 2>/dev/null || true)"
    if [ -f "$destination" ] && cmp -s -- "$source" "$destination" && \
       [ "$current_mode" = "${mode#0}" ]; then
        say "Unchanged: $destination"
        return 0
    fi
    install -m "$mode" "$source" "$destination"
    LAST_INSTALL_CHANGED=1
    SYSTEM_CHANGED=1
    say "Updated: $destination"
}

enable_service_if_needed() {
    local service="$1"
    if systemctl is-enabled --quiet "$service" 2>/dev/null; then
        say "Service already enabled: $service"
    else
        sudo systemctl enable "$service"
        SYSTEM_CHANGED=1
    fi
}

CURRENT_STEP="configuring the private OmniBot Wi-Fi hotspot"
say "Configuring the private OmniBot Wi-Fi hotspot..."
if ! sudo test -d "$CONFIG_DIR"; then
    sudo install -d -m 0755 "$CONFIG_DIR"
    SYSTEM_CHANGED=1
fi
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
    SYSTEM_CHANGED=1
fi

ensure_config_key() {
    local key="$1" value="$2"
    if ! sudo grep -qE "^${key}=" "$CONFIG_FILE"; then
        printf '%s=%s\n' "$key" "$value" | sudo tee -a "$CONFIG_FILE" >/dev/null
        SYSTEM_CHANGED=1
        say "Added new persistent setting: $key"
    else
        say "Persistent setting already present: $key"
    fi
}
ensure_config_key HOTSPOT_SSID "OmniBot"
ensure_config_key HOTSPOT_PASSWORD "omnibot1"
ensure_config_key WIFI_INTERFACE "wlan0"
ensure_config_key HOTSPOT_ADDRESS "10.42.0.1/24"
ensure_config_key HOTSPOT_CHANNEL "6"
if [ "$(sudo stat -c '%a' "$CONFIG_FILE" 2>/dev/null || true)" != "600" ]; then
    sudo chmod 0600 "$CONFIG_FILE"
    SYSTEM_CHANGED=1
fi

install_root_file_if_changed \
    "$APP_DIR/installer/hotspot.sh" /usr/local/sbin/omnibot-hotspot 0755
if [ "$LAST_INSTALL_CHANGED" = "1" ]; then
    HOTSPOT_CHANGED=1
fi
install_root_file_if_changed \
    "$APP_DIR/installer/systemd/omnibot-hotspot.service" \
    /etc/systemd/system/omnibot-hotspot.service 0644
if [ "$LAST_INSTALL_CHANGED" = "1" ]; then
    HOTSPOT_CHANGED=1
fi

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
if sudo cmp -s -- "$HOSTS_TEMP" /etc/hosts; then
    say "Host mapping is unchanged; skipping /etc/hosts."
else
    sudo cp -a -- /etc/hosts "$HOSTS_BACKUP"
    sudo install -o root -g root -m 0644 "$HOSTS_TEMP" /etc/hosts
    SYSTEM_CHANGED=1
    say "Updated /etc/hosts; backup saved at $HOSTS_BACKUP"
fi
rm -f "$HOSTS_TEMP"
if [ "$(hostnamectl --static 2>/dev/null || hostname)" = "omnibot" ]; then
    say "Hostname is already omnibot; skipping."
else
    sudo hostnamectl set-hostname omnibot
    SYSTEM_CHANGED=1
fi

if [ "$HOTSPOT_CHANGED" = "1" ]; then
    sudo systemctl daemon-reload
fi
enable_service_if_needed NetworkManager.service
enable_service_if_needed avahi-daemon.service
enable_service_if_needed omnibot-hotspot.service

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
if ! sudo test -d /etc/nginx/sites-available || ! sudo test -d /etc/nginx/sites-enabled; then
    sudo install -d -m 0755 /etc/nginx/sites-available /etc/nginx/sites-enabled
    SYSTEM_CHANGED=1
    NGINX_CHANGED=1
fi
install_root_file_if_changed \
    "$NGINX_TEMP" /etc/nginx/sites-available/omnibot-dashboard 0644
if [ "$LAST_INSTALL_CHANGED" = "1" ]; then
    NGINX_CHANGED=1
fi
rm -f "$NGINX_TEMP"
if [ "$(sudo readlink /etc/nginx/sites-enabled/omnibot-dashboard 2>/dev/null || true)" != \
     "/etc/nginx/sites-available/omnibot-dashboard" ]; then
    sudo ln -sfn /etc/nginx/sites-available/omnibot-dashboard /etc/nginx/sites-enabled/omnibot-dashboard
    SYSTEM_CHANGED=1
    NGINX_CHANGED=1
else
    say "Nginx dashboard link is unchanged; skipping."
fi
if ! sudo "$NGINX_BIN" -t; then
    sudo rm -f /etc/nginx/sites-enabled/omnibot-dashboard
    fail "The generated dashboard proxy conflicted with the existing Nginx configuration."
fi
if sudo test -e /etc/nginx/sites-enabled/default || sudo test -L /etc/nginx/sites-enabled/default; then
    sudo rm -f /etc/nginx/sites-enabled/default
    SYSTEM_CHANGED=1
    NGINX_CHANGED=1
fi
sudo "$NGINX_BIN" -t
enable_service_if_needed nginx.service
if [ "$NGINX_CHANGED" = "1" ]; then
    sudo systemctl restart nginx.service
elif systemctl is-active --quiet nginx.service; then
    say "Nginx configuration is unchanged and running; skipping restart."
else
    sudo systemctl start nginx.service
    SYSTEM_CHANGED=1
fi

CURRENT_STEP="creating the OmniBot launcher and desktop auto-start"
say "Creating the launcher and desktop auto-start..."
RUNNER_TEMP="$(mktemp)"
cat > "$RUNNER_TEMP" <<EOF
#!/usr/bin/env bash
set -u
cd "$APP_DIR"
exec 9>"$APP_DIR/.omnibot.lock"
flock -n 9 || exit 0
printf '\n===== OmniBot startup: %s =====\n' "\$(date)" >> "$LOG_FILE"
exec python3 "$APP_DIR/omni_robot.py" >> "$LOG_FILE" 2>&1
EOF
install_user_file_if_changed "$RUNNER_TEMP" "$RUNNER" 0755
if [ "$LAST_INSTALL_CHANGED" = "1" ]; then
    LAUNCHER_CHANGED=1
fi
rm -f "$RUNNER_TEMP"

if [ ! -d "$HOME/.config/autostart" ] || [ ! -d "$HOME/.config/labwc" ]; then
    mkdir -p "$HOME/.config/autostart" "$HOME/.config/labwc"
    SYSTEM_CHANGED=1
fi
AUTOSTART_TEMP="$(mktemp)"
cat > "$AUTOSTART_TEMP" <<EOF
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
install_user_file_if_changed \
    "$AUTOSTART_TEMP" "$HOME/.config/autostart/omnibot.desktop" 0644
if [ "$LAST_INSTALL_CHANGED" = "1" ]; then
    LAUNCHER_CHANGED=1
fi
rm -f "$AUTOSTART_TEMP"

LABWC_TEMP="$(mktemp)"
python3 - "$HOME/.config/labwc/autostart" "$LABWC_TEMP" "$RUNNER" <<'PY'
from pathlib import Path
import sys

source, destination = map(Path, sys.argv[1:3])
runner = sys.argv[3]
lines = source.read_text(encoding="utf-8").splitlines() if source.exists() else []
result = []
managed = False
for line in lines:
    if line == "# OMNIBOT START":
        managed = True
        continue
    if managed:
        if line == "# OMNIBOT END":
            managed = False
        continue
    result.append(line)
while result and not result[-1].strip():
    result.pop()
if result:
    result.append("")
result.extend(("# OMNIBOT START", f"{runner} &", "# OMNIBOT END"))
destination.write_text("\n".join(result) + "\n", encoding="utf-8")
PY
install_user_file_if_changed "$LABWC_TEMP" "$HOME/.config/labwc/autostart" 0644
if [ "$LAST_INSTALL_CHANGED" = "1" ]; then
    LAUNCHER_CHANGED=1
fi
rm -f "$LABWC_TEMP"

if [ "$INSTALL_MODE" != "update" ] && command -v raspi-config >/dev/null 2>&1; then
    sudo raspi-config nonint do_boot_behaviour B4 || true
fi
if ! systemctl is-enabled --quiet bluetooth.service 2>/dev/null; then
    if sudo systemctl enable bluetooth.service 2>/dev/null; then
        SYSTEM_CHANGED=1
    fi
else
    say "Bluetooth is already enabled; skipping."
fi

if [ "$INSTALL_MODE" = "fresh" ]; then
    RESULT_LABEL="Fresh installation complete"
elif [ "$CODE_CHANGED" = "1" ]; then
    RESULT_LABEL="OmniBot update complete"
elif [ "$PACKAGES_CHANGED" = "1" ] || [ "$SYSTEM_CHANGED" = "1" ]; then
    RESULT_LABEL="OmniBot installation repaired"
else
    RESULT_LABEL="OmniBot is already current"
fi

say "$RESULT_LABEL."
echo "Install mode: $INSTALL_MODE"
echo "Code changed: $CODE_CHANGED"
echo "Packages changed: $PACKAGES_CHANGED"
echo "System configuration changed: $SYSTEM_CHANGED"
echo "Your existing Bluetooth pairing is preserved."
echo "Wi-Fi name: $(sudo sed -n 's/^HOTSPOT_SSID=//p' "$CONFIG_FILE" | tail -n 1)"
echo "Wi-Fi password: $(sudo sed -n 's/^HOTSPOT_PASSWORD=//p' "$CONFIG_FILE" | tail -n 1)"
echo "Laptop controller: http://10.42.0.1"
echo "Friendly address (when supported): http://omnibot.local"
echo "Direct fallback: http://10.42.0.1:8080"
echo "Runtime log: $LOG_FILE"
echo "The Pi will reboot automatically in 10 seconds."
sync
if command -v systemd-run >/dev/null 2>&1; then
    REBOOT_UNIT="omnibot-installer-reboot-$(date +%s)"
    sudo systemd-run \
        --unit="$REBOOT_UNIT" \
        --on-active=10s \
        --timer-property=AccuracySec=1s \
        "$(command -v systemctl)" reboot
else
    sudo shutdown -r +1 "OmniBot installation complete"
fi
INSTALL_SUCCESS=1
