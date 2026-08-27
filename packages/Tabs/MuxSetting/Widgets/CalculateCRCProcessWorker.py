import zlib
from os.path import getsize

from PySide6.QtCore import QObject, QThread, Signal

class CalculateCRCProcessWorker(QObject):
    crc_progress_signal = Signal(int)
    crc_result_signal = Signal(str)
    crc_failed_signal = Signal(str)
    all_finished = Signal()

    def __init__(self, file_name=""):
        super().__init__()
        self.file_name = file_name
        self.progress = 0
        self.chunk_size = 1024 * 1024
        self.wait = True
        self.stop = False

    def run(self):
        try:
            while not self.stop:
                if not self.wait:
                    try:
                        # StartMuxingWorker supplies the exact completed output
                        # path. Rewriting its extension here used to append the
                        # overwrite suffix twice and made CRC jobs stall.
                        file_size = getsize(self.file_name)
                        with open(self.file_name, "rb") as file:
                            checksum = 0
                            current_read = 0
                            last_reported_percent = -1
                            while chunk := file.read(self.chunk_size):
                                if self.stop:
                                    break
                                current_read += len(chunk)
                                current_percent = int(min(100 * current_read / file_size, 100))
                                # Reading a large video in small chunks used to queue
                                # one GUI event per chunk.  The GUI only displays an
                                # integer percentage, so duplicate events could leave
                                # its event loop permanently behind after a long batch.
                                if current_percent != last_reported_percent:
                                    self.crc_progress_signal.emit(current_percent)
                                    last_reported_percent = current_percent
                                checksum = zlib.crc32(chunk, checksum)
                            if self.stop:
                                break
                            crc_string = format(checksum & 0xFFFFFFFF, '08x').upper()
                            self.crc_result_signal.emit(crc_string)
                    except (OSError, ValueError, ZeroDivisionError) as error:
                        self.crc_failed_signal.emit(str(error))
                    finally:
                        self.wait = True
                else:
                    QThread.msleep(50)
        finally:
            self.all_finished.emit()
