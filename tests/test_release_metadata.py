import re
import unittest
from pathlib import Path

from packages.Startup.Version import Version


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ReleaseMetadataTests(unittest.TestCase):
    def test_release_version_is_consistent(self):
        self.assertRegex(Version, r"^\d+\.\d+\.\d+$")
        expected_fragments = {
            PROJECT_ROOT / "CHANGELOG.md": f"## [{Version}]",
            PROJECT_ROOT / "packaging/windows/Installer.iss": (
                f'#define MyAppVersion "{Version}"'
            ),
            PROJECT_ROOT / "packaging/windows/VersionFile.txt": (
                f"StringStruct(u'ProductVersion', u'{Version}')"
            ),
            PROJECT_ROOT / "packaging/windows/build_release.ps1": (
                f'[string]$Version = "{Version}"'
            ),
        }
        for path, expected in expected_fragments.items():
            with self.subTest(path=path):
                self.assertIn(expected, path.read_text(encoding="utf-8"))

    def test_workflow_uses_exact_official_action_revisions(self):
        workflow = (
            PROJECT_ROOT / ".github/workflows/build-and-release.yml"
        ).read_text(encoding="utf-8")
        action_references = re.findall(r"uses:\s+([^\s#]+)", workflow)
        self.assertGreaterEqual(len(action_references), 8)
        for reference in action_references:
            with self.subTest(reference=reference):
                owner_repository, revision = reference.rsplit("@", 1)
                self.assertTrue(owner_repository.startswith("actions/"))
                self.assertRegex(revision, r"^[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
