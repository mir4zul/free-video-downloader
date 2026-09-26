#!/bin/sh
set -eu
APP_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec uv run --locked --project "$APP_ROOT" free-video-downloader "$@"
