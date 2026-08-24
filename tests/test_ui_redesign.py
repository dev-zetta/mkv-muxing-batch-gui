import os
import subprocess
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from packages.Startup.AppStyle import get_dark_glass_stylesheet
from packages.Tabs.MuxSetting.MuxSetting import MuxSettingTab


class UiRedesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_dark_glass_style_contains_no_gradients(self):
        stylesheet = get_dark_glass_stylesheet().lower()
        self.assertNotIn("qlineargradient", stylesheet)
        self.assertNotIn("qradialgradient", stylesheet)
        self.assertIn("qframe#sidebar", stylesheet)
        self.assertIn("qpushbutton#primaryactionbutton", stylesheet)

    def test_sidebar_navigation_controls_the_page_stack(self):
        script = (
            "from packages.Startup.MainApplication import MainApplication; "
            "from packages.Tabs.TabsManager import TabsManager; "
            "workspace=TabsManager(); "
            "assert workspace.page_stack.count() == 6; "
            "assert workspace.brand_label.text() == 'MKV Muxing Batch'; "
            "workspace.setCurrentIndex(5); MainApplication.processEvents(); "
            "assert workspace.currentIndex() == 5; "
            "assert workspace.page_title.text() == 'Mux Queue'; "
            "assert 'saved automatically' in workspace.workspace_status.text(); "
            "workspace.close()"
        )
        environment = os.environ.copy()
        environment["QT_QPA_PLATFORM"] = "offscreen"
        process = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).parents[1],
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(0, process.returncode, process.stderr)

    def test_mux_workspace_is_queue_first_with_a_bounded_inspector(self):
        tab = MuxSettingTab()
        try:
            self.assertIs(tab.MainLayout.itemAt(0).widget(), tab.job_queue_groupBox)
            self.assertIs(tab.MainLayout.itemAt(1).widget(), tab.mux_setting_groupBox)
            self.assertEqual("Mux Queue", tab.job_queue_groupBox.title())
            self.assertEqual("Output && Behavior", tab.mux_setting_groupBox.title())
            self.assertLessEqual(tab.mux_setting_groupBox.maximumWidth(), 370)
            self.assertEqual("Metadata Names", tab.name_manipulation_button.text())
        finally:
            tab.deleteLater()
            self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
