"""Exercise the CLI as an external process, without credentials."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def run_cli(self, *args, script=None):
        script = script or ROOT / "scripts" / "token_saver.py"
        self.assertTrue(script.is_file(), "CLI entry point must exist")
        env = {key: value for key, value in os.environ.items()
               if key not in {"OPENAI_API_KEY", "GH_TOKEN", "GITHUB_TOKEN", "PYTHONPATH"}}
        env["PYTHONUTF8"] = "1"
        return subprocess.run([sys.executable, str(script), *args],
                              cwd=tempfile.gettempdir(), env=env,
                              capture_output=True, text=True, encoding="utf-8", timeout=10)

    def test_help_is_offline_and_successful(self):
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("contract", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_missing_or_unknown_command_is_usage_error(self):
        for args in ((), ("missing",), ("contract", "--invalid")):
            result = self.run_cli(*args)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertIn("error:", result.stderr)

    def test_contract_is_a_versioned_json_envelope(self):
        result = self.run_cli("contract")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["operation"], "contract")
        self.assertEqual(payload["data"]["statuses"],
                         ["completed", "failed", "partial", "blocked", "uncertain"])
        self.assertIsNone(payload["exit_code"])

    def test_cli_survives_relocation_with_spaces_and_unicode(self):
        with tempfile.TemporaryDirectory(prefix="token saver 测试 ") as temp:
            destination = Path(temp) / "scripts"
            shutil.copytree(ROOT / "scripts", destination, ignore=shutil.ignore_patterns("__pycache__"))
            result = self.run_cli("contract", script=destination / "token_saver.py")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["schema_version"], 1)
