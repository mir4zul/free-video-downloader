"""Isolated yt-dlp worker. stdout is a JSON-lines event protocol."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import errno
import tempfile
import threading

EVENT_LOCK = threading.Lock()


def retry_delay(n):
    return min(8, 2 ** max(0, n))


def transfer_options(config):
    return {"concurrent_fragment_downloads": max(1, min(16, int(config.get("fragments", 4)))),
            "ratelimit": None, "retries": 3, "fragment_retries": 3, "extractor_retries": 3,
            "retry_sleep_functions": {key: retry_delay for key in ("http", "fragment", "extractor")}}


def check_space(folder, required=0):
    # Keep room for metadata and the filesystem even when the source size is unknown.
    if shutil.disk_usage(folder).free < max(32 * 1024 * 1024, required):
        raise ValueError("Not enough free disk space. Choose another folder or free some space.")


def prepare_folder(folder, estimate=0):
    try:
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=folder) as probe:
            probe.write(b"write check")
            probe.flush()
        check_space(folder, int(estimate or 0) * 2 + 32 * 1024 * 1024)
    except PermissionError as error:
        raise ValueError("Cannot write to this folder. Choose a writable download folder.") from error
    except OSError as error:
        if error.errno in (errno.ENOSPC, errno.EDQUOT):
            raise ValueError("The destination disk is full or its storage quota is exhausted.") from error
        raise

from app.services.formats import validate_url


def emit(kind, **values):
    with EVENT_LOCK:
        print(json.dumps({"type": kind, **values}), flush=True)


def verify_output(path, container, expected_duration=None, expected_height=None, expected_width=None):
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0 or path.suffix != "." + container:
        raise ValueError("The output file is missing, empty or has the wrong format.")
    result = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                             "-of", "json", str(path)], capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise ValueError("Output verification failed: " + result.stderr[-1000:])
    info = json.loads(result.stdout)
    streams = info.get("streams", [])
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    video = [s for s in streams if s.get("codec_type") == "video"]
    duration = float(info.get("format", {}).get("duration") or 0)
    if not audio or (container != "mp3" and not video) or duration <= 0:
        raise ValueError("Output verification failed: required media streams or duration are missing.")
    if container == "mp3" and (video or audio[0].get("codec_name") != "mp3"):
        raise ValueError("Output verification failed: expected MP3 audio.")
    if container == "mp4" and "mp4" not in info.get("format", {}).get("format_name", ""):
        raise ValueError("Output verification failed: expected an MP4 container.")
    if container in ("webm", "mkv") and "matroska" not in info.get("format", {}).get("format_name", ""):
        raise ValueError("Output verification failed: expected a WebM/Matroska container.")
    if expected_height and (not video or video[0].get("height") != expected_height):
        raise ValueError(f"Resolution mismatch: expected {expected_height}p. Analyze again; lower quality was not accepted.")
    if expected_width and (not video or video[0].get("width") != expected_width):
        raise ValueError("Output width does not match the selected video. Analyze again.")
    if expected_duration and duration < float(expected_duration) - max(2, float(expected_duration) * .05):
        raise ValueError("Output appears incomplete. Retry or analyze the link again.")
    return info


def publish(path, folder, title, container):
    from yt_dlp.utils import sanitize_filename
    stem = sanitize_filename(title or "Video", restricted=True)[:100] or "Video"
    for index in range(10000):
        name = stem + (f" ({index})" if index else "") + "." + container
        destination = folder / name
        try:
            # Work directory is on the same filesystem. Never overwrite another file.
            os.link(path, destination)
        except FileExistsError:
            continue
        path.unlink()
        return destination
    raise ValueError("Too many files with this name. Choose another folder.")


def ensure_mp3_bitrate(path, bitrate, probe):
    audio = next(s for s in probe["streams"] if s.get("codec_type") == "audio")
    if abs(int(audio.get("bit_rate") or 0) - bitrate * 1000) <= bitrate * 50:
        return
    # yt-dlp preserves existing MP3 audio; honor the user's requested bitrate here too.
    emit("stage", message=f"Converting to MP3 at {bitrate} kbps…")
    converted = path.with_name("normalized.mp3")
    result = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-map", "0:a:0",
        "-vn", "-c:a", "libmp3lame", "-b:a", f"{bitrate}k", str(converted)],
        capture_output=True, text=True)
    if result.returncode:
        raise ValueError("MP3 conversion failed: " + result.stderr[-1000:])
    verify_output(converted, "mp3", float(probe["format"]["duration"]))
    os.replace(converted, path)


def run(config):
    from yt_dlp import YoutubeDL
    from yt_dlp.postprocessor.common import PostProcessor
    url = validate_url(config["url"])
    container = config["container"]
    if container not in ("mp4", "mp3", "webm", "mkv", "mov", "flv", "avi", "ogg", "ogv", "ts", "mpeg", "3gp"):
        raise ValueError("Unsupported output format.")
    if container == "mp3" and config.get("bitrate") not in (128, 192, 256, 320):
        raise ValueError("Unsupported MP3 bitrate.")
    for binary in ("ffmpeg", "ffprobe"):
        if not shutil.which(binary):
            raise ValueError(f"{binary} is missing. Open Check setup for installation instructions.")
    folder = Path(config["folder"]).expanduser().resolve()
    prepare_folder(folder, config.get("estimated_size"))
    key = hashlib.sha256(json.dumps([url, config["selector"], container, config.get("bitrate")]).encode()).hexdigest()[:24]
    work = folder / ".fvd-partials" / key
    work.mkdir(parents=True, exist_ok=True)
    lock = (work / "lock").open("a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise ValueError("This download is already running in another window.")
    previous = work / ("media." + container)
    if previous.exists():
        try:
            verify_output(previous, container, config.get("duration"), config.get("height"), config.get("width"))
        except (ValueError, subprocess.TimeoutExpired):
            # Only discard an invalid completed-name file in our own private work directory.
            # .part files and downloaded source streams remain available for resume.
            previous.unlink()
    last = [0.0]
    last_space_check = [0.0]

    def progress(data):
        now = time.monotonic()
        if data["status"] == "downloading" and now - last[0] < .2:
            return
        last[0] = now
        if now - last_space_check[0] >= 2:
            check_space(folder)
            last_space_check[0] = now
        emit("progress", downloaded=data.get("downloaded_bytes", 0),
             total=data.get("total_bytes") or data.get("total_bytes_estimate"),
             speed=data.get("speed"), eta=data.get("eta"),
             stream=data.get("info_dict", {}).get("format_id"), status=data["status"])

    class Logger:
        def debug(self, message):
            pass
        def info(self, message):
            pass
        def warning(self, message):
            emit("warning", message=str(message))
        def error(self, message):
            emit("warning", message=str(message))

    output = []

    class CaptureOutput(PostProcessor):
        def run(self, info):
            output.append(Path(info["filepath"]))
            return [], info

    def processing(data):
        name = data.get("postprocessor", "")
        if data.get("status") == "started":
            check_space(folder)
            emit("stage", message="Converting to MP3…" if "ExtractAudio" in name else
                 "Merging video and audio…" if "Merger" in name else "Processing media…")

    options = {"format": config["selector"], "outtmpl": str(work / "media.%(ext)s"),
               "noplaylist": True, "quiet": True, "noprogress": True, "logger": Logger(),
               "continuedl": True, "overwrites": False, "nopart": False,
               "socket_timeout": 20, "retries": 2, "fragment_retries": 2,
               "skip_unavailable_fragments": False, "cachedir": False,
               "progress_hooks": [progress], "postprocessor_hooks": [processing],
               "merge_output_format": container if container != "mp3" else None}
    options.update(transfer_options(config))
    if not shutil.which("deno") and shutil.which("node"):
        options["js_runtimes"] = {"node": {}}
    if container == "mp3":
        options["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3",
                                      "preferredquality": str(config["bitrate"])}]
    emit("stage", message="Connecting… Partial downloads will resume when supported.")
    with lock, YoutubeDL(options) as ydl:
        ydl.add_post_processor(CaptureOutput(), when="after_move")
        info = ydl.extract_info(url, download=True)
        if not info or info.get("_type") in ("playlist", "multi_video"):
            raise ValueError("Expected a single video.")
        if not output:
            raise ValueError("The download engine did not return an output file.")
        path = output[-1]
        emit("stage", message="Verifying output…")
        probe = verify_output(path, container, info.get("duration") or config.get("duration"),
                              config.get("height"), config.get("width"))
        if container == "mp3":
            ensure_mp3_bitrate(path, config["bitrate"], probe)
        destination = publish(path, folder, info.get("title"), container)
        emit("completed", path=str(destination))


def main():
    # FFmpeg and ffprobe inherit this process group, allowing cancellation of all work.
    os.setsid()
    try:
        run(json.loads(sys.stdin.readline()))
    except Exception as error:
        message = str(error)[:2000]
        if isinstance(error, PermissionError) or "Permission denied" in message:
            message = "Permission denied. Choose a writable folder and retry."
        elif isinstance(error, OSError) and error.errno in (errno.ENOSPC, errno.EDQUOT) or "No space left" in message:
            message = "Disk full or storage quota exhausted. Free space and retry."
        emit("failed", message=message)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
