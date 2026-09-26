# Free Video Downloader — Linux

A free desktop downloader for Linux. Paste a video link from YouTube or another supported website to view its preview and available formats, then download the video at your chosen resolution.

**Current status:** Steps 1–5 are implemented. Step 6 automated tests, the Arch Wayland launcher check, installer, and package builds have been verified. Real 720p–4K media downloads and playback, Ubuntu, and X11 remain unverified, so release validation is partially complete.

## How format selection works

Following the user's updated requirements, the MP3/MP4 mode selector has been removed. You now choose only a resolution. The older milestone records below describe the earlier MP4/MP3 implementation for historical context; those are not choices in the current interface. Compatibility with previously saved MP3 queue/history entries is retained.

## How to use

1. Paste a video link and click **Analyze**.
2. Review the thumbnail, title, duration, and available qualities.
3. Choose an available resolution, such as 720p, 1080p, 1440p/2K, or 2160p/4K.
4. The output container is selected automatically based on the source; you do not choose a format separately.
5. Choose a save folder and click **Download**.
6. Follow the progress, speed, remaining time, and processing status. When complete, open the file or its folder.

## Feature goals

| Area | Plan |
| --- | --- |
| Platform | Arch Linux and Ubuntu first; other Linux distributions depend on dependency and compatibility checks |
| Links | YouTube and other websites supported by the download engine |
| Preview | Thumbnail, title, duration, source |
| Video | MP4/WebM/other supported containers according to the source; 360p, 480p, 720p, 1080p, 1440p (commonly called 2K), and 2160p (4K) when available from the source |
| Audio | Source audio paired with the selected video; new downloads have no audio-only/MP3 selector |
| Format details | Resolution, FPS, codec, and file size when known; estimates are labeled |
| Progress | Percentage, downloaded bytes, speed, ETA, and separate merging/conversion status |
| Controls | Cancel, retry, queue, and resume supported downloads |
| Storage | Folder picker, filenames, and completed download history |
| Speed | Limited parallel downloading for supported fragmented streams; avoid unnecessary conversion |

## Linux compatibility, interface, and speed plan

- **Arch and Ubuntu:** Provide separate setup instructions for both distributions. Python dependencies should stay in an isolated environment to avoid conflicts with system Python. List the tested distributions and versions for each release.
- **Desktop compatibility:** Test launch, scaling, folder selection, and file opening on Wayland and X11. Do not call another distribution verified until it has been tested.
- **Interface:** Use a clear layout with readable text, video preview, an obvious resolution selector, and a primary Download button. Show analysis, downloading, merging, completed, and failed states separately; long-running work must not freeze the window.
- **Network use:** The app has no built-in speed cap by default. Use configurable parallel fragments for supported streams, with an option to lower concurrency if it causes more errors.
- **Speed display:** Show transfer speed and ETA; these are not the advertised speed of the user's internet plan. Aim to use the capacity allowed by the source and network.
- **Verification criteria:** Pass install, link analysis, MP4/MP3 download, and playback checks on Arch and Ubuntu. Compare speed using the same source and network and report the results; do not claim “full speed” without testing.

## Practical limitations

- Not every website or link is guaranteed to work. Show a clear error for unsupported, unavailable, or login-required links.
- Only show resolutions available from the source; do not create real 4K from a 720p video.
- MP4 is a container; codec compatibility is a separate matter. Merge compatible streams for faster downloads. If conversion is required, show that it may take time.
- Increasing an MP3 bitrate does not improve the source audio quality.
- Download speed depends on the internet connection, source server, and throttling; a specific speed cannot be guaranteed.

## Proposed technology and architecture

- **Python + PySide6:** Linux desktop interface.
- **yt-dlp:** Video information, available formats, and download engine.
- **FFmpeg / ffprobe:** Merge video and audio, convert to MP3, and verify output.
- **Background worker:** Keep the interface responsive during analysis, downloads, and conversion.
- **Local settings/history:** Store the save folder and download history.
- **Dependency check:** Check yt-dlp, FFmpeg, and the JavaScript runtime/components needed for YouTube extraction, then show setup instructions.
- **Process execution:** Never pass URLs as shell commands; use an argument list and stop the child process when canceled.

Proposed code layout: `app/ui/`, `app/services/`, `app/workers/`, `app/storage/`, `tests/`. Dependency versions and installation commands will be verified and added during implementation.

## Work checklist

`[x]` = complete / OK; `[ ]` = remaining. Update a checkbox only after the task has been implemented and appropriately verified.

