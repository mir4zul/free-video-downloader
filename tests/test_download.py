import contextlib
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
from time import perf_counter
import unittest
from unittest.mock import patch

from app.services.download_worker import run, verify_output, publish, ensure_mp3_bitrate
from app.services.download import DownloadJob
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
class DownloadIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=24",
            "-f", "lavfi", "-i", "sine=frequency=440", "-t", "2", "-c:v", "libx264",
            "-pix_fmt", "yuv420p", "-c:a", "aac", str(cls.root / "source.mp4")], check=True)
        for name, flag in (("video.mp4", "-an"), ("audio.m4a", "-vn")):
            subprocess.run(["ffmpeg", "-v", "error", "-i", str(cls.root / "source.mp4"),
                flag, "-c", "copy", str(cls.root / name)], check=True)
        cls.ranges = []
        cls.fragment_active = 0
        cls.fragment_peak = 0
        cls.fragment_lock = threading.Lock()
        cls.flaky_times = []
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(cls.root / "source.mp4"),
            "-c:v", "libx264", "-g", "12", "-c:a", "aac", "-hls_time", "0.5",
            "-hls_list_size", "0", str(cls.root / "segments.m3u8")], check=True)

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass
            def do_GET(self):
                name = self.path.lstrip("/")
                if name == "flaky.mp4":
                    cls.flaky_times.append(time.monotonic())
                    if len(cls.flaky_times) <= 2:
                        self.send_error(503)
                        return
                    name = "source.mp4"
                path = cls.root / name
                if not path.is_file():
                    self.send_error(404)
                    return
                data = path.read_bytes()
                start = int(self.headers.get("Range", "bytes=0-").split("=")[1].split("-")[0])
                if "Range" in self.headers:
                    cls.ranges.append(start)
                    self.send_response(206)
                    self.send_header("Content-Range", f"bytes {start}-{len(data)-1}/{len(data)}")
                else:
                    self.send_response(200)
                self.send_header("Content-Type", "application/vnd.apple.mpegurl" if name.endswith("m3u8") else "video/mp4")
                self.send_header("Content-Length", str(len(data) - start))
                self.end_headers()
                if name.endswith(".ts"):
                    with cls.fragment_lock:
                        cls.fragment_active += 1
                        cls.fragment_peak = max(cls.fragment_peak, cls.fragment_active)
                    time.sleep(.15)
                try:
                    self.wfile.write(data[start:])
                finally:
                    if name.endswith(".ts"):
                        with cls.fragment_lock:
                            cls.fragment_active -= 1

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def config(self, container="mp4", selector="direct"):
        return {"url": self.base + "/source.mp4", "folder": str(self.root / self._testMethodName),
                "container": container, "selector": selector, "bitrate": 192 if container == "mp3" else None}

    def metadata(self, split=False):
        formats = ([{"format_id": "v", "url": self.base + "/video.mp4", "ext": "mp4",
                     "vcodec": "avc1", "acodec": "none"},
                    {"format_id": "a", "url": self.base + "/audio.m4a", "ext": "m4a",
                     "vcodec": "none", "acodec": "mp4a"}] if split else
                   [{"format_id": "direct", "url": self.base + "/source.mp4", "ext": "mp4",
                     "vcodec": "avc1", "acodec": "mp4a"}])
        return {"id": "fixture", "title": "Download fixture", "duration": 2,
                "extractor": "fixture", "webpage_url": self.base + "/source.mp4", "formats": formats}

    def execute(self, config, split=False):
        from yt_dlp import YoutubeDL
        metadata = self.metadata(split)
        def extract(ydl, url, download=True):
            return ydl.process_ie_result(metadata, download=download)
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.object(YoutubeDL, "extract_info", extract):
            run(config)
        events = [json.loads(line) for line in output.getvalue().splitlines() if line.startswith("{")]
        self.assertEqual(events[-1]["type"], "completed")
        path = Path(events[-1]["path"])
        self.assertTrue(path.is_file())
        return path, events

    def test_video_audio_merge(self):
        path, events = self.execute(self.config(selector="v+a"), split=True)
        verify_output(path, "mp4", 2)
        self.assertTrue(any("Merging" in e.get("message", "") for e in events))
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"], check=True)

    def test_native_hls_four_fragments_and_progress(self):
        metadata = self.metadata()
        metadata["formats"][0].update(url=self.base + "/segments.m3u8", protocol="m3u8_native")
        type(self).fragment_peak = 0
        with patch.object(self, "metadata", return_value=metadata):
            path, events = self.execute(self.config())
        self.assertGreater(type(self).fragment_peak, 1)
        self.assertLessEqual(type(self).fragment_peak, 4)
        self.assertTrue(any(e["type"] == "progress" and e.get("speed") for e in events))
        verify_output(path, "mp4", 2)

    def test_same_source_parallel_speed_benchmark(self):
        timings = {}
        for fragments in (1, 4):
            metadata = self.metadata()
            metadata["formats"][0].update(url=self.base + "/segments.m3u8", protocol="m3u8_native")
            config = self.config(selector="direct")
            config["fragments"] = fragments
            type(self).fragment_peak = 0
            with patch.object(self, "metadata", return_value=metadata):
                started = perf_counter()
                path, _ = self.execute(config)
                timings[fragments] = perf_counter() - started
            verify_output(path, "mp4", 2)
        print(f"Same HLS fixture (150ms response delay/segment): 1 fragment {timings[1]:.2f}s; "
              f"4 fragments {timings[4]:.2f}s; speed ratio {timings[1]/timings[4]:.2f}x")
        self.assertLess(timings[4], timings[1])

    def test_http_retry_with_backoff(self):
        self.flaky_times.clear()
        metadata = self.metadata()
        metadata["formats"][0]["url"] = self.base + "/flaky.mp4"
        with patch.object(self, "metadata", return_value=metadata):
            self.execute(self.config())
        self.assertEqual(len(self.flaky_times), 3)
        self.assertGreaterEqual(self.flaky_times[1] - self.flaky_times[0], .9)
        self.assertGreaterEqual(self.flaky_times[2] - self.flaky_times[1], 1.9)

    def test_real_worker_process_download(self):
        app = QApplication.instance() or QApplication([])
        config = self.config(selector="best")
        job = DownloadJob(config)
        events = []
        job.event.connect(events.append)
        loop = QEventLoop()
        job.finished.connect(loop.quit)
        guard = QTimer()
        guard.setSingleShot(True)
        guard.timeout.connect(job.cancel)
        guard.start(15000)
        job.start()
        loop.exec()
        guard.stop()
        self.assertEqual(events[-1]["type"], "completed", events)
        verify_output(events[-1]["path"], "mp4", 2)

    def test_mp3_conversion(self):
        path, events = self.execute(self.config("mp3"))
        verify_output(path, "mp3", 2)
        self.assertTrue(any("Converting" in e.get("message", "") for e in events))
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"], check=True)

    def test_existing_mp3_honors_requested_bitrate(self):
        path = self.root / "low-bitrate.mp3"
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(self.root / "source.mp4"),
            "-vn", "-b:a", "64k", str(path)], check=True)
        with contextlib.redirect_stdout(io.StringIO()):
            ensure_mp3_bitrate(path, 192, verify_output(path, "mp3", 2))
        probe = verify_output(path, "mp3", 2)
        self.assertEqual(int(probe["streams"][0]["bit_rate"]), 192000)

    def test_partial_resume(self):
        config = self.config()
        key = hashlib.sha256(json.dumps([config["url"], "direct", "mp4", None]).encode()).hexdigest()[:24]
        work = Path(config["folder"]) / ".fvd-partials" / key
        work.mkdir(parents=True)
        data = (self.root / "source.mp4").read_bytes()
        offset = len(data) // 2
        (work / "media.mp4.part").write_bytes(data[:offset])
        self.ranges.clear()
        path, _ = self.execute(config)
        self.assertIn(offset, self.ranges)
        self.assertEqual(path.read_bytes(), data)

    def test_invalid_output_and_missing_stream_rejected(self):
        bad = self.root / "bad.mp4"
        bad.write_bytes(b"invalid")
        for path in (bad, self.root / "video.mp4"):
            with self.assertRaises(ValueError):
                verify_output(path, "mp4")
        with self.assertRaisesRegex(ValueError, "Resolution mismatch"):
            verify_output(self.root / "source.mp4", "mp4", expected_height=2160)
        verify_output(self.root / "source.mp4", "mp4", expected_height=240, expected_width=320)

    def test_webm_and_mkv_outputs(self):
        webm = self.root / "source.webm"
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(self.root / "source.mp4"),
            "-c:v", "libvpx-vp9", "-c:a", "libopus", str(webm)], check=True)
        metadata = self.metadata()
        metadata["formats"][0].update(url=self.base + "/source.webm", ext="webm", vcodec="vp9", acodec="opus")
        config = self.config("webm")
        with patch.object(self, "metadata", return_value=metadata):
            path, _ = self.execute(config)
        verify_output(path, "webm", expected_height=240)
        metadata = self.metadata(True)
        config = self.config("mkv", "v+a")
        with patch.object(self, "metadata", return_value=metadata):
            path, _ = self.execute(config)
        verify_output(path, "mkv", expected_height=240)

    def test_publish_preserves_existing_file(self):
        folder = self.root / self._testMethodName
        folder.mkdir()
        first = folder / "Video.mp4"
        first.write_bytes(b"existing")
        source = folder / "temp.mp4"
        source.write_bytes(b"new")
        destination = publish(source, folder, "Video", "mp4")
        self.assertEqual(first.read_bytes(), b"existing")
        self.assertEqual(destination.read_bytes(), b"new")

    def test_verification_failure_never_completes(self):
        with patch("app.services.download_worker.verify_output", side_effect=ValueError("broken")):
            with self.assertRaises(ValueError):
                self.execute(self.config())
        self.assertFalse(list(Path(self.config()["folder"]).glob("*.mp4")))


class DownloadProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_cancel_kills_child_and_never_reports_completion(self):
        job = DownloadJob({})
        job.process.setArguments(["-c", "import os,subprocess,json,time; os.setsid(); "
            "p=subprocess.Popen(['sleep','30']); print(json.dumps({'type':'stage','child':p.pid}),flush=True); time.sleep(30)"])
        events = []
        def receive(event):
            events.append(event)
            if "child" in event:
                job.cancel()
        job.event.connect(receive)
        loop = QEventLoop()
        job.finished.connect(loop.quit)
        guard = QTimer()
        guard.setSingleShot(True)
        guard.timeout.connect(job.cancel)
        guard.start(3000)
        job.start()
        loop.exec()
        guard.stop()
        self.assertEqual(events[-1]["type"], "cancelled")
        self.assertFalse(any(e["type"] == "completed" for e in events))
        child = next(e["child"] for e in events if "child" in e)
        status = Path(f"/proc/{child}/status")
        try:
            state = status.read_text()
        except (FileNotFoundError, ProcessLookupError):
            state = "Z (zombie)"  # Already reaped by the OS.
        self.assertIn("Z (zombie)", state)

    def test_nonzero_exit_cannot_report_completed(self):
        job = DownloadJob({})
        job.process.setArguments(["-c", "import json,sys; print(json.dumps({'type':'completed','path':'fake'})); sys.exit(1)"])
        events = []
        job.event.connect(events.append)
        loop = QEventLoop()
        job.finished.connect(loop.quit)
        job.start()
        loop.exec()
        self.assertEqual(events[-1]["type"], "failed")
        self.assertFalse(any(e["type"] == "completed" for e in events))
