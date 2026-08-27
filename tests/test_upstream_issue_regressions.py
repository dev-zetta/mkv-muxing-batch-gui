import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from packages.Startup import GlobalFiles
from packages.Tabs.GlobalSetting import GlobalSetting
from packages.Tabs.MuxSetting.MuxSetting import (
    check_if_mkvpropedit_wanted_to_be_used,
)
from packages.Tabs.MuxSetting.Widgets.GetJsonForMkvmergeJob import (
    GetJsonForMkvmergeJob,
)
from packages.Tabs.MuxSetting.Widgets.JobQueueTable import (
    replace_source_with_mux_output,
)
from packages.Tabs.MuxSetting.Widgets.SingleJobData import SingleJobData
from packages.Tabs.MuxSetting.Widgets.StartMuxingProcessWorker import (
    StartMuxingProcessWorker,
)
from packages.Tabs.MuxSetting.Widgets.StartMuxingWorker import (
    get_mux_output_path,
    is_successful_mkvtoolnix_exit_code,
    mux_output_is_valid,
)


class SourceContainerOptionTests(unittest.TestCase):
    def setUp(self):
        self.old_chapter_enabled = GlobalSetting.CHAPTER_ENABLED
        self.old_discard_chapters = GlobalSetting.CHAPTER_DISCARD_OLD

    def tearDown(self):
        GlobalSetting.CHAPTER_ENABLED = self.old_chapter_enabled
        GlobalSetting.CHAPTER_DISCARD_OLD = self.old_discard_chapters

    def test_discard_chapters_and_attachments_are_independent(self):
        job = SingleJobData()
        job.discard_old_attachments = True
        builder = GetJsonForMkvmergeJob.__new__(GetJsonForMkvmergeJob)
        builder.job = job
        builder.attachments_json_info = []
        builder.attachments_attach_command = ""
        builder.chapter_attach_command = ""
        builder.discard_old_attachments_command = ""
        builder.discard_old_chapters_command = ""
        GlobalSetting.CHAPTER_ENABLED = True
        GlobalSetting.CHAPTER_DISCARD_OLD = True

        builder.setup_attachments_options()
        builder.setup_chapter_options()

        self.assertIn("--no-attachments", builder.discard_old_attachments_command)
        self.assertIn("--no-chapters", builder.discard_old_chapters_command)

    def test_new_chapter_file_can_replace_old_chapters(self):
        job = SingleJobData()
        job.chapter_found = True
        job.chapter_name_absolute = "/tmp/replacement-chapters.xml"
        builder = GetJsonForMkvmergeJob.__new__(GetJsonForMkvmergeJob)
        builder.job = job
        builder.chapter_attach_command = ""
        builder.discard_old_chapters_command = ""
        GlobalSetting.CHAPTER_ENABLED = True
        GlobalSetting.CHAPTER_DISCARD_OLD = True

        builder.setup_chapter_options()

        self.assertIn("--chapters", builder.chapter_attach_command)
        self.assertIn("replacement-chapters.xml", builder.chapter_attach_command)
        self.assertIn("--no-chapters", builder.discard_old_chapters_command)


class MuxModeSelectionTests(unittest.TestCase):
    def test_ineligible_fast_mux_clears_previous_session_choice(self):
        old_value = GlobalSetting.USE_MKVPROPEDIT
        try:
            GlobalSetting.USE_MKVPROPEDIT = True
            with patch(
                "packages.Tabs.MuxSetting.MuxSetting.check_if_mkvpropedit_can_be_used",
                return_value=False,
            ):
                result = check_if_mkvpropedit_wanted_to_be_used(window_parent=None)
            self.assertEqual("No", result)
            self.assertFalse(GlobalSetting.USE_MKVPROPEDIT)
        finally:
            GlobalSetting.USE_MKVPROPEDIT = old_value


