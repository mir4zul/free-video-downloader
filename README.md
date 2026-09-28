# Free Video Downloader for Linux

A free desktop app for downloading videos from YouTube and other websites supported by [yt-dlp](https://github.com/yt-dlp/yt-dlp). Paste a link, inspect the available formats, choose a resolution, and download it to your computer.

## Features

- Preview a video's thumbnail, title, duration, and available resolutions.
- Choose a source resolution, including 720p, 1080p, 1440p (often called 2K), or 2160p (4K) when available.
- Switch to **Audio only (MP3)** to extract audio from a supported video link; choose an MP3 bitrate.
- Automatically select a suitable video container from the source formats. Video downloads may use MP4, WebM, or MKV; audio-only downloads use MP3.
- Show download progress, speed, ETA, queue status, and processing state.
- Queue downloads, limit simultaneous jobs and parallel fragments, pause or cancel jobs, and resume supported partial downloads later.
- Save download history and settings locally; open completed files or their folders.
- Verify the completed file and selected resolution before marking a job complete.

## Format and quality behavior

In Video mode, the resolution list comes from formats actually offered by the source. The app does not upscale or re-encode video. It selects a compatible source container automatically: for example, MP4 with AAC audio can be saved as MP4, WebM with Opus/Vorbis as WebM, and incompatible mixed streams may be merged into MKV without re-encoding.

In **Audio only (MP3)** mode, the app extracts audio from a supported video link and offers 128, 192, 256, and 320 kbps output settings. Choosing a higher bitrate does not improve the original source quality. FFmpeg is required for conversion.

The selected height and width are checked with FFprobe after download. If they do not match the selected resolution, the job is not marked complete. A resolution being available during analysis does not guarantee that the source will allow a successful download.

## Requirements

- Linux (Arch Linux and Ubuntu setup commands are shown below)
- Python 3.11 or newer
- [`uv`](https://docs.astral.sh/uv/)
- FFmpeg and FFprobe
- Deno or Node.js for JavaScript-dependent YouTube extraction features

The app itself only checks for required components. The quick installer below can install missing system packages after asking for your confirmation.

### Arch Linux

```bash
sudo pacman -Syu python uv ffmpeg deno
```

### Ubuntu

```bash
sudo apt update
sudo apt install ffmpeg python3 python3-venv
```

Install Python 3.11+ if the distribution's `python3` package is older. Deno is optional when Node.js is installed. See the [Deno installation guide](https://docs.deno.com/runtime/getting_started/installation/).

## Install and run

### Quick install (Arch Linux and Ubuntu)

Download and run the installer:

```bash
curl -fsSL https://raw.githubusercontent.com/mir4zul/free-video-downloader/main/install.sh -o install-free-video-downloader.sh
bash install-free-video-downloader.sh
```

The installer checks for Git, Python, FFmpeg, and Node.js or Deno. If system tools are missing, it asks before installing them with `pacman` or `apt` and may prompt for your sudo password. It installs `uv` for your user, downloads Python 3.11 through `uv`, prepares the app, and adds a launcher to the desktop app menu. Do not run it with `sudo`.

To update an existing installation, download and run the same installer again. It fast-forward updates the installed checkout, syncs dependencies, and refreshes the desktop launcher. It keeps your download history, settings, and downloaded files.

### Run from an existing checkout

If you already cloned this repository, install the locked Python dependencies and launch the app:

```bash
uv sync --locked
uv run --locked free-video-downloader
```

To add a launcher for the current user from the checkout:

```bash
./scripts/install-user.sh
```

The desktop launcher uses the installed `uv` executable directly. To run from a development checkout, use `./scripts/run.sh`.

### Uninstall

Download and run the uninstaller:

```bash
curl -fsSL https://raw.githubusercontent.com/mir4zul/free-video-downloader/main/uninstall.sh -o uninstall-free-video-downloader.sh
bash uninstall-free-video-downloader.sh
```

After confirmation, it removes the app launcher, desktop entry, icon, and installer-managed source checkout. It keeps your download history, settings, downloaded videos, and shared system tools such as `uv`, FFmpeg, and Node.js.

## Browser right-click menu

A Chromium extension is included for testing and future store distribution. It adds **Download video with Free Video Downloader** to the right-click menu on videos and opens the Linux desktop app with the selected link. Choose a video resolution or audio-only MP3 quality in the app to start downloading. For YouTube, the extension sends the watch page URL so yt-dlp can inspect available formats; on other sites it uses a direct HTTP(S) video URL when available and otherwise sends the page URL. The browser may ask permission the first time it opens the desktop app. Firefox is not supported yet.

The extension is not yet published in the Chrome Web Store. Until it is approved and published, load the `browser-extension` folder through the browser's **Load unpacked** developer option to test it. The Web Store package and listing materials are in `store-assets/` and can be rebuilt with `scripts/package-browser-extension.sh`.

## Download a video

1. Paste a link and click **Analyze**.
2. Review the preview and available resolutions.
3. Choose **Video** and select a resolution, or choose **Audio only (MP3)** and select a bitrate.
4. Click **Download / Add to queue**.
5. Follow the job in **Downloads & history**. Open the verified file or its folder when it completes.

Analysis can be canceled and times out after 90 seconds. If the thumbnail is unavailable, format selection can still work. You can analyze another link while a download is running.

## Settings and downloaded files

The app has no built-in transfer speed cap. Parallel fragments apply only to supported fragmented streams; they do not split a direct single-file transfer. The default is 4 fragments and 2 simultaneous downloads. Increasing concurrency may use more network connections and CPU, and cannot bypass limits imposed by your network or the source server.

Settings and download history are stored in SQLite at `$XDG_DATA_HOME/free-video-downloader/state.sqlite3`, or by default at `~/.local/share/free-video-downloader/state.sqlite3`. Set `FVD_DATA_DIR` to use another data directory, for example during testing.

Partial downloads are stored in `.fvd-partials/` under the selected folder. Resume is attempted when the source supports it. If the app closes, unfinished jobs do not restart automatically; select one and choose **Retry / Resume**. When a filename already exists, a numbered suffix is added.

## Limitations

- Supported links and available formats depend on the source website. Login-required, DRM-protected, live, unavailable, or otherwise unsupported media may fail.
- The app cannot create a resolution that the source does not provide. Download speed depends on the user's connection, source server, and throttling.
- Ubuntu and X11 have not been validated in the current release checks. The app was launched on Arch Linux under Wayland at 125% scaling.
- Real YouTube 720p–4K file downloads and playback have not been fully validated. YouTube 4K format analysis succeeded, but the full 4K download was not run.
- Publishing a completed file uses filesystem hard links; the destination filesystem must support them.

## Development and tests

Run the test suite with the Qt offscreen platform:

```bash
QT_QPA_PLATFORM=offscreen uv run --locked python -m unittest discover -s tests -v
```

The suite contains unit and local media/HTTP fixture tests. Some integration tests need localhost socket access and FFmpeg/FFprobe. Build source and wheel packages with:

```bash
uv build
```

## References

- [yt-dlp documentation](https://github.com/yt-dlp/yt-dlp#readme)
- [PySide6 / Qt for Python setup](https://doc.qt.io/qtforpython-6/gettingstarted.html)
