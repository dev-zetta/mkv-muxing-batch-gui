import hashlib
import json
import logging
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from PySide6.QtCore import QObject, Signal

from packages.Startup import GlobalFiles
from packages.Startup.UpdateChecker import (
    MKVTOOLNIX_RELEASE_API_URL,
    extract_version,
    parse_mkvtoolnix_release,
)


OFFICIAL_HOST = "mkvtoolnix.download"
DOWNLOAD_TIMEOUT_SECONDS = 30
MAX_METADATA_SIZE = 2 * 1024 * 1024
MAX_DOWNLOAD_SIZE = 300 * 1024 * 1024
DOWNLOAD_CHUNK_SIZE = 256 * 1024
USER_AGENT = "MKV-Muxing-Batch-GUI-dependency-installer"


class DependencyInstallError(RuntimeError):
    """Raised when MKVToolNix cannot be downloaded, verified, or installed."""


@dataclass(frozen=True)
class DownloadPlan:
    version: str
    source_url: str
    metadata_url: str
    filename: str
    digest_name: str
    digest: str
    expected_size: int | None
    package_kind: str


@dataclass(frozen=True)
class DependencyInstallResult:
    version: str
    destination: Path
    mkvmerge_path: Path
    mkvpropedit_path: Path
    mkvmerge_version: str
    mkvpropedit_version: str
    source_url: str
    digest_name: str
    digest: str


def _validate_official_url(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() != OFFICIAL_HOST:
        raise DependencyInstallError(f"Refusing non-publisher URL: {url}")


def _open_official_url(url):
    _validate_official_url(url)
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        response = urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS)
    except Exception as error:
        raise DependencyInstallError(f"Could not download {url}: {error}") from error
    try:
        _validate_official_url(response.geturl())
    except Exception:
        response.close()
        raise
    return response


def _read_official_url(url, maximum_size=MAX_METADATA_SIZE):
    with _open_official_url(url) as response:
        declared_size = response.headers.get("Content-Length")
        if declared_size and int(declared_size) > maximum_size:
            raise DependencyInstallError(f"Publisher metadata is too large: {url}")
        payload = response.read(maximum_size + 1)
    if len(payload) > maximum_size:
        raise DependencyInstallError(f"Publisher metadata is too large: {url}")
    return payload


def fetch_latest_mkvtoolnix_version():
    version = parse_mkvtoolnix_release(
        _read_official_url(MKVTOOLNIX_RELEASE_API_URL)
    )
    if not re.fullmatch(r"\d+(?:\.\d+){1,3}", version):
        raise DependencyInstallError("The publisher returned an invalid version")
    return version


def parse_zsync_metadata(payload, expected_filename):
    """Read the publisher-served AppImage length and SHA-1 zsync metadata."""
    header = payload.replace(b"\r\n", b"\n").split(b"\n\n", 1)[0]
    try:
        lines = header.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise DependencyInstallError("Invalid AppImage verification metadata") from error
    fields = {}
    for line in lines:
        key, separator, value = line.partition(":")
        if separator:
            fields[key.strip().lower()] = value.strip()

    if fields.get("filename") != expected_filename:
        raise DependencyInstallError("AppImage metadata names an unexpected file")
    if PurePosixPath(fields.get("url", "")).name != expected_filename:
        raise DependencyInstallError("AppImage metadata contains an unexpected URL")
    digest = fields.get("sha-1", "").lower()
    if not re.fullmatch(r"[0-9a-f]{40}", digest):
        raise DependencyInstallError("AppImage metadata has no valid SHA-1")
    try:
        expected_size = int(fields["length"])
    except (KeyError, ValueError) as error:
        raise DependencyInstallError("AppImage metadata has no valid length") from error
    if expected_size <= 0 or expected_size > MAX_DOWNLOAD_SIZE:
        raise DependencyInstallError("AppImage metadata contains an unsafe length")
    return expected_size, digest


def parse_sha256_sidecar(payload, expected_filename):
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise DependencyInstallError("Invalid publisher checksum file") from error
    for line in text.splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?(.+)", line.strip())
        if match and PurePosixPath(match.group(2)).name == expected_filename:
            return match.group(1).lower()
    raise DependencyInstallError(
        f"Publisher checksum does not contain {expected_filename}"
    )


