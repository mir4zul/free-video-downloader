import json
import os
import signal
import sys

from PySide6.QtCore import QObject, QProcess, Signal


class DownloadJob(QObject):
    event = Signal(object)
    finished = Signal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.process = QProcess(self)
        self.process.setProgram(sys.executable)
        self.process.setArguments(["-m", "app.services.download_worker"])
        self.process.started.connect(self.send_config)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.readyReadStandardError.connect(self.read_errors)
        self.process.finished.connect(self.complete)
        self.process.errorOccurred.connect(self.process_error)
        self.buffer = bytearray()
        self.errors = bytearray()
        self.cancelled = False
        self.terminal = False
        self.done = False
        self.result = None

    def start(self):
        self.process.start()

    def send_config(self):
        self.process.write((json.dumps(self.config) + "\n").encode())
        self.process.closeWriteChannel()
        if self.cancelled:
            self.cancel()

    def read_errors(self):
        self.errors.extend(bytes(self.process.readAllStandardError()))
        self.errors = self.errors[-8000:]

    def read_output(self):
        self.buffer.extend(bytes(self.process.readAllStandardOutput()))
        while b"\n" in self.buffer:
            line, _, self.buffer = self.buffer.partition(b"\n")
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("type") == "completed":
                self.result = event
            elif event.get("type") == "failed":
                self.terminal = True
                self.event.emit(event)
            elif not self.cancelled:
                self.event.emit(event)

    def cancel(self):
        if self.done:
            return
        self.cancelled = True
        pid = self.process.processId()
        if pid:
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                self.process.kill()  # Worker may not have created its session yet.

    def process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.errors.extend(b"Could not start download worker.")
            self.complete(-1)

    def complete(self, code, *_):
        if self.done:
            return
        self.read_output()
        self.read_errors()
        self.done = True
        if self.result and code == 0:
            self.event.emit(self.result)
        elif not self.terminal:
            self.event.emit({"type": "cancelled" if self.cancelled else "failed", "message":
                "Cancelled. Retry resumes supported partial downloads." if self.cancelled else
                self.errors.decode(errors="replace")[-1500:] or "Download failed before output verification."})
        self.finished.emit()
