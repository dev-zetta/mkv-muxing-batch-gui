from collections import defaultdict
import json
import tempfile
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from packages.Startup import GlobalFiles
from packages.Startup.PreDefined import AllVideosExtensions
from packages.Tabs.GlobalSetting import GlobalSetting
from packages.Tabs.MuxSetting.MuxSetting import (
    MuxSettingTab,
    check_if_mkvpropedit_wanted_to_be_used,
    is_valid_destination_path_syntax,
)
from packages.Tabs.MuxSetting.Widgets.GetJsonForMkvmergeJob import (
    GetJsonForMkvmergeJob,
    change_file_extension_to_mkv_with_random_suffix,
)
from packages.Tabs.MuxSetting.Widgets.GetJsonForMkvpropeditJob import (
    GetJsonForMkvpropeditJob,
)
from packages.Tabs.MuxSetting.Widgets.JobQueueTable import (
    JobQueueTable,
    replace_source_with_mux_output,
)
from packages.Tabs.MuxSetting.Widgets.SingleJobData import SingleJobData
from packages.Tabs.MuxSetting.Widgets.StartMuxingProcessWorker import (
    StartMuxingProcessWorker,
)
from packages.Tabs.MuxSetting.Widgets.StartMuxingWorker import (
    StartMuxingWorker,
    change_file_extension_to_temporary_mkv,
    get_mux_output_path,
    is_successful_mkvtoolnix_exit_code,
    mux_output_audio_track_count,
    mux_output_is_valid,
    mux_output_satisfies_audio_guard,
    remove_rejected_mux_output,
)
from packages.Tabs.VideoTab.VideoSelection import filter_unsupported_files
from packages.Tabs.VideoTab.Widgets.GenerateMediaInfoFilesWorker import (
    GenerateMediaInfoFilesWorker,
)
from packages.Tabs.VideoTab.Widgets.VideoSourceLineEdit import VideoSourceLineEdit
from packages.Tabs.AudioTab.Widgets.AudioSetDefaultCheckBox import (
    AudioSetDefaultCheckBox,
)
from packages.Tabs.AudioTab.Widgets.AudioSetForcedCheckBox import (
    AudioSetForcedCheckBox,
)
from packages.Tabs.SubtitleTab.Widgets.SubtitleSetDefaultCheckBox import (
    SubtitleSetDefaultCheckBox,
)
from packages.Tabs.SubtitleTab.Widgets.SubtitleSetForcedCheckBox import (
    SubtitleSetForcedCheckBox,
)
from packages.Widgets.AudioInfoDialog import AudioInfoDialog
from packages.Widgets.SingleOldTrackData import SingleOldTrackData
from packages.Widgets.SubtitleInfoDialog import SubtitleInfoDialog
from packages.Widgets.TableFixedHeader import TableFixedHeaderWidget


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

    def test_m2ts_is_available_as_a_video_extension(self):
        self.assertIn("M2TS", AllVideosExtensions)

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

    def test_process_receives_literal_argv_without_a_shell(self):
        command = ["/opt/MKV ToolNix/mkvmerge", "@/share/show & extras/job.json"]
        worker = StartMuxingProcessWorker(command=command)
        worker.wait = False

        def stop_worker(_exit_code):
            worker.stop = True

        worker.finished_job_signal.connect(stop_worker)
        old_log_path = GlobalFiles.MuxingLogFilePath
        with tempfile.TemporaryDirectory() as temp_dir:
            GlobalFiles.MuxingLogFilePath = str(Path(temp_dir) / "mux.log")
            try:
                with patch(
                    "packages.Tabs.MuxSetting.Widgets.StartMuxingProcessWorker.subprocess.run",
                    return_value=SimpleNamespace(returncode=0),
                ) as run_process:
                    worker.run()
            finally:
                GlobalFiles.MuxingLogFilePath = old_log_path

        self.assertEqual(command, run_process.call_args.args[0])
        self.assertNotIn("shell", run_process.call_args.kwargs)

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


