import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

from packages.Startup import DependencyInstaller, GlobalFiles


class PublisherMetadataTests(unittest.TestCase):
    def test_parses_appimage_zsync_integrity_metadata(self):
        filename = "MKVToolNix_GUI-101.0-x86_64.AppImage"
        payload = (
            "zsync: 0.6.2\n"
            f"Filename: {filename}\n"
            "Length: 62746600\n"
            f"URL: {filename}\n"
            "SHA-1: 884b7e5c66936c2dbb4019caffe9e821452ada18\n\n"
        ).encode("ascii") + b"binary block data"

        self.assertEqual(
            (62746600, "884b7e5c66936c2dbb4019caffe9e821452ada18"),
            DependencyInstaller.parse_zsync_metadata(payload, filename),
        )

    def test_rejects_appimage_metadata_for_another_file(self):
        payload = (
            "Filename: unexpected.AppImage\n"
            "Length: 100\n"
            "URL: unexpected.AppImage\n"
            "SHA-1: 884b7e5c66936c2dbb4019caffe9e821452ada18\n\n"
        ).encode("ascii")
        with self.assertRaises(DependencyInstaller.DependencyInstallError):
            DependencyInstaller.parse_zsync_metadata(
                payload, "MKVToolNix_GUI-101.0-x86_64.AppImage"
            )

    def test_linux_plan_uses_latest_official_appimage(self):
        filename = "MKVToolNix_GUI-101.0-x86_64.AppImage"
        metadata = (
            f"Filename: {filename}\nLength: 62746600\nURL: {filename}\n"
            "SHA-1: 884b7e5c66936c2dbb4019caffe9e821452ada18\n\n"
        ).encode("ascii")
        with patch.object(
            DependencyInstaller, "_read_official_url", return_value=metadata
        ):
            plan = DependencyInstaller.create_download_plan(
                version="101.0", system="linux", machine="x86_64"
            )

        self.assertEqual("appimage", plan.package_kind)
        self.assertEqual("101.0", plan.version)
        self.assertEqual(
            f"https://mkvtoolnix.download/appimage/{filename}", plan.source_url
        )

    def test_windows_plan_requires_publisher_sha256(self):
        filename = "mkvtoolnix-64-bit-101.0.zip"
        digest = "a" * 64
        with patch.object(
            DependencyInstaller,
            "_read_official_url",
            return_value=f"{digest}  {filename}\n".encode("ascii"),
        ):
            plan = DependencyInstaller.create_download_plan(
                version="101.0", system="win32", machine="amd64"
            )

        self.assertEqual("zip", plan.package_kind)
        self.assertEqual("sha256", plan.digest_name)
        self.assertEqual(digest, plan.digest)


