# Free Video Downloader — Linux

Linux-এর জন্য একটি ফ্রি desktop downloader তৈরির পরিকল্পনা। YouTube বা অন্য supported website-এর video link দিলে আগে video preview এবং available format দেখাবে। এরপর পছন্দমতো video বা audio download করা যাবে।

**বর্তমান অবস্থা:** Step 1–5 implementation সম্পূর্ণ / OK। Step 6-এর automated tests, Arch Wayland launcher check, installer ও package build যাচাই হয়েছে। Real 720p–4K media playback/download, Ubuntu ও X11 যাচাই বাকি; তাই release validation আংশিক সম্পূর্ণ।

## বর্তমান নির্বাচন পদ্ধতি

ব্যবহারকারীর সংশোধিত নির্দেশ অনুযায়ী MP3/MP4 mode selector সরানো হয়েছে। এখন শুধু resolution নির্বাচন করতে হয়। নিচের পুরোনো milestone records-এ আগের MP4/MP3 implementation-এর বিবরণ ঐতিহাসিক তথ্য; নতুন interface-এ সেগুলো selection হিসেবে নেই। পূর্বে সংরক্ষিত MP3 queue/history-এর compatibility রাখা হয়েছে।

## ব্যবহার করার ধাপ

1. Video link paste করে **Analyze** চাপুন।
2. Thumbnail, title, duration এবং available quality দেখুন।
3. Available resolution (যেমন 720p, 1080p, 1440p/2K, 2160p/4K) বেছে নিন।
4. Source অনুযায়ী automatic output container দেখুন; format আলাদা করে বাছতে হয় না।
5. Save folder নির্বাচন করে **Download** চাপুন।
6. Progress, speed, remaining time এবং processing status দেখুন। শেষ হলে file বা folder খুলুন।

## ফিচারের লক্ষ্য

| বিষয় | পরিকল্পনা |
| --- | --- |
| Platform | প্রথম লক্ষ্য Arch Linux ও Ubuntu; অন্য Linux distro-তে dependency ও compatibility যাচাই সাপেক্ষে |
| Link | YouTube এবং downloader engine সমর্থিত অন্য website |
| Preview | Thumbnail, title, duration, source |
| Video | Source অনুযায়ী MP4/WebM/অন্য supported container; source-এ থাকলে 360p, 480p, 720p, 1080p, 1440p (সাধারণভাবে 2K বলা হয়), 2160p (4K) |
| Audio | নির্বাচিত ভিডিওর সঙ্গে source audio; নতুন download-এ audio-only/MP3 selector নেই |
| Format details | Resolution, FPS, codec এবং জানা থাকলে file size; estimate হলে তা উল্লেখ |
| Progress | Percentage, downloaded bytes, speed, ETA; merging/conversion-এর আলাদা status |
| Controls | Cancel, retry, queue, supported downloads resume |
| Storage | Folder picker, filename, completed download history |
| Speed | Supported fragmented streams-এ সীমিত parallel downloading; অপ্রয়োজনীয় conversion এড়ানো |

## Linux compatibility, interface ও speed পরিকল্পনা

- **Arch ও Ubuntu:** দুই distro-র জন্য আলাদা dependency/setup নির্দেশনা থাকবে। Python dependencies isolated environment-এ রাখার পরিকল্পনা, যাতে system Python-এর সঙ্গে সংঘাত না হয়। Release-এর সময় পরীক্ষিত distro ও version লিখতে হবে।
- **Desktop compatibility:** Wayland ও X11-এ launch, scaling, folder picker এবং file opening পরীক্ষা করা হবে। অন্য distro পরীক্ষা না হলে সেটিকে verified বলা হবে না।
- **Interface:** পরিষ্কার layout, readable text, video preview, স্পষ্ট resolution selector ও প্রধান Download button থাকবে। Analysis, downloading, merging, completed ও failed state আলাদা করে দেখাবে; দীর্ঘ কাজে window freeze হবে না।
- **Network ব্যবহার:** Default-এ app-এর নিজস্ব speed cap থাকবে না। Supported streams-এ configurable parallel fragments ব্যবহার করা হবে; অতিরিক্ত concurrency-তে error বাড়লে কমানোর সুযোগ থাকবে।
- **Speed display:** চলমান transfer-এর speed ও ETA দেখাবে; এটি internet package-এর advertised speed নয়। Source এবং network যতটুকু অনুমতি দেয় ততটুকু ব্যবহার করার লক্ষ্য থাকবে।
- **যাচাইয়ের শর্ত:** Arch ও Ubuntu-তে install, link analysis, MP4/MP3 download এবং playback পরীক্ষা পাস করতে হবে। Speed তুলনায় একই source ও network ব্যবহার করে ফল লিখতে হবে; পরীক্ষা ছাড়া “full speed” দাবি করা হবে না।

