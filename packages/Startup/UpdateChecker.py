import gzip
import io
import json
import logging
import re
import threading
from dataclasses import dataclass
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from PySide6.QtCore import QObject, Signal


APP_RELEASE_API_URL = (
    "https://api.github.com/repos/dev-zetta/mkv-muxing-batch-gui/releases/latest"
)
APP_RELEASES_URL = "https://github.com/dev-zetta/mkv-muxing-batch-gui/releases/latest"
MKVTOOLNIX_RELEASE_API_URL = "https://mkvtoolnix.download/latest-release.xml.gz"
MKVTOOLNIX_DOWNLOAD_URL = "https://mkvtoolnix.download/downloads.html"
MAX_UPDATE_RESPONSE_SIZE = 1024 * 1024
UPDATE_TIMEOUT_SECONDS = 7


@dataclass(frozen=True)
class AvailableUpdate:
    component: str
    current_version: str
    latest_version: str
    download_url: str


@dataclass(frozen=True)
class UpdateReport:
    updates: tuple[AvailableUpdate, ...] = ()
    errors: tuple[str, ...] = ()


def extract_version(value):
    """Return a numeric dotted version from a tag or tool version string."""
    match = re.search(r"(?<!\d)[vV]?(\d+(?:\.\d+){1,3})(?!\d)", str(value))
    return match.group(1) if match else ""


def version_key(value):
    version = extract_version(value)
    if not version:
        return None
    parts = tuple(int(part) for part in version.split("."))
    return parts + (0,) * (4 - len(parts))


def is_newer_version(latest_version, current_version):
    latest_key = version_key(latest_version)
    current_key = version_key(current_version)
    return bool(latest_key and current_key and latest_key > current_key)


def parse_app_release(payload):
    release = json.loads(payload.decode("utf-8"))
    if release.get("draft") or release.get("prerelease"):
        raise ValueError("The latest application release is not stable")
    latest_version = extract_version(release.get("tag_name", ""))
    if not latest_version:
        raise ValueError("The latest application release has no valid version")
    return latest_version


def parse_mkvtoolnix_release(payload):
    if payload.startswith(b"\x1f\x8b"):
        with gzip.GzipFile(fileobj=io.BytesIO(payload)) as compressed_feed:
            payload = compressed_feed.read(MAX_UPDATE_RESPONSE_SIZE + 1)
        if len(payload) > MAX_UPDATE_RESPONSE_SIZE:
            raise ValueError("The decompressed update response is unexpectedly large")
    root = ElementTree.fromstring(payload)
    latest_version = extract_version(root.findtext("./latest-source/version", ""))
    if not latest_version:
        raise ValueError("The MKVToolNix update feed has no valid version")
    return latest_version


def _read_update_url(url):
    request = Request(
        url,
        headers={
            "Accept": "application/json, application/xml, text/xml, */*",
            "User-Agent": "MKV-Muxing-Batch-GUI-update-check",
        },
    )
    with urlopen(request, timeout=UPDATE_TIMEOUT_SECONDS) as response:
        payload = response.read(MAX_UPDATE_RESPONSE_SIZE + 1)
    if len(payload) > MAX_UPDATE_RESPONSE_SIZE:
        raise ValueError("The update response is unexpectedly large")
    return payload


def _installed_mkvtoolnix_version(mkvmerge_version, mkvpropedit_version):
    versions = [extract_version(mkvmerge_version), extract_version(mkvpropedit_version)]
    if not all(versions):
        return "", ""
    oldest_version = min(versions, key=version_key)
    if versions[0] == versions[1]:
        display_version = versions[0]
    else:
        display_version = f"mkvmerge {versions[0]}; mkvpropedit {versions[1]}"
    return oldest_version, display_version


def fetch_update_report(app_version, mkvmerge_version, mkvpropedit_version):
    updates = []
    errors = []

    try:
        latest_app_version = parse_app_release(_read_update_url(APP_RELEASE_API_URL))
        if is_newer_version(latest_app_version, app_version):
            updates.append(AvailableUpdate(
                component="MKV Muxing Batch GUI",
                current_version=extract_version(app_version) or str(app_version),
                latest_version=latest_app_version,
                download_url=APP_RELEASES_URL,
            ))
    except Exception as error:
        logging.info("Application update check failed: %s", error)
        errors.append("MKV Muxing Batch GUI")

    try:
        latest_mkvtoolnix_version = parse_mkvtoolnix_release(
            _read_update_url(MKVTOOLNIX_RELEASE_API_URL)
        )
        installed_version, display_version = _installed_mkvtoolnix_version(
            mkvmerge_version,
            mkvpropedit_version,
        )
        # Missing tools have their own actionable startup prompt. Avoid showing
        # a second, less useful "outdated" notification for the same problem.
        if not installed_version:
            errors.append("MKVToolNix (not installed)")
        elif is_newer_version(latest_mkvtoolnix_version, installed_version):
            updates.append(AvailableUpdate(
                component="MKVToolNix",
                current_version=display_version,
                latest_version=latest_mkvtoolnix_version,
                download_url=MKVTOOLNIX_DOWNLOAD_URL,
            ))
    except Exception as error:
        logging.info("MKVToolNix update check failed: %s", error)
        errors.append("MKVToolNix")

    return UpdateReport(updates=tuple(updates), errors=tuple(errors))


class UpdateChecker(QObject):
    """Run network checks off the GUI thread and return one combined report."""

    finished = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._checking = False

    @property
    def checking(self):
        return self._checking

    def check(self, app_version, mkvmerge_version, mkvpropedit_version):
        if self._checking:
            return False
        self._checking = True
        thread = threading.Thread(
            target=self._run,
            args=(app_version, mkvmerge_version, mkvpropedit_version),
            name="update-checker",
            daemon=True,
        )
        thread.start()
        return True

    def _run(self, app_version, mkvmerge_version, mkvpropedit_version):
        report = fetch_update_report(app_version, mkvmerge_version, mkvpropedit_version)
        self._checking = False
        try:
            self.finished.emit(report)
        except RuntimeError:
            # The owning dialog/window may have closed while the request was in
            # flight. A completed background check must never delay shutdown.
            pass
