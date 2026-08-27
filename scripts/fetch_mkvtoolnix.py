#!/usr/bin/env python3
"""Download and stage a pinned, publisher-verified MKVToolNix release."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "packaging" / "dependencies.json"
DEPENDENCY_NAME = "mkvtoolnix_windows_x64"
OFFICIAL_HOST = "mkvtoolnix.download"
USER_AGENT = "mkv-muxing-batch-gui dependency fetcher"


class DependencyError(RuntimeError):
    """Raised when dependency provenance or content validation fails."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_official_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != OFFICIAL_HOST:
        raise DependencyError(
            f"Dependency URL must use https://{OFFICIAL_HOST}: {url}"
        )


def load_dependency(manifest_path: Path = MANIFEST_PATH) -> dict:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        dependency = manifest[DEPENDENCY_NAME]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise DependencyError(f"Invalid dependency manifest: {error}") from error

    required = {
        "version",
        "archive_url",
        "checksum_url",
        "sha256",
        "archive_root",
        "files",
    }
    missing = required.difference(dependency)
    if missing:
        raise DependencyError(
            "Dependency manifest is missing: " + ", ".join(sorted(missing))
        )

    _validate_official_url(dependency["archive_url"])
    _validate_official_url(dependency["checksum_url"])
    if not re.fullmatch(r"[0-9a-f]{64}", dependency["sha256"]):
        raise DependencyError("Pinned SHA-256 must be 64 lowercase hexadecimal digits")
    if not isinstance(dependency["files"], dict) or not dependency["files"]:
        raise DependencyError("Dependency file selection must be a non-empty object")
    return dependency


def parse_checksum_sidecar(text: str, expected_filename: str) -> str:
    for line in text.splitlines():
        match = re.fullmatch(r"\s*([0-9A-Fa-f]{64})\s+\*?(.+?)\s*", line)
        if not match:
            continue
        if PurePosixPath(match.group(2).replace("\\", "/")).name == expected_filename:
            return match.group(1).lower()
    raise DependencyError(
        f"Publisher checksum does not contain an entry for {expected_filename}"
    )


def _open_official_url(url: str):
    _validate_official_url(url)
    try:
        response = urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=60
        )
    except urllib.error.URLError as error:
        raise DependencyError(f"Could not download {url}: {error.reason}") from error
    final_url = response.geturl()
    try:
        _validate_official_url(final_url)
    except DependencyError:
        response.close()
        raise
    return response


def verify_publisher_checksum(dependency: dict) -> None:
    with _open_official_url(dependency["checksum_url"]) as response:
        sidecar = response.read(16 * 1024 + 1)
    if len(sidecar) > 16 * 1024:
        raise DependencyError("Publisher checksum response is unexpectedly large")
    try:
        checksum_text = sidecar.decode("utf-8")
    except UnicodeDecodeError as error:
        raise DependencyError("Publisher checksum is not UTF-8 text") from error

    filename = PurePosixPath(urlparse(dependency["archive_url"]).path).name
    publisher_hash = parse_checksum_sidecar(checksum_text, filename)
    if publisher_hash != dependency["sha256"]:
        raise DependencyError(
            "Publisher checksum does not match the repository-pinned SHA-256"
        )


def download_archive(dependency: dict, cache_directory: Path) -> Path:
    cache_directory.mkdir(parents=True, exist_ok=True)
    filename = PurePosixPath(urlparse(dependency["archive_url"]).path).name
    archive_path = cache_directory / filename
    expected_hash = dependency["sha256"]

    if archive_path.is_file() and sha256_file(archive_path) == expected_hash:
        return archive_path

    temporary_path = archive_path.with_name(archive_path.name + ".part")
    temporary_path.unlink(missing_ok=True)
    digest = hashlib.sha256()
    try:
        with _open_official_url(dependency["archive_url"]) as response:
            with temporary_path.open("wb") as destination:
                for chunk in iter(lambda: response.read(1024 * 1024), b""):
                    digest.update(chunk)
                    destination.write(chunk)
        if digest.hexdigest() != expected_hash:
            raise DependencyError("Downloaded archive does not match pinned SHA-256")
        os.replace(temporary_path, archive_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return archive_path


def _safe_output_path(staging_directory: Path, relative_name: str) -> Path:
    relative_path = PurePosixPath(relative_name)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise DependencyError(f"Unsafe output path in dependency manifest: {relative_name}")
    return staging_directory.joinpath(*relative_path.parts)


def stage_archive(archive_path: Path, destination: Path, dependency: dict) -> Path:
    actual_hash = sha256_file(archive_path)
    if actual_hash != dependency["sha256"]:
        raise DependencyError(
            f"Archive SHA-256 mismatch: expected {dependency['sha256']}, got {actual_hash}"
        )

    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent)
    )
    staging_directory = temporary_root / "payload"
    staging_directory.mkdir()
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for source_name, output_name in dependency["files"].items():
                member_name = f"{dependency['archive_root'].rstrip('/')}/{source_name}"
                try:
                    member = archive.getinfo(member_name)
                except KeyError as error:
                    raise DependencyError(
                        f"Required archive member is missing: {member_name}"
                    ) from error
                if member.is_dir():
                    raise DependencyError(f"Required archive member is a directory: {member_name}")
                output_path = _safe_output_path(staging_directory, output_name)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, output_path.open("wb") as output:
                    shutil.copyfileobj(source, output)

        for executable_name in ("mkvmerge.exe", "mkvpropedit.exe"):
            executable_path = staging_directory / executable_name
            with executable_path.open("rb") as executable:
                signature = executable.read(2)
            if signature != b"MZ":
                raise DependencyError(f"Extracted {executable_name} is not a PE executable")

        provenance = {
            "name": "MKVToolNix",
            "version": dependency["version"],
            "source": dependency["archive_url"],
            "publisher_checksum": dependency["checksum_url"],
            "sha256": dependency["sha256"],
            "selected_files": dependency["files"],
        }
        (staging_directory / "PROVENANCE.json").write_text(
            json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        if destination.exists():
            if not destination.is_dir():
                raise DependencyError(f"Destination exists and is not a directory: {destination}")
            shutil.rmtree(destination)
        os.replace(staging_directory, destination)
    except (OSError, zipfile.BadZipFile) as error:
        raise DependencyError(f"Could not stage MKVToolNix: {error}") from error
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)
    return destination


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument(
        "--cache-dir", type=Path, default=PROJECT_ROOT / ".dependency-cache"
    )
    parser.add_argument(
        "--archive",
        type=Path,
        help="Use an already downloaded archive (still requires the pinned SHA-256)",
    )
    return parser


def main() -> int:
    arguments = build_argument_parser().parse_args()
    dependency = load_dependency()
    if arguments.archive:
        archive_path = arguments.archive.resolve()
    else:
        verify_publisher_checksum(dependency)
        archive_path = download_archive(dependency, arguments.cache_dir.resolve())
    staged = stage_archive(archive_path, arguments.destination, dependency)
    print(
        f"Staged MKVToolNix {dependency['version']} in {staged} "
        f"(SHA-256 {dependency['sha256']})"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DependencyError as error:
        raise SystemExit(f"Dependency verification failed: {error}") from error
