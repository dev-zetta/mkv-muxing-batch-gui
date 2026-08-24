import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from packages.Startup import GlobalFiles
from packages.Tabs.GlobalSetting import GlobalSetting
from packages.Tabs.MuxSetting.Widgets.SingleJobData import SingleJobData
from packages.Widgets.PathData import PathData
from packages.Widgets.SingleOldTrackData import SingleOldTrackData

SCHEMA_VERSION = 1
logger = logging.getLogger(__name__)
_VOLATILE_GLOBALS = {"JOB_QUEUE_EMPTY", "JOB_QUEUE_FINISHED", "MUXING_ON"}
_OBJECT_TYPES = {
    "PathData": PathData,
    "SingleOldTrackData": SingleOldTrackData,
}
_DEFAULT_FACTORIES = {
    "bool": bool,
    "float": float,
    "int": int,
    "list": list,
    "str": str,
    "SingleOldTrackData": SingleOldTrackData,
}


def _encode(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return {"__type__": "path", "value": str(value)}
    if isinstance(value, (list, tuple)):
        return [_encode(item) for item in value]
    if isinstance(value, dict):
        factory = None
        if isinstance(value, defaultdict) and value.default_factory is not None:
            factory = value.default_factory.__name__
        return {
            "__type__": "mapping",
            "default_factory": factory,
            "items": [[_encode(key), _encode(item)] for key, item in value.items()],
        }
    if isinstance(value, (PathData, SingleOldTrackData)):
        return {
            "__type__": value.__class__.__name__,
            "attributes": _encode(vars(value)),
        }
    raise TypeError(f"Unsupported queue-session value: {type(value).__name__}")


def _decode(value):
    if isinstance(value, list):
        return [_decode(item) for item in value]
    if not isinstance(value, dict) or "__type__" not in value:
        return value
    value_type = value["__type__"]
    if value_type == "path":
        return value["value"]
    if value_type == "mapping":
        factory_name = value.get("default_factory")
        if factory_name:
            result = defaultdict(_DEFAULT_FACTORIES.get(factory_name, str))
        else:
            result = {}
        for key, item in value.get("items", []):
            result[_decode(key)] = _decode(item)
        return result
    object_class = _OBJECT_TYPES.get(value_type)
    if object_class is not None:
        result = object_class()
        attributes = _decode(value.get("attributes", {}))
        for name, item in attributes.items():
            setattr(result, name, item)
        return result
    raise ValueError(f"Unknown queue-session type: {value_type}")


def _global_snapshot():
    snapshot = {}
    for name, value in vars(GlobalSetting).items():
        if not name.isupper() or name in _VOLATILE_GLOBALS:
            continue
        try:
            snapshot[name] = _encode(value)
        except TypeError:
            logger.warning("Queue recovery skipped unsupported setting %s", name)
    return snapshot


class QueueSessionStore:
    """Atomically stores the unfinished mux queue and the settings it needs."""

    def __init__(self, path=None):
        self.path = Path(path or GlobalFiles.QueueSessionFilePath)

    def save(self, jobs, state="queued", active_job=None):
        if not jobs:
            self.delete()
            return
        document = {
            "schema_version": SCHEMA_VERSION,
            "saved_at": datetime.now().astimezone().isoformat(),
            "state": state,
            "active_job": active_job,
            "globals": _global_snapshot(),
            "jobs": [_encode(vars(job)) for job in jobs],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with open(temporary_path, "w", encoding="utf-8", newline="\n") as file:
                json.dump(document, file, ensure_ascii=False, indent=2)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, self.path)
        except Exception:
            logger.exception("Could not save the persistent mux queue")
            try:
                temporary_path.unlink()
            except OSError:
                pass

    def load(self):
        if not self.path.is_file():
            return None
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                document = json.load(file)
            if document.get("schema_version") != SCHEMA_VERSION:
                raise ValueError("Unsupported queue-session version")
            encoded_jobs = document.get("jobs")
            if not isinstance(encoded_jobs, list) or not encoded_jobs:
                raise ValueError("Queue session does not contain jobs")

            globals_snapshot = document.get("globals", {})
            if not isinstance(globals_snapshot, dict):
                raise TypeError("Queue session settings are invalid")

            jobs = []
            default_attributes = vars(SingleJobData())
            for encoded_job in encoded_jobs:
                attributes = _decode(encoded_job)
                if not isinstance(attributes, dict):
                    raise TypeError("Queue session job is invalid")
                job = SingleJobData()
                for name, value in attributes.items():
                    if name in default_attributes:
                        setattr(job, name, value)
                if not job.done:
                    # A process killed during a job cannot safely continue at a
                    # byte offset. Restart only that job; completed jobs remain done.
                    job.progress = 0
                    job.progress_crc = 0
                    job.error_occurred = False
                    job.muxing_message = ""
                    job.used_mkvpropedit = False
                    job.new_crc = ""
                jobs.append(job)
            retryable_jobs = [
                job for job in jobs
                if not job.done
                or (job.error_occurred and "There is not enough space" in job.muxing_message)
            ]
            if not retryable_jobs:
                self.delete()
                return None

            for name, value in globals_snapshot.items():
                if name.isupper() and name not in _VOLATILE_GLOBALS and hasattr(GlobalSetting, name):
                    setattr(GlobalSetting, name, _decode(value))
            return {
                "jobs": jobs,
                "state": document.get("state", "queued"),
                "active_job": document.get("active_job"),
                "saved_at": document.get("saved_at", ""),
            }
        except Exception:
            logger.exception("Could not restore the persistent mux queue")
            self._quarantine_corrupt_file()
            return None

    def delete(self):
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            logger.exception("Could not remove the completed mux queue session")

    def _quarantine_corrupt_file(self):
        if not self.path.exists():
            return
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        corrupt_path = self.path.with_name(f"{self.path.stem}.corrupt-{timestamp}{self.path.suffix}")
        try:
            os.replace(self.path, corrupt_path)
        except OSError:
            logger.exception("Could not quarantine the corrupt mux queue session")
