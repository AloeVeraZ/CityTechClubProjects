#!/usr/bin/env bash
# Install 3TSahur on MotionModule.
#
# 1. Installs pigpio (ramp servo timing) and the camera packages.
# 2. Removes the original 3TSahur server, hotspot service and kiosk.
# 3. Keeps GPIO18 free for ramp servo 2 and names the hotspot 3TSahur-Swarm.
# 4. Installs the 3TSahur robot project as MotionModule's active robot.
# 5. Installs MotionModule itself, which tests the release, starts the
#    dashboard and reboots.
#
# After this, everything is done in the browser: drive, deploy robot code
# (Code page) and update MotionModule (Update card). Run this script again to
# update the 3TSahur robot folder from GitHub; --robot-only skips MotionModule.
#
# Run as the normal Pi user, not as root.
set -Eeuo pipefail

REPO_URL="${STEM_REPO_URL:-https://github.com/AloeVeraZ/CityTechClubProjects.git}"
REPO_BRANCH="${STEM_REPO_BRANCH:-main}"
SOURCE_SUBDIR="${STEM_SOURCE_SUBDIR:-stem-research-academy}"
MOTIONMODULE_REF="${STEM_MOTIONMODULE_VERSION:-main}"
MOTIONMODULE_RAW="https://raw.githubusercontent.com/AloeVeraZ/MotionModule"
ROBOT_NAME="3TSahur"
ROBOT_HOSTNAME="3tsahur"
HOTSPOT_SSID="3TSahur-Swarm"
HOTSPOT_PASSWORD="roboswarm1"
PROJECT_DIR="${MOTIONMODULE_PROJECT_DIR:-$HOME/MotionModule}"
ROBOT_DIR="$PROJECT_DIR/robots"
TARGET_DIR="$ROBOT_DIR/$ROBOT_NAME"
IMU_OVERLAY='dtoverlay=i2c-gpio,i2c_gpio_sda=17,i2c_gpio_scl=18'
ROBOT_ONLY=false
MOTIONMODULE_ARGS=()

while [ "$#" -gt 0 ]; do
    case "$1" in
        --robot-only) ROBOT_ONLY=true; shift ;;
        --no-reboot) MOTIONMODULE_ARGS+=(--no-reboot); shift ;;
        --motionmodule-version) MOTIONMODULE_REF="$2"; shift 2 ;;
        *) printf '[3TSahur ERROR] Unknown option: %s\n' "$1" >&2; exit 2 ;;
    esac
done

say() { printf '\n\033[1;36m[3TSahur]\033[0m %s\n' "$*"; }
fail() { printf '\n\033[1;31m[3TSahur ERROR]\033[0m %s\n' "$*" >&2; exit 1; }
trap 'fail "Installation stopped on line $LINENO: $BASH_COMMAND. Fix the error above and rerun the same command."' ERR

[ "$(id -u)" -ne 0 ] || fail "Run this as the normal Raspberry Pi user, without sudo."
command -v sudo >/dev/null 2>&1 || fail "sudo is required."

TEMP_DIR="$(mktemp -d)"
cleanup() { sudo rm -rf -- "$TEMP_DIR" 2>/dev/null || rm -rf -- "$TEMP_DIR"; }
trap cleanup EXIT

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
        [ "$attempt" -lt 20 ] || fail "APT stayed busy. Wait for Raspberry Pi OS updates to finish, then rerun the installer."
        say "APT is busy; retrying in 15 seconds ($attempt/20)..."
        sleep 15
        attempt=$((attempt + 1))
        : > "$output"
    done
}

apt_has_candidate() {
    apt-cache policy "$1" 2>/dev/null | awk '
        $1 == "Candidate:" && $2 != "(none)" { found = 1 }
        END { exit(found ? 0 : 1) }
    '
}

install_pigpio() {
    if command -v pigpiod >/dev/null 2>&1 && python3 -c 'import pigpio' >/dev/null 2>&1; then
        say "pigpio is already installed."
        return 0
    fi
    if apt_has_candidate pigpio && apt_has_candidate python3-pigpio; then
        say "Installing pigpio from the Raspberry Pi OS package repository..."
        apt_get install -y pigpio python3-pigpio
    else
        say "pigpio has no APT candidate; building official pigpio v79..."
        apt_get install -y build-essential python3-setuptools
        local build="$TEMP_DIR/pigpio"
        mkdir -p "$build"
        curl --fail --location --retry 3 --retry-delay 2 \
            https://github.com/joan2937/pigpio/archive/refs/tags/v79.tar.gz \
            --output "$build/pigpio-v79.tar.gz"
        tar -xzf "$build/pigpio-v79.tar.gz" -C "$build"
        make -C "$build/pigpio-79" -j"$(nproc)"
        sudo make -C "$build/pigpio-79" install
    fi
    command -v pigpiod >/dev/null 2>&1 || fail "pigpiod was not installed."
    python3 -c 'import pigpio' >/dev/null 2>&1 || fail "The pigpio Python module is unavailable after installation."
}

