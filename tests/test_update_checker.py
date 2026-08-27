import gzip
import json
import threading
import unittest
from unittest.mock import patch

from PySide6.QtCore import QEventLoop, QTimer

from packages.Startup import UpdateChecker


def app_release(version, *, draft=False, prerelease=False):
    return json.dumps({
        "tag_name": version,
        "draft": draft,
        "prerelease": prerelease,
    }).encode("utf-8")


def mkvtoolnix_release(version, *, compressed=True):
    payload = (
        "<?xml version='1.0' encoding='utf-8'?>"
        "<mkvtoolnix-releases><latest-source>"
        f"<version>{version}</version>"
        "</latest-source></mkvtoolnix-releases>"
    ).encode("utf-8")
    return gzip.compress(payload) if compressed else payload


class VersionComparisonTests(unittest.TestCase):
    def test_extracts_app_tags_and_tool_output(self):
        self.assertEqual("2.7.3", UpdateChecker.extract_version("v2.7.3"))
        self.assertEqual(
            "101.0",
            UpdateChecker.extract_version("mkvmerge v101.0 ('Time To Turn') 64-bit"),
        )

    def test_compares_numeric_components_instead_of_strings(self):
        self.assertTrue(UpdateChecker.is_newer_version("101.0", "99.0"))
        self.assertTrue(UpdateChecker.is_newer_version("2.10.0", "2.9.9"))
        self.assertFalse(UpdateChecker.is_newer_version("2.7.2", "2.7.2"))
        self.assertFalse(UpdateChecker.is_newer_version("unknown", "2.7.2"))


class UpdateFeedParsingTests(unittest.TestCase):
    def test_parses_stable_github_release(self):
        self.assertEqual(
            "2.8.0",
            UpdateChecker.parse_app_release(app_release("v2.8.0")),
        )

    def test_rejects_prerelease_or_invalid_github_payload(self):
        with self.assertRaises(ValueError):
            UpdateChecker.parse_app_release(app_release("3.0.0-beta", prerelease=True))
        with self.assertRaises(ValueError):
            UpdateChecker.parse_app_release(app_release("not-a-version"))

    def test_parses_compressed_and_plain_mkvtoolnix_feeds(self):
        self.assertEqual(
            "101.0",
            UpdateChecker.parse_mkvtoolnix_release(mkvtoolnix_release("101.0")),
        )
        self.assertEqual(
            "101.0",
            UpdateChecker.parse_mkvtoolnix_release(
                mkvtoolnix_release("101.0", compressed=False)
            ),
        )


class UpdateReportTests(unittest.TestCase):
    @staticmethod
    def fake_response(url):
        if url == UpdateChecker.APP_RELEASE_API_URL:
            return app_release("2.8.0")
        if url == UpdateChecker.MKVTOOLNIX_RELEASE_API_URL:
            return mkvtoolnix_release("101.0")
        raise AssertionError(f"Unexpected URL: {url}")

    def test_reports_application_and_oldest_tool_update(self):
        with patch.object(
            UpdateChecker,
            "_read_update_url",
            side_effect=self.fake_response,
        ):
            report = UpdateChecker.fetch_update_report(
                "2.7.2",
                "mkvmerge v100.0 ('Do Hot Girls Like Chords') 64-bit",
                "mkvpropedit v99.0 ('Buka') 64-bit",
            )

        self.assertEqual(
            ["MKV Muxing Batch GUI", "MKVToolNix"],
            [update.component for update in report.updates],
        )
        self.assertEqual(
            "mkvmerge 100.0; mkvpropedit 99.0",
            report.updates[1].current_version,
        )
        self.assertEqual((), report.errors)

    def test_current_versions_produce_no_notification(self):
        with patch.object(
            UpdateChecker,
            "_read_update_url",
            side_effect=self.fake_response,
        ):
            report = UpdateChecker.fetch_update_report(
                "2.8.0",
                "mkvmerge v101.0 ('Time To Turn') 64-bit",
                "mkvpropedit v101.0 ('Time To Turn') 64-bit",
            )

        self.assertEqual((), report.updates)
        self.assertEqual((), report.errors)

    def test_missing_tools_use_the_dependency_prompt_not_an_update(self):
        with patch.object(
            UpdateChecker,
            "_read_update_url",
            side_effect=self.fake_response,
        ):
            report = UpdateChecker.fetch_update_report(
                "2.8.0",
                "mkvmerge: not found!",
                "mkvpropedit: not found!",
            )

        self.assertEqual((), report.updates)
        self.assertEqual(("MKVToolNix (not installed)",), report.errors)

    def test_network_failures_are_reported_without_raising(self):
        with patch.object(
            UpdateChecker,
            "_read_update_url",
            side_effect=OSError("offline"),
        ):
            report = UpdateChecker.fetch_update_report(
                "2.7.2",
                "mkvmerge v100.0 ('Example') 64-bit",
                "mkvpropedit v100.0 ('Example') 64-bit",
            )

        self.assertEqual((), report.updates)
        self.assertEqual(("MKV Muxing Batch GUI", "MKVToolNix"), report.errors)


class BackgroundUpdateCheckerTests(unittest.TestCase):
    def test_check_returns_report_without_blocking_the_gui_thread(self):
        expected_report = UpdateChecker.UpdateReport()
        reports = []
        worker_started = threading.Event()
        release_worker = threading.Event()
        event_loop = QEventLoop()
        checker = UpdateChecker.UpdateChecker()
        checker.finished.connect(lambda report: (reports.append(report), event_loop.quit()))

        def delayed_report(*_args):
            worker_started.set()
            release_worker.wait(timeout=2)
            return expected_report

        with patch.object(
            UpdateChecker,
            "fetch_update_report",
            side_effect=delayed_report,
        ):
            self.assertTrue(checker.check("2.7.2", "mkvmerge v101.0", "mkvpropedit v101.0"))
            self.assertTrue(worker_started.wait(timeout=1))
            self.assertFalse(checker.check("2.7.2", "mkvmerge v101.0", "mkvpropedit v101.0"))
            release_worker.set()
            QTimer.singleShot(2000, event_loop.quit)
            event_loop.exec()

        self.assertEqual([expected_report], reports)
        self.assertFalse(checker.checking)


if __name__ == "__main__":
    unittest.main()
