import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from packages.Tabs.SubtitleTab.SubtitleSelection import SubtitleSelectionSetting
from packages.Tabs.MuxSetting.MuxSetting import MuxSettingTab


class SubtitleDirectoryMonitoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp_directory.name)
        self.subtitle_tab = SubtitleSelectionSetting(91)

    def tearDown(self):
        self.subtitle_tab.deleteLater()
        self.app.processEvents()
        self.temp_directory.cleanup()

    def write_subtitle(self, name, content="subtitle"):
        path = self.folder / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_new_subtitle_marks_directory_stale_without_changing_matching(self):
        self.write_subtitle("Episode 1.ass")
        self.subtitle_tab.update_folder_path(str(self.folder))
        original_matching = self.subtitle_tab.files_names_list.copy()

        self.write_subtitle("Episode 2.ass")
        changed = self.subtitle_tab.check_folder_for_changes()

        self.assertTrue(changed)
        self.assertTrue(self.subtitle_tab.subtitle_directory_is_stale)
        self.assertEqual(original_matching, self.subtitle_tab.files_names_list)
        self.assertIn("1 added", self.subtitle_tab.subtitle_directory_status_label.text())

    def test_refresh_accepts_changes_and_clears_stale_state(self):
        self.write_subtitle("Episode 1.ass")
        self.subtitle_tab.update_folder_path(str(self.folder))
        self.write_subtitle("Episode 2.ass")
        self.subtitle_tab.check_folder_for_changes()

        self.subtitle_tab.update_folder_path(str(self.folder))

        self.assertFalse(self.subtitle_tab.subtitle_directory_is_stale)
        self.assertTrue(self.subtitle_tab.subtitle_directory_status_label.isHidden())
        self.assertEqual(["Episode 1.ass", "Episode 2.ass"], self.subtitle_tab.files_names_list)

    def test_manual_reordering_does_not_look_like_a_directory_change(self):
        self.write_subtitle("Episode 1.ass")
        self.write_subtitle("Episode 2.ass")
        self.subtitle_tab.update_folder_path(str(self.folder))
        self.subtitle_tab.files_names_list.reverse()

        changed = self.subtitle_tab.check_folder_for_changes()

        self.assertFalse(changed)
        self.assertFalse(self.subtitle_tab.subtitle_directory_is_stale)

    def test_removed_subtitle_and_missing_folder_are_detected(self):
        subtitle = self.write_subtitle("Episode 1.ass")
        self.subtitle_tab.update_folder_path(str(self.folder))
        subtitle.unlink()

        self.assertTrue(self.subtitle_tab.check_folder_for_changes())
        self.assertIn("1 removed", self.subtitle_tab.subtitle_directory_status_label.text())

        self.subtitle_tab.clear_directory_stale_state()
        self.temp_directory.cleanup()
        self.assertTrue(self.subtitle_tab.check_folder_for_changes())
        self.assertIn("unavailable", self.subtitle_tab.subtitle_directory_status_label.text())

    def test_stale_directory_validator_blocks_queue_creation(self):
        mux_tab = MuxSettingTab()
        try:
            mux_tab.subtitle_directories_validator = Mock(return_value=False)
            mux_tab.job_queue_layout.setup_queue = Mock()

            mux_tab.add_to_queue_button_clicked()

            mux_tab.subtitle_directories_validator.assert_called_once_with()
            mux_tab.job_queue_layout.setup_queue.assert_not_called()
        finally:
            mux_tab.deleteLater()


if __name__ == "__main__":
    unittest.main()
