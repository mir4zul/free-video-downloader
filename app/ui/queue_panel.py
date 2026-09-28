from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QBrush, QColor, QDesktopServices
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QSpinBox,
    QMessageBox, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from app.services.formats import duration_text, size_text


PANEL_STYLE = """
QFrame#summaryCard, QFrame#settingsCard, QFrame#emptyCard {
    background: #182235; border: 1px solid #304059; border-radius: 12px;
}
QLabel#sectionTitle { font-size: 19px; font-weight: 700; }
QLabel#statValue { font-size: 23px; font-weight: 700; color: #e7edf7; }
QLabel#statCaption { color: #a7b6ce; font-size: 12px; }
QLabel#settingsHeading { font-size: 14px; font-weight: 700; }
QLabel#emptyIcon { font-size: 28px; color: #6ee7c0; }
QLabel#emptyTitle { font-size: 16px; font-weight: 700; }
QPushButton#viewButton { background: #182235; border: 1px solid #304059;
    border-radius: 8px; padding: 9px 14px; text-align: left; }
QPushButton#viewButton:checked { background: #203b43; border-color: #6ee7c0;
    color: #8af0ce; font-weight: 700; }
QTreeWidget#downloadList { background: #101724; alternate-background-color: #141e2e;
    border: 1px solid #304059; border-radius: 10px; padding: 5px; }
QTreeWidget#downloadList::item { padding: 8px 6px; border-bottom: 1px solid #253249; }
QTreeWidget#downloadList::item:selected { background: #263b53; color: #ffffff; }
QTreeWidget#downloadList QHeaderView::section { background: #182235; color: #a7b6ce;
    border: 0; border-bottom: 1px solid #304059; padding: 9px 7px; font-weight: 700; }
QWidget#rowActions QPushButton { font-size: 12px; padding: 4px 3px; min-width: 0; }
QPushButton#dangerButton { color: #ffaaaa; }
QPushButton#dangerButton:disabled { color: #8c9bb0; }
QProgressBar#rowProgress { border: 0; border-radius: 4px; background: #26354a;
    min-height: 8px; max-height: 8px; }
QProgressBar#rowProgress::chunk { border-radius: 4px; background: #6ee7c0; }
QProgressBar#rowProgress[paused="true"]::chunk { background: #f5c76b; }
QProgressBar#rowProgress[failed="true"]::chunk { background: #ff8a8a; }
QSpinBox { min-width: 56px; }
"""