# ---- 1. The 3TSahur robot project ------------------------------------------
script_dir=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
    script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
fi
ROBOT_SOURCE=""
if [ -n "$script_dir" ] && [ -f "$script_dir/../robot/$ROBOT_NAME/robot.py" ]; then
    ROBOT_SOURCE="$(cd -- "$script_dir/../robot/$ROBOT_NAME" && pwd)"
    say "Using the $ROBOT_NAME robot project from this checkout: $ROBOT_SOURCE"
fi

if [ "$ROBOT_ONLY" != true ]; then
    say "Installing download, camera and servo-timing packages..."
    apt_get update
    apt_get install -y ca-certificates curl git python3 python3-opencv v4l-utils
    install_pigpio
fi
command -v python3 >/dev/null 2>&1 || fail "python3 is required."

if [ -z "$ROBOT_SOURCE" ]; then
    say "Downloading the $ROBOT_NAME robot project from $REPO_BRANCH..."
    ROBOT_PREFIX="${SOURCE_SUBDIR#/}"
    ROBOT_PREFIX="${ROBOT_PREFIX%/}"
    [ -n "$ROBOT_PREFIX" ] && [ "$ROBOT_PREFIX" != "." ] && ROBOT_PREFIX="$ROBOT_PREFIX/" || ROBOT_PREFIX=""
    ROBOT_PREFIX="${ROBOT_PREFIX}robot/$ROBOT_NAME"
    REPO_PATH="${REPO_URL#https://github.com/}"
    REPO_PATH="${REPO_PATH%.git}"
    if ! python3 - "$REPO_PATH" "$REPO_BRANCH" "$ROBOT_PREFIX" "$TEMP_DIR/robot" <<'PY'
import json
import pathlib
import sys
import time
import urllib.parse
import urllib.request

repo, branch, prefix, destination = sys.argv[1:]
headers = {"User-Agent": "3TSahur-Installer"}


def download(url, attempts=5):
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
                return response.read()
        except Exception:
            if attempt + 1 == attempts:
                raise
            time.sleep(2)


ref = urllib.parse.quote(branch, safe="")
tree = json.loads(download(f"https://api.github.com/repos/{repo}/git/trees/{ref}?recursive=1"))
if tree.get("truncated"):
    raise RuntimeError("GitHub returned a truncated repository tree")
files = [
    entry["path"] for entry in tree.get("tree", [])
    if entry.get("type") == "blob" and entry["path"].startswith(prefix + "/")
]
if not files:
    raise RuntimeError(f"{prefix} was not found in {repo}@{branch}")
root = pathlib.Path(destination).resolve()
for path in files:
    target = (root / path[len(prefix) + 1:]).resolve()
    if root not in target.parents:
        raise RuntimeError(f"Unsafe repository path: {path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(download(
        f"https://raw.githubusercontent.com/{repo}/{ref}/{urllib.parse.quote(path, safe='/')}"
    ))
print(f"Downloaded {len(files)} robot project files.")
PY
    then
        say "GitHub API download failed; trying a sparse Git clone..."
        rm -rf -- "$TEMP_DIR/robot" "$TEMP_DIR/git"
        git -c http.version=HTTP/1.1 clone --depth 1 --filter=blob:none --no-checkout \
            --branch "$REPO_BRANCH" --single-branch "$REPO_URL" "$TEMP_DIR/git"
        git -C "$TEMP_DIR/git" sparse-checkout set --no-cone "/$ROBOT_PREFIX/"
        git -C "$TEMP_DIR/git" checkout "$REPO_BRANCH"
        cp -a "$TEMP_DIR/git/$ROBOT_PREFIX" "$TEMP_DIR/robot"
    fi
    ROBOT_SOURCE="$TEMP_DIR/robot"
fi

for required in robot.py hardware.py mixer.py ramp.py dashboard.py test.py; do
    [ -f "$ROBOT_SOURCE/$required" ] || fail "The $ROBOT_NAME robot project is missing $required."
done
python3 - "$ROBOT_SOURCE" <<'PY'
import pathlib
import sys

