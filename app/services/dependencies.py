from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from shutil import which


@dataclass(frozen=True)
class Dependency:
    name: str
    available: bool
    detail: str


def check_dependencies():
    """Check local availability only; no network or package installation."""
    results = []
    for package in ("PySide6", "yt-dlp", "yt-dlp-ejs"):
        try:
            results.append(Dependency(package, True, version(package)))
        except PackageNotFoundError:
            results.append(Dependency(package, False, "Missing — run uv sync"))
    for executable in ("ffmpeg", "ffprobe"):
        path = which(executable)
        results.append(Dependency(executable, bool(path), path or "Missing — install FFmpeg"))
    path = which("deno") or which("node")
    results.append(Dependency("JavaScript runtime (Deno / Node)", bool(path), path or
                              "Missing — install Deno; see setup guide"))
    return results
