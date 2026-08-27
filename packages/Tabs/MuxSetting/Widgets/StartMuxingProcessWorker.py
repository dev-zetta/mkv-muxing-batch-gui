import subprocess
import traceback

from PySide6.QtCore import Signal, QObject, QThread

from packages.Startup import GlobalFiles
from packages.Tabs.GlobalSetting import write_to_log_file


class StartMuxingProcessWorker(QObject):
    finished_job_signal = Signal(int)
    all_finished = Signal()

    def __init__(self, command=""):
        super().__init__()
        self.command = command
        self.wait = True
        self.stop = False

    def run(self):
        try:
            while not self.stop:
                if not self.wait:
                    try:
                        with open(GlobalFiles.MuxingLogFilePath, "a+", encoding="UTF-8") as log_file:
                            mux_process = subprocess.run(
                                self.command,
                                shell=True,
                                stdout=log_file,
                                env=GlobalFiles.ENVIRONMENT,
                            )
                        exit_code = mux_process.returncode
                    except Exception:
                        write_to_log_file(traceback.format_exc())
                        exit_code = 2
                    self.finished_job_signal.emit(exit_code)
                    self.wait = True
                else:
                    QThread.msleep(50)
        finally:
            self.all_finished.emit()
