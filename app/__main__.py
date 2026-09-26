import sys
from pathlib import Path


def main():
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("PySide6 is missing. Run: uv sync", file=sys.stderr)
        return 1
    from app.ui.window import MainWindow

    application = QApplication(sys.argv)
    application.setApplicationName("Free Video Downloader")
    application.setStyle("Fusion")
    from PySide6.QtGui import QIcon
    icon_path = Path(__file__).parent / "assets" / "downloader.svg"
    application.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
