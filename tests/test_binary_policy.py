import subprocess
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class BinaryPolicyTests(unittest.TestCase):
    def test_repository_contains_no_executable_or_archive_payloads(self):
        forbidden_suffixes = {
            ".7z",
            ".a",
            ".appimage",
            ".class",
            ".com",
            ".dll",
            ".dylib",
            ".exe",
            ".jar",
            ".lib",
            ".msi",
            ".o",
            ".obj",
            ".pyd",
            ".rar",
            ".so",
            ".tlb",
            ".wasm",
            ".zip",
        }
        forbidden_magic = (b"MZ", b"\x7fELF", b"Rar!")
        violations = []
        try:
            tracked_output = subprocess.check_output(
                ["git", "ls-files", "-z"], cwd=PROJECT_ROOT
            )
            candidates = [
                PROJECT_ROOT / path.decode("utf-8")
                for path in tracked_output.split(b"\0")
                if path
            ]
        except (OSError, subprocess.CalledProcessError):
            excluded_directories = {
                ".dependency-cache",
                ".git",
                ".venv",
                "__pycache__",
                "build",
                "dist",
                "release",
                "venv",
            }
            candidates = [
                path
                for path in PROJECT_ROOT.rglob("*")
                if path.is_file()
                and not excluded_directories.intersection(
                    path.relative_to(PROJECT_ROOT).parts
                )
            ]

        for path in candidates:
            if not path.is_file():
                continue
            relative = path.relative_to(PROJECT_ROOT)
            lower_name = path.name.lower()
            if any(lower_name.endswith(suffix) for suffix in forbidden_suffixes):
                violations.append(str(relative))
                continue
            with path.open("rb") as source:
                header = source.read(4)
            if any(header.startswith(magic) for magic in forbidden_magic):
                violations.append(str(relative))

        self.assertEqual(sorted(violations), [])

    def test_tools_directory_contains_documentation_only(self):
        tools_root = PROJECT_ROOT / "Resources" / "Tools"
        files = sorted(
            str(path.relative_to(tools_root))
            for path in tools_root.rglob("*")
            if path.is_file()
        )
        self.assertEqual(files, ["README.md"])


if __name__ == "__main__":
    unittest.main()