class ZeroAudioGuardTests(unittest.TestCase):
    def setUp(self):
        self.old_destination = GlobalSetting.DESTINATION_FOLDER_PATH
        self.old_overwrite = GlobalSetting.OVERWRITE_SOURCE_FILES
        self.old_guard = GlobalSetting.MUX_SETTING_REQUIRE_AUDIO
        GlobalSetting.MUX_SETTING_REQUIRE_AUDIO = True
        GlobalSetting.OVERWRITE_SOURCE_FILES = False

    def tearDown(self):
        GlobalSetting.DESTINATION_FOLDER_PATH = self.old_destination
        GlobalSetting.OVERWRITE_SOURCE_FILES = self.old_overwrite
        GlobalSetting.MUX_SETTING_REQUIRE_AUDIO = self.old_guard

    @staticmethod
    def probe_result(tracks, returncode=0, stdout=None):
        return SimpleNamespace(
            returncode=returncode,
            stdout=stdout if stdout is not None else json.dumps({"tracks": tracks}),
        )

    def test_actual_output_tracks_are_probed(self):
        job = SingleJobData()
        job.video_name = "Episode.mkv"
        with tempfile.TemporaryDirectory() as temp_dir:
            GlobalSetting.DESTINATION_FOLDER_PATH = temp_dir
            with patch(
                "packages.Tabs.MuxSetting.Widgets.StartMuxingWorker.subprocess.run",
                return_value=self.probe_result([
                    {"type": "video"},
                    {"type": "audio"},
                    {"type": "subtitles"},
                ]),
            ) as probe:
                self.assertEqual(1, mux_output_audio_track_count(job))
            self.assertEqual(
                [GlobalFiles.MKVMERGE_PATH, "-J", str(Path(temp_dir) / "Episode.mkv")],
                probe.call_args.args[0],
            )

    def test_zero_audio_and_failed_probe_are_rejected(self):
        job = SingleJobData()
        job.video_name = "Episode.mkv"
        with tempfile.TemporaryDirectory() as temp_dir:
            GlobalSetting.DESTINATION_FOLDER_PATH = temp_dir
            for result in (
                self.probe_result([{"type": "video"}]),
                self.probe_result([], returncode=2),
                self.probe_result([], stdout="not json"),
            ):
                with self.subTest(result=result), patch(
                    "packages.Tabs.MuxSetting.Widgets.StartMuxingWorker.subprocess.run",
                    return_value=result,
                ):
                    self.assertFalse(mux_output_satisfies_audio_guard(job))

    def test_guard_can_be_disabled_and_never_rejects_mkvpropedit(self):
        job = SingleJobData()
        GlobalSetting.MUX_SETTING_REQUIRE_AUDIO = False
        with patch(
            "packages.Tabs.MuxSetting.Widgets.StartMuxingWorker.subprocess.run"
        ) as probe:
            self.assertTrue(mux_output_satisfies_audio_guard(job))
            probe.assert_not_called()

        GlobalSetting.MUX_SETTING_REQUIRE_AUDIO = True
        job.used_mkvpropedit = True
        with patch(
            "packages.Tabs.MuxSetting.Widgets.StartMuxingWorker.subprocess.run"
        ) as probe:
            self.assertTrue(mux_output_satisfies_audio_guard(job))
            probe.assert_not_called()

    def test_rejected_remux_is_removed_without_touching_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            GlobalSetting.DESTINATION_FOLDER_PATH = temp_dir
            job = SingleJobData()
            job.video_name = "Episode.mp4"
            job.video_name_absolute = str(Path(temp_dir) / "Episode.mp4")
            source = Path(job.video_name_absolute)
            source.write_bytes(b"source")
            output = get_mux_output_path(job)
            output.write_bytes(b"video only")

            remove_rejected_mux_output(job)

            self.assertFalse(output.exists())
            self.assertEqual(b"source", source.read_bytes())

    def test_overwrite_temp_name_is_portable_and_has_no_trailing_space(self):
        old_suffix = GlobalSetting.RANDOM_OUTPUT_SUFFIX
        try:
            GlobalSetting.RANDOM_OUTPUT_SUFFIX = "12345"
            expected = "Episode#12345.tmp.mkv"
            self.assertEqual(expected, change_file_extension_to_temporary_mkv("Episode.mp4"))
            self.assertEqual(expected, change_file_extension_to_mkv_with_random_suffix("Episode.mp4"))
        finally:
            GlobalSetting.RANDOM_OUTPUT_SUFFIX = old_suffix


class MultipleTrackFlagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_tab_checkboxes_keep_multiple_flags(self):
        cases = (
            (AudioSetDefaultCheckBox, "AUDIO_SET_DEFAULT"),
            (AudioSetForcedCheckBox, "AUDIO_SET_FORCED"),
            (SubtitleSetDefaultCheckBox, "SUBTITLE_SET_DEFAULT"),
            (SubtitleSetForcedCheckBox, "SUBTITLE_SET_FORCED"),
        )
        for widget_class, setting_name in cases:
            with self.subTest(widget=widget_class.__name__):
                old_value = getattr(GlobalSetting, setting_name)
                values = defaultdict(bool)
                setattr(GlobalSetting, setting_name, values)
                try:
                    first = widget_class(0)
                    second = widget_class(1)
                    first.setCheckState(Qt.CheckState.Checked)
                    second.setCheckState(Qt.CheckState.Checked)
                    self.assertTrue(values[0])
                    self.assertTrue(values[1])
                finally:
                    setattr(GlobalSetting, setting_name, old_value)

    def test_per_job_dialog_editors_keep_multiple_flags(self):
        cases = (
            (AudioInfoDialog.update_current_audio_set_default, "current_audio_set_default"),
            (AudioInfoDialog.update_current_audio_set_forced, "current_audio_set_forced"),
            (SubtitleInfoDialog.update_current_subtitle_set_default, "current_subtitle_set_default"),
            (SubtitleInfoDialog.update_current_subtitle_set_forced, "current_subtitle_set_forced"),
        )
        for update_method, values_name in cases:
            with self.subTest(method=update_method.__name__):
                checkbox_name = update_method.__name__.replace("update_current_", "") + "_checkBox"
                holder = SimpleNamespace(
                    current_audio_index=1,
                    current_subtitle_index=1,
                    **{values_name: [True, False]},
                    **{checkbox_name: SimpleNamespace(
                        checkState=lambda: Qt.CheckState.Checked
                    )},
                )
                update_method(holder)
                self.assertEqual([True, True], getattr(holder, values_name))

    def test_new_tracks_do_not_clear_other_default_or_forced_flags(self):
        old_audio_enabled = GlobalSetting.AUDIO_ENABLED
        old_subtitle_enabled = GlobalSetting.SUBTITLE_ENABLED
        try:
            GlobalSetting.AUDIO_ENABLED = True
            GlobalSetting.SUBTITLE_ENABLED = True
            job = SingleJobData()
            job.audio_found = True
            job.audio_name_absolute = ["audio-1.aac", "audio-2.aac"]
            job.audio_language = ["English", "English"]
            job.audio_track_name = ["Main", "Commentary"]
            job.audio_set_default = [True, True]
            job.audio_set_forced = [True, True]
            job.audio_delay = [0, 0]
            job.subtitle_found = True
            job.subtitle_name_absolute = ["sub-1.srt", "sub-2.srt"]
            job.subtitle_language = ["English", "English"]
            job.subtitle_track_name = ["Full", "Signs"]
            job.subtitle_set_default = [True, True]
            job.subtitle_set_forced = [True, True]
            job.subtitle_delay = [0, 0]

            builder = GetJsonForMkvmergeJob.__new__(GetJsonForMkvmergeJob)
            builder.job = job
            builder.audios_track_json_info = [SimpleNamespace(id="1")]
            builder.subtitles_track_json_info = [SimpleNamespace(id="2")]
            builder.new_audio_append_command = ""
            builder.new_subtitle_append_command = ""
            builder.change_default_forced_audio_track_setting_source_video_command = ""
            builder.change_default_forced_subtitle_track_setting_source_video_command = ""

            builder.setup_new_audio_tracks_options()
            builder.setup_new_subtitle_tracks_options()

            self.assertEqual("", builder.change_default_forced_audio_track_setting_source_video_command)
            self.assertEqual("", builder.change_default_forced_subtitle_track_setting_source_video_command)
            self.assertEqual(4, builder.new_audio_append_command.count('"0:yes"'))
            self.assertEqual(4, builder.new_subtitle_append_command.count('"0:yes"'))
        finally:
            GlobalSetting.AUDIO_ENABLED = old_audio_enabled
            GlobalSetting.SUBTITLE_ENABLED = old_subtitle_enabled


class NetworkPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_windows_destination_syntax_accepts_unc_paths(self):
        self.assertTrue(
            is_valid_destination_path_syntax(
                r"\\media-server\shows\output",
                platform_name="nt",
            )
        )
        self.assertTrue(
            is_valid_destination_path_syntax(r"Z:\shows\output", platform_name="nt")
        )
        self.assertFalse(
            is_valid_destination_path_syntax("relative/output", platform_name="nt")
        )

    def test_source_line_edit_preserves_manual_unc_path(self):
        source_path = r"\\media-server\shows\source"
        line_edit = VideoSourceLineEdit()
        emitted_paths = []
        line_edit.edit_finished_signal.connect(emitted_paths.append)
        line_edit.setText(source_path)
        line_edit.setModified(True)

        with patch(
            "packages.Tabs.VideoTab.Widgets.VideoSourceLineEdit.os.path.isdir",
            return_value=True,
        ):
            line_edit.check_new_path()

        self.assertEqual(source_path, line_edit.text())
        self.assertEqual([source_path], emitted_paths)

    def test_destination_check_preserves_writable_unc_path(self):
        destination_path = r"\\media-server\shows\output"
        line_edit = SimpleNamespace(
            text=lambda: destination_path,
            setText=lambda _value: None,
        )
        holder = SimpleNamespace(destination_path_lineEdit=line_edit)
        old_destination = GlobalSetting.DESTINATION_FOLDER_PATH
        old_sources = GlobalSetting.VIDEO_SOURCE_PATHS
        old_overwrite = GlobalSetting.OVERWRITE_SOURCE_FILES
        try:
            GlobalSetting.DESTINATION_FOLDER_PATH = ""
            GlobalSetting.VIDEO_SOURCE_PATHS = []
            with patch(
                "packages.Tabs.MuxSetting.MuxSetting.makedirs"
            ) as make_directory, patch(
                "packages.Tabs.MuxSetting.MuxSetting.open",
                create=True,
            ) as open_file, patch(
                "packages.Tabs.MuxSetting.MuxSetting.os.remove"
            ) as remove_file:
                open_file.return_value.__enter__.return_value.write.return_value = None
                self.assertTrue(MuxSettingTab.check_destination_path(holder))

            make_directory.assert_called_once_with(destination_path, exist_ok=True)
            open_file.assert_called_once()
            remove_file.assert_called_once()
            self.assertEqual(destination_path, GlobalSetting.DESTINATION_FOLDER_PATH)
        finally:
            GlobalSetting.DESTINATION_FOLDER_PATH = old_destination
            GlobalSetting.VIDEO_SOURCE_PATHS = old_sources
            GlobalSetting.OVERWRITE_SOURCE_FILES = old_overwrite


