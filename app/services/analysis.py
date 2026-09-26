"""Asynchronous, cancellable metadata extraction; never downloads media."""
import json
import sys
from shutil import which

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from app.services.formats import validate_url


def analysis_arguments(url):
    args = ["-m", "yt_dlp", "--ignore-config", "--no-plugin-dirs", "--no-playlist",
            "--flat-playlist", "--skip-download", "--dump-single-json", "--no-progress",
            "--no-colors", "--socket-timeout", "15", "--retries", "1",
            "--extractor-retries", "1", "--no-cache-dir"]
    # Deno is enabled by default; explicitly enable Node when it is the available runtime.
    if not which("deno") and which("node"):
        args += ["--js-runtimes", "node"]
    return args + ["--", validate_url(url)]


class AnalysisJob(QObject):
    succeeded = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.arguments = analysis_arguments(url)
        self.process = QProcess(self)
        self.process.setProgram(sys.executable)
        self.process.setArguments(self.arguments)
        self.output = bytearray()
        self.errors = bytearray()
        self.reason = None
        self.done = False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(lambda: self.cancel("Analysis timed out. Check your connection and retry."))
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.readyReadStandardError.connect(self.read_errors)
        self.process.finished.connect(self.complete)
        self.process.errorOccurred.connect(self.process_error)

    def start(self):
        self.timer.start(90000)
        self.process.start()

    def read_output(self):
        self.output.extend(bytes(self.process.readAllStandardOutput()))
        if len(self.output) > 16 * 1024 * 1024:
            self.cancel("Metadata is too large. Use a single video link.")

    def read_errors(self):
        self.errors.extend(bytes(self.process.readAllStandardError()))
        self.errors = self.errors[-16000:]

    def cancel(self, reason="Analysis cancelled."):
        if self.done:
            return
        self.reason = reason
        self.process.kill()

    def process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.reason = "Could not start the analysis engine. Check your Python environment."
            self.complete(-1)

    def complete(self, code, *_):
        if self.done:
            return
        self.read_output()
        self.read_errors()
        self.done = True
        self.timer.stop()
        if self.reason:
            self.failed.emit(self.reason)
        elif code:
            lines = self.errors.decode("utf-8", errors="replace").strip().splitlines()
            errors = [line for line in lines if "ERROR:" in line]
            detail = (errors or lines or ["No metadata returned."])[-1]
            self.failed.emit("Could not analyze this link. " + detail[:1800])
        else:
            try:
                info = json.loads(self.output)
                if not isinstance(info, dict):
                    raise ValueError()
                self.succeeded.emit(info)
            except (ValueError, TypeError):
                self.failed.emit("The source returned invalid metadata. Try another link.")
        self.finished.emit()
