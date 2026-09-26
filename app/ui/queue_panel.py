from pathlib import Path
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QPushButton, QTreeWidget, QTreeWidgetItem
from app.services.formats import size_text, duration_text


class QueuePanel(QWidget):
    def __init__(self, queue, store, parent=None):
        super().__init__(parent)
        self.queue, self.store = queue, store
        self.rows = {}
        layout = QVBoxLayout(self)
        settings = QHBoxLayout()
        settings.addWidget(QLabel("Parallel fragments"))
        self.fragments = QSpinBox()
        self.fragments.setRange(1, 16)
        self.fragments.setValue(int(store.setting("fragments", 4)))
        self.fragments.setToolTip("Per download, for supported fragmented streams. Applies to new queue entries.")
        settings.addWidget(self.fragments)
        settings.addWidget(QLabel("Simultaneous downloads"))
        self.limit = QSpinBox()
        self.limit.setRange(1, 4)
        self.limit.setValue(queue.limit)
        settings.addWidget(self.limit)
        layout.addLayout(settings)
        self.fragments.valueChanged.connect(lambda n: self.save_setting("fragments", n))
        self.limit.valueChanged.connect(self.change_limit)
        layout.addWidget(QLabel("No speed cap • Retry waits: 1s, 2s, 4s • Select a row for actions"))
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Download / quality", "State", "Progress / details"])
        self.tree.setRootIsDecorated(False)
        self.tree.setMinimumHeight(210)
        self.tree.setColumnWidth(0, 260)
        self.tree.setColumnWidth(1, 100)
        layout.addWidget(self.tree)
        actions = QHBoxLayout()
        self.cancel = QPushButton("Cancel selected")
        self.retry = QPushButton("Retry / Resume")
        self.open_file = QPushButton("Open file")
        self.open_folder = QPushButton("Open folder")
        for button in (self.cancel, self.retry, self.open_file, self.open_folder):
            actions.addWidget(button)
        layout.addLayout(actions)
        self.message = QLabel()
        self.message.setTextFormat(Qt.TextFormat.PlainText)
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.cancel.clicked.connect(lambda: self.queue.cancel(self.selected()) if self.selected() else None)
        self.retry.clicked.connect(self.retry_selected)
        self.open_file.clicked.connect(lambda: self.open_path(False))
        self.open_folder.clicked.connect(lambda: self.open_path(True))
        self.tree.itemSelectionChanged.connect(self.update_actions)
        queue.changed.connect(self.refresh)
        queue.storage_error.connect(self.message.setText)
        self.refresh()

    def save_setting(self, key, value):
        try:
            self.store.set_setting(key, value)
        except Exception as error:
            self.message.setText("Settings could not be saved: " + str(error))

    def change_limit(self, value):
        self.save_setting("limit", value)
        self.queue.set_limit(value)

    def selected(self):
        row = self.tree.currentItem()
        return next((t for t in self.queue.tasks if row and t["id"] == row.data(0, Qt.ItemDataRole.UserRole)), None)

    def refresh(self):
        for task in self.queue.tasks:
            row = self.rows.get(task["id"])
            if row is None:
                row = QTreeWidgetItem(self.tree)
                row.setData(0, Qt.ItemDataRole.UserRole, task["id"])
                self.rows[task["id"]] = row
            config = task["config"]
            row.setText(0, f"{config.get('title') or config['url']} · {config.get('quality') or config['container']}")
            row.setText(1, task["state"].title())
            event = task.get("event", {})
            detail = task.get("message", "")
            if event.get("type") == "progress" and task["state"] == "running":
                total, done = event.get("total"), event.get("downloaded") or 0
                percent = f"{min(100, done * 100 / total):.0f}% · " if total else ""
                speed = f"{size_text(event['speed'])}/s" if event.get("speed") else "Speed unknown"
                eta = duration_text(event["eta"]) if event.get("eta") is not None else "unknown"
                detail = f"Stream {event.get('stream') or ''} · {percent}{size_text(done)} / {size_text(total)} · {speed} · ETA {eta}"
            row.setText(2, detail)
            row.setToolTip(0, config["url"])
            row.setToolTip(2, task.get("path") or detail)
        self.update_actions()

    def update_actions(self):
        task = self.selected()
        state = task["state"] if task else ""
        self.cancel.setEnabled(state in ("queued", "running"))
        self.retry.setEnabled(state in ("failed", "cancelled", "interrupted") and task["id"] not in self.queue.active)
        self.open_file.setEnabled(state == "completed")
        self.open_folder.setEnabled(bool(task))

    def retry_selected(self):
        task = self.selected()
        if task:
            try:
                self.queue.retry(task)
            except ValueError as error:
                self.message.setText(str(error))

    def open_path(self, folder):
        task = self.selected()
        if not task:
            return
        path = Path(task["config"]["folder"] if folder else task.get("path", ""))
        if not path.exists():
            self.message.setText("This file or folder no longer exists.")
        elif not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve()))):
            self.message.setText("Could not open this path. Check your default desktop application.")
