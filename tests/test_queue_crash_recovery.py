import os
import subprocess
import sys
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from packages.Startup import GlobalFiles
from packages.Tabs.GlobalSetting import GlobalSetting
from packages.Tabs.MuxSetting.MuxSetting import MuxSettingTab
from packages.Tabs.MuxSetting.Widgets.JobQueueTable import JobQueueTable
from packages.Tabs.MuxSetting.Widgets.QueueSessionStore import QueueSessionStore
from packages.Tabs.MuxSetting.Widgets.SingleJobData import SingleJobData
from packages.Widgets.PathData import PathData
from packages.Widgets.SingleOldTrackData import SingleOldTrackData


class QueueSessionStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.session_path = Path(self.temp_dir.name) / "queue_session.json"
        self.store = QueueSessionStore(self.session_path)
        self.original_destination = GlobalSetting.DESTINATION_FOLDER_PATH
        self.original_subtitles = GlobalSetting.SUBTITLE_FILES_LIST
        self.original_old_tracks = GlobalSetting.VIDEO_OLD_TRACKS_AUDIOS_BULK_SETTING
        self.original_attachment_paths = GlobalSetting.ATTACHMENT_PATH_DATA_LIST

    def tearDown(self):
        GlobalSetting.DESTINATION_FOLDER_PATH = self.original_destination
        GlobalSetting.SUBTITLE_FILES_LIST = self.original_subtitles
        GlobalSetting.VIDEO_OLD_TRACKS_AUDIOS_BULK_SETTING = self.original_old_tracks
        GlobalSetting.ATTACHMENT_PATH_DATA_LIST = self.original_attachment_paths
        self.temp_dir.cleanup()

    @staticmethod
    def make_job(index, done=False, progress=0):
        job = SingleJobData()
        job.video_name = f"Episode {index:03}.mp4"
        job.video_name_absolute = f"C:/source/Episode {index:03}.mp4"
        job.video_name_with_spaces = f" {job.video_name}   "
        job.video_name_displayed = "\u200e" + job.video_name_with_spaces
        job.size_before_muxing = " 120.00 MB"
        job.done = done
        job.progress = progress
        if done:
            job.output_video_name = Path(f"Episode {index:03}.mkv")
            job.output_video_absolute_path = f"C:/output/Episode {index:03}.mkv"
            job.size_after_muxing = " 121.00 MB"
        return job

    def test_atomic_round_trip_restores_settings_and_restarts_interrupted_job(self):
        GlobalSetting.DESTINATION_FOLDER_PATH = "C:/خروجی"
        GlobalSetting.SUBTITLE_FILES_LIST = defaultdict(list, {0: ["فارسی.srt"]})
        track = SingleOldTrackData()
        track.id = "1"
        track.track_name = "Main audio"
        track.is_enabled = True
        track.order = 0
        GlobalSetting.VIDEO_OLD_TRACKS_AUDIOS_BULK_SETTING = defaultdict(
            SingleOldTrackData, {"1": track}
        )
        attachment_path = PathData()
        attachment_path.name = "Fonts"
        attachment_path.absolute_name = "C:/Fonts"
        attachment_path.files_list = ["C:/Fonts/font.ttf"]
        GlobalSetting.ATTACHMENT_PATH_DATA_LIST = [attachment_path]
        completed = self.make_job(1, done=True, progress=100)
        interrupted = self.make_job(2, progress=67)
        interrupted.used_mkvpropedit = True
        interrupted.new_crc = "1234ABCD"

        self.store.save([completed, interrupted], state="running", active_job=1)

        self.assertTrue(self.session_path.is_file())
        self.assertFalse(self.session_path.with_suffix(".json.tmp").exists())
        GlobalSetting.DESTINATION_FOLDER_PATH = "changed"
        GlobalSetting.SUBTITLE_FILES_LIST = defaultdict(list)
        GlobalSetting.ATTACHMENT_PATH_DATA_LIST = []
        recovered = self.store.load()

        self.assertEqual("C:/خروجی", GlobalSetting.DESTINATION_FOLDER_PATH)
        self.assertEqual(["فارسی.srt"], GlobalSetting.SUBTITLE_FILES_LIST[0])
        self.assertEqual("Main audio", GlobalSetting.VIDEO_OLD_TRACKS_AUDIOS_BULK_SETTING["1"].track_name)
        self.assertEqual(["C:/Fonts/font.ttf"], GlobalSetting.ATTACHMENT_PATH_DATA_LIST[0].files_list)
        self.assertTrue(recovered["jobs"][0].done)
        self.assertEqual(100, recovered["jobs"][0].progress)
        self.assertFalse(recovered["jobs"][1].done)
        self.assertEqual(0, recovered["jobs"][1].progress)
        self.assertFalse(recovered["jobs"][1].used_mkvpropedit)
        self.assertEqual("", recovered["jobs"][1].new_crc)

    def test_large_queue_keeps_completed_prefix_and_pending_remainder(self):
        jobs = [self.make_job(index, done=index < 57, progress=100 if index < 57 else 0)
                for index in range(250)]
        jobs[57].progress = 81
        self.store.save(jobs, state="running", active_job=57)

        recovered = self.store.load()["jobs"]

        self.assertEqual(250, len(recovered))
        self.assertEqual(57, sum(job.done for job in recovered))
        self.assertEqual(0, recovered[57].progress)
        self.assertEqual("Episode 249.mp4", recovered[-1].video_name)

    def test_session_survives_abrupt_process_exit(self):
        script = (
            "import os; "
            "from packages.Tabs.MuxSetting.Widgets.QueueSessionStore import QueueSessionStore; "
            "from packages.Tabs.MuxSetting.Widgets.SingleJobData import SingleJobData; "
            "job=SingleJobData(); job.video_name='Interrupted.mkv'; job.progress=73; "
            f"QueueSessionStore({str(self.session_path)!r}).save([job], state='running', active_job=0); "
            "os._exit(37)"
        )

        process = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).parents[1],
            check=False,
        )
        recovered = self.store.load()

        self.assertEqual(37, process.returncode)
        self.assertEqual("Interrupted.mkv", recovered["jobs"][0].video_name)
        self.assertEqual(0, recovered["jobs"][0].progress)

    def test_corrupt_session_is_quarantined_instead_of_raising(self):
        self.session_path.write_text('{"schema_version": 1, "jobs": [', encoding="utf-8")

        with self.assertLogs(level="ERROR"):
            recovered = self.store.load()

        self.assertIsNone(recovered)
        self.assertFalse(self.session_path.exists())
        quarantined = list(self.session_path.parent.glob("queue_session.corrupt-*.json"))
        self.assertEqual(1, len(quarantined))

    def test_delete_removes_completed_or_cleared_session(self):
        self.store.save([self.make_job(1)])
        self.store.delete()
        self.assertFalse(self.session_path.exists())

    def test_fully_completed_session_is_discarded_on_startup(self):
        self.store.save([self.make_job(1, done=True, progress=100)], state="running")

        recovered = self.store.load()

        self.assertIsNone(recovered)
        self.assertFalse(self.session_path.exists())


class QueueRecoveryUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_recovered_table_shows_completed_and_resumable_jobs(self):
        old_empty = GlobalSetting.JOB_QUEUE_EMPTY
        old_finished = GlobalSetting.JOB_QUEUE_FINISHED
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                session_path = Path(temp_dir) / "queue_session.json"
                store = QueueSessionStore(session_path)
                completed = QueueSessionStoreTests.make_job(1, done=True, progress=100)
                interrupted = QueueSessionStoreTests.make_job(2, progress=54)
                store.save([completed, interrupted], state="running", active_job=1)
                table = JobQueueTable(queue_session_path=session_path)

                restored = table.restore_queue()

                self.assertTrue(restored)
                self.assertEqual(2, table.rowCount())
                self.assertEqual(1, table.number_of_done_jobs)
                self.assertEqual(0, table.data[1].progress)
                self.assertIn("ready to resume", table.cellWidget(1, table.column_ids["Status"]).toolTip())
                self.assertEqual(0, table.cellWidget(1, table.column_ids["Progress"]).value)
                table.deleteLater()
                self.app.processEvents()
        finally:
            GlobalSetting.JOB_QUEUE_EMPTY = old_empty
            GlobalSetting.JOB_QUEUE_FINISHED = old_finished

    def test_mux_tab_startup_automatically_offers_resume(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session_path = Path(temp_dir) / "queue_session.json"
            old_session_path = GlobalFiles.QueueSessionFilePath
            old_destination = GlobalSetting.DESTINATION_FOLDER_PATH
            old_empty = GlobalSetting.JOB_QUEUE_EMPTY
            old_finished = GlobalSetting.JOB_QUEUE_FINISHED
            try:
                GlobalFiles.QueueSessionFilePath = str(session_path)
                GlobalSetting.DESTINATION_FOLDER_PATH = "C:/recovered-output"
                QueueSessionStore(session_path).save(
                    [QueueSessionStoreTests.make_job(1)], state="running", active_job=0
                )
                tab = MuxSettingTab()

                tab.set_preset_options()

                self.assertEqual("RESUME", tab.control_queue_button.state)
                self.assertEqual("C:/recovered-output", tab.destination_path_lineEdit.text())
                self.assertTrue(tab.clear_job_queue_button.isEnabled())
                self.assertIn("recovered", tab.job_queue_groupBox.title())
                tab.deleteLater()
                self.app.processEvents()
            finally:
                GlobalFiles.QueueSessionFilePath = old_session_path
                GlobalSetting.DESTINATION_FOLDER_PATH = old_destination
                GlobalSetting.JOB_QUEUE_EMPTY = old_empty
                GlobalSetting.JOB_QUEUE_FINISHED = old_finished


if __name__ == "__main__":
    unittest.main()