for path in sorted(pathlib.Path(sys.argv[1]).glob("*.py")):
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
print("Robot project Python files compiled.")
PY

install_robot_project() {
    mkdir -p "$ROBOT_DIR" "$PROJECT_DIR/backups"
    if [ -d "$TARGET_DIR" ]; then
        if diff -rq --exclude='__pycache__' --exclude='.*' "$ROBOT_SOURCE" "$TARGET_DIR" >/dev/null 2>&1; then
            say "The $ROBOT_NAME robot project is already up to date."
        else
            local backup="$PROJECT_DIR/backups/$ROBOT_NAME-$(date +%Y%m%d-%H%M%S)"
            cp -a "$TARGET_DIR" "$backup"
            say "Kept the previous $ROBOT_NAME folder as $backup."
        fi
    fi
    local staged="$ROBOT_DIR/.$ROBOT_NAME.installing.$$"
    rm -rf -- "$staged"
    cp -a "$ROBOT_SOURCE" "$staged"
    find "$staged" -name '__pycache__' -prune -exec rm -rf -- {} +
    rm -rf -- "$TARGET_DIR"
    mv "$staged" "$TARGET_DIR"

    local active="$PROJECT_DIR/active"
    if [ -e "$active" ] && [ ! -L "$active" ]; then
        fail "$active must be a symlink; rename that file or folder and rerun the installer."
    fi
    ln -s "$TARGET_DIR" "$PROJECT_DIR/active.new.$$"
    mv -Tf "$PROJECT_DIR/active.new.$$" "$active"
    say "Installed $TARGET_DIR as the active MotionModule robot."
}

if [ "$ROBOT_ONLY" = true ]; then
    [ -f /etc/systemd/system/motionmodule.service ] || fail "MotionModule is not installed yet. Run without --robot-only first."
    install_robot_project
    sudo systemctl restart motionmodule.service
    say "Restarted MotionModule on the updated $ROBOT_NAME project."
    exit 0
fi

# ---- 2. Retire the original 3TSahur server ---------------------------------
say "Removing the original 3TSahur dashboard, hotspot service and kiosk..."
for unit in stem-robot-dashboard.service stem-robot-hotspot.service; do
    if [ -f "/etc/systemd/system/$unit" ]; then
        sudo systemctl disable --now "$unit" >/dev/null 2>&1 || true
        sudo rm -f -- "/etc/systemd/system/$unit"
        say "Removed $unit."
    fi
done
sudo rm -f -- /usr/local/sbin/stem-robot-hotspot
if command -v nmcli >/dev/null 2>&1 && nmcli -t -f NAME connection show 2>/dev/null | grep -Fxq stem-robot-hotspot; then
    # MotionModule manages Wi-Fi now: saved network first, hotspot as fallback.
    if nmcli -t -f NAME connection show --active 2>/dev/null | grep -Fxq stem-robot-hotspot; then
        # This SSH session may be running over it, so it stays up until the
        # reboot at the end and simply never starts again. The next run of
        # this installer deletes the profile.
        sudo nmcli connection modify stem-robot-hotspot connection.autoconnect no
        say "The old always-on hotspot stays up until the reboot, then MotionModule manages Wi-Fi."
    else
        sudo nmcli connection delete stem-robot-hotspot >/dev/null || true
        say "Removed the old always-on stem-robot-hotspot connection."
    fi
fi
sudo rm -f -- /etc/nginx/sites-enabled/3tsahur-dashboard /etc/nginx/sites-available/3tsahur-dashboard
rm -f -- "$HOME/.config/autostart/stem-robot-kiosk.desktop"
if [ -f "$HOME/.config/labwc/autostart" ]; then
    sed -i '/# STEM ROBOT KIOSK START/,/# STEM ROBOT KIOSK END/d' "$HOME/.config/labwc/autostart"
fi
for old in "$HOME/STEMResearchAcademy" "$HOME/STEMResearchAcademy.previous"; do
    if [ -d "$old" ] && [ -f "$old/run.py" ]; then
        rm -rf -- "$old"
        say "Removed the original application folder $old."
    fi
done
sudo rm -rf -- /etc/stem-research-academy

# ---- 3. pigpio, GPIO18 and the hotspot name --------------------------------
say "Enabling pigpiod for the ramp servos..."
PIGPIOD_BIN="$(command -v pigpiod)"
SERVICE_TEMP="$TEMP_DIR/pigpiod.service"
cat > "$SERVICE_TEMP" <<EOF
[Unit]
Description=DMA-timed GPIO daemon for the 3TSahur ramp servos
After=local-fs.target
Before=motionmodule.service