def create_download_plan(version=None, system=None, machine=None):
    version = version or fetch_latest_mkvtoolnix_version()
    if not re.fullmatch(r"\d+(?:\.\d+){1,3}", version):
        raise DependencyInstallError("The publisher returned an invalid version")
    system = system or sys.platform
    machine = (machine or platform.machine()).lower()
    if machine not in {"amd64", "x86_64"}:
        raise DependencyInstallError(
            f"Automatic MKVToolNix installation is not available for {machine or 'this architecture'}"
        )

    if system.startswith("linux"):
        filename = f"MKVToolNix_GUI-{version}-x86_64.AppImage"
        source_url = f"https://{OFFICIAL_HOST}/appimage/{filename}"
        metadata_url = source_url + ".zsync"
        expected_size, digest = parse_zsync_metadata(
            _read_official_url(metadata_url),
            filename,
        )
        return DownloadPlan(
            version=version,
            source_url=source_url,
            metadata_url=metadata_url,
            filename=filename,
            digest_name="sha1",
            digest=digest,
            expected_size=expected_size,
            package_kind="appimage",
        )

    if system == "win32":
        filename = f"mkvtoolnix-64-bit-{version}.zip"
        source_url = (
            f"https://{OFFICIAL_HOST}/windows/releases/{version}/{filename}"
        )
        metadata_url = source_url + ".sha256"
        digest = parse_sha256_sidecar(
            _read_official_url(metadata_url),
            filename,
        )
        return DownloadPlan(
            version=version,
            source_url=source_url,
            metadata_url=metadata_url,
            filename=filename,
            digest_name="sha256",
            digest=digest,
            expected_size=None,
            package_kind="zip",
        )

    raise DependencyInstallError(
        f"Automatic MKVToolNix installation is not available on {system}"
    )


def _download(plan, parent_directory, progress=None):
    parent_directory.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=".mkvtoolnix-download-",
        suffix=".part",
        dir=parent_directory,
    )
    os.close(handle)
    temporary_path = Path(temporary_name)
    digest = hashlib.new(plan.digest_name)
    downloaded = 0
    try:
        with _open_official_url(plan.source_url) as response, temporary_path.open("wb") as output:
            declared_size = response.headers.get("Content-Length")
            total_size = int(declared_size) if declared_size else plan.expected_size
            if total_size and total_size > MAX_DOWNLOAD_SIZE:
                raise DependencyInstallError("The dependency download is unexpectedly large")
            if plan.expected_size and total_size and total_size != plan.expected_size:
                raise DependencyInstallError("The dependency size does not match publisher metadata")

            while True:
                chunk = response.read(DOWNLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                downloaded += len(chunk)
                if downloaded > MAX_DOWNLOAD_SIZE:
                    raise DependencyInstallError("The dependency download exceeded its size limit")
                output.write(chunk)
                digest.update(chunk)
                if progress:
                    percent = int(downloaded * 100 / total_size) if total_size else -1
                    progress(percent, f"Downloading MKVToolNix {plan.version}")

        if total_size is not None and downloaded != total_size:
            raise DependencyInstallError(
                f"Downloaded {downloaded} bytes; publisher metadata requires {total_size}"
            )
        actual_digest = digest.hexdigest().lower()
        if actual_digest != plan.digest:
            raise DependencyInstallError(
                f"Downloaded MKVToolNix failed {plan.digest_name.upper()} verification"
            )
        return temporary_path
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def _write_provenance(destination, plan, selected_files):
    provenance = {
        "name": "MKVToolNix",
        "version": plan.version,
        "source": plan.source_url,
        "publisher_metadata": plan.metadata_url,
        plan.digest_name: plan.digest,
        "selected_files": selected_files,
    }
    temporary_path = destination / ".PROVENANCE.json.new"
    temporary_path.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary_path, destination / "PROVENANCE.json")


