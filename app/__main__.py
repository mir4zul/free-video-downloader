import sys
from pathlib import Path


def main():
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("PySide6 is missing. Run: uv sync", file=sys.stderr)
        return 1
    from app.ui.window import MainWindow

    incoming_urls = sys.argv[1:]
    application = QApplication(sys.argv[:1])
    application.setApplicationName("Free Video Downloader")
    application.setStyle("Fusion")
    from PySide6.QtGui import QIcon
    icon_path = Path(__file__).parent / "assets" / "downloader.svg"
    application.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow()
    window.show()
    for incoming_url in incoming_urls:
        if window.open_external_url(incoming_url):
            break
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
