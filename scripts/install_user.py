from pathlib import Path
import shlex
import shutil
import sys


def main():
    app_root = Path(sys.argv[1]).resolve()
    home = Path.home()
    uv_executable = shutil.which("uv")
    if not uv_executable:
        raise SystemExit("uv is missing; install it before installing the desktop launcher.")
    binary = home / ".local/bin/free-video-downloader"
    applications = home / ".local/share/applications"
    icons = home / ".local/share/icons/hicolor/scalable/apps"
    desktop = applications / "free-video-downloader.desktop"
    icon = icons / "free-video-downloader.svg"
    binary.parent.mkdir(parents=True, exist_ok=True)
    applications.mkdir(parents=True, exist_ok=True)
    icons.mkdir(parents=True, exist_ok=True)
    icon.write_bytes((app_root / "app/assets/downloader.svg").read_bytes())
    project = shlex.quote(str(app_root))
    binary.write_text("#!/bin/sh\nset -eu\nexec " + shlex.quote(uv_executable) + " run --locked --project " + project + " free-video-downloader \"$@\"\n")
    binary.chmod(0o755)
    # Desktop Exec quoting follows the Desktop Entry spec and supports spaces in home paths.
    executable = str(binary).replace("\\", "\\\\").replace('"', '\\"')
    desktop.write_text("""[Desktop Entry]
Type=Application
Name=Free Video Downloader
Comment=Download a video at the resolution you choose
Exec=""" + '"' + executable + '"' + """
Terminal=false
Icon=free-video-downloader
Categories=AudioVideo;Video;
StartupNotify=true
""")
    desktop.chmod(0o644)


if __name__ == "__main__":
    main()