def _replace_symlink(link_path, target_name):
    temporary_link = link_path.with_name(f".{link_path.name}.new")
    temporary_link.unlink(missing_ok=True)
    temporary_link.symlink_to(target_name)
    os.replace(temporary_link, link_path)


def _install_appimage(plan, downloaded_path, destination):
    os.chmod(downloaded_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    destination.mkdir(parents=True, exist_ok=True)
    versions_directory = destination / "versions"
    versions_directory.mkdir(parents=True, exist_ok=True)
    version_directory = versions_directory / f"{plan.version}-{plan.digest[:12]}"

    with tempfile.TemporaryDirectory(
        prefix=".mkvtoolnix-appimage-", dir=destination.parent
    ) as stage_name:
        stage = Path(stage_name)
        try:
            extraction = subprocess.run(
                [str(downloaded_path), "--appimage-extract"],
                cwd=stage,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=120,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise DependencyInstallError(f"Could not extract the AppImage: {error}") from error
        if extraction.returncode != 0:
            details = extraction.stderr.strip() or "unknown AppImage extraction error"
            raise DependencyInstallError(f"Could not extract the AppImage: {details}")
        extracted_root = stage / "squashfs-root"
        required_paths = (
            extracted_root / "usr/bin/mkvmerge",
            extracted_root / "usr/bin/mkvpropedit",
            extracted_root / "usr/lib",
        )
        if not all(path.exists() for path in required_paths):
            raise DependencyInstallError("The AppImage does not contain the required tools")
        reuse_existing = False
        if version_directory.exists():
            try:
                _validate_installed_tools(
                    plan,
                    version_directory / "usr/bin/mkvmerge",
                    version_directory / "usr/bin/mkvpropedit",
                )
                reuse_existing = True
            except DependencyInstallError:
                suffix = 1
                while version_directory.with_name(
                    f"{version_directory.name}-{suffix}"
                ).exists():
                    suffix += 1
                version_directory = version_directory.with_name(
                    f"{version_directory.name}-{suffix}"
                )
        if not reuse_existing:
            shutil.move(str(extracted_root), version_directory)

    actual_mkvmerge = version_directory / "usr/bin/mkvmerge"
    actual_mkvpropedit = version_directory / "usr/bin/mkvpropedit"
    # Validate the new version before switching the stable command symlinks.
    _validate_installed_tools(plan, actual_mkvmerge, actual_mkvpropedit)

    mkvmerge_path = destination / "mkvmerge"
    mkvpropedit_path = destination / "mkvpropedit"
    relative_version_directory = version_directory.relative_to(destination)
    _replace_symlink(
        mkvmerge_path,
        relative_version_directory / "usr/bin/mkvmerge",
    )
    _replace_symlink(
        mkvpropedit_path,
        relative_version_directory / "usr/bin/mkvpropedit",
    )
    _write_provenance(
        destination,
        plan,
        {
            "mkvmerge": str(relative_version_directory / "usr/bin/mkvmerge"),
            "mkvpropedit": str(relative_version_directory / "usr/bin/mkvpropedit"),
        },
    )
    return mkvmerge_path, mkvpropedit_path


def _find_zip_member(archive, relative_name):
    matches = [
        member
        for member in archive.namelist()
        if not member.endswith("/")
        and PurePosixPath(member).parts
        and PurePosixPath(member).parts[-len(PurePosixPath(relative_name).parts):]
        == PurePosixPath(relative_name).parts
    ]
    if len(matches) != 1:
        raise DependencyInstallError(f"Archive does not contain exactly one {relative_name}")
    member_path = PurePosixPath(matches[0])
    if member_path.is_absolute() or ".." in member_path.parts:
        raise DependencyInstallError("Dependency archive contains an unsafe path")
    return matches[0]


def _install_windows_zip(plan, downloaded_path, destination):
    selected_files = {
        "mkvmerge.exe": "mkvmerge.exe",
        "mkvpropedit.exe": "mkvpropedit.exe",
        "doc/COPYING.txt": "LICENSE.MKVToolNix.txt",
        "doc/README.txt": "README.MKVToolNix.txt",
    }
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".mkvtoolnix-stage-", dir=destination) as stage_name:
        stage = Path(stage_name)
        try:
            archive = zipfile.ZipFile(downloaded_path)
        except (OSError, zipfile.BadZipFile) as error:
            raise DependencyInstallError("Downloaded MKVToolNix archive is invalid") from error
        with archive:
            for source_name, output_name in selected_files.items():
                member = _find_zip_member(archive, source_name)
                with archive.open(member) as source, (stage / output_name).open("wb") as output:
                    shutil.copyfileobj(source, output)
        for executable_name in ("mkvmerge.exe", "mkvpropedit.exe"):
            with (stage / executable_name).open("rb") as executable:
                header = executable.read(2)
            if header != b"MZ":
                raise DependencyInstallError(f"{executable_name} is not a Windows executable")
        # Run the staged tools before replacing a previously working install.
        _validate_installed_tools(
            plan,
            stage / "mkvmerge.exe",
            stage / "mkvpropedit.exe",
        )
        for output_name in selected_files.values():
            os.replace(stage / output_name, destination / output_name)

    downloaded_path.unlink(missing_ok=True)
    _write_provenance(destination, plan, selected_files)
    return destination / "mkvmerge.exe", destination / "mkvpropedit.exe"


def _validate_installed_tools(plan, mkvmerge_path, mkvpropedit_path):
    versions = {}
    for program_name, program_path in (
        ("mkvmerge", mkvmerge_path),
        ("mkvpropedit", mkvpropedit_path),
    ):
        environment = GlobalFiles.get_tool_environment(program_path)
        version_output = GlobalFiles.get_program_version(
            program_path,
            program_name,
            environment=environment,
        )
        if extract_version(version_output) != plan.version:
            raise DependencyInstallError(
                f"Downloaded {program_name} did not report MKVToolNix {plan.version}"
            )
        versions[program_name] = version_output
    return versions


def install_latest_mkvtoolnix(destination=None, progress=None):
    destination = Path(destination or GlobalFiles.ManagedToolsFolderPath)
    if progress:
        progress(-1, "Finding the latest MKVToolNix release")
    plan = create_download_plan()
    if progress:
        progress(0, f"Downloading MKVToolNix {plan.version}")
    downloaded_path = _download(plan, destination.parent, progress=progress)
    try:
        if plan.package_kind == "appimage":
            mkvmerge_path, mkvpropedit_path = _install_appimage(
                plan, downloaded_path, destination
            )
        elif plan.package_kind == "zip":
            mkvmerge_path, mkvpropedit_path = _install_windows_zip(
                plan, downloaded_path, destination
            )
        else:
            raise DependencyInstallError(f"Unsupported package type: {plan.package_kind}")
        if progress:
            progress(-1, "Validating downloaded tools")
        versions = _validate_installed_tools(plan, mkvmerge_path, mkvpropedit_path)
    finally:
        downloaded_path.unlink(missing_ok=True)

    return DependencyInstallResult(
        version=plan.version,
        destination=destination,
        mkvmerge_path=mkvmerge_path,
        mkvpropedit_path=mkvpropedit_path,
        mkvmerge_version=versions["mkvmerge"],
        mkvpropedit_version=versions["mkvpropedit"],
        source_url=plan.source_url,
        digest_name=plan.digest_name,
        digest=plan.digest,
    )


class DependencyInstaller(QObject):
    """Download and validate MKVToolNix without blocking the GUI thread."""

    progress = Signal(int, str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._installing = False

    @property
    def installing(self):
        return self._installing

    def install(self):
        if self._installing:
            return False
        self._installing = True
        thread = threading.Thread(
            target=self._run,
            name="mkvtoolnix-installer",
            daemon=True,
        )
        thread.start()
        return True

    def _run(self):
        try:
            result = install_latest_mkvtoolnix(
                progress=lambda percent, message: self.progress.emit(percent, message)
            )
        except Exception as error:
            logging.exception("MKVToolNix installation failed")
            self._installing = False
            try:
                self.failed.emit(str(error))
            except RuntimeError:
                pass
            return
        self._installing = False
        try:
            self.finished.emit(result)
        except RuntimeError:
            pass
