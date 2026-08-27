import time
import traceback

from PySide6.QtCore import Signal, QObject, QThread

from packages.Startup import GlobalFiles
from packages.Tabs.GlobalSetting import write_to_log_file
from packages.Tabs.MuxSetting.Widgets.MuxingParams import MuxingParams


def next_line(file, should_stop=lambda: False):
    file.seek(0, 2)  # go to the end of file
    while True:
        line = file.readline()
        if line:
            yield line
        elif should_stop():
            return
        else:
            time.sleep(0.05)


class ReadFromMkvpropeditLogWorker(QObject):
    finished_job_signal = Signal()
    all_finished = Signal()
    send_muxing_progress_data_signal = Signal(MuxingParams)

    def __init__(self, job_index):
        super().__init__()
        self.job_index = job_index
        self.wait = True
        self.stop = False
        self.process_finished = False

    def run(self):
        try:
            while not self.stop:
                if not self.wait:
                    muxing_params = MuxingParams()
                    muxing_params.index = self.job_index
                    muxing_params.progress = 0
                    with open(GlobalFiles.MuxingLogFilePath, "a+", encoding="UTF-8") as log_file:
                        for line in next_line(
                                log_file,
                                lambda: self.stop or self.process_finished):
                            if line.find('Done.') != -1 or line.find('No changes were made') != -1:
                                muxing_params.progress = 100
                                self.send_muxing_progress_data_signal.emit(muxing_params)
                                break
                            elif line.find('Error:') != -1:
                                muxing_params.error = True
                                muxing_params.message = line
                                self.send_muxing_progress_data_signal.emit(muxing_params)
                                break
                    if self.stop:
                        break
                    self.finished_job_signal.emit()
                    self.wait = True
                    self.process_finished = False
                else:
                    QThread.msleep(50)

        except Exception:
            write_to_log_file(traceback.format_exc())
        finally:
            self.all_finished.emit()
