#!/usr/bin/env bash
set -euo pipefail

FVD_HOME_DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
FVD_SOURCE_DIR="$FVD_HOME_DATA/free-video-downloader/source"
FVD_LAUNCHER="$HOME/.local/bin/free-video-downloader"
FVD_DESKTOP_ENTRY="$HOME/.local/share/applications/free-video-downloader.desktop"
FVD_ICON="$HOME/.local/share/icons/hicolor/scalable/apps/free-video-downloader.svg"

if [[ "$(id -u)" -eq 0 ]]; then
    printf '%s\n' 'Run this uninstaller as the same normal user who installed the app, not with sudo.' >&2
    exit 1
fi

case "${1:-}" in
    --help|-h)
        cat <<'HELP'
Uninstall Free Video Downloader for the current user.

Usage: ./uninstall.sh [--yes]

Removes the app launcher, desktop entry, icon, and installer-managed source
checkout. Keeps download history, settings, downloaded files, and shared
system dependencies such as uv, FFmpeg, and Node.js.
HELP
        exit 0
        ;;
    --yes) ;;
    "")
        printf '%s\n' 'This removes the app launcher, desktop entry, icon, and installer-managed app files.'
        printf '%s\n' 'Your download history, settings, downloaded videos, and shared system tools will be kept.'
        read -r -p 'Continue? [y/N] ' FVD_CONFIRM
        case "$FVD_CONFIRM" in
            y|Y|yes|YES) ;;
            *) printf '%s\n' 'Uninstall canceled.'; exit 1 ;;
        esac
        ;;
    *)
        printf 'Unknown option: %s\n' "$1" >&2
        printf '%s\n' 'Usage: ./uninstall.sh [--yes]' >&2
        exit 2
        ;;
esac

rm -f -- "$FVD_LAUNCHER" "$FVD_DESKTOP_ENTRY" "$FVD_ICON"
if [[ -d "$FVD_SOURCE_DIR/.git" ]]; then
    rm -rf -- "$FVD_SOURCE_DIR"
fi

FVD_DESKTOP_DATABASE="$(command -v update-desktop-database || true)"
if [[ -n "$FVD_DESKTOP_DATABASE" && -d "$HOME/.local/share/applications" ]]; then
    "$FVD_DESKTOP_DATABASE" "$HOME/.local/share/applications" >/dev/null 2>&1 || true
fi

printf '%s\n' 'Free Video Downloader has been uninstalled for this user.'
printf 'Kept download history and settings at: %s/free-video-downloader/state.sqlite3\n' "$FVD_HOME_DATA"