class QueuePanel(QWidget):
    def __init__(self, queue, store, parent=None):
        super().__init__(parent)
        self.queue, self.store = queue, store
        self.rows = {}
        self.progress_cells = {}
        self.action_cells = {}
        self.current_view = "active"
        self.setStyleSheet(PANEL_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 24)
        layout.setSpacing(14)

        heading = QHBoxLayout()
        title_block = QVBoxLayout()
        title_block.setSpacing(3)
        title = QLabel("Downloads & history")
        title.setObjectName("sectionTitle")
        subtitle = QLabel("Follow current transfers and find your finished files.")
        subtitle.setObjectName("muted")
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        heading.addLayout(title_block)
        heading.addStretch(1)
        layout.addLayout(heading)

        stats = QHBoxLayout()
        stats.setSpacing(10)
        self.stat_labels = {}
        for key, caption in (("running", "Downloading"), ("queued", "In queue"),
                             ("completed", "Completed"), ("attention", "Needs attention")):
            card = QFrame()
            card.setObjectName("summaryCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 10, 14, 10)
            card_layout.setSpacing(2)
            value = QLabel("0")
            value.setObjectName("statValue")
            text = QLabel(caption)
            text.setObjectName("statCaption")
            card_layout.addWidget(value)
            card_layout.addWidget(text)
            stats.addWidget(card, 1)
            self.stat_labels[key] = value
        layout.addLayout(stats)

        settings_card = QFrame()
        settings_card.setObjectName("settingsCard")
        settings = QHBoxLayout(settings_card)
        settings.setContentsMargins(14, 10, 14, 10)
        settings.setSpacing(10)
        settings_heading = QLabel("Download settings")
        settings_heading.setObjectName("settingsHeading")
        settings.addWidget(settings_heading)
        settings.addSpacing(6)
        settings.addWidget(QLabel("Parallel fragments"))
        self.fragments = QSpinBox()
        self.fragments.setRange(1, 16)
        self.fragments.setValue(int(store.setting("fragments", 4)))
        self.fragments.setToolTip("For supported fragmented streams. Applies to new downloads.")
        settings.addWidget(self.fragments)
        settings.addSpacing(5)
        settings.addWidget(QLabel("Simultaneous downloads"))
        self.limit = QSpinBox()
        self.limit.setRange(1, 4)
        self.limit.setValue(queue.limit)
        settings.addWidget(self.limit)
        settings.addStretch(1)
        layout.addWidget(settings_card)
        self.fragments.valueChanged.connect(lambda n: self.save_setting("fragments", n))
        self.limit.valueChanged.connect(self.change_limit)

        view_row = QHBoxLayout()
        view_row.setSpacing(8)
        self.active_view = QPushButton("In progress · 0")
        self.history_view = QPushButton("History · 0")
        for button in (self.active_view, self.history_view):
            button.setObjectName("viewButton")
            button.setCheckable(True)
            button.setMinimumWidth(150)
        self.active_view.setChecked(True)
        self.active_view.clicked.connect(lambda: self.set_view("active"))
        self.history_view.clicked.connect(lambda: self.set_view("history"))
        view_row.addWidget(self.active_view)
        view_row.addWidget(self.history_view)
        view_row.addStretch(1)
        self.pause_all_button = QPushButton("Pause all")
        self.resume_all_button = QPushButton("Resume / retry all")
        self.cancel_all_button = QPushButton("Cancel all")
        self.clear_history_button = QPushButton("Delete history")
        self.clear_history_button.setObjectName("dangerButton")
        view_row.addWidget(self.pause_all_button)
        view_row.addWidget(self.resume_all_button)
        view_row.addWidget(self.cancel_all_button)
        view_row.addWidget(self.clear_history_button)
        layout.addLayout(view_row)

        self.tree = QTreeWidget()
        self.tree.setObjectName("downloadList")
        self.tree.setHeaderLabels(["File and quality", "Status", "Progress / details", "Actions"])
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(False)
        self.tree.setMinimumHeight(210)
        self.tree.setColumnWidth(0, 230)
        self.tree.setColumnWidth(1, 95)
        self.tree.setColumnWidth(2, 300)
        self.tree.setColumnWidth(3, 220)
        self.tree.header().setStretchLastSection(True)
        layout.addWidget(self.tree, 1)

        self.empty_card = QFrame()
        self.empty_card.setObjectName("emptyCard")
        empty_layout = QVBoxLayout(self.empty_card)
        empty_layout.setContentsMargins(20, 24, 20, 24)
        empty_layout.setSpacing(5)
        icon = QLabel("↓")
        icon.setObjectName("emptyIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_title = QLabel("Nothing downloading right now")
        self.empty_title.setObjectName("emptyTitle")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_description = QLabel("New downloads will appear here with their live progress.")
        self.empty_description.setObjectName("muted")
        self.empty_description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(icon)
        empty_layout.addWidget(self.empty_title)
        empty_layout.addWidget(self.empty_description)
        layout.addWidget(self.empty_card, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.open_file = QPushButton("Open file")
        self.open_folder = QPushButton("Open folder")
        self.open_file.setObjectName("primary")
        for button in (self.open_file, self.open_folder):
            actions.addWidget(button)
        layout.addLayout(actions)

        self.message = QLabel()
        self.message.setObjectName("muted")
        self.message.setTextFormat(Qt.TextFormat.PlainText)
        self.message.setWordWrap(True)
        layout.addWidget(self.message)

        self.pause_all_button.clicked.connect(self.queue.pause_all)
        self.resume_all_button.clicked.connect(self.queue.resume_all)
        self.cancel_all_button.clicked.connect(self.cancel_all_confirmed)
        self.clear_history_button.clicked.connect(self.clear_history_confirmed)
        self.open_file.clicked.connect(lambda: self.open_path(False))
        self.open_folder.clicked.connect(lambda: self.open_path(True))
        self.tree.itemSelectionChanged.connect(self.update_actions)
        queue.changed.connect(self.refresh)
        queue.storage_error.connect(self.message.setText)
        self.refresh()

    def set_view(self, view):
        self.current_view = view
        self.active_view.setChecked(view == "active")
        self.history_view.setChecked(view == "history")
        self.tree.clearSelection()
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
        return next((task for task in self.queue.tasks
                     if row and task["id"] == row.data(0, Qt.ItemDataRole.UserRole)), None)

    @staticmethod
    def is_active(task):
        return task["state"] in ("queued", "running")

    def refresh(self):
        active_count = sum(task["state"] == "running" for task in self.queue.tasks)
        queued_count = sum(task["state"] == "queued" for task in self.queue.tasks)
        completed_count = sum(task["state"] == "completed" for task in self.queue.tasks)
        attention_count = sum(task["state"] in ("paused", "failed", "cancelled", "interrupted")
                              for task in self.queue.tasks)
        self.stat_labels["running"].setText(str(active_count))
        self.stat_labels["queued"].setText(str(queued_count))
        self.stat_labels["completed"].setText(str(completed_count))
        self.stat_labels["attention"].setText(str(attention_count))
        active_view_count = active_count + queued_count
        history_count = completed_count + attention_count
        self.active_view.setText(f"In progress · {active_view_count}")
        self.history_view.setText(f"History · {history_count}")

        for task in self.queue.tasks:
            row = self.rows.get(task["id"])
            if row is None:
                row = QTreeWidgetItem(self.tree)
                row.setData(0, Qt.ItemDataRole.UserRole, task["id"])
                self.rows[task["id"]] = row
                self.progress_cells[task["id"]] = self.create_progress_cell(task)
                self.action_cells[task["id"]] = self.create_action_cell(task)
            config = task.get("config", {})
            title = config.get("title") or config.get("url", "Video")
            quality = config.get("quality") or config.get("container", "")
            row.setText(0, f"{title}\n{quality}")
            state = task.get("state", "failed")
            state_labels = {"queued": "In queue", "running": "Downloading",
                            "completed": "Completed", "failed": "Failed",
                            "cancelled": "Cancelled", "interrupted": "Interrupted", "paused": "Paused"}
            row.setText(1, state_labels.get(state, state.title()))
            detail, percent, indeterminate = self.progress_details(task, state)
            self.update_progress_cell(task, state, detail, percent, indeterminate)
            row.setText(2, detail)
            row.setToolTip(0, config.get("url", ""))
            row.setToolTip(2, task.get("path") or detail)
            row.setForeground(1, QBrush(QColor({
                "running": "#6ee7c0", "queued": "#f5c76b", "completed": "#6ee7c0",
                "failed": "#ff8a8a", "cancelled": "#a7b6ce", "interrupted": "#f5c76b",
                "paused": "#f5c76b",
            }.get(state, "#e7edf7"))))
            row.setHidden(self.is_active(task) != (self.current_view == "active"))
            _, controls = self.action_cells[task["id"]]
            active = self.is_active(task)
            resumable = state in ("paused", "failed", "cancelled", "interrupted")
            controls["pause"].setEnabled(active)
            controls["cancel"].setEnabled(active)
            controls["resume"].setEnabled(resumable)
            controls["resume"].setText("Resume" if state in ("paused", "interrupted") else "Retry")
            controls["delete"].setEnabled(not active)
            controls["delete"].setToolTip(
                "Pause or cancel this active download before deleting its history"
                if active else "Remove this entry from history (keeps downloaded files)")

        self.remove_stale_rows()
        shown = active_view_count if self.current_view == "active" else history_count
        self.tree.setVisible(shown > 0)
        self.empty_card.setVisible(shown == 0)
        if shown == 0 and self.current_view == "history":
            self.empty_title.setText("Your history is clear")
            self.empty_description.setText("Finished and interrupted downloads will be saved here.")
        else:
            self.empty_title.setText("Nothing downloading right now")
            self.empty_description.setText("New downloads will appear here with their live progress.")
        self.update_actions()

    def update_actions(self):
        task = self.selected()
        state = task["state"] if task else ""
        self.open_file.setEnabled(state == "completed")
        self.open_folder.setEnabled(bool(task))
        active_count = sum(self.is_active(entry) for entry in self.queue.tasks)
        resumable_count = sum(task["state"] in ("paused", "failed", "cancelled", "interrupted")
                              for task in self.queue.tasks)
        history_count = sum(not self.is_active(entry) for entry in self.queue.tasks)
        self.pause_all_button.setEnabled(active_count > 0)
        self.cancel_all_button.setEnabled(active_count > 0)
        self.resume_all_button.setEnabled(resumable_count > 0)
        self.clear_history_button.setEnabled(history_count > 0)

    def create_action_cell(self, task):
        cell = QWidget(self.tree)
        cell.setObjectName("rowActions")
        buttons = QHBoxLayout(cell)
        buttons.setContentsMargins(4, 2, 4, 2)
        buttons.setSpacing(4)
        controls = {}
        for key, title in (("pause", "Pause"), ("resume", "Resume"),
                           ("cancel", "Cancel"), ("delete", "Delete")):
            button = QPushButton(title, cell)
            button.setFixedWidth({"pause": 48, "resume": 50, "cancel": 48, "delete": 45}[key])
            button.setToolTip({
                "pause": "Pause this download and keep its resumable data",
                "resume": "Resume this download",
                "cancel": "Cancel this download",
                "delete": "Remove this entry from history (keeps downloaded files)",
            }[key])
            if key == "delete":
                button.setObjectName("dangerButton")
            button.clicked.connect(lambda _checked=False, task_id=task["id"], action=key:
                                   self.row_action(task_id, action))
            buttons.addWidget(button)
            controls[key] = button
        self.tree.setItemWidget(self.rows[task["id"]], 3, cell)
        return cell, controls

    def row_action(self, task_id, action):
        task = next((entry for entry in self.queue.tasks if entry["id"] == task_id), None)
        if not task:
            return
        if action == "pause":
            self.queue.pause(task)
        elif action == "cancel":
            self.queue.cancel(task)
        elif action == "resume":
            try:
                self.queue.retry(task)
                self.set_view("active")
            except ValueError as error:
                self.message.setText(str(error))
        elif action == "delete":
            answer = QMessageBox.question(
                self, "Delete history item?",
                "Remove this entry from history? Any downloaded file will stay on disk.",
                QMessageBox.StandardButton.Delete | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer == QMessageBox.StandardButton.Delete:
                self.queue.delete_history(task)

    def remove_stale_rows(self):
        current_ids = {task["id"] for task in self.queue.tasks}
        for task_id in set(self.rows) - current_ids:
            row = self.rows.pop(task_id)
            index = self.tree.indexOfTopLevelItem(row)
            if index >= 0:
                self.tree.takeTopLevelItem(index)
            progress = self.progress_cells.pop(task_id, None)
            if progress:
                progress[0].parentWidget().deleteLater()
            actions = self.action_cells.pop(task_id, None)
            if actions:
                actions[0].deleteLater()

    def cancel_all_confirmed(self):
        if QMessageBox.question(
                self, "Cancel all downloads?", "Cancel every queued and running download?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.queue.cancel_all()

    def clear_history_confirmed(self):
        if QMessageBox.question(
                self, "Delete all history?",
                "Remove every history entry? Downloaded files will stay on disk.",
                QMessageBox.StandardButton.Delete | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel) == QMessageBox.StandardButton.Delete:
            self.queue.clear_history()

    def create_progress_cell(self, task):
        cell = QWidget(self.tree)
        cell.setMinimumHeight(28)
        line = QHBoxLayout(cell)
        line.setContentsMargins(5, 3, 6, 3)
        line.setSpacing(10)
        bar = QProgressBar(cell)
        bar.setObjectName("rowProgress")
        bar.setTextVisible(False)
        bar.setAccessibleName(f"Download progress for {task.get('config', {}).get('title') or 'video'}")
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setMinimumWidth(65)
        bar.setMaximumWidth(115)
        detail_label = QLabel(cell)
        detail_label.setObjectName("muted")
        detail_label.setMinimumWidth(40)
        line.addWidget(bar)
        line.addWidget(detail_label, 1)
        self.tree.setItemWidget(self.rows[task["id"]], 2, cell)
        return bar, detail_label

    @staticmethod
    def progress_details(task, state):
        event = task.get("event", {})
        progress = task.get("last_progress") or (event if event.get("type") == "progress" else {})
        total = progress.get("total")
        done = progress.get("downloaded") or 0
        percent = min(100, int(done * 100 / total)) if total else 0
        indeterminate = state == "running" and bool(progress) and not total
        if state == "completed":
            return "Finished and verified", 100, False
        if state == "queued":
            return task.get("message", "Waiting…"), 0, False
        if state == "running" and progress:
            speed = f"{size_text(progress['speed'])}/s" if progress.get("speed") else "Speed unknown"
            eta = duration_text(progress["eta"]) if progress.get("eta") is not None else "unknown"
            size_total = size_text(total) if total else "Unknown size"
            amount = f"{size_text(done)} / {size_total}"
            return f"{amount} · {speed} · ETA {eta}", percent, indeterminate
        if progress:
            detail = f"{size_text(done)} received"
            if total:
                detail = f"Paused at {percent}% · {detail}"
            else:
                detail = f"{state.title()} · {detail}"
            return detail, percent, False
        return task.get("message", ""), 0, False

    def update_progress_cell(self, task, state, detail, percent, indeterminate):
        bar, text = self.progress_cells[task["id"]]
        bar.setRange(0, 0 if indeterminate else 100)
        if not indeterminate:
            bar.setValue(percent)
        bar.setProperty("paused", state in ("paused", "interrupted", "cancelled"))
        bar.setProperty("failed", state == "failed")
        bar.style().unpolish(bar)
        bar.style().polish(bar)
        text.setText(detail)
        text.setToolTip(detail)

    def open_path(self, folder):
        task = self.selected()
        if not task:
            return
        path = Path(task["config"]["folder"] if folder else task.get("path", ""))
        if not path.exists():
            self.message.setText("This file or folder no longer exists.")
        elif not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve()))):
            self.message.setText("Could not open this path. Check your default desktop application.")
