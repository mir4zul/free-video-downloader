#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out_dir="$repo_root/dist"
extension_dir="$repo_root/browser-extension"
mkdir -p "$out_dir"
archive="$out_dir/free-video-downloader-extension-1.0.0.zip"
python3 "$repo_root/scripts/package_browser_extension.py" "$extension_dir" "$archive"
printf 'Created %s\n' "$archive"
