import io
import os
import tempfile
import unittest

from PySide6.QtCore import QThread, QTimer
from PySide6.QtWidgets import QApplication

from packages.Startup import GlobalFiles
from packages.Tabs.GlobalSetting import GlobalSetting
from packages.Tabs.MuxSetting.Widgets.CalculateCRCProcessWorker import (
    CalculateCRCProcessWorker,
)
from packages.Tabs.MuxSetting.Widgets.ReadFromMkvmergeLogWorker import (
    ReadFromMkvmergeLogWorker,
    next_line,
)
from packages.Tabs.MuxSetting.Widgets.SingleJobData import SingleJobData
from packages.Tabs.MuxSetting.Widgets.StartMuxingWorker import StartMuxingWorker


class MuxingWorkerLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def run_completed_queue(self, job_count):
        jobs = [SingleJobData() for _ in range(job_count)]
        for job in jobs:
            job.done = True

        controller_thread = QThread()
        worker = StartMuxingWorker(jobs)
        completed = []
        timed_out = []

        worker.moveToThread(controller_thread)
        controller_thread.started.connect(worker.run)
        worker.finished_all_jobs_signal.connect(lambda: completed.append(True))
        worker.finished_all_jobs_signal.connect(controller_thread.quit)
        controller_thread.finished.connect(self.app.quit)

        def fail_on_timeout():
            timed_out.append(True)
            self.app.quit()

        timeout_timer = QTimer()
        timeout_timer.setSingleShot(True)
        timeout_timer.timeout.connect(fail_on_timeout)
        timeout_timer.start(5000)
        controller_thread.start()
        self.app.exec()
        timeout_timer.stop()

        self.assertFalse(timed_out, "worker shutdown timed out")
        self.assertTrue(completed, "queue never emitted its completion signal")
        self.assertFalse(controller_thread.isRunning())

    def test_large_completed_queue_does_not_recurse(self):
        self.run_completed_queue(2000)

    def test_repeated_queue_shutdown_joins_all_helper_threads(self):
        for _ in range(60):
            self.run_completed_queue(0)

    def test_log_tail_can_be_interrupted_without_a_sentinel_line(self):
        stopped_tail = next_line(io.StringIO(""), should_stop=lambda: True)
        with self.assertRaises(StopIteration):
            next(stopped_tail)

    def test_active_log_reader_stops_without_a_sentinel_line(self):
        original_log_path = GlobalFiles.MuxingLogFilePath
        log_file = tempfile.NamedTemporaryFile(delete=False)
        log_file.close()

        reader_thread = QThread()
        reader = ReadFromMkvmergeLogWorker(job_index=0)
        reader.wait = False
        reader.moveToThread(reader_thread)
        reader_thread.started.connect(reader.run)
        reader.all_finished.connect(reader_thread.quit)
        reader_thread.finished.connect(self.app.quit)

        try:
            GlobalFiles.MuxingLogFilePath = log_file.name
            timed_out = []
            timeout_timer = QTimer()
            timeout_timer.setSingleShot(True)
            timeout_timer.timeout.connect(lambda: (timed_out.append(True), self.app.quit()))
            timeout_timer.start(5000)
            reader_thread.start()
            QTimer.singleShot(100, lambda: setattr(reader, "stop", True))
            self.app.exec()
            timeout_timer.stop()
            self.assertFalse(timed_out, "active log reader shutdown timed out")
            self.assertFalse(reader_thread.isRunning())
        finally:
            GlobalFiles.MuxingLogFilePath = original_log_path
            if reader_thread.isRunning():
                reader.stop = True
                reader_thread.quit()
                reader_thread.wait()
            os.unlink(log_file.name)

    def test_crc_worker_coalesces_progress_updates_for_large_files(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mkv") as file_handle:
            file_handle.write(b"x" * 10_000)

        worker = CalculateCRCProcessWorker(file_handle.name)
        worker.chunk_size = 1
        worker.wait = False
        progress_updates = []
        results = []
        worker.crc_progress_signal.connect(progress_updates.append)

        def finish(crc):
            results.append(crc)
            worker.stop = True

        worker.crc_result_signal.connect(finish)
        try:
            worker.run()
            self.assertTrue(results)
            self.assertLessEqual(len(progress_updates), 101)
            self.assertEqual(progress_updates, sorted(set(progress_updates)))
            self.assertEqual(progress_updates[-1], 100)
        finally:
            os.unlink(file_handle.name)

    def test_crc_worker_reads_exact_overwrite_output_path(self):
        old_overwrite = GlobalSetting.OVERWRITE_SOURCE_FILES
        with tempfile.NamedTemporaryFile(
                delete=False,
                suffix="#12345.tmp.mkv",
        ) as file_handle:
            file_handle.write(b"completed mux output")

        worker = CalculateCRCProcessWorker(file_handle.name)
        worker.wait = False
        results = []

        def finish(crc):
            results.append(crc)
            worker.stop = True

        worker.crc_result_signal.connect(finish)
        try:
            GlobalSetting.OVERWRITE_SOURCE_FILES = True
            worker.run()
            self.assertEqual(1, len(results))
        finally:
            GlobalSetting.OVERWRITE_SOURCE_FILES = old_overwrite
            os.unlink(file_handle.name)

    def test_crc_failure_is_reported_instead_of_silently_ending(self):
        worker = CalculateCRCProcessWorker("/missing/completed-output.mkv")
        worker.wait = False
        errors = []

        def fail(error):
            errors.append(error)
            worker.stop = True

        worker.crc_failed_signal.connect(fail)
        worker.run()

        self.assertEqual(1, len(errors))
        self.assertIn("completed-output.mkv", errors[0])

    def test_log_reader_finishes_when_process_ends_without_marker(self):
        original_log_path = GlobalFiles.MuxingLogFilePath
        log_file = tempfile.NamedTemporaryFile(delete=False)
        log_file.close()
        reader = ReadFromMkvmergeLogWorker(job_index=3)
        reader.wait = False
        reader.process_finished = True
        finished = []

        def finish():
            finished.append(True)
            reader.stop = True

        reader.finished_job_signal.connect(finish)
        try:
            GlobalFiles.MuxingLogFilePath = log_file.name
            reader.run()
            self.assertEqual([True], finished)
        finally:
            GlobalFiles.MuxingLogFilePath = original_log_path
            os.unlink(log_file.name)


if __name__ == "__main__":
    unittest.main()