## বাস্তব সীমা

- সব website বা সব link কাজ করবে এমন নিশ্চয়তা নেই। Unsupported, unavailable বা login-required link হলে পরিষ্কার error দেখাবে।
- Source-এ যে resolution আছে শুধু সেটিই দেখাবে; 720p video থেকে আসল 4K তৈরি করবে না।
- MP4 একটি container; codec compatibility আলাদা বিষয়। দ্রুত download-এর জন্য compatible streams merge করা হবে। Conversion দরকার হলে সময় লাগার বিষয়টি আগে দেখাবে।
- MP3 bitrate বাড়ালে source audio-এর আসল quality বাড়ে না।
- Download speed internet connection, source server এবং throttling-এর ওপর নির্ভর করে; নির্দিষ্ট speed নিশ্চিত করা যাবে না।

## প্রস্তাবিত প্রযুক্তি ও গঠন

- **Python + PySide6:** Linux desktop interface।
- **yt-dlp:** Video information, available formats এবং download engine।
- **FFmpeg / ffprobe:** Video/audio merge, MP3 conversion এবং output verification।
- **Background worker:** Analysis, download ও conversion চললেও interface responsive থাকবে।
- **Local settings/history:** Save folder ও download history রাখা হবে।
- **Dependency check:** yt-dlp, FFmpeg এবং YouTube extraction-এর জন্য প্রয়োজনীয় JavaScript runtime/components পরীক্ষা করে setup নির্দেশনা দেখাবে।
- **Process execution:** URL shell command হিসেবে চালানো হবে না; argument list ব্যবহার করা হবে এবং cancel করলে child process বন্ধ হবে।

প্রস্তাবিত code layout: `app/ui/`, `app/services/`, `app/workers/`, `app/storage/`, `tests/`। Implementation-এর সময় dependency versions ও install commands যাচাই করে যোগ করা হবে।

## কাজের চেকলিস্ট

`[x]` = শেষ / OK; `[ ]` = বাকি। কাজ implement এবং উপযুক্তভাবে verify হওয়ার পরই সংশ্লিষ্ট checkbox update হবে।

### 1. পরিকল্পনা

- [x] চাহিদা, user flow এবং feature scope লেখা — OK
- [x] প্রস্তাবিত প্রযুক্তি ও বাস্তব সীমা নির্ধারণ — OK
- [x] README এবং ধাপে ধাপে checklist তৈরি — OK
- [x] Arch/Ubuntu compatibility ও অন্য distro যাচাইয়ের পরিকল্পনা লেখা — OK
- [x] সুন্দর responsive interface ও network speed ব্যবহারের লক্ষ্য লেখা — OK

### 2. Project setup

- [x] Python project, dependencies ও application entry point তৈরি — OK
- [x] Main window, URL input, Analyze button ও folder picker তৈরি — OK
- [x] Readable layout, preview area ও পরিষ্কার Video/Audio controls তৈরি — OK
- [x] Dependency detection এবং প্রয়োজনীয় setup নির্দেশনা যোগ — OK

### 3. Link analysis ও format নির্বাচন

- [x] Background-এ link analyze এবং thumbnail/title/duration দেখানো — OK
- [x] Available video/audio formats থেকে সঠিক options তৈরি — OK
- [x] MP4 quality selector এবং MP3 bitrate selector তৈরি — OK
- [x] Unavailable format, invalid link এবং source error handle করা — OK
- [x] নির্বাচিত output format, quality ও সম্ভাব্য size দেখানো — OK

