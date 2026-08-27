import unittest
from unittest.mock import Mock, patch

import main
from packages.Startup import GlobalFiles
from packages.Widgets.MissingFilesMessage import MissingFilesMessage


class ToolDiscoveryRefreshTests(unittest.TestCase):
    def setUp(self):
        self.original_values = (
            GlobalFiles.MKVMERGE_PATH,
            GlobalFiles.MKVMERGE_VERSION,
            GlobalFiles.MKVPROPEDIT_PATH,
            GlobalFiles.MKVPROPEDIT_VERSION,
            GlobalFiles.ENVIRONMENT,
        )

    def tearDown(self):
        (
            GlobalFiles.MKVMERGE_PATH,
            GlobalFiles.MKVMERGE_VERSION,
            GlobalFiles.MKVPROPEDIT_PATH,
            GlobalFiles.MKVPROPEDIT_VERSION,
            GlobalFiles.ENVIRONMENT,
        ) = self.original_values

    def test_missing_tool_list_is_specific(self):
        GlobalFiles.MKVMERGE_VERSION = "mkvmerge: not found!"
        GlobalFiles.MKVPROPEDIT_VERSION = "mkvpropedit v101.0 ('Time To Turn')"
        self.assertEqual(["mkvmerge"], GlobalFiles.get_missing_tools())

    def test_refresh_replaces_paths_versions_and_environment(self):
        discovered = [
            ("/tools/mkvmerge", "mkvmerge v101.0 ('Time To Turn')"),
            ("/tools/mkvpropedit", "mkvpropedit v101.0 ('Time To Turn')"),
        ]
        with patch.object(GlobalFiles, "resolve_program", side_effect=discovered), patch.object(
            GlobalFiles,
            "get_tool_environment",
            return_value={"UPDATED": "1"},
        ):
            self.assertTrue(GlobalFiles.refresh_tools())

        self.assertEqual("/tools/mkvmerge", GlobalFiles.MKVMERGE_PATH)
        self.assertEqual("/tools/mkvpropedit", GlobalFiles.MKVPROPEDIT_PATH)
        self.assertEqual({"UPDATED": "1"}, GlobalFiles.ENVIRONMENT)


class StartupDependencyPromptTests(unittest.TestCase):
    def test_prompt_offers_download_retry_and_continue(self):
        dialog = MissingFilesMessage("mkvmerge and mkvpropedit are missing")
        button_texts = {button.text() for button in dialog.buttons()}
        self.assertEqual(
            {"Download Latest MKVToolNix", "Check Again", "Continue Without It"},
            button_texts,
        )

    def test_continue_keeps_startup_alive_when_tools_are_missing(self):
        dialog = Mock()
        dialog.execute.return_value = "continue"
        with patch.object(
            main.GlobalFiles,
            "get_missing_tools_error",
            side_effect=["MKVToolNix is missing", "MKVToolNix is missing"],
        ), patch.object(main, "MissingFilesMessage", return_value=dialog):
            main.window = None
            main.show_missing_tools_prompt()

        dialog.execute.assert_called_once_with()

    def test_download_action_starts_the_in_app_installer(self):
        dialog = Mock()
        dialog.execute.return_value = "download"
        toolbar = Mock()
        window = Mock()
        window.tabs.status_toolbar = toolbar
        with patch.object(
            main.GlobalFiles,
            "get_missing_tools_error",
            side_effect=["MKVToolNix is missing", "MKVToolNix is missing"],
        ), patch.object(main, "MissingFilesMessage", return_value=dialog):
            main.window = window
            main.show_missing_tools_prompt()

        toolbar.install_latest.assert_called_once_with()

    def test_retry_runs_tool_discovery_and_closes_after_success(self):
        dialog = Mock()
        dialog.execute.return_value = "retry"
        with patch.object(
            main.GlobalFiles,
            "get_missing_tools_error",
            side_effect=["MKVToolNix is missing", "MKVToolNix is missing", ""],
        ), patch.object(
            main.GlobalFiles,
            "refresh_tools",
            return_value=True,
        ) as refresh_tools, patch.object(main, "MissingFilesMessage", return_value=dialog):
            main.window = None
            main.show_missing_tools_prompt()

        refresh_tools.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
