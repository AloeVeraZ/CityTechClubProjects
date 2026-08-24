#!/usr/bin/env bash
# One-command bootstrap for a trusted Raspberry Pi OS installation.
set -Eeuo pipefail

REPO_BRANCH="${OMNIBOT_REPO_BRANCH:-main}"
INSTALLER_URL="https://raw.githubusercontent.com/AloeVeraZ/OmniBot/${REPO_BRANCH}/installer/install.sh"
TEMP_INSTALLER="$(mktemp)"

cleanup() { rm -f -- "$TEMP_INSTALLER"; }
trap cleanup EXIT

if [ "$(id -u)" -eq 0 ]; then
    echo "Run this as the normal Raspberry Pi user, without sudo." >&2
    exit 1
fi
command -v curl >/dev/null 2>&1 || {
    echo "curl is required. Install curl, then rerun this command." >&2
    exit 1
}

echo "Downloading OmniBot installer from ${REPO_BRANCH}..."
curl --fail --location --retry 3 --retry-delay 2 --silent --show-error \
    "$INSTALLER_URL" -o "$TEMP_INSTALLER"
OMNIBOT_REPO_BRANCH="$REPO_BRANCH" bash "$TEMP_INSTALLER"
