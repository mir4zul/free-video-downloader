from datetime import datetime, timezone
from uuid import uuid4
import sqlite3

from PySide6.QtCore import QObject, Signal, QTimer
from app.services.download import DownloadJob


class DownloadQueue(QObject):
    changed = Signal()
    idle = Signal()
    storage_error = Signal(str)

    def __init__(self, store, limit=2, factory=DownloadJob, parent=None):
        super().__init__(parent)
        self.store, self.factory = store, factory
        self.limit = max(1, min(4, int(limit)))
        self.active = {}
        self.stopping = False
        self.tasks = store.tasks()
        for task in self.tasks:
            if task["state"] in ("queued", "running"):
                task.pop("pause_requested", None)
                task.update(state="interrupted", message="Interrupted — choose Retry / Resume.")
                self.persist(task)

    def persist(self, task):
        try:
            self.store.save(task)
        except (sqlite3.Error, OSError) as error:
            self.storage_error.emit("Could not save download history: " + str(error))

    def add(self, config):
        signature = lambda c: tuple(c.get(k) for k in ("url", "selector", "container", "bitrate", "folder"))
        for task in self.tasks:
            if task["state"] in ("queued", "running") and signature(task["config"]) == signature(config):
                raise ValueError("This format is already queued or downloading.")
        task = {"id": uuid4().hex, "config": dict(config), "state": "queued", "message": "Waiting…",
                "created": datetime.now(timezone.utc).isoformat(), "path": ""}
        self.tasks.append(task)
        self.persist(task)
        self.changed.emit()
        QTimer.singleShot(0, self.pump)
        return task

    def set_limit(self, limit):
        self.limit = max(1, min(4, int(limit)))
        self.pump()

    def pump(self):
        if self.stopping:
            return
        for task in self.tasks:
            if len(self.active) >= self.limit:
                break
            if task["state"] != "queued":
                continue
            task.update(state="running", message="Starting…")
            job = self.factory(task["config"], self)
            self.active[task["id"]] = job
            job.event.connect(lambda event, t=task: self.receive(t, event))
            job.finished.connect(lambda t=task: self.finished(t))
            self.persist(task)
            job.start()
        self.changed.emit()

    def receive(self, task, event):
        kind = event.get("type")
        task["event"] = event
        if kind == "progress":
            task["last_progress"] = event
        if kind in ("completed", "failed", "cancelled"):
            if kind == "cancelled" and task.pop("pause_requested", False):
                task.update(state="paused", message="Paused. Resume to continue the partial download.")
            else:
                task.update(state=kind, message=event.get("message", "Completed and verified"))
            if kind == "completed":
                task["path"] = event["path"]
                task["completed"] = datetime.now(timezone.utc).isoformat()
            self.persist(task)
        elif event.get("message"):
            task["message"] = event["message"]
        self.changed.emit()

    def finished(self, task):
        job = self.active.pop(task["id"])
        job.deleteLater()
        if task["state"] == "running":
            task.update(state="failed", message="Worker stopped without a verified output.")
            self.persist(task)
        self.changed.emit()
        if not self.active:
            self.idle.emit()
        QTimer.singleShot(0, self.pump)

    def cancel(self, task):
        job = self.active.get(task["id"])
        if job:
            job.cancel()
        elif task["state"] == "queued":
            task.update(state="cancelled", message="Removed from queue.")
            self.persist(task)
            self.changed.emit()

    def pause(self, task):
        if task["state"] == "queued":
            task.update(state="paused", message="Paused before starting. Resume when ready.")
            self.persist(task)
            self.changed.emit()
            return
        job = self.active.get(task["id"])
        if job and task["state"] == "running":
            task["pause_requested"] = True
            task.update(message="Pausing and saving resumable data…")
            self.persist(task)
            self.changed.emit()
            job.cancel()

    def retry(self, task):
        if task["id"] in self.active or task["state"] not in (
                "paused", "failed", "cancelled", "interrupted"):
            return
        signature = lambda c: tuple(c.get(k) for k in ("url", "selector", "container", "bitrate", "folder"))
        if any(t is not task and t["state"] in ("running", "queued") and
               signature(t["config"]) == signature(task["config"]) for t in self.tasks):
            raise ValueError("This format is already queued or downloading.")
        was_paused = task["state"] == "paused"
        task.pop("pause_requested", None)
        task.update(state="queued", message="Waiting to resume…" if was_paused else "Waiting to retry…",
                    event={})
        self.persist(task)
        self.changed.emit()
        QTimer.singleShot(0, self.pump)

    def shutdown(self):
        self.stopping = True
        for task in self.tasks:
            if task["state"] == "queued":
                task.update(state="interrupted", message="App closed — choose Retry / Resume.")
                self.persist(task)
        for job in list(self.active.values()):
            job.cancel()