class MuxProcessResultTests(unittest.TestCase):
    def test_only_documented_success_and_warning_codes_are_accepted(self):
        self.assertTrue(is_successful_mkvtoolnix_exit_code(0))
        self.assertTrue(is_successful_mkvtoolnix_exit_code(1))
        for exit_code in (2, 3, 126, 127, -9):
            with self.subTest(exit_code=exit_code):
                self.assertFalse(is_successful_mkvtoolnix_exit_code(exit_code))

    def test_process_launch_exception_emits_failure(self):
        worker = StartMuxingProcessWorker(command="mkvmerge @job.json")
        worker.wait = False
        exit_codes = []

        def record_failure(exit_code):
            exit_codes.append(exit_code)
            worker.stop = True

        worker.finished_job_signal.connect(record_failure)
        old_log_path = GlobalFiles.MuxingLogFilePath
        with tempfile.TemporaryDirectory() as temp_dir:
            GlobalFiles.MuxingLogFilePath = str(Path(temp_dir) / "mux.log")
            try:
                with self.assertLogs(level="ERROR"):
                    with patch(
                        "packages.Tabs.MuxSetting.Widgets.StartMuxingProcessWorker.subprocess.run",
                        side_effect=OSError("executable disappeared"),
                    ):
                        worker.run()
            finally:
                GlobalFiles.MuxingLogFilePath = old_log_path
        self.assertEqual([2], exit_codes)

    def test_expected_output_must_exist_and_be_non_empty(self):
        old_destination = GlobalSetting.DESTINATION_FOLDER_PATH
        old_overwrite = GlobalSetting.OVERWRITE_SOURCE_FILES
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                GlobalSetting.DESTINATION_FOLDER_PATH = temp_dir
                GlobalSetting.OVERWRITE_SOURCE_FILES = False
                job = SingleJobData()
                job.video_name = "Episode 01.mp4"
                job.video_name_absolute = str(Path(temp_dir) / job.video_name)
                output_path = get_mux_output_path(job)

                self.assertEqual(Path(temp_dir) / "Episode 01.mkv", output_path)
                self.assertFalse(mux_output_is_valid(job))
                output_path.write_bytes(b"")
                self.assertFalse(mux_output_is_valid(job))
                output_path.write_bytes(b"valid mkv placeholder")
                self.assertTrue(mux_output_is_valid(job))
        finally:
            GlobalSetting.DESTINATION_FOLDER_PATH = old_destination
            GlobalSetting.OVERWRITE_SOURCE_FILES = old_overwrite


class OverwriteSafetyTests(unittest.TestCase):
    def test_missing_generated_file_never_deletes_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.mkv"
            source.write_bytes(b"original")
            with self.assertRaises(FileNotFoundError):
                replace_source_with_mux_output(
                    source,
                    Path(temp_dir) / "missing.mkv",
                    source,
                )
            self.assertEqual(b"original", source.read_bytes())

    def test_mkv_source_is_atomically_replaced_after_output_validation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.mkv"
            generated = Path(temp_dir) / "source#temporary.mkv"
            source.write_bytes(b"original")
            generated.write_bytes(b"replacement")

            replace_source_with_mux_output(source, generated, source)

            self.assertEqual(b"replacement", source.read_bytes())
            self.assertFalse(generated.exists())

    def test_non_mkv_source_is_removed_only_after_new_mkv_is_published(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.mp4"
            generated = Path(temp_dir) / "source#temporary.mkv"
            target = Path(temp_dir) / "source.mkv"
            source.write_bytes(b"original mp4")
            generated.write_bytes(b"replacement mkv")

            replace_source_with_mux_output(source, generated, target)

            self.assertFalse(source.exists())
            self.assertFalse(generated.exists())
            self.assertEqual(b"replacement mkv", target.read_bytes())


class ToolDiscoveryTests(unittest.TestCase):
    def test_system_tool_is_preferred_to_stale_portable_copy(self):
        with patch(
            "packages.Startup.GlobalFiles.which",
            return_value="/usr/bin/mkvmerge",
        ):
            candidates = GlobalFiles.get_program_candidates("mkvmerge")
        self.assertEqual(Path("/usr/bin/mkvmerge"), candidates[0])
        self.assertEqual(
            Path(GlobalFiles.ToolsFolderPath) / "mkvmerge",
            candidates[-1],
        )


if __name__ == "__main__":
    unittest.main()