### 4. Download ও conversion

- [x] নির্বাচিত video ও audio streams download এবং merge — OK
- [x] Audio-only download ও MP3 conversion — OK
- [x] Progress, speed, ETA এবং processing status দেখানো — OK
- [x] Cancel/retry এবং supported partial download resume — OK
- [x] Output file verify হওয়ার পরেই completed দেখানো — OK

### 5. Speed ও ব্যবহার সুবিধা

- [x] Configurable fragment concurrency যোগ; প্রথমে 4 দিয়ে পরীক্ষা — OK
- [x] Default speed cap ছাড়া transfer এবং live speed/ETA যাচাই — OK
- [x] Network failure-এ সীমিত retry এবং backoff — OK
- [x] Download queue ও একসঙ্গে download-এর সীমা — OK
- [x] Settings, history এবং open file/folder actions — OK
- [x] Duplicate filename, low disk space ও write permission error handle করা — OK

### 6. যাচাই ও release — 2026-09-26

- [x] Resolution-based format selection, quality/container labels, mismatch rejection, error handling ও queue tests
- [ ] Real YouTube link-এ 720p/1080p/2K/4K media download, output resolution ও playback
- [x] Local media fixtures-এ MP4/WebM/MKV merge, playback decode, exact resolution match/mismatch verification
- [x] Cancel, HTTP retry/backoff, interrupted partial resume, child-process cleanup ও verification failure tests
- [x] 1 বনাম 4 fragments, একই throttled HLS fixture; environment ও ফল নিচে লেখা
- [x] Linux launch script, user desktop launcher, build artifacts এবং installation guide তৈরি
- [ ] Arch-এ real supported media download/playback যাচাই; শুধু YouTube format analysis সফল হয়েছে
- [ ] Ubuntu install/download/playback: এই host Arch; Docker socket access অনুমতি দেয়নি, তাই Ubuntu যাচাই করা যায়নি
- [x] Wayland session-এ user desktop launcher দিয়ে launch; 125% scaling-এ offscreen UI tests
- [ ] X11 session, native interactive folder/file opening যাচাই; বর্তমান session Wayland, path-opening test desktop service mock ব্যবহার করে
- [x] Clean temporary Python environment-এ wheel install করে offscreen app launch
- [x] PyPI sdist ও wheel build সফল; sdist-এ user installation scripts আছে

## প্রথম ব্যবহারযোগ্য সংস্করণের শর্ত

Link paste → preview → available resolution নির্বাচন → folder নির্বাচন → download → resolution-verified output file। পুরো কাজের সময় UI responsive থাকবে এবং failure হলে completed দেখাবে না। এরপর queue, history ও speed tuning শেষ করা হবে।

## Reference

