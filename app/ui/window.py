from pathlib import Path

from PySide6.QtCore import Qt, QStandardPaths, QUrl, QUrlQuery
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QPushButton,
    QScrollArea, QTextBrowser, QVBoxLayout, QWidget, QTabWidget,
)

from app.services.dependencies import check_dependencies
from app.services.analysis import AnalysisJob
from app.services.formats import build_choices, duration_text, validate_url
from app.services.thumbnail import ThumbnailLoader
from app.services.store import Store
from app.services.queue import DownloadQueue
from app.ui.queue_panel import QueuePanel


STYLE = """
QWidget { background: #101724; color: #e7edf7; font-size: 14px; }
QLabel#title { font-size: 28px; font-weight: 700; }
QLabel#muted { color: #a7b6ce; }
QLabel { background: transparent; }
QFrame#card { background: #182235; border: 1px solid #304059; border-radius: 12px; }
QLineEdit, QComboBox, QTextBrowser { background: #0e1624; border: 1px solid #40516d;
    border-radius: 7px; padding: 10px; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #6ee7c0; }
QPushButton { background: #293c58; border: 1px solid #40516d;
    border-radius: 7px; padding: 10px 18px; }
QPushButton:hover { background: #354e71; }
QPushButton#primary { background: #6ee7c0; color: #10251f; font-weight: 700; }
QPushButton:disabled, QComboBox:disabled { background: #202b3b; color: #8c9bb0; }
QPushButton#primary:disabled { background: #202b3b; color: #8c9bb0; }
QRadioButton { padding: 8px; }
QRadioButton::indicator { width: 17px; height: 17px; }
"""


def label(text, muted=False):
    result = QLabel(text)
    result.setTextFormat(Qt.TextFormat.PlainText)
    result.setWordWrap(True)
    if muted:
        result.setObjectName("muted")
    return result


