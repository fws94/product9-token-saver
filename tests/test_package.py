"""Synthetic package artifact tests for the first release workflow."""
import json
import os
from pathlib import Path
import shutil
import subprocess
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
        self.assertEqual(first.version, "0.1.0-dev.13")
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
        self.assertIn("0.1.0-dev.13", run.stdout)

    def test_directory_output_uses_manifest_version_in_filename(self):
        result = self.package(Path(self.temp.name) / "artifacts")
        self.assertEqual(result.path.name, "token-saver-0.1.0-dev.13.zip")
        self.assertTrue(result.path.is_file())

    def test_sensitive_files_are_excluded_and_public_root_output_is_reproducible(self):
        from package_plugin import package_plugin
        copy = Path(self.temp.name) / "plugin-copy"
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("scratch", "reports", "__pycache__"))
        (copy / "scripts/credentials.json").write_text("secret", encoding="utf-8")
        (copy / "scripts/events.log").write_text("private log", encoding="utf-8")
        output = copy / "docs" / "pkg.zip"
        first = package_plugin(copy, output)
        first_bytes = first.path.read_bytes()
        second = package_plugin(copy, output)
        self.assertEqual(first_bytes, second.path.read_bytes())
        with zipfile.ZipFile(second.path) as archive:
            names = archive.namelist()
            self.assertFalse(any(name.endswith("credentials.json") or name.endswith("events.log") for name in names))
            self.assertNotIn("token-saver/docs/pkg.zip", names)

    def test_archive_markdown_links_resolve_after_relocation(self):
        from check_repository import check_links
        destination = Path(self.temp.name) / "relocated plugin"
        with zipfile.ZipFile(self.package().path) as archive:
            archive.extractall(destination)
        plugin_root = destination / "token-saver"
        errors = [error for document in plugin_root.rglob("*.md")
                  for error in check_links(document, plugin_root)]
        self.assertEqual(errors, [])

    def test_unlisted_local_files_do_not_enter_release_package(self):
        from package_plugin import package_plugin
        copy = Path(self.temp.name) / "plugin-with-local-files"
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("scratch", "reports", "__pycache__"))
        private_files = ("docs/session.jsonl", "docs/private.md", "scripts/.env",
                         "scripts/private.py", "skills/usage-report/private.md")
        for relative in private_files:
            (copy / relative).write_text("synthetic private data", encoding="utf-8")
        result = package_plugin(copy, Path(self.temp.name) / "local-files.zip")
        with zipfile.ZipFile(result.path) as archive:
            names = set(archive.namelist())
        self.assertTrue(all("token-saver/" + name not in names for name in private_files))

    def test_public_file_symlink_cannot_read_outside_plugin(self):
        from package_plugin import package_plugin
        copy = Path(self.temp.name) / "plugin-with-linked-license"
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("scratch", "reports", "__pycache__"))
        private = Path(self.temp.name) / "private-license.txt"
        private.write_text("synthetic outside secret", encoding="utf-8")
        license_path = copy / "LICENSE"
        license_path.unlink()
        try:
            os.symlink(private, license_path)
        except (OSError, NotImplementedError):
            self.skipTest("host cannot create symlinks")
        with self.assertRaises(ValueError):
            package_plugin(copy, Path(self.temp.name) / "linked-license.zip")

    @unittest.skipUnless(os.name == "nt", "junctions are Windows-only")
    def test_directory_junction_cannot_read_outside_plugin(self):
        from package_plugin import package_plugin
        copy = Path(self.temp.name) / "plugin-with-junction"
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("scratch", "reports", "__pycache__"))
        docs = copy / "docs"
        self.assertTrue(docs.resolve().is_relative_to(copy.resolve()))
        shutil.rmtree(docs)
        outside = Path(self.temp.name) / "outside-docs"
        shutil.copytree(ROOT / "docs", outside)
        created = subprocess.run(["cmd", "/d", "/c", "mklink", "/J", str(docs), str(outside)],
                                 capture_output=True, text=True, errors="replace", timeout=10)
        if created.returncode != 0:
            self.skipTest("host cannot create a directory junction")
        self.assertFalse(docs.is_symlink())
        self.assertEqual(docs.resolve(), outside.resolve())
        with self.assertRaises(ValueError):
            package_plugin(copy, Path(self.temp.name) / "junction.zip")

    def test_manifest_name_cannot_escape_archive_root(self):
        from package_plugin import package_plugin
        copy = Path(self.temp.name) / "plugin-with-unsafe-name"
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("scratch", "reports", "__pycache__"))
        manifest = copy / ".codex-plugin" / "plugin.json"
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["name"] = "../escape"
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(ValueError):
            package_plugin(copy, Path(self.temp.name) / "unsafe.zip")

    def test_manifest_version_cannot_escape_output_directory(self):
        from package_plugin import package_plugin
        copy = Path(self.temp.name) / "plugin-with-unsafe-version"
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("scratch", "reports", "__pycache__"))
        manifest = copy / ".codex-plugin" / "plugin.json"
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["version"] = "../escape"
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(ValueError):
            package_plugin(copy, Path(self.temp.name) / "artifacts" / "package.zip")
