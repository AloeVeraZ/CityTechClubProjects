#!/usr/bin/env bash
# One-command bootstrap for a trusted Raspberry Pi OS installation.
# It downloads the versioned installer, which then performs the validated,
# atomic application installation. Do not run this as root.
set -Eeuo pipefail

REPO_URL="${STEM_REPO_URL:-https://github.com/AloeVeraZ/CityTechClubProjects.git}"
REPO_BRANCH="${STEM_REPO_BRANCH:-main}"
SOURCE_SUBDIR="${STEM_SOURCE_SUBDIR:-stem-research-academy}"
RAW_REPO="${REPO_URL#https://github.com/}"
RAW_REPO="${RAW_REPO%.git}"
SOURCE_PREFIX="${SOURCE_SUBDIR#/}"
SOURCE_PREFIX="${SOURCE_PREFIX%/}"
if [ -n "$SOURCE_PREFIX" ] && [ "$SOURCE_PREFIX" != "." ]; then
    SOURCE_PREFIX="${SOURCE_PREFIX}/"
else
    SOURCE_PREFIX=""
fi
INSTALLER_URL="https://raw.githubusercontent.com/${RAW_REPO}/${REPO_BRANCH}/${SOURCE_PREFIX}installer/install.sh"
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

echo "Downloading 3TSahur installer from ${REPO_BRANCH}..."
curl --fail --location --retry 3 --retry-delay 2 --silent --show-error \
    "$INSTALLER_URL" -o "$TEMP_INSTALLER"
STEM_REPO_URL="$REPO_URL" STEM_REPO_BRANCH="$REPO_BRANCH" STEM_SOURCE_SUBDIR="$SOURCE_SUBDIR" \
    bash "$TEMP_INSTALLER"