[Service]
Type=forking
PIDFile=/run/pigpio.pid
# -l: accept pigpio commands from this Pi only, never from the hotspot.
ExecStart=$PIGPIOD_BIN -l
ExecStop=/bin/kill -TERM \$MAINPID
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF
sudo install -m 0644 "$SERVICE_TEMP" /etc/systemd/system/pigpiod.service
sudo systemctl daemon-reload
sudo systemctl enable pigpiod.service
sudo systemctl restart pigpiod.service

# MotionModule enables a software I2C bus for its reference IMU on GPIO17/18.
# GPIO18 is 3TSahur's ramp servo 2 and the robot has no IMU, so keep that
# overlay line inside a [none] section: the Pi firmware ignores it, and
# MotionModule's installer finds the line and does not add it again on updates.
BOOT_CONFIG=/boot/firmware/config.txt
[ -f "$BOOT_CONFIG" ] || BOOT_CONFIG=/boot/config.txt
[ -f "$BOOT_CONFIG" ] || fail "Raspberry Pi boot config was not found."
BOOT_TEMP="$TEMP_DIR/config.txt"
boot_status=0
python3 - "$BOOT_CONFIG" "$BOOT_TEMP" "$IMU_OVERLAY" <<'PY' || boot_status=$?
import sys
from pathlib import Path

source, destination, overlay = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
lines = Path(source).read_text(encoding="utf-8").splitlines()
marker = "# 3TSahur: GPIO18 drives ramp servo 2, so the MotionModule IMU bus stays off."
section, parked, kept = "[all]", False, []
for line in lines:
    stripped = line.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        section = stripped.lower()
    if stripped == overlay:
        if section == "[none]" and not parked:
            parked = True
            kept.append(line)
        continue  # an active copy would take GPIO18 from the ramp
    kept.append(line)
if parked:
    if kept == lines:
        sys.exit(3)  # already parked; nothing to change
else:
    while kept and not kept[-1].strip():
        kept.pop()
    kept += ["", marker, "[none]", overlay, "[all]"]
destination.write_text("\n".join(kept) + "\n", encoding="utf-8")
PY
case "$boot_status" in
    0)
        sudo cp -a -- "$BOOT_CONFIG" "$BOOT_CONFIG.before-3tsahur-$(date +%Y%m%d-%H%M%S)"
        sudo tee "$BOOT_CONFIG" < "$BOOT_TEMP" >/dev/null
        say "Kept GPIO18 free for ramp servo 2 (MotionModule's IMU bus overlay is parked under [none])."
        ;;
    3) say "GPIO18 is already kept free for ramp servo 2." ;;
    *) fail "Could not update $BOOT_CONFIG to keep GPIO18 free for the ramp." ;;
esac

say "Naming the fallback hotspot $HOTSPOT_SSID..."
sudo python3 - "$HOTSPOT_SSID" "$HOTSPOT_PASSWORD" <<'PY'
import json
import os
import sys
from pathlib import Path

ssid, password = sys.argv[1:]
path = Path("/etc/motionmodule/network.json")
try:
    config = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        config = {}
except (OSError, ValueError):
    config = {}
# Keep a name someone chose in the dashboard; replace only MotionModule's defaults.
if config.get("hotspot_ssid") in (None, "", "MotionModule"):
    config["hotspot_ssid"] = ssid
if config.get("hotspot_password") in (None, "", "motionrobot"):
    config["hotspot_password"] = password
path.parent.mkdir(parents=True, exist_ok=True)
temporary = path.with_name(f"{path.name}.tmp.{os.getpid()}")
temporary.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
os.chmod(temporary, 0o600)
os.replace(temporary, path)
PY

for group in gpio video; do
    getent group "$group" >/dev/null && sudo usermod -aG "$group" "$USER" || true
done

# ---- 4. The robot project, then MotionModule -------------------------------
install_robot_project

say "Installing MotionModule ($MOTIONMODULE_REF). It tests itself, starts the dashboard and reboots."
curl --fail --location --retry 3 --retry-delay 2 --silent --show-error \
    "$MOTIONMODULE_RAW/$MOTIONMODULE_REF/install.sh" -o "$TEMP_DIR/motionmodule-install.sh"
trap - ERR
bash "$TEMP_DIR/motionmodule-install.sh" --version "$MOTIONMODULE_REF" --hostname "$ROBOT_HOSTNAME" \
    "${MOTIONMODULE_ARGS[@]}"