### 1. Planning

- [x] Document requirements, user flow, and feature scope — OK
- [x] Define proposed technology and practical limitations — OK
- [x] Create the README and step-by-step checklist — OK
- [x] Document the Arch/Ubuntu compatibility plan and checks for other distributions — OK
- [x] Document goals for a polished responsive interface and network speed use — OK

### 2. Project setup

- [x] Create the Python project, dependencies, and application entry point — OK
- [x] Create the main window, URL input, Analyze button, and folder picker — OK
- [x] Create a readable layout, preview area, and clear Video/Audio controls — OK
- [x] Add dependency detection and required setup instructions — OK

### 3. Link analysis and format selection

- [x] Analyze links in the background and show thumbnail/title/duration — OK
- [x] Build the correct options from available video/audio formats — OK
- [x] Create an MP4 quality selector and an MP3 bitrate selector — OK
- [x] Handle unavailable formats, invalid links, and source errors — OK
- [x] Show the selected output format, quality, and estimated size — OK

### 4. Download and conversion

- [x] Download and merge the selected video and audio streams — OK
- [x] Download audio only and convert to MP3 — OK
- [x] Show progress, speed, ETA, and processing status — OK
- [x] Add cancel/retry and resume supported partial downloads — OK
- [x] Mark a download complete only after verifying the output file — OK

### 5. Speed and usability

- [x] Add configurable fragment concurrency; test with 4 initially — OK
- [x] Verify transfers have no default speed cap and show live speed/ETA — OK
- [x] Add limited retries and backoff for network failures — OK
- [x] Add a download queue and limit simultaneous downloads — OK
- [x] Add settings, history, and open file/folder actions — OK
- [x] Handle duplicate filenames, low disk space, and write permission errors — OK

### 6. Verification and release — 2026-09-26

- [x] Resolution-based format selection, quality/container labels, mismatch rejection, error handling, and queue tests
- [ ] Download media from real YouTube links at 720p/1080p/2K/4K, then verify output resolution and playback
- [x] Merge local MP4/WebM/MKV fixtures, decode playback, and verify exact resolution match/mismatch
- [x] Test cancellation, HTTP retry/backoff, interrupted partial resume, child-process cleanup, and verification failures
- [x] Compare 1 vs. 4 fragments on the same throttled HLS fixture; record environment and results below
- [x] Create Linux launch script, user desktop launcher, build artifacts, and installation guide
- [ ] Verify real supported media download/playback on Arch; only YouTube format analysis has succeeded
- [ ] Verify Ubuntu install/download/playback: this host is Arch; Docker socket access was denied, so Ubuntu could not be tested
- [x] Launch through the user desktop launcher on Wayland; run offscreen UI tests at 125% scaling
- [ ] Verify an X11 session and native interactive folder/file opening; this session is Wayland, and the path-opening test uses a desktop service mock
- [x] Install the wheel in a clean temporary Python environment and launch the app offscreen
- [x] Build PyPI sdist and wheel successfully; the sdist includes user installation scripts

## First usable release criteria

Paste a link → preview → choose an available resolution → choose a folder → download → receive a resolution-verified output file. The interface must remain responsive throughout and must never report completion on failure. Then complete queue, history, and speed tuning.

## Reference

