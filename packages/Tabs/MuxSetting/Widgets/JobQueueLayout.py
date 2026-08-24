from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from packages.Tabs.MuxSetting.Widgets.CompletedJobsCounter import CompletedJobsCounter
from packages.Tabs.MuxSetting.Widgets.JobDividingLine import JobDividingLine
from packages.Tabs.MuxSetting.Widgets.JobQueueTable import JobQueueTable
from packages.Tabs.MuxSetting.Widgets.ProgreeBar import ProgressBar


class QueueSummaryCard(QFrame):
    def __init__(self, caption, value=0, parent=None):
        super().__init__(parent)
        self.setObjectName("summaryCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(0)
        self.value_label = QLabel(str(value))
        self.value_label.setObjectName("summaryValue")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.caption_label = QLabel(caption)
        self.caption_label.setObjectName("summaryCaption")
        self.caption_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.value_label)
        layout.addWidget(self.caption_label)

    def set_value(self, value):
        self.value_label.setText(str(value))


class JobQueueLayout(QGridLayout):
    update_task_bar_progress_signal = Signal(int)
    paused_done_signal = Signal()
    cancel_done_signal = Signal()
    finished_all_jobs_signal = Signal()
    pause_from_error_occurred_signal = Signal()

    def __init__(self, parent=None, queue_session_path=None):
        super().__init__(parent=parent)
        self.number_of_jobs = 0
        self.number_of_completed_jobs = 0
        self.number_of_active_jobs = 0

        self.table = JobQueueTable(queue_session_path=queue_session_path)
        self.total_progress_label = QLabel("Overall")
        self.total_progress_progressBar = ProgressBar(value=0, show_percentage=True)
        self.total_progress_progressBar.setMinimumWidth(180)
        self.job_dividing_line = JobDividingLine()
        self.completed_jobs_counter = CompletedJobsCounter()
        self.queue_saved_label = QLabel("●  Queue saved automatically")
        self.queue_saved_label.setObjectName("queueSavedLabel")

        self.jobs_card = QueueSummaryCard("Jobs")
        self.completed_card = QueueSummaryCard("Completed")
        self.running_card = QueueSummaryCard("Running")
        self.pending_card = QueueSummaryCard("Pending")

        self.setup_layout()
        self.table.update_total_progress_signal.connect(self.update_total_progress)
        self.table.paused_done_signal.connect(self.paused_done)
        self.table.cancel_done_signal.connect(self.cancel_done)
        self.table.pause_from_error_occurred_signal.connect(self.pause_from_error_occurred)
        self.table.finished_all_jobs_signal.connect(self.finished_all_jobs)
        self.table.increase_number_of_done_jobs_signal.connect(self.increase_completed_jobs)
        self.table.set_number_of_jobs_signal.connect(self.set_number_of_jobs)
        self.table.set_number_of_done_jobs_signal.connect(self.set_number_of_done_jobs)

    def setup_layout(self):
        self.setContentsMargins(10, 12, 10, 10)
        self.setHorizontalSpacing(10)
        self.setVerticalSpacing(10)

        summary_widget = QWidget()
        summary_layout = QHBoxLayout(summary_widget)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(8)
        summary_layout.addWidget(self.jobs_card)
        summary_layout.addWidget(self.completed_card)
        summary_layout.addWidget(self.running_card)
        summary_layout.addWidget(self.pending_card)

        footer_widget = QWidget()
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(9)
        footer_layout.addWidget(self.queue_saved_label)
        footer_layout.addStretch(1)
        footer_layout.addWidget(self.total_progress_label)
        footer_layout.addWidget(self.total_progress_progressBar)
        footer_layout.addWidget(self.job_dividing_line)
        footer_layout.addWidget(self.completed_jobs_counter)

        self.addWidget(summary_widget, 0, 0)
        self.addWidget(self.table, 1, 0)
        self.addWidget(footer_widget, 2, 0)
        self.setRowStretch(1, 1)

    def update_summary(self):
        pending = max(
            self.number_of_jobs - self.number_of_completed_jobs - self.number_of_active_jobs,
            0,
        )
        self.jobs_card.set_value(self.number_of_jobs)
        self.completed_card.set_value(self.number_of_completed_jobs)
        self.running_card.set_value(self.number_of_active_jobs)
        self.pending_card.set_value(pending)

    def update_layout(self):
        self.table.update_widget()

    def setup_queue(self):
        self.number_of_active_jobs = 0
        self.table.setup_queue()
        self.update_summary()

    def restore_queue(self):
        restored = self.table.restore_queue()
        self.number_of_active_jobs = 0
        self.update_summary()
        return restored

    def persist_queue(self):
        self.table.persist_queue()

    def show_necessary_table_columns(self):
        self.table.show_necessary_columns()

    def clear_queue(self):
        self.number_of_jobs = 0
        self.number_of_completed_jobs = 0
        self.number_of_active_jobs = 0
        self.completed_jobs_counter.initiate_number_of_jobs(0)
        self.total_progress_progressBar.setValue(0)
        self.table.clear_queue()
        self.update_summary()

    def start_muxing(self):
        self.number_of_active_jobs = 1 if self.number_of_jobs > self.number_of_completed_jobs else 0
        self.update_summary()
        self.table.start_muxing()

    def paused_done(self):
        self.number_of_active_jobs = 0
        self.update_summary()
        self.paused_done_signal.emit()

    def cancel_done(self):
        self.number_of_active_jobs = 0
        self.update_summary()
        self.cancel_done_signal.emit()

    def update_total_progress(self, new_progress):
        self.total_progress_progressBar.setValue(new_progress)
        self.update_task_bar_progress_signal.emit(new_progress)

    def increase_completed_jobs(self):
        self.number_of_completed_jobs += 1
        self.completed_jobs_counter.increase_completed_jobs()
        self.update_summary()

    def set_number_of_jobs(self, number_of_jobs):
        self.number_of_jobs = number_of_jobs
        self.completed_jobs_counter.initiate_number_of_jobs(number_of_jobs)
        self.update_summary()

    def set_number_of_done_jobs(self, number_of_done_jobs):
        self.number_of_completed_jobs = number_of_done_jobs
        self.completed_jobs_counter.set_number_of_completed_jobs(number_of_done_jobs)
        self.update_summary()

    def pause_muxing(self):
        self.table.pause_muxing()

    def finished_all_jobs(self):
        self.number_of_active_jobs = 0
        self.update_summary()
        self.finished_all_jobs_signal.emit()

    def pause_from_error_occurred(self):
        self.pause_from_error_occurred_signal.emit()
