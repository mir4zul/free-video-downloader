"""Turn extractor metadata into explicit, downloadable output choices."""
from dataclasses import dataclass
from urllib.parse import urlsplit


def validate_url(value):
    value = value.strip()
    try:
        parsed = urlsplit(value)
        valid = parsed.scheme in ("http", "https") and parsed.hostname and parsed.port != 0
    except ValueError:
        valid = False
    if not valid or any(c.isspace() or ord(c) < 32 for c in value):
        raise ValueError("Enter a complete http:// or https:// video link.")
    return value


def size_text(size):
    return f"{size / 1024 / 1024:.1f} MiB" if size else "Unknown size"


def duration_text(seconds):
    if seconds is None:
        return "Duration unknown"
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes}:{seconds:02}"


def has_codec(fmt, kind):
    return fmt.get(kind) not in (None, "none", "unknown")


@dataclass(frozen=True)
class OutputChoice:
    label: str
    selector: str
    container: str
    details: str
    bitrate: int | None = None
    estimated_size: int | None = None
    height: int | None = None
    width: int | None = None


def build_choices(info):
    if not isinstance(info, dict) or info.get("_type") in ("playlist", "multi_video"):
        raise ValueError("Please use a single video link; playlists are not supported yet.")
    if info.get("is_live") or info.get("live_status") in ("is_live", "is_upcoming"):
        raise ValueError("Live and upcoming streams are not supported yet. Choose a recorded video.")
    formats = [f for f in (info.get("formats") or [info])
               if f.get("format_id") is not None and f.get("url") and not f.get("has_drm")]
    audio = [f for f in formats if has_codec(f, "acodec")]
    audio_only = [f for f in audio if f.get("vcodec") == "none"]
    aac = [f for f in audio_only if f.get("ext") in ("m4a", "mp4")
           and str(f.get("acodec", "")).startswith(("mp4a", "aac"))]
    best_aac = max(aac, key=lambda f: f.get("abr") or f.get("tbr") or 0, default=None)
    webm_audio = [f for f in audio_only if f.get("ext") == "webm" and
                  str(f.get("acodec", "")).startswith(("opus", "vorbis"))]
    best_webm = max(webm_audio, key=lambda f: f.get("abr") or f.get("tbr") or 0, default=None)
    best_audio = max(audio_only, key=lambda f: f.get("abr") or f.get("tbr") or 0, default=None)
    videos = []
    for f in sorted(formats, key=lambda f: (f.get("height") or 0, f.get("fps") or 0,
                                            f.get("tbr") or 0), reverse=True):
        if f.get("ext") not in ("mp4", "webm", "mkv", "mov", "flv", "avi", "ogg", "ogv", "ts", "mpeg", "3gp") or not has_codec(f, "vcodec"):
            continue
        container = f["ext"]
        companion = None
        if not has_codec(f, "acodec"):
            companion = (best_aac if container == "mp4" else best_webm if container == "webm" else None)
            if companion is None:
                companion = best_audio
                container = "mkv"
        if not has_codec(f, "acodec") and companion is None:
            continue  # Never offer a silent video as a normal MP4 download.
        selected = [f] + ([companion] if companion else [])
        sizes = [part.get("filesize") or part.get("filesize_approx") for part in selected]
        size = sum(sizes) if all(sizes) else None
        height = f.get("height")
        if height and any(choice.height == height for choice in videos):
            continue
        resolution = f"{height}p" if height else f.get("resolution") or "Resolution unknown"
        resolution += " (4K)" if height == 2160 else " (2K / QHD)" if height == 1440 else ""
        fps = f" · {f['fps']:g} fps" if f.get("fps") else ""
        codec = str(f.get("vcodec", "unknown"))
        selector = "+".join(str(part["format_id"]) for part in selected)
        rate = f" · {f['tbr']:.0f} kbps" if f.get("tbr") else ""
        videos.append(OutputChoice(
            f"{resolution}{fps} · {container.upper()}", selector, container,
            f"{container.upper()} · {resolution}{fps} · {codec} · Original video codec, no re-encoding · "
            f"{'Estimated output: ' + size_text(size) if size else 'Output size unknown'}"
            + (" · Video + audio merge required" if companion else " · Audio included"), estimated_size=size,
            height=height, width=f.get("width")))
    audios = []
    source = max(audio_only or audio, key=lambda f: f.get("abr") or f.get("tbr") or 0, default=None)
    if source:
        for bitrate in (128, 192, 256, 320):
            size = info.get("duration", 0) or 0
            size = size * bitrate * 1000 / 8
            audios.append(OutputChoice(f"MP3 · {bitrate} kbps", str(source["format_id"]), "mp3",
                f"MP3 · {bitrate} kbps · Estimated output: {size_text(size)} · Conversion required. "
                "Higher bitrate does not improve the source quality.", bitrate, int(size) or None))
    if not videos and not audios:
        raise ValueError("No usable MP4 with audio or audio source was found. Try another video.")
    return videos, audios