Engine capabilities, format selection, dependencies, and download options are based on the [official yt-dlp documentation](https://github.com/yt-dlp/yt-dlp#readme).

## Development setup and launch

Python 3.11+ and `uv` are required. From the project folder:

```bash
uv sync --locked
uv run --locked free-video-downloader
```

Alternatively, use a Python virtual environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m app
```

`uv.lock` pins dependency versions; the pip alternative does not use the lock file. The app uses the Qt bundled with PySide6; installing packages into system Python is not required. See the [Qt setup documentation](https://doc.qt.io/qtforpython-6/gettingstarted.html).

System dependencies for the download engine:

```bash
# Arch Linux
sudo pacman -Syu python uv ffmpeg deno

# Ubuntu (Deno is optional; installed Node also works)
sudo apt update
sudo apt install ffmpeg python3 python3-venv
```

For Deno on Ubuntu, follow the [official installation guide](https://docs.deno.com/runtime/getting_started/installation/). On Arch, use the [Deno package](https://archlinux.org/packages/extra/x86_64/deno/). The app's **Check setup** checks for PySide6, yt-dlp, yt-dlp-ejs, FFmpeg/ffprobe, and Deno or Node; it does not verify version compatibility or perform a real download. If Deno is missing, installed Node is enabled as a fallback for analysis. The app does not install system packages automatically.

Paste a link and click **Analyze** to see the title, duration, thumbnail, and formats available from the source. Choose a resolution and folder, then click **Download / Add to queue**. When complete, the app shows the verified output file path.

To install a user-level launcher and desktop app entry on Arch/Ubuntu, run `./scripts/install-user.sh` from the project folder. Install `uv`, Python 3, and FFmpeg/ffprobe first; the script does not install system dependencies through the Ubuntu/Arch package manager. **Free Video Downloader** will appear in the desktop app menu. If you move the source folder, reinstall the launcher. To launch directly from a development checkout, use `./scripts/run.sh`.

You can cancel analysis with **Cancel**; it times out after 90 seconds. Entering a new link clears old metadata and selections. Formats remain selectable if a thumbnail is unavailable. Playlists, live/upcoming streams, DRM-only sources, and unusable formats produce an error.

The resolution list is built from source video formats; there is no MP4-only filter. The selector shows the container alongside the selected resolution. MP4+AAC uses MP4; WebM+Opus/Vorbis uses WebM; other mixed combinations use MKV to merge audio/video without re-encoding codecs. Files that already contain audio keep their supported source container. Video is not re-encoded or upscaled. After download, FFprobe checks the selected height/width; a mismatch is not marked Completed.

Headless interface checks:

```bash
QT_QPA_PLATFORM=offscreen uv run --locked python -m unittest discover -s tests -v
```

### Step 2 verification

- Installation in an isolated environment on the Arch host and `uv sync --locked --offline` succeeded.
- Two automated tests passed: reporting missing dependencies; folder selection/cancel and Video/Audio mode switching.
- The offscreen Qt window was rendered to inspect the layout; syntax checks passed.
- During Step 2 testing, this host had FFmpeg/ffprobe and Python dependencies; Deno was reported missing. An installed Node fallback was added in Step 3.
- Native Wayland/X11 sessions, Ubuntu, and real downloads have not yet been tested; those remained on later checklists.

### Step 3 verification — 2026-09-23

- All 13 automated tests passed: URL validation, audio/video pairing, DRM filtering, unknown size, MP3 estimate, playlist/live rejection, subprocess success/error/invalid JSON/cancel, responsive event loop, close cleanup, thumbnail failure, and stale selection reset.
- The real YouTube link `jNQXAC9IVRw` returned “Me at the zoo” metadata, 10 MP4 options, and 4 MP3 bitrate options. Thumbnail fetch and image decoding succeeded (20,969 bytes). These results apply to that link; they do not represent the number of formats available for all videos.
- The unavailable YouTube link `BaW_jenozKc` reported the source error correctly.
- The Step 3 headless UI render checked the preview and selection layout; no media was downloaded in that step.

### Step 4 usage and verification — 2026-09-23

- During a download, the app shows percentage, bytes, speed, and ETA for the current stream. Separate video/audio downloads restart the percentage for the next stream. Merge, conversion, and verification have separate statuses; unknown totals use indeterminate progress.
- **Cancel download** stops the worker and its FFmpeg/ffprobe process group. **Retry / Resume** reuses the same link, format, and folder; partial data is reused when the source supports HTTP range/fragment resume. If conversion is interrupted, it starts again.
- Partial files remain in `.fvd-partials/` inside the selected folder. After restarting the app, downloading again with the same link, format, and folder attempts to resume. If the source changes formats, analyze the link again.
- FFprobe checks that the output is nonempty and has the required container, audio/video streams, and duration. A failed check is never marked Completed. This is not a full decode test of every file.
- Verified output is published to the folder; if the name already exists, a `(1)`, `(2)` suffix is added. Atomic publication currently requires hard-link support on the destination filesystem (such as ext4/Btrfs); unsupported filesystems return an error.
- All 23 automated tests passed. Local HTTP fixtures tested real byte downloads, separate video/audio merge, MP3 conversion/bitrate, range resume, invalid output rejection, duplicate filename preservation, worker exit, and child-process cancellation. Tests open a localhost socket and require FFmpeg/ffprobe.
- MP4 and 128 kbps MP3 downloads from the real YouTube video “Me at the zoo” succeeded; both outputs passed a full FFmpeg decode test.
- Broader 720p–4K testing, Ubuntu/Wayland/X11 release validation, queue/history, and speed tuning remained for later steps.

### Step 5 usage and verification

- In the **New download** tab, analyze a link, choose a format/folder, then click **Download / Add to queue**. The **Downloads & history** tab shows each job's state, stream progress, speed, and ETA. You can analyze another link while a download is running.
- **Parallel fragments:** default 4, range 1–16; applies to supported fragmented streams and new queue entries. It does not automatically split a direct single-file transfer.
- **Simultaneous downloads:** default 2, range 1–4 per window. Lowering the limit does not stop running jobs; new jobs start under the lower limit after they finish. Raising both limits increases connection and CPU use.
- The engine has no speed cap. HTTP/fragment/extractor retries are limited to 3, with delays of 1, 2, and 4 seconds. The source server may prevent use of the full internet connection speed.
- Select a row in the queue/history to use **Cancel selected**, **Retry / Resume**, **Open file**, or **Open folder**. Retry reuses the previous format/folder/settings. A job already queued or running is not added again.
- The save folder, concurrency settings, and job history are stored in SQLite: `$XDG_DATA_HOME/free-video-downloader/state.sqlite3`, defaulting to `~/.local/share/free-video-downloader/state.sqlite3`. Tests/isolated runs can use `FVD_DATA_DIR`. Older Step 4 download history is not imported automatically.
- When the app closes, active jobs are canceled and waiting jobs are marked interrupted. In the next launch, unfinished jobs do not start automatically; select a row and use Retry / Resume.
- The app checks folder write access. When estimated output size is known, preflight requires about twice that size plus a 32 MiB reserve; for unknown sizes it checks a 32 MiB reserve. Free space is also checked periodically during transfer. Estimates do not guarantee a successful download; disk-full/permission failures show an error and leave partial data.
- All 32 automated tests passed. A local HLS fixture with the default 4 fragments tested concurrent requests, live speed events, and verified output; HTTP 503 was followed by the actual 1s/2s backoff and a successful retry.
- Queue limits/FIFO/cancel/retry/shutdown, settings/history restart, duplicate handling, missing files, low disk space, and permission errors were tested. Desktop-open URL dispatch was tested with a mock; full native desktop application launch remained for Step 6.
- The Downloads & history tab was rendered headlessly. Controlled local network benchmark and distribution-wide release limitations are documented in Step 6.

### Step 6 release verification — 2026-09-26

- The resolution selector includes the output container. Selection maps to a resolution available from the source; after download, FFprobe prevents Completed status if height/width do not match. The full automated suite passed 35 tests, including a synthetic 2160p selection/mismatch test and playback validation of generated MP4/WebM/MKV clips.
- The real YouTube link `ocVNYZ9O1G0` (“Big Buck Bunny [4k 2160p 60fps]”) analyzed successfully. Available formats included 2160p, 1440p, 1080p, and 720p, each at 60 fps. The best MP4 2160p stream did not report a size. A WebM 2160p stream was reported at about 955 MB. The 4K download/playback was deliberately left unverified because the source is 635 seconds long and the MP4 size is unknown; the network might transfer over 1 GB. Another 4K test link was unavailable.
- Local generated MP4/WebM/MKV outputs were decoded end-to-end by FFmpeg. Real YouTube 4K metadata is verified; full 4K file download and playback are not.
- The same synthetic HLS source with a 150 ms response delay per segment measured 0.88 s at 1 fragment and 0.43 s at 4 (2.07× in the final run). This demonstrates concurrency on a controlled localhost fixture. It is not a measurement of YouTube or the user's internet speed.
- `uv build --offline` generated `dist/free_video_downloader-0.1.0.tar.gz` and `dist/free_video_downloader-0.1.0-py3-none-any.whl`. The source archive includes install/launch scripts.
- `scripts/install-user.sh` installed a temporary user launcher and `.desktop` entry under a test home. `desktop-file-validate` passed, and the generated launcher opened the offscreen app. A fresh Python 3.14 environment installed the wheel; its app entry point launched with the existing locked Qt dependencies exposed only for offline validation.
- The actual host is Arch Linux, Wayland, scale 1.25. The desktop-installed app stayed open in Wayland until its timed test stopped it. Ubuntu could not be tested because Docker socket access was denied. X11 is not active here. Native interactive folder/file opening and real downloads on both distributions remain to be checked.
- To install for the current user from this checkout, first install `uv`, Python 3, FFmpeg/ffprobe, and a supported JavaScript runtime, then run `./scripts/install-user.sh`. The script validates tools and does not install system packages. Ubuntu's `python3` package may be older than the app's `>=3.11` requirement; install a Python 3.11+ interpreter if so.
