"""Offscreen smoke test: the full main window builds, opens Screen Guide and closes cleanly."""
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from core import config, instructions, manager_prompt, memory, workspace


class MainWindowSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.old = (config.APP_DIR, config.CONFIG_PATH, memory.MEMORY_PATH, instructions.PATH,
                    manager_prompt.PATH, workspace.APP_DIR)
        config.APP_DIR, config.CONFIG_PATH = root, root / "config.json"
        memory.MEMORY_PATH = root / "memory.json"
        instructions.PATH = root / "custom_instructions.txt"
        manager_prompt.PATH = root / "manager_prompt.txt"
        workspace.APP_DIR = root
        cfg = config.load_config()
        cfg["voice"]["always_listening"] = False
        cfg["updates"]["automatic_check"] = False
        config.save_config(cfg)

    def tearDown(self):
        (config.APP_DIR, config.CONFIG_PATH, memory.MEMORY_PATH, instructions.PATH,
         manager_prompt.PATH, workspace.APP_DIR) = self.old
        self.tmp.cleanup()

    def test_main_window_exposes_screen_guide_page(self):
        with patch("core.secrets.get_secret", return_value=""), \
             patch("ui.main_window.get_secret", return_value=""):
            from ui.main_window import MainWindow
            window = MainWindow()
            try:
                self.assertIn("JARVIS V8", window.windowTitle())
                window.navigate("Guide")
                self.assertIs(window.workspace_stack.currentWidget(), window.screen_guide_page)
                deadline = time.time() + 5
                while window.screen_guide_page.runner.busy and time.time() < deadline:
                    self.app.processEvents(); time.sleep(0.01)
                # Linux CI has no UI Automation; the page must say so instead of failing silently.
                if os.name != "nt":
                    self.assertIn("Windows", window.screen_guide_page.support_reason.text())
            finally:
                window.close()
                self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
