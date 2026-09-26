import json
import sys
import unittest
from unittest.mock import patch

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from app.services.analysis import AnalysisJob, analysis_arguments
from app.services.formats import build_choices, validate_url
from app.ui.window import MainWindow
from app.services.store import Store


def sample():
    return {"title": "<b>Literal title</b>", "duration": 120, "formats": [
        {"format_id": "v", "url": "https://example.com/v", "ext": "mp4",
         "vcodec": "avc1", "acodec": "none", "height": 1080, "fps": 60, "filesize": 1000000},
        {"format_id": "a", "url": "https://example.com/a", "ext": "m4a",
         "vcodec": "none", "acodec": "mp4a.40.2", "abr": 128, "filesize": 200000},
        {"format_id": "drm", "url": "https://example.com/drm", "ext": "mp4",
         "vcodec": "avc1", "acodec": "mp4a", "height": 2160, "has_drm": True},
    ]}


class FormatTests(unittest.TestCase):
    def test_webm_4k_and_mixed_container_without_mp4_filter(self):
        info = sample()
        info["formats"][0].update(ext="webm", vcodec="vp9", height=2160, width=3840)
        info["formats"][1].update(ext="webm", acodec="opus")
        videos, _ = build_choices(info)
        self.assertEqual(videos[0].container, "webm")
        self.assertEqual(videos[0].height, 2160)
        self.assertIn("4K", videos[0].label)
        info["formats"][1].update(ext="m4a", acodec="mp4a")
        self.assertEqual(build_choices(info)[0][0].container, "mkv")

    def test_url_validation(self):
        for url in ("", "youtube.com/watch?v=1", "file:///etc/passwd", "https://", "https://a:bad", "https://a/ x"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)
        self.assertEqual(validate_url(" https://example.com/video?a=1&b=2 "), "https://example.com/video?a=1&b=2")

    def test_explicit_merge_and_audio_estimates(self):
        videos, audios = build_choices(sample())
        self.assertEqual(len(videos), 1)
        self.assertEqual(videos[0].selector, "v+a")
        self.assertIn("1080p", videos[0].label)
        self.assertIn("1.1 MiB", videos[0].details)
        self.assertEqual([c.bitrate for c in audios], [128, 192, 256, 320])
        self.assertIn("1.8 MiB", audios[0].details)

    def test_missing_audio_cannot_be_offered_as_normal_video(self):
        info = sample()
        info["formats"] = info["formats"][:1]
        with self.assertRaises(ValueError):
            build_choices(info)

    def test_muxed_unknown_size_and_audio_only(self):
        info = sample()
        info["formats"] = info["formats"][1:2]
        videos, audios = build_choices(info)
        self.assertFalse(videos)
        self.assertEqual(len(audios), 4)
        fmt = info["formats"][0]
        fmt.update(ext="mp4", vcodec="avc1", filesize=None)
        videos, _ = build_choices(info)
        self.assertIn("size unknown", videos[0].details)
        self.assertEqual(videos[0].selector, "a")

    def test_playlist_live_and_unavailable(self):
        for info in ({"_type": "playlist"}, {"is_live": True}, {"formats": []}):
            with self.subTest(info=info), self.assertRaises(ValueError):
                build_choices(info)

    def test_engine_uses_safe_metadata_only_arguments(self):
        args = analysis_arguments("https://example.com/a?x=1&y=2")
        self.assertIn("--skip-download", args)
        self.assertIn("--ignore-config", args)
        self.assertEqual(args[-2], "--")


class AsyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def run_job(self, program, cancel=False):
        job = AnalysisJob("https://example.com/video")
        job.process.setProgram(sys.executable)
        job.process.setArguments(["-c", program])
        values, errors, heartbeats = [], [], []
        job.succeeded.connect(values.append)
        job.failed.connect(errors.append)
        loop = QEventLoop()
        job.finished.connect(loop.quit)
        tick = QTimer()
        tick.timeout.connect(lambda: heartbeats.append(True))
        tick.start(10)
        deadline = QTimer()
        deadline.setSingleShot(True)
        deadline.timeout.connect(lambda: job.cancel("Test deadline"))
        deadline.start(3000)
        job.start()
        if cancel:
            QTimer.singleShot(60, job.cancel)
        loop.exec()
        tick.stop()
        deadline.stop()
        self.assertTrue(job.done)
        return values, errors, heartbeats

    def test_background_success_keeps_event_loop_alive(self):
        values, errors, ticks = self.run_job("import time; time.sleep(.1); print(" + repr(json.dumps(sample())) + ")")
        self.assertEqual(values[0]["title"], sample()["title"])
        self.assertFalse(errors)
        self.assertTrue(ticks)

    def test_errors_invalid_json_and_cancel(self):
        for program in ("import sys; sys.stderr.write('ERROR: Video unavailable'); sys.exit(1)", "print('bad json')"):
            values, errors, _ = self.run_job(program)
            self.assertFalse(values)
            self.assertTrue(errors)
        values, errors, _ = self.run_job("import time; time.sleep(30)", cancel=True)
        self.assertFalse(values)
        self.assertEqual(errors, ["Analysis cancelled."])

    def test_ui_selection_and_stale_result_reset(self):
        window = MainWindow(Store(":memory:"))
        window.url.setText("https://example.com/video")
        self.assertTrue(window.analyze.isEnabled())
        window.analysis_succeeded(sample())
        self.assertTrue(window.quality.isEnabled())
        self.assertIn("1080p", window.selection.text())
        self.assertIn("2:00", window.metadata.text())
        self.assertFalse(hasattr(window, "audio"))
        window.url.setText("https://example.com/other")
        self.assertIsNone(window.info)
        self.assertFalse(window.quality.isEnabled())
        self.assertFalse(window.download.isEnabled())
        window.url.setText("bad link")
        window.start_analysis()
        self.assertIn("http", window.status.text())
        self.assertIsNone(window.job)
        window.close()

    def test_closing_window_cancels_running_process(self):
        window = MainWindow(Store(":memory:"))
        window.url.setText("https://example.com/video")
        args = ["-c", "import time; time.sleep(30)"]
        with patch("app.services.analysis.analysis_arguments", return_value=args):
            window.start_analysis()
        job = window.job
        loop = QEventLoop()
        job.finished.connect(loop.quit)
        QTimer.singleShot(30, window.close)
        guard = QTimer()
        guard.setSingleShot(True)
        guard.timeout.connect(loop.quit)
        guard.start(3000)
        loop.exec()
        guard.stop()
        self.assertIsNone(window.job)
        self.assertTrue(window.close_pending)

    def test_bad_thumbnail_does_not_break_metadata(self):
        window = MainWindow(Store(":memory:"))
        window.analysis_succeeded(sample())
        window.show_thumbnail(b"not an image")
        self.assertEqual(window.preview.text(), "Thumbnail unavailable")
        self.assertTrue(window.quality.isEnabled())
        window.close()


if __name__ == "__main__":
    unittest.main()