class MainWindow(QMainWindow):
    def __init__(self, store=None):
        super().__init__()
        self.store = store or Store()
        self.queue = DownloadQueue(self.store, self.store.setting("limit", 2), parent=self)
        self.queue.idle.connect(self.queue_idle)
        self.job = None
        self.close_pending = False
        self.external_auto_download = False
        self.info = None
        self.video_choices = []
        self.audio_choices = []
        self.thumbnail = ThumbnailLoader(self)
        self.thumbnail.loaded.connect(self.show_thumbnail)
        self.setWindowTitle("Free Video Downloader")
        self.resize(900, 820)
        self.setMinimumSize(620, 540)
        self.setStyleSheet(STYLE)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.addTab(scroll, "New download")
        body = QWidget()
        scroll.setWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)
        title = label("Free Video Downloader")
        title.setObjectName("title")
        layout.addWidget(title)
        layout.addWidget(label("Choose a video resolution or download audio only.", True))

        link_row = QHBoxLayout()
        self.url = QLineEdit()
        self.url.setPlaceholderText("Paste a YouTube or supported video link")
        self.url.setAccessibleName("Video link")
        self.analyze = QPushButton("Analyze")
        self.analyze.setEnabled(False)
        self.analyze.setToolTip("Read available formats without downloading the video.")
        self.analyze.clicked.connect(self.start_analysis)
        self.url.returnPressed.connect(self.start_analysis)
        self.url.textChanged.connect(self.link_changed)
        self.cancel_analysis = QPushButton("Cancel")
        self.cancel_analysis.setVisible(False)
        self.cancel_analysis.clicked.connect(lambda: self.job.cancel() if self.job else None)
        link_row.addWidget(self.url, 1)
        link_row.addWidget(self.analyze)
        link_row.addWidget(self.cancel_analysis)
        layout.addLayout(link_row)

        preview = QFrame()
        preview.setObjectName("card")
        preview_layout = QVBoxLayout(preview)
        preview_layout.setContentsMargins(24, 24, 24, 24)
        self.preview = label("Video preview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(95)
        preview_layout.addWidget(self.preview)
        self.metadata = label("Title, thumbnail and available formats will appear here after analysis.", True)
        preview_layout.addWidget(self.metadata)
        layout.addWidget(preview)

        layout.addWidget(label("Download mode"))
        self.mode = QComboBox()
        self.mode.setAccessibleName("Download mode")
        self.mode.addItem("Video", "video")
        self.mode.addItem("Audio only (MP3)", "audio")
        self.mode.setEnabled(False)
        self.mode.currentIndexChanged.connect(self.update_mode)
        layout.addWidget(self.mode)

        self.format_label = label("Resolution")
        layout.addWidget(self.format_label)
        self.quality = QComboBox()
        self.quality.setAccessibleName("Output quality")
        self.quality.addItem("Available after link analysis")
        self.quality.setEnabled(False)
        layout.addWidget(self.quality)
        self.selection = label("Choose a link to see available formats.", True)
        layout.addWidget(self.selection)
        self.quality.currentIndexChanged.connect(self.selection_changed)
        self.quality.activated.connect(self.quality_activated)

        layout.addWidget(label("Save to"))
        folder_row = QHBoxLayout()
        download_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        self.folder = QLineEdit(self.store.setting("folder", download_dir or str(Path.home() / "Downloads")))
        self.folder.setReadOnly(True)
        self.folder.setAccessibleName("Download folder")
        self.browse = QPushButton("Choose folder…")
        self.browse.clicked.connect(self.choose_folder)
        folder_row.addWidget(self.folder, 1)
        folder_row.addWidget(self.browse)
        layout.addLayout(folder_row)

        self.download = QPushButton("Download / Add to queue")
        self.download.setObjectName("primary")
        self.download.setEnabled(False)
        self.download.setToolTip("Download the selected output and verify the finished file.")
        self.download.clicked.connect(self.start_download)
        layout.addWidget(self.download)
        self.queue_panel = QueuePanel(self.queue, self.store)
        self.tabs.addTab(self.queue_panel, "Downloads && history")
        self.status = label("Paste a link and choose Analyze.", True)
        layout.addWidget(self.status)

        setup_row = QHBoxLayout()
        self.dependency_status = label("", True)
        setup_row.addWidget(self.dependency_status, 1)
        setup = QPushButton("Check setup")
        setup.clicked.connect(self.show_setup)
        setup_row.addWidget(setup)
        layout.addLayout(setup_row)
        layout.addStretch()
        self.refresh_dependencies()

    def open_external_url(self, external_url):
        parsed = QUrl(external_url)
        if parsed.scheme().lower() != "free-video-downloader":
            return False
        query = QUrlQuery(parsed)
        target_url = query.queryItemValue("url", QUrl.ComponentFormattingOption.FullyDecoded)
        try:
            target_url = validate_url(target_url)
        except ValueError as error:
            self.status.setText(f"Could not open browser video link: {error}")
            return True
        self.tabs.setCurrentIndex(0)
        self.url.setText(target_url)
        self.start_analysis()
        self.external_auto_download = True
        return True

    def update_mode(self):
        audio_mode = self.mode.currentData() == "audio"
        self.format_label.setText("MP3 bitrate" if audio_mode else "Resolution")
        self.quality.setAccessibleName("MP3 bitrate" if audio_mode else "Output resolution")
        self.quality.clear()
        choices = self.audio_choices if audio_mode else self.video_choices
        for choice in choices:
            self.quality.addItem(choice.label, choice)
        if not choices:
            unavailable = "No audio format available" if audio_mode else "No compatible video format available"
            self.quality.addItem(unavailable if self.info else "Available after link analysis")
        self.quality.setEnabled(bool(choices))
        self.mode.setEnabled(bool(self.info))
        self.selection_changed()

    def selection_changed(self, *_):
        choice = self.quality.currentData()
        no_choice = ("No audio-only format is available for this link."
                     if self.mode.currentData() == "audio" else
                     "No usable video with audio was found. Try another link.")
        self.selection.setText(choice.details if choice else
            no_choice
            if self.info else "Choose a link to see available formats.")
        self.download.setEnabled(bool(choice) and self.job is None)

    def quality_activated(self, *_):
        if self.external_auto_download and self.quality.currentData():
            self.external_auto_download = False
            self.start_download()

    def link_changed(self):
        self.external_auto_download = False
        self.thumbnail.cancel()
        self.info = None
        self.video_choices = []
        self.audio_choices = []
        self.mode.setCurrentIndex(0)
        self.preview.clear()
        self.preview.setText("Video preview")
        self.metadata.setText("Analyze the link to view title, duration and available formats.")
        self.update_mode()
        self.analyze.setEnabled(bool(self.url.text().strip()) and self.job is None)
        self.status.setText("Ready to analyze.")

    def start_analysis(self):
        if self.job:
            return
        try:
            url = validate_url(self.url.text())
        except ValueError as error:
            self.status.setText(str(error))
            return
        self.link_changed()
        self.job = AnalysisJob(url, self)
        self.job.succeeded.connect(self.analysis_succeeded)
        self.job.failed.connect(self.status.setText)
        self.job.finished.connect(self.analysis_finished)
        self.url.setEnabled(False)
        self.analyze.setEnabled(False)
        self.cancel_analysis.setVisible(True)
        self.status.setText("Analyzing link… Reading title and available formats.")
        self.job.start()

    def analysis_succeeded(self, info):
        try:
            videos, audios = build_choices(info)
        except ValueError as error:
            self.status.setText(str(error))
            return
        self.info = info
        self.video_choices, self.audio_choices = videos, audios
        self.metadata.setText(f"{info.get('title') or 'Untitled video'}\n"
            f"{duration_text(info.get('duration'))} · {info.get('extractor_key') or info.get('extractor') or 'Video'}")
        self.preview.setText("Thumbnail unavailable")
        self.thumbnail.load(info.get("thumbnail"))
        self.update_mode()
        self.status.setText(
            "Analysis complete. Choose a quality to start downloading."
            if self.external_auto_download else
            "Analysis complete. Select a format and choose Download.")

    def analysis_finished(self):
        job, self.job = self.job, None
        job.deleteLater()
        self.url.setEnabled(True)
        self.analyze.setEnabled(bool(self.url.text().strip()))
        self.cancel_analysis.setVisible(False)
        self.selection_changed()
        if self.close_pending:
            self.close()

    def show_thumbnail(self, data):
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            self.preview.setPixmap(pixmap.scaled(360, 180, Qt.AspectRatioMode.KeepAspectRatio,
                                                 Qt.TransformationMode.SmoothTransformation))

    def closeEvent(self, event):
        self.thumbnail.cancel()
        self.close_pending = True
        self.queue.shutdown()
        if self.job:
            self.job.cancel()
        if self.job or self.queue.active:
            event.ignore()
        else:
            event.accept()

    def queue_idle(self):
        if self.close_pending and not self.job:
            self.close()

    def start_download(self):
        choice = self.quality.currentData()
        if not choice or self.job:
            return
        self.external_auto_download = False
        config = {"url": self.url.text().strip(), "selector": choice.selector,
            "container": choice.container, "bitrate": choice.bitrate, "folder": self.folder.text(),
            "duration": self.info.get("duration") if self.info else None,
            "title": self.info.get("title") if self.info else "Video", "quality": choice.label,
            "fragments": self.queue_panel.fragments.value(), "estimated_size": choice.estimated_size,
            "height": choice.height, "width": choice.width}
        try:
            task = self.queue.add(config)
            self.queue_panel.tree.setCurrentItem(self.queue_panel.rows[task["id"]])
            self.tabs.setCurrentWidget(self.queue_panel)
            self.status.setText("Added to queue. You can analyze another link while this downloads.")
        except ValueError as error:
            self.status.setText(str(error))

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose download folder", self.folder.text())
        if folder:
            self.folder.setText(folder)
            self.queue_panel.save_setting("folder", folder)

    def refresh_dependencies(self):
        results = check_dependencies()
        missing = sum(not item.available for item in results)
        self.dependency_status.setText(
            f"Setup: {missing} missing component(s)" if missing else
            "Setup: components found (download compatibility not yet tested)"
        )
        return results

    def show_setup(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Dependency check & setup")
        dialog.resize(640, 460)
        layout = QVBoxLayout(dialog)
        text = QTextBrowser()
        report = "\n".join(
            f"{'FOUND' if item.available else 'MISSING'}  {item.name}\n    {item.detail}"
            for item in self.refresh_dependencies()
        )
        text.setPlainText(report + "\n\nSetup instructions\n"
            "Python packages: run uv sync in the project folder.\n"
            "Arch: sudo pacman -Syu ffmpeg deno\n"
            "Ubuntu: sudo apt update && sudo apt install ffmpeg\n"
            "Deno installation: https://docs.deno.com/runtime/getting_started/installation/\n\n"
            "If Deno is missing, an installed Node runtime is enabled for analysis.\n"
            "Reopen this check after installing components. Restart the app if PATH changed.\n"
            "This checks availability, not runtime versions or real download compatibility.\n"
            "Nothing is installed automatically.")
        layout.addWidget(text)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()
