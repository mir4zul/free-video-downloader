#!/bin/sh
set -eu
APP_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
command -v uv >/dev/null 2>&1 || { printf '%s\n' 'Install uv first: https://docs.astral.sh/uv/getting-started/installation/'; exit 1; }
command -v python3 >/dev/null 2>&1 || { printf '%s\n' 'Python 3 is required.'; exit 1; }
command -v ffmpeg >/dev/null 2>&1 || { printf '%s\n' 'Install ffmpeg first (Arch: sudo pacman -S ffmpeg; Ubuntu: sudo apt install ffmpeg).'; exit 1; }
command -v ffprobe >/dev/null 2>&1 || { printf '%s\n' 'ffprobe is missing; install the FFmpeg package.'; exit 1; }
mkdir -p "$HOME/.local/bin" "$HOME/.local/share/applications"
uv sync --locked --project "$APP_ROOT"
python3 "$APP_ROOT/scripts/install_user.py" "$APP_ROOT"
printf '%s\n' 'Free Video Downloader installed for this user.' 'Launch it from the desktop app menu or run: ~/.local/bin/free-video-downloader'