Engine capabilities, format selection, dependencies এবং download options-এর ভিত্তি: [yt-dlp official documentation](https://github.com/yt-dlp/yt-dlp#readme)।

## Development setup ও চালানো

Python 3.11+ এবং `uv` প্রয়োজন। Project folder থেকে:

```bash
uv sync --locked
uv run --locked free-video-downloader
```

বিকল্পভাবে Python virtual environment দিয়ে:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m app
```

`uv.lock` নির্দিষ্ট dependency versions রাখে; pip-এর বিকল্পটি lock file ব্যবহার করে না। PySide6-এর bundled Qt ব্যবহার হবে; system Python-এ package install প্রয়োজন নেই। [Qt setup documentation](https://doc.qt.io/qtforpython-6/gettingstarted.html)।

Download engine-এর system dependencies:

```bash
# Arch Linux
sudo pacman -Syu python uv ffmpeg deno

# Ubuntu (Deno optional; installed Node also works)
sudo apt update
sudo apt install ffmpeg python3 python3-venv
```

Ubuntu-তে Deno setup-এর জন্য [official installation guide](https://docs.deno.com/runtime/getting_started/installation/) অনুসরণ করুন। Arch-এর [Deno package](https://archlinux.org/packages/extra/x86_64/deno/) ব্যবহার করা যাবে। App-এর **Check setup** PySide6, yt-dlp, yt-dlp-ejs, FFmpeg/ffprobe ও Deno অথবা Node পাওয়া যাচ্ছে কি না দেখায়; এটি version compatibility বা বাস্তব download পরীক্ষা নয়। Deno না থাকলে installed Node analysis-এর জন্য enable করা হয়। কোনো system package নিজে থেকে install করে না।

Link paste করে **Analyze** চাপলে title, duration, thumbnail ও source-এর available formats দেখা যায়। Resolution এবং folder বেছে **Download / Add to queue** চাপুন। কাজ শেষে verified output file-এর path দেখাবে।

Arch/Ubuntu-তে user-level launcher ও desktop app entry বসাতে project folder-এ `./scripts/install-user.sh` চালান। আগে `uv`, Python 3 এবং FFmpeg/ffprobe install থাকতে হবে; script Ubuntu/Arch package manager থেকে system dependency নিজে install করে না। Desktop app menu-তে “Free Video Downloader” দেখা যাবে। Source folder সরালে launcher-টি reinstall করুন। Development থেকে সরাসরি চালাতে `./scripts/run.sh` ব্যবহার করুন।

Analysis চলার সময় **Cancel** করা যায়; 90 সেকেন্ডে timeout হয়। নতুন link লিখলে পুরোনো metadata ও selection মুছে যায়। Thumbnail পাওয়া না গেলেও format নির্বাচন করা যায়। Playlist, live/upcoming stream, DRM-only source এবং unusable formats-এর ক্ষেত্রে error দেখায়।

Resolution তালিকা source video formats থেকে তৈরি হয়; MP4-only filter নেই। নির্বাচিত resolution-এর সঙ্গে container নাম selector-এ দেখায়। MP4+AAC হলে MP4, WebM+Opus/Vorbis হলে WebM; অন্য mixed combination-এ MKV ব্যবহার করে codec re-encode ছাড়া audio/video merge হয়। আগে থেকেই audio থাকা file তার supported source container রাখে। Video re-encode বা upscale হয় না। Download শেষে নির্বাচিত height/width FFprobe দিয়ে মিলিয়ে দেখে; mismatch হলে Completed দেখায় না।

Headless interface checks:

```bash
QT_QPA_PLATFORM=offscreen uv run --locked python -m unittest discover -s tests -v
```

### Step 2 যাচাই

- Arch host-এ isolated environment install ও `uv sync --locked --offline` সফল।
- দুইটি automated test পাস: missing dependencies report; folder নির্বাচন/cancel এবং Video/Audio mode switching।
- Offscreen Qt window render করে layout দেখা হয়েছে; syntax check পাস।
- Step 2 পরীক্ষায় এই host-এ FFmpeg/ffprobe ও Python dependencies ছিল; Deno missing দেখানো হয়েছিল। Step 3-এ installed Node fallback যুক্ত হয়েছে।
- Native Wayland/X11 session, Ubuntu এবং বাস্তব download এখনো পরীক্ষা হয়নি; এগুলো পরবর্তী checklist-এ বাকি আছে।

### Step 3 যাচাই — 2026-09-23

- মোট 13টি automated test পাস: URL validation, audio/video pairing, DRM filtering, unknown size, MP3 estimate, playlist/live rejection, subprocess success/error/invalid JSON/cancel, responsive event loop, close cleanup, thumbnail failure এবং stale selection reset।
- বাস্তব YouTube `jNQXAC9IVRw` link-এ “Me at the zoo” metadata, 10টি MP4 option ও 4টি MP3 bitrate option পাওয়া গেছে। Thumbnail fetch ও image decode সফল (20,969 bytes)। এটি ওই link-এর পরীক্ষার ফল, সব video-র format সংখ্যা নয়।
- Unavailable YouTube `BaW_jenozKc` link-এর source error সঠিকভাবে report হয়েছে।
- Step 3-এ headless UI render দেখে preview ও selection layout যাচাই করা হয়েছিল; সেই ধাপে media download করা হয়নি।

### Step 4 ব্যবহার ও যাচাই — 2026-09-23

- Download-এর সময় percentage, bytes, speed ও ETA বর্তমান stream-এর জন্য দেখায়। আলাদা video/audio download হলে পরের stream-এ percentage আবার শুরু হয়। Merge, conversion ও verification আলাদা status; অজানা total হলে indeterminate progress।
- **Cancel download** worker এবং তার FFmpeg/ffprobe process group বন্ধ করে। **Retry / Resume** আগের link, format ও folder-ই ব্যবহার করে; source HTTP range/fragment resume সমর্থন করলে partial data reuse হয়। Conversion বন্ধ হলে সেটি আবার শুরু হয়।
- Partial files নির্বাচিত folder-এর `.fvd-partials/`-এ থাকে। App restart-এর পরও একই link, format ও folder দিয়ে Download করলে resume করার চেষ্টা করে। Source-এ format বদলে গেলে আবার Analyze করতে হবে।
- Output nonempty কি না, container, প্রয়োজনীয় audio/video streams এবং duration FFprobe দিয়ে পরীক্ষা করা হয়। যাচাই ব্যর্থ হলে Completed দেখায় না। এটি প্রতিটি file-এর full decode test নয়।
- Verified output folder-এ publish হয়; একই নাম থাকলে `(1)`, `(2)` suffix যোগ হয়। বর্তমান atomic publication-এর জন্য destination filesystem-এ hard-link support প্রয়োজন (যেমন ext4/Btrfs); unsupported filesystem হলে error দেখাবে।
- মোট 23টি automated test পাস। Local HTTP fixture-এ বাস্তব bytes download, আলাদা video/audio merge, MP3 conversion/bitrate, range resume, invalid output rejection, duplicate filename preservation, worker exit ও child-process cancellation পরীক্ষা হয়েছে। Tests localhost socket খোলে এবং FFmpeg/ffprobe প্রয়োজন।
- বাস্তব YouTube “Me at the zoo” দিয়ে MP4 ও 128 kbps MP3 download সফল; দুটো output পুরো FFmpeg decode test পাস করেছে।
- 720p–4K-এর বিস্তৃত পরীক্ষা, Ubuntu/Wayland/X11 release validation, queue/history ও speed tuning পরবর্তী ধাপে বাকি।

### Step 5 ব্যবহার ও যাচাই

- **New download** tab-এ Analyze করে format/folder বেছে **Download / Add to queue** চাপুন। **Downloads & history** tab-এ প্রতিটি কাজের state, stream progress, speed ও ETA দেখা যায়। Download চলার সময় অন্য link Analyze করা যায়।
- **Parallel fragments:** default 4, সীমা 1–16; supported fragmented streams-এর জন্য, নতুন queue entry-তে প্রযোজ্য। Direct single-file transfer-কে এটি স্বয়ংক্রিয়ভাবে split করে না।
- **Simultaneous downloads:** default 2, সীমা 1–4, প্রতি window-তে। Limit কমালে চলমান কাজ বন্ধ হয় না; সেগুলো শেষ হলে কম limit মেনে নতুন কাজ শুরু হয়। দুই সীমা একসঙ্গে বাড়ালে connection ও CPU ব্যবহার বাড়বে।
- Engine-এ speed cap নেই। HTTP/fragment/extractor retry সর্বোচ্চ 3 বার; retry delay 1, 2, 4 সেকেন্ড। Source server-এর limit থাকলে পুরো internet speed পাওয়া নিশ্চিত নয়।
- Queue/history থেকে row select করে **Cancel selected**, **Retry / Resume**, **Open file**, **Open folder** ব্যবহার করুন। Retry আগের format/folder/settings ব্যবহার করে। একই কাজ চলমান বা queued থাকলে duplicate যোগ হয় না।
- Save folder, concurrency settings এবং job history SQLite-এ থাকে: `$XDG_DATA_HOME/free-video-downloader/state.sqlite3`, default `~/.local/share/free-video-downloader/state.sqlite3`। Tests/isolated runs-এর জন্য `FVD_DATA_DIR` ব্যবহার করা যায়। পুরোনো Step 4 downloads history-তে নিজে থেকে import হয় না।
- App বন্ধ করলে active jobs cancel এবং waiting jobs interrupted হয়। পরের launch-এ অসমাপ্ত কাজ নিজে থেকে download শুরু করে না; row select করে Retry / Resume করুন।
- Folder-এ write check হয়। Estimated output size জানা থাকলে তার প্রায় দ্বিগুণ এবং 32 MiB reserve ধরে free-space preflight হয়; অজানা size-এ 32 MiB reserve check হয়। Transfer চলার সময়ও periodically free space পরীক্ষা হয়। Estimate download সফল হওয়ার নিশ্চয়তা নয়; disk-full/permission failure-এ error দেখায় ও partial data থাকে।
- মোট 32টি automated test পাস। Local HLS fixture-এ default 4 fragments দিয়ে concurrent requests, live speed events ও verified output; HTTP 503-এর পরে বাস্তব 1s/2s backoff ও successful retry পরীক্ষা হয়েছে।
- Queue limits/FIFO/cancel/retry/shutdown, settings/history restart, duplicate handling, missing files, low disk space ও permission errors পরীক্ষা হয়েছে। Desktop-open URL dispatch mock দিয়ে যাচাই; native desktop application launch-এর পূর্ণ পরীক্ষা Step 6-এ বাকি।
- Downloads & history tab headless render করে দেখা হয়েছে। Controlled local network benchmark ও distribution-wide release সীমাগুলো Step 6-এ নথিভুক্ত।

### Step 6 release verification — 2026-09-26

- Resolution selector-এ output container label যোগ হয়েছে। Selection source-এর available resolution-এ map হয়; download শেষে FFprobe-এ height/width না মিললে Completed হয় না। Full automated suite: 35 tests pass, including a synthetic 2160p selection/mismatch test and MP4/WebM/MKV playback validation using generated clips.
- Real YouTube `ocVNYZ9O1G0` (“Big Buck Bunny [4k 2160p 60fps]”) link analyzed successfully. Available formats included 2160p, 1440p, 1080p and 720p, each at 60 fps. The best MP4 2160p stream reported no size. A WebM 2160p stream was reported at about 955 MB. 4K media download/playback was deliberately left unverified because the source is 635 seconds long and the MP4 size is unknown; the network may transfer over 1 GB. Another 4K test link was unavailable.
- Local generated MP4/WebM/MKV outputs were decoded end-to-end by FFmpeg. Real YouTube 4K metadata is verified; full 4K file download and playback are not.
- The same synthetic HLS source with a 150 ms response delay per segment measured 0.88 s at 1 fragment and 0.43 s at 4 (2.07× in the final run). This demonstrates concurrency on a controlled localhost fixture. It is not a measurement of YouTube or the user's internet speed.
- `uv build --offline` generated `dist/free_video_downloader-0.1.0.tar.gz` and `dist/free_video_downloader-0.1.0-py3-none-any.whl`. The source archive includes install/launch scripts.
- `scripts/install-user.sh` installed a temporary user launcher and `.desktop` entry under a test home. `desktop-file-validate` passed, and the generated launcher opened the offscreen app. A fresh Python 3.14 environment installed the wheel; its app entry point launched with the existing locked Qt dependencies exposed only for offline validation.
- The actual host is Arch Linux, Wayland, scale 1.25. The desktop-installed app stayed open in Wayland until its timed test stopped it. Ubuntu could not be tested because Docker socket access is denied. X11 is not active here. Native interactive folder/file opening and real downloads on both distributions remain to be checked.
- To install for the current user from this checkout, first install `uv`, Python 3, FFmpeg/ffprobe and a supported JavaScript runtime, then run `./scripts/install-user.sh`. The script validates tools and does not install system packages. Ubuntu’s `python3` package may be older than the app’s `>=3.11` requirement; install a Python 3.11+ interpreter if so.
