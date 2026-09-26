import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication
from app.services.queue import DownloadQueue
from app.services.store import Store
from app.services.download_worker import prepare_folder, transfer_options, retry_delay
from app.ui.queue_panel import QueuePanel
from app.ui.window import MainWindow


class FakeJob(QObject):
    event = Signal(object)
    finished = Signal()
    def __init__(self, config, parent):
        super().__init__(parent)
        self.config = config
        self.cancelled = False
    def start(self):
        pass
    def cancel(self):
        self.cancelled = True
        self.event.emit({"type": "cancelled", "message": "Cancelled"})
        self.finished.emit()
    def complete(self):
        self.event.emit({"type": "completed", "path": "/tmp/result.mp4"})
        self.finished.emit()


class QueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.store = Store(":memory:")
        self.queue = DownloadQueue(self.store, 2, FakeJob)
    def tearDown(self):
        self.queue.shutdown()
        self.store.db.close()
    def add(self, name):
        return self.queue.add({"url": "https://example.com/" + name, "folder": "/tmp", "container": "mp4", "selector": "1"})

    def test_limit_fifo_and_lowering_limit(self):
        tasks = [self.add(str(n)) for n in range(4)]
        self.queue.pump()
        self.assertEqual(len(self.queue.active), 2)
        self.queue.set_limit(1)
        self.queue.active[tasks[0]["id"]].complete()
        self.queue.pump()
        self.assertEqual(tasks[2]["state"], "queued")
        self.queue.active[tasks[1]["id"]].complete()
        self.queue.pump()
        self.assertEqual(tasks[2]["state"], "running")
        self.assertEqual(tasks[3]["state"], "queued")

    def test_duplicate_cancel_retry_and_shutdown(self):
        task = self.add("a")
        with self.assertRaises(ValueError):
            self.add("a")
        self.queue.cancel(task)
        self.assertEqual(task["state"], "cancelled")
        self.queue.retry(task)
        self.queue.pump()
        waiting = self.add("b")
        self.queue.shutdown()
        self.queue.pump()
        self.assertFalse(self.queue.active)
        self.assertEqual(waiting["state"], "interrupted")

    def test_restart_restores_history_and_requires_manual_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.sqlite3"
            first = Store(path)
            first.set_setting("fragments", 8)
            first.save({"id": "a", "state": "running", "config": {}, "message": ""})
            first.save({"id": "b", "state": "completed", "config": {}, "path": "/tmp/done.mp4"})
            first.db.close()
            second = Store(path)
            queue = DownloadQueue(second, factory=FakeJob)
            self.assertEqual(second.setting("fragments", 4), 8)
            self.assertEqual(queue.tasks[0]["state"], "interrupted")
            self.assertEqual(queue.tasks[1]["path"], "/tmp/done.mp4")
            self.assertFalse(queue.active)
            second.db.close()

    def test_open_missing_file_and_desktop_url(self):
        task = self.add("a")
        self.queue.cancel(task)
        task.update(state="completed", path="/does/not/exist.mp4")
        panel = QueuePanel(self.queue, self.store)
        panel.tree.setCurrentItem(panel.rows[task["id"]])
        with patch("app.ui.queue_panel.QDesktopServices.openUrl", return_value=True) as opener:
            panel.open_path(False)
            opener.assert_not_called()
            panel.open_path(True)
            self.assertTrue(opener.call_args.args[0].isLocalFile())
        panel.close()

    def test_window_can_add_new_link_while_queue_runs(self):
        from test_analysis import sample
        window = MainWindow(self.store)
        window.queue.factory = FakeJob
        window.url.setText("https://example.com/one")
        window.analysis_succeeded(sample())
        window.start_download()
        window.queue.pump()
        self.assertTrue(window.queue.active)
        self.assertTrue(window.url.isEnabled())
        window.url.setText("https://example.com/two")
        self.assertTrue(window.analyze.isEnabled())
        self.assertEqual(window.queue.tasks[0]["config"]["url"], "https://example.com/one")
        window.close()
        self.assertFalse(window.queue.active)


class TransferSettingsTests(unittest.TestCase):
    def test_defaults_limits_and_backoff(self):
        options = transfer_options({})
        self.assertEqual(options["concurrent_fragment_downloads"], 4)
        self.assertIsNone(options["ratelimit"])
        self.assertEqual(options["retries"], 3)
        self.assertEqual([retry_delay(n) for n in (0, 1, 2, 3, 4)], [1, 2, 4, 8, 8])
        self.assertEqual(transfer_options({"fragments": 99})["concurrent_fragment_downloads"], 16)

    def test_disk_and_permission_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("app.services.download_worker.shutil.disk_usage", return_value=SimpleNamespace(free=1)):
                with self.assertRaisesRegex(ValueError, "disk space"):
                    prepare_folder(Path(directory), 100)
            with patch("app.services.download_worker.tempfile.TemporaryFile", side_effect=PermissionError()):
                with self.assertRaisesRegex(ValueError, "writable"):
                    prepare_folder(Path(directory))
