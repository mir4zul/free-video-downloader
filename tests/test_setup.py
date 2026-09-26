import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from app.services.dependencies import check_dependencies
from app.ui.window import MainWindow
from app.services.store import Store


class SetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_missing_tools_are_reported(self):
        with patch("app.services.dependencies.which", return_value=None):
            missing = {item.name for item in check_dependencies() if not item.available}
        self.assertTrue({"ffmpeg", "ffprobe", "JavaScript runtime (Deno / Node)"} <= missing)

    def test_folder_cancel_preserves_selection_and_mode_switches(self):
        window = MainWindow(Store(":memory:"))
        original = window.folder.text()
        with patch("app.ui.window.QFileDialog.getExistingDirectory", return_value=""):
            window.choose_folder()
        self.assertEqual(window.folder.text(), original)
        with patch("app.ui.window.QFileDialog.getExistingDirectory", return_value="/tmp"):
            window.choose_folder()
        self.assertEqual(window.folder.text(), "/tmp")
        self.assertFalse(hasattr(window, "audio"))
        self.assertFalse(hasattr(window, "video"))
        self.assertFalse(window.download.isEnabled())
        self.assertFalse(window.analyze.isEnabled())
        window.show()
        self.application.processEvents()
        window.close()


if __name__ == "__main__":
    unittest.main()