class DependencyStagingTests(unittest.TestCase):
    @staticmethod
    def plan(package_kind):
        return DependencyInstaller.DownloadPlan(
            version="101.0",
            source_url="https://mkvtoolnix.download/test-package",
            metadata_url="https://mkvtoolnix.download/test-package.metadata",
            filename="MKVToolNix_GUI-101.0-x86_64.AppImage",
            digest_name="sha1",
            digest="a" * 40,
            expected_size=6,
            package_kind=package_kind,
        )

    def test_appimage_staging_creates_command_symlinks_and_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            downloaded = root / "download.part"
            downloaded.write_bytes(b"binary")
            destination = root / "tools"
            plan = self.plan("appimage")

            def extract_appimage(*_args, **kwargs):
                app_root = Path(kwargs["cwd"]) / "squashfs-root"
                (app_root / "usr/bin").mkdir(parents=True)
                (app_root / "usr/lib").mkdir(parents=True)
                (app_root / "usr/bin/mkvmerge").write_bytes(b"ELF merge")
                (app_root / "usr/bin/mkvpropedit").write_bytes(b"ELF propedit")
                return Mock(returncode=0, stderr="")

            with patch.object(
                DependencyInstaller.subprocess,
                "run",
                side_effect=extract_appimage,
            ), patch.object(
                DependencyInstaller,
                "_validate_installed_tools",
                return_value={"mkvmerge": "v101.0", "mkvpropedit": "v101.0"},
            ):
                mkvmerge, mkvpropedit = DependencyInstaller._install_appimage(
                    plan, downloaded, destination
                )

            self.assertTrue(mkvmerge.is_symlink())
            self.assertTrue(mkvpropedit.is_symlink())
            self.assertEqual(
                f"versions/101.0-{plan.digest[:12]}/usr/bin/mkvmerge",
                mkvmerge.readlink().as_posix(),
            )
            provenance = json.loads(
                (destination / "PROVENANCE.json").read_text(encoding="utf-8")
            )
            self.assertEqual("101.0", provenance["version"])
            self.assertEqual(plan.source_url, provenance["source"])

    def test_windows_staging_extracts_only_required_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            downloaded = root / "download.zip"
            with zipfile.ZipFile(downloaded, "w") as archive:
                archive.writestr("mkvtoolnix/mkvmerge.exe", b"MZmerge")
                archive.writestr("mkvtoolnix/mkvpropedit.exe", b"MZpropedit")
                archive.writestr("mkvtoolnix/doc/COPYING.txt", b"license")
                archive.writestr("mkvtoolnix/doc/README.txt", b"readme")
                archive.writestr("mkvtoolnix/other.exe", b"MZignored")
            plan = self.plan("zip")
            destination = root / "tools"

            with patch.object(
                DependencyInstaller,
                "_validate_installed_tools",
                return_value={"mkvmerge": "v101.0", "mkvpropedit": "v101.0"},
            ):
                DependencyInstaller._install_windows_zip(plan, downloaded, destination)

            self.assertEqual(
                {
                    "LICENSE.MKVToolNix.txt",
                    "PROVENANCE.json",
                    "README.MKVToolNix.txt",
                    "mkvmerge.exe",
                    "mkvpropedit.exe",
                },
                {path.name for path in destination.iterdir()},
            )

    def test_managed_tools_are_checked_before_system_and_bundled_tools(self):
        with patch.object(
            GlobalFiles, "get_custom_program_path", return_value=None
        ), patch.object(GlobalFiles, "which", return_value="/usr/bin/mkvmerge"):
            candidates = GlobalFiles.get_program_candidates("mkvmerge")
        executable_name = "mkvmerge.exe" if sys.platform == "win32" else "mkvmerge"
        self.assertEqual(
            Path(GlobalFiles.ManagedToolsFolderPath) / executable_name,
            candidates[0],
        )

    def test_download_requires_the_publisher_digest_and_exact_size(self):
        payload = b"verified dependency"
        digest = hashlib.sha1(payload).hexdigest()
        plan = DependencyInstaller.DownloadPlan(
            version="101.0",
            source_url="https://mkvtoolnix.download/test.AppImage",
            metadata_url="https://mkvtoolnix.download/test.AppImage.zsync",
            filename="test.AppImage",
            digest_name="sha1",
            digest=digest,
            expected_size=len(payload),
            package_kind="appimage",
        )

        class Response:
            headers = {"Content-Length": str(len(payload))}

            def __enter__(self):
                self.remaining = payload
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _size):
                current, self.remaining = self.remaining, b""
                return current

        with tempfile.TemporaryDirectory() as directory, patch.object(
            DependencyInstaller, "_open_official_url", return_value=Response()
        ):
            downloaded = DependencyInstaller._download(plan, Path(directory))
            self.assertEqual(payload, downloaded.read_bytes())

        invalid_plan = DependencyInstaller.DownloadPlan(
            **{**plan.__dict__, "digest": "0" * 40}
        )
        with tempfile.TemporaryDirectory() as directory, patch.object(
            DependencyInstaller, "_open_official_url", return_value=Response()
        ):
            with self.assertRaisesRegex(
                DependencyInstaller.DependencyInstallError, "verification"
            ):
                DependencyInstaller._download(invalid_plan, Path(directory))
            self.assertEqual([], list(Path(directory).iterdir()))


if __name__ == "__main__":
    unittest.main()
