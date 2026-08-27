import hashlib
import json
import os
import subprocess
import time
import traceback

from PySide6.QtCore import QObject, Signal

from packages.Startup import GlobalFiles
from packages.Tabs.GlobalSetting import write_to_log_file


def get_attribute(data, attribute, default_value):
    return data.get(attribute) or default_value


def check_if_valid_video_input(file_name):
    string_name_hash = hashlib.sha1((str(file_name)).encode('utf-8')).hexdigest()
    media_info_file_path = os.path.join(GlobalFiles.MediaInfoFolderPath, string_name_hash + ".json")
    with open(media_info_file_path, 'r', encoding="UTF-8") as media_info_file:
        json_info = json.load(media_info_file)
    tracks_json_info = get_attribute(json_info, "tracks", False)
    if not tracks_json_info:
        return False
    is_valid_video = False
    for track in tracks_json_info:
        if get_attribute(track, "type", "not video") == "video":
            is_valid_video = True
            break
    return is_valid_video


class GenerateMediaInfoFilesWorker(QObject):
    job_succeeded_signal = Signal()
    job_unsupported_file_signal = Signal(str)
    finished_all_jobs_signal = Signal()

    def __init__(self, video_list):
        super().__init__()
        self.video_list = video_list

    def run(self):
        try:
            for file_name in self.video_list:
                valid_video = False
                try:
                    string_name_hash = hashlib.sha1((str(file_name)).encode('utf-8')).hexdigest()
                    media_info_file_path = os.path.join(
                        GlobalFiles.MediaInfoFolderPath,
                        string_name_hash + ".json",
                    )
                    with open(media_info_file_path, 'w+', encoding="UTF-8") as media_info_file:
                        command = [GlobalFiles.MKVMERGE_PATH, "-J", str(file_name)]
                        result = subprocess.run(
                            command,
                            stdout=media_info_file,
                            env=GlobalFiles.ENVIRONMENT,
                        )
                    valid_video = (
                        result.returncode in (0, 1)
                        and check_if_valid_video_input(file_name)
                    )
                except Exception:
                    write_to_log_file(traceback.format_exc())
                if not valid_video:
                    self.job_unsupported_file_signal.emit(file_name)
                self.job_succeeded_signal.emit()
                time.sleep(0.05)
        finally:
            self.finished_all_jobs_signal.emit()
