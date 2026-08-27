import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.fetch_mkvtoolnix import (
    DependencyError,
    load_dependency,
    parse_checksum_sidecar,
    stage_archive,
)


class DependencyFetcherTests(unittest.TestCase):
    def test_checked_in_manifest_uses_pinned_official_source(self):
        dependency = load_dependency()
        self.assertEqual(dependency["version"], "101.0")
        self.assertTrue(
            dependency["archive_url"].startswith("https://mkvtoolnix.download/")
        )
        self.assertEqual(len(dependency["sha256"]), 64)

    def create_archive(self, root: Path) -> tuple[Path, dict]:
        archive_path = root / "mkvtoolnix.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("mkvtoolnix/mkvmerge.exe", b"MZmerge")
            archive.writestr("mkvtoolnix/mkvpropedit.exe", b"MZpropedit")
            archive.writestr("mkvtoolnix/doc/COPYING.txt", b"license")
            archive.writestr("mkvtoolnix/doc/README.txt", b"readme")
            archive.writestr("mkvtoolnix/ignored.exe", b"MZignored")
            archive.writestr("../escape.exe", b"MZescape")
        digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        dependency = {
            "version": "test",
            "archive_url": "https://mkvtoolnix.download/test.zip",
            "checksum_url": "https://mkvtoolnix.download/test.zip.sha256",
            "sha256": digest,
            "archive_root": "mkvtoolnix",
            "files": {
                "mkvmerge.exe": "mkvmerge.exe",
                "mkvpropedit.exe": "mkvpropedit.exe",
                "doc/COPYING.txt": "LICENSE.MKVToolNix.txt",
                "doc/README.txt": "README.MKVToolNix.txt",
            },
        }
        return archive_path, dependency

    def test_stage_archive_extracts_only_selected_verified_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path, dependency = self.create_archive(root)
            destination = root / "stage"

            stage_archive(archive_path, destination, dependency)

            self.assertEqual(
                sorted(path.name for path in destination.iterdir()),
                [
                    "LICENSE.MKVToolNix.txt",
                    "PROVENANCE.json",
                    "README.MKVToolNix.txt",
                    "mkvmerge.exe",
                    "mkvpropedit.exe",
                ],
            )
            self.assertFalse((root / "escape.exe").exists())
            provenance = json.loads((destination / "PROVENANCE.json").read_text())
            self.assertEqual(provenance["sha256"], dependency["sha256"])

    def test_stage_archive_rejects_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path, dependency = self.create_archive(root)
            dependency["sha256"] = "0" * 64
            with self.assertRaisesRegex(DependencyError, "SHA-256 mismatch"):
                stage_archive(archive_path, root / "stage", dependency)

    def test_checksum_parser_requires_expected_archive(self):
        digest = "a" * 64
        self.assertEqual(
            parse_checksum_sidecar(f"{digest}  expected.zip\n", "expected.zip"),
            digest,
        )
        with self.assertRaises(DependencyError):
            parse_checksum_sidecar(f"{digest}  another.zip\n", "expected.zip")


if __name__ == "__main__":
    unittest.main()
