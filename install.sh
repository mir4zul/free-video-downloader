#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_URL="https://github.com/mir4zul/free-video-downloader.git"
FVD_DATA_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/free-video-downloader"
FVD_SOURCE_DIR="$FVD_DATA_ROOT/source"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<'HELP'
Install Free Video Downloader for the current Linux user.

Usage: ./install.sh

On Arch Linux or Ubuntu, this installer can install missing system tools
after asking for confirmation. It then downloads the app, prepares Python
dependencies, and adds a launcher to the desktop app menu.
HELP
    exit 0
fi

if [[ "$(id -u)" -eq 0 ]]; then
    printf '%s\n' 'Run this installer as your normal user, not with sudo.' >&2
    exit 1
fi

if [[ ! -r /etc/os-release ]]; then
    printf '%s\n' 'Cannot identify this Linux distribution (/etc/os-release is missing).' >&2
    exit 1
fi
# shellcheck disable=SC1091
. /etc/os-release

case "${ID:-} ${ID_LIKE:-}" in
    *arch*) FVD_PACKAGE_MANAGER=arch ;;
    *ubuntu*|*debian*) FVD_PACKAGE_MANAGER=ubuntu ;;
    *)
        printf 'Unsupported distribution: %s. This installer supports Arch Linux and Ubuntu.\n' "${PRETTY_NAME:-unknown}" >&2
        exit 1
        ;;
esac

FVD_MISSING=()
command -v git >/dev/null 2>&1 || FVD_MISSING+=(git)
command -v curl >/dev/null 2>&1 || FVD_MISSING+=(curl)
command -v python3 >/dev/null 2>&1 || FVD_MISSING+=(python3)
command -v ffmpeg >/dev/null 2>&1 || FVD_MISSING+=(ffmpeg)
command -v ffprobe >/dev/null 2>&1 || FVD_MISSING+=(ffprobe)
if ! command -v deno >/dev/null 2>&1 && ! command -v node >/dev/null 2>&1; then
    FVD_MISSING+=(nodejs)
fi

if ((${#FVD_MISSING[@]})); then
    printf 'The following system tools are missing: %s\n' "${FVD_MISSING[*]}"
    printf '%s\n' 'They will be installed using the system package manager.'
    read -r -p 'Continue? [y/N] ' FVD_CONFIRM
    case "$FVD_CONFIRM" in
        y|Y|yes|YES) ;;
        *) printf '%s\n' 'Installation canceled.'; exit 1 ;;
    esac

    if ! command -v sudo >/dev/null 2>&1; then
        printf '%s\n' 'sudo is required to install system packages.' >&2
        exit 1
    fi
    if [[ "$FVD_PACKAGE_MANAGER" == arch ]]; then
        sudo pacman -S --needed --noconfirm git curl python ffmpeg nodejs
    else
        sudo apt-get update
        sudo apt-get install -y git curl python3 ffmpeg nodejs
    fi
fi

export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
    printf '%s\n' 'Installing uv in your user account...'
    FVD_UV_INSTALLER="$(mktemp)"
    trap 'rm -f "$FVD_UV_INSTALLER"' EXIT
    curl --fail --silent --show-error --location https://astral.sh/uv/install.sh --output "$FVD_UV_INSTALLER"
    sh "$FVD_UV_INSTALLER"
    rm -f "$FVD_UV_INSTALLER"
    trap - EXIT
fi

mkdir -p "$FVD_DATA_ROOT"
if [[ -d "$FVD_SOURCE_DIR/.git" ]]; then
    printf 'Using the existing checkout at %s\n' "$FVD_SOURCE_DIR"
elif [[ -e "$FVD_SOURCE_DIR" ]]; then
    printf 'Cannot install: %s exists and is not a Git checkout.\n' "$FVD_SOURCE_DIR" >&2
    exit 1
else
    git clone --depth 1 "$REPOSITORY_URL" "$FVD_SOURCE_DIR"
fi

uv python install 3.11
"$FVD_SOURCE_DIR/scripts/install-user.sh"
