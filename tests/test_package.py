"""Synthetic package artifact tests for the first release workflow."""
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="package 包 ")
        self.addCleanup(self.temp.cleanup)
        self.plugin = ROOT

    def package(self, output=None):
        self.assertIsNotNone(__import__("importlib").util.find_spec("package_plugin"),
                             "package helper must exist")
        from package_plugin import package_plugin
        output = output or Path(self.temp.name) / "out" / "token-saver.zip"
        return package_plugin(self.plugin, output)

    def test_artifact_is_versioned_deterministic_and_contains_public_plugin_files(self):
        first = self.package(Path(self.temp.name) / "one.zip")
        second = self.package(Path(self.temp.name) / "two.zip")
        self.assertEqual(first.version, "0.1.0-dev.9")
        self.assertEqual(first.path.read_bytes(), second.path.read_bytes())
        with zipfile.ZipFile(first.path) as archive:
            names = archive.namelist()
            self.assertEqual(names, sorted(names))
            self.assertIn("token-saver/.codex-plugin/plugin.json", names)
            self.assertIn("token-saver/scripts/token_saver.py", names)
            self.assertIn("token-saver/skills/usage-report/SKILL.md", names)
            self.assertIn("token-saver/skills/issue-admin/SKILL.md", names)
            self.assertIn("token-saver/references/worker-handoff.md", names)
            self.assertIn("token-saver/docs/usage-report.md", names)
            self.assertTrue(all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist()))
            self.assertTrue(all("scratch/" not in name and "tests/" not in name for name in names))
            self.assertFalse(any(name.endswith(".log") or "credentials" in name for name in names))

    def test_package_rejects_missing_manifest_and_writes_parent_directories(self):
        from package_plugin import package_plugin
        missing = Path(self.temp.name) / "missing"
        missing.mkdir()
        with self.assertRaises(ValueError):
            package_plugin(missing, Path(self.temp.name) / "missing.zip")

    def test_cli_package_help_and_output_work_from_relocated_directory(self):
        import subprocess
        output = Path(self.temp.name) / "nested" / "token-saver.zip"
        run = subprocess.run([sys.executable, str(ROOT / "scripts/token_saver.py"),
                              "package", "--plugin-root", str(ROOT), "--output", str(output)],
                             cwd=self.temp.name, capture_output=True, text=True,
                             encoding="utf-8", timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(output.exists(), True)
        self.assertIn("0.1.0-dev.9", run.stdout)

