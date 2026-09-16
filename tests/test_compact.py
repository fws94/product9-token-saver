"""Synthetic cases that protect evidence while reducing captured output."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class CompactTests(unittest.TestCase):
    def compact(self, content, **kwargs):
        self.assertIsNotNone(importlib.util.find_spec("token_saver_lib.compact"),
                             "compact helper must exist")
        from token_saver_lib.compact import compact_file
        with tempfile.TemporaryDirectory(prefix="compact 测试 ") as directory:
            source = Path(directory) / "captured output.txt"
            original = content.encode("utf-8") if isinstance(content, str) else content
            source.write_bytes(original)
            result = compact_file(source, **kwargs).to_dict()
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(result["evidence"], [str(source.resolve())])
            return result

    def test_noisy_success_is_smaller_and_counted(self):
        result = self.compact("PASS item\n" * 100, format="test", max_lines=5)
        data = result["data"]
        self.assertEqual(result["status"], "completed")
        self.assertIn("100", data["text"])
        self.assertEqual(data["before"], {"bytes": 1000, "lines": 100})
        self.assertLess(data["after"]["bytes"], 1000)
        self.assertLessEqual(data["after"]["lines"], 5)
        self.assertEqual(data["after"]["bytes"], len(data["text"].encode("utf-8")))
        self.assertIsNone(result["exit_code"])

    def test_failure_between_distinct_success_runs_survives(self):
        text = "".join(f"PASS case_{i}\n" for i in range(100))
        text += "FAILED payment: expected 4 got 5\nexit code: 1\n"
        text += "".join(f"PASS case_{i}\n" for i in range(100, 200))
        data = self.compact(text, format="test", max_lines=5)["data"]
        self.assertIn("FAILED payment: expected 4 got 5", data["text"])
        self.assertIn("exit code: 1", data["text"])
        self.assertLessEqual(data["after"]["lines"], 5)

    def test_repeated_errors_keep_occurrence_count(self):
        data = self.compact("ERROR missing fixture\n" * 7, max_lines=5)["data"]
        self.assertIn("ERROR missing fixture", data["text"])
        self.assertIn("7", data["text"])

    def test_diagnostic_blocks_outlive_tiny_budget(self):
        text = "PASS before\nTraceback (most recent call last):\n  File synthetic.py, line 8\n    fail()\nValueError: first failure\n\nWARNING second issue\n  recoverable detail\nPASS after\n"
        result = self.compact(text, format="test", max_lines=2)
        for fragment in ("Traceback", "File synthetic.py", "fail()", "ValueError", "WARNING", "recoverable detail"):
            self.assertIn(fragment, result["data"]["text"])
        self.assertTrue(result["data"]["budget_exceeded"])
        self.assertTrue(result["warnings"])

    def test_unknown_format_has_bounded_excerpt_and_explicit_omission(self):
        text = "".join(f"record {i}\n" for i in range(30))
        result = self.compact(text, format="custom-tool", max_lines=4)
        self.assertLessEqual(result["data"]["after"]["lines"], 4)
        self.assertIn("omitted", result["data"]["text"])
        self.assertGreater(result["data"]["omitted_lines"], 0)
        self.assertTrue(result["warnings"])

    def test_raw_view_preserves_unicode_and_carriage_returns(self):
        text = "进度 1\r进度 2\r\nWARNING 合成\n"
        result = self.compact(text, raw=True, max_lines=1)
        self.assertEqual(result["data"]["text"], text)
        self.assertEqual(result["data"]["before"]["bytes"], len(text.encode("utf-8")))
        self.assertEqual(result["data"]["before"], result["data"]["after"])
        self.assertEqual(result["data"]["omitted_lines"], 0)

    def test_empty_input_has_zero_counts(self):
        result = self.compact("")
        self.assertEqual(result["data"]["text"], "")
        self.assertEqual(result["data"]["before"], {"bytes": 0, "lines": 0})
        self.assertEqual(result["data"]["after"], {"bytes": 0, "lines": 0})

    def test_invalid_utf8_returns_explicit_failure(self):
        result = self.compact(b"\xff\xfe")
        self.assertEqual(result["status"], "failed")
        self.assertIn("UTF-8", result["summary"])

    def test_git_status_preserves_paths_and_warning(self):
        text = " M src/文件 name.py\n?? new file.txt\nwarning: synthetic diagnostic\n"
        result = self.compact(text, format="git-status", max_lines=8)
        self.assertIn("src/文件 name.py", result["data"]["text"])
        self.assertIn("warning: synthetic diagnostic", result["data"]["text"])

    def test_cli_missing_input_and_invalid_budget_are_usage_errors(self):
        for args in (("compact",), ("compact", "--input", "missing", "--max-lines", "0")):
            run = subprocess.run([sys.executable, str(ROOT / "scripts/token_saver.py"), *args],
                                 capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(run.stdout, "")

    def test_cli_missing_file_is_a_blocked_json_result(self):
        with tempfile.TemporaryDirectory() as directory:
            run = subprocess.run([sys.executable, str(ROOT / "scripts/token_saver.py"),
                                  "compact", "--input", str(Path(directory) / "missing.txt")],
                                 capture_output=True, text=True, encoding="utf-8", timeout=10)
        self.assertEqual(run.returncode, 1)
        self.assertEqual(json.loads(run.stdout)["status"], "blocked")

    def test_cli_compact_reads_synthetic_fixture(self):
        run = subprocess.run([sys.executable, str(ROOT / "scripts/token_saver.py"),
                              "compact", "--input", str(ROOT / "tests/fixtures/compact/noisy-test.txt"),
                              "--format", "test", "--max-lines", "6"],
                             capture_output=True, text=True, encoding="utf-8", timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        data = json.loads(run.stdout)["data"]
        self.assertIn("FAILED sample", data["text"])
        self.assertLess(data["after"]["bytes"], data["before"]["bytes"])

    def test_abbreviated_warning_and_error_markers_survive_budget(self):
        for marker in ("WARN missing optional input", "npm WARN retry", "npm ERR! missing module", "\x1b[33mWARN colored\x1b[0m"):
            with self.subTest(marker=marker):
                result = self.compact("header\n\n" + marker + "\n\nfooter\n", max_lines=2)
                self.assertIn(marker, result["data"]["text"])