class CommandAndModelAuditTests(unittest.TestCase):
    def test_media_probe_passes_special_characters_as_literal_argv(self):
        old_media_info_folder = GlobalFiles.MediaInfoFolderPath
        video_path = "/share/Series & Specials/Episode '01'.mkv"
        with tempfile.TemporaryDirectory() as temp_dir:
            GlobalFiles.MediaInfoFolderPath = temp_dir
            try:
                with patch(
                    "packages.Tabs.VideoTab.Widgets.GenerateMediaInfoFilesWorker.subprocess.run",
                    return_value=SimpleNamespace(returncode=0),
                ) as probe, patch(
                    "packages.Tabs.VideoTab.Widgets.GenerateMediaInfoFilesWorker.check_if_valid_video_input",
                    return_value=True,
                ), patch(
                    "packages.Tabs.VideoTab.Widgets.GenerateMediaInfoFilesWorker.time.sleep"
                ):
                    GenerateMediaInfoFilesWorker([video_path]).run()
            finally:
                GlobalFiles.MediaInfoFolderPath = old_media_info_folder

        self.assertEqual(
            [GlobalFiles.MKVMERGE_PATH, "-J", video_path],
            probe.call_args.args[0],
        )
        self.assertNotIn("shell", probe.call_args.kwargs)

    def test_failed_media_probe_reports_file_and_always_finishes(self):
        old_media_info_folder = GlobalFiles.MediaInfoFolderPath
        video_path = "/share/broken-video.mkv"
        with tempfile.TemporaryDirectory() as temp_dir:
            GlobalFiles.MediaInfoFolderPath = temp_dir
            worker = GenerateMediaInfoFilesWorker([video_path])
            unsupported = []
            progress = []
            finished = []
            worker.job_unsupported_file_signal.connect(unsupported.append)
            worker.job_succeeded_signal.connect(lambda: progress.append(True))
            worker.finished_all_jobs_signal.connect(lambda: finished.append(True))
            try:
                with patch(
                    "packages.Tabs.VideoTab.Widgets.GenerateMediaInfoFilesWorker.subprocess.run",
                    side_effect=OSError("probe failed"),
                ), patch(
                    "packages.Tabs.VideoTab.Widgets.GenerateMediaInfoFilesWorker.time.sleep"
                ), self.assertLogs(level="ERROR"):
                    worker.run()
            finally:
                GlobalFiles.MediaInfoFolderPath = old_media_info_folder

        self.assertEqual([video_path], unsupported)
        self.assertEqual([True], progress)
        self.assertEqual([True], finished)

    def test_job_builders_probe_with_literal_argv(self):
        old_info_path = GlobalFiles.mkvmergeJsonInfoFilePath
        video_path = "/share/Series & Specials/Episode '01'.mkv"
        job = SingleJobData()
        job.video_name_absolute = video_path

        def write_probe_json(_command, **kwargs):
            kwargs["stdout"].write('{"tracks": [], "attachments": []}')
            return SimpleNamespace(returncode=0)

        with tempfile.TemporaryDirectory() as temp_dir:
            GlobalFiles.mkvmergeJsonInfoFilePath = str(Path(temp_dir) / "probe.json")
            try:
                for builder_type in (GetJsonForMkvmergeJob, GetJsonForMkvpropeditJob):
                    with self.subTest(builder=builder_type.__name__), patch(
                        f"{builder_type.__module__}.subprocess.run",
                        side_effect=write_probe_json,
                    ) as probe:
                        builder = builder_type.__new__(builder_type)
                        builder.job = job
                        builder.videos_track_json_info = []
                        builder.audios_track_json_info = []
                        builder.subtitles_track_json_info = []
                        builder.attachments_json_info = []
                        builder.generate_info_file()
                    self.assertEqual(
                        [GlobalFiles.MKVMERGE_PATH, "-J", video_path],
                        probe.call_args.args[0],
                    )
                    self.assertNotIn("shell", probe.call_args.kwargs)
            finally:
                GlobalFiles.mkvmergeJsonInfoFilePath = old_info_path

    def test_start_worker_builds_response_file_argv(self):
        old_merge_path = GlobalFiles.MKVMERGE_PATH
        old_edit_path = GlobalFiles.MKVPROPEDIT_PATH
        old_merge_job = GlobalFiles.mkvmergeJsonJobFilePath
        old_edit_job = GlobalFiles.mkvpropeditJsonJobFilePath
        try:
            GlobalFiles.MKVMERGE_PATH = "/opt/MKV ToolNix/mkvmerge"
            GlobalFiles.MKVPROPEDIT_PATH = "/opt/MKV ToolNix/mkvpropedit"
            GlobalFiles.mkvmergeJsonJobFilePath = "/share/show & extras/merge.json"
            GlobalFiles.mkvpropeditJsonJobFilePath = "/share/show & extras/edit.json"
            controller = StartMuxingWorker.__new__(StartMuxingWorker)
            controller.current_job = 0
            controller.data = [SingleJobData()]
            controller.add_header_info_to_log_file = lambda: None
            controller.start_muxing_process_worker = SimpleNamespace(command=None, wait=True)
            controller.read_log_mkvmerge_worker = SimpleNamespace(job_index=-1, wait=True)
            controller.read_log_mkvpropedit_worker = SimpleNamespace(job_index=-1, wait=True)

            controller.start_mkvmerge_muxing()
            self.assertEqual(
                [GlobalFiles.MKVMERGE_PATH, "@" + GlobalFiles.mkvmergeJsonJobFilePath],
                controller.start_muxing_process_worker.command,
            )
            controller.start_mkvpropedit_muxing()
            self.assertEqual(
                [GlobalFiles.MKVPROPEDIT_PATH, "@" + GlobalFiles.mkvpropeditJsonJobFilePath],
                controller.start_muxing_process_worker.command,
            )
        finally:
            GlobalFiles.MKVMERGE_PATH = old_merge_path
            GlobalFiles.MKVPROPEDIT_PATH = old_edit_path
            GlobalFiles.mkvmergeJsonJobFilePath = old_merge_job
            GlobalFiles.mkvpropeditJsonJobFilePath = old_edit_job
            GlobalSetting.MUXING_ON = False

    def test_unsupported_video_filter_keeps_other_files(self):
        valid_first = Path("/videos/valid-first.mkv")
        unsupported = Path("/videos/not-video.mkv")
        valid_second = Path("/videos/valid-second.mkv")
        self.assertEqual(
            [valid_first, valid_second],
            filter_unsupported_files(
                [valid_first, unsupported, valid_second],
                [str(unsupported)],
            ),
        )

    def test_old_track_model_initializes_comparison_fields(self):
        first = SingleOldTrackData()
        second = SingleOldTrackData()
        self.assertEqual("", first.is_enabled)
        self.assertEqual(-1, first.order)
        self.assertEqual(first, second)

    def test_fixed_header_widgets_do_not_share_a_default_table(self):
        app = QApplication.instance() or QApplication([])
        first = TableFixedHeaderWidget()
        second = TableFixedHeaderWidget()
        try:
            self.assertIsNot(first.table, second.table)
        finally:
            first.close()
            second.close()
        self.assertIsNotNone(app)

    def test_failed_crc_job_does_not_rename_or_publish_output(self):
        job = SingleJobData()
        job.is_crc_calculating_required = True
        calls = []
        holder = SimpleNamespace(
            data=[job],
            start_muxing_worker=SimpleNamespace(pause=False),
            set_job_status_bad=lambda row_index: calls.append(("status", row_index)),
            rename_output_file_if_needed=lambda job_index: calls.append(("rename", job_index)),
            set_row_value_size_after_muxing=lambda finished_job, row_index: calls.append(
                ("size", row_index)
            ),
            persist_queue=lambda: calls.append(("persist", None)),
        )
        old_abort = GlobalSetting.MUX_SETTING_ABORT_ON_ERRORS
        try:
            GlobalSetting.MUX_SETTING_ABORT_ON_ERRORS = False
            JobQueueTable.job_error_occurred(holder, 0)
        finally:
            GlobalSetting.MUX_SETTING_ABORT_ON_ERRORS = old_abort

        self.assertTrue(job.done)
        self.assertTrue(job.error_occurred)
        self.assertNotIn(("rename", 0), calls)


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
    def test_managed_and_system_tools_are_preferred_to_stale_portable_copy(self):
        with patch.object(
            GlobalFiles, "get_custom_program_path", return_value=None
        ), patch(
            "packages.Startup.GlobalFiles.which",
            return_value="/usr/bin/mkvmerge",
        ):
            candidates = GlobalFiles.get_program_candidates("mkvmerge")
        executable_name = "mkvmerge.exe" if sys.platform == "win32" else "mkvmerge"
        self.assertEqual(
            Path(GlobalFiles.ManagedToolsFolderPath) / executable_name,
            candidates[0],
        )
        self.assertLess(
            candidates.index(Path("/usr/bin/mkvmerge")),
            candidates.index(Path(GlobalFiles.ToolsFolderPath) / executable_name),
        )
        self.assertEqual(
            Path(GlobalFiles.ToolsFolderPath) / executable_name,
            candidates[-1],
        )


if __name__ == "__main__":
    unittest.main()
