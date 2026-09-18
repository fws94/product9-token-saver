"""Behavioral tests for bounded repository lookup."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class LookupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lookup 空间 ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "src/子目录").mkdir(parents=True)
        (self.root / ".gitignore").write_text("ignored.txt\nignored-dir/\n", encoding="utf-8")
        (self.root / "src/子目录/hello world.py").write_text(
            "alpha\nneedle literal\ncontext line\nneedle literal\nomega\n", encoding="utf-8")
        (self.root / "README.md").write_text("needle markdown\n", encoding="utf-8")
        (self.root / "ignored.txt").write_text("needle ignored\n", encoding="utf-8")
        (self.root / "ignored-dir").mkdir()
        (self.root / "ignored-dir/hidden.py").write_text("needle hidden\n", encoding="utf-8")
        (self.root / "binary.dat").write_bytes(b"needle\x00binary\xff")

    def lookup(self, query, **kwargs):
        from token_saver_lib.lookup import lookup
        return lookup(self.root, query, **kwargs).to_dict()

    def test_text_literal_returns_relative_lines_and_context(self):
        result = self.lookup("needle literal", mode="text", pattern_mode="literal",
                             max_results=10, context_lines=1)
        self.assertEqual(result["status"], "completed")
        matches = result["data"]["matches"]
        self.assertEqual([(row["path"], row["line"], row["kind"]) for row in matches], [
            ("src/子目录/hello world.py", 1, "context"),
            ("src/子目录/hello world.py", 2, "match"),
            ("src/子目录/hello world.py", 3, "context"),
            ("src/子目录/hello world.py", 4, "match"),
            ("src/子目录/hello world.py", 5, "context"),
        ])
        self.assertTrue(all(not Path(row["path"]).is_absolute() for row in matches))
        self.assertNotIn("ignored", " ".join(row["excerpt"] for row in matches))

    def test_text_regex_is_explicit_and_literal_metacharacters_are_safe(self):
        literal = self.lookup("needle.", mode="text", pattern_mode="literal")
        self.assertEqual(literal["data"]["matches"], [])
        regex = self.lookup(r"needle (literal|markdown)", mode="text", pattern_mode="regex")
        self.assertEqual([(row["path"], row["line"]) for row in regex["data"]["matches"]], [
            ("README.md", 1), ("src/子目录/hello world.py", 2), ("src/子目录/hello world.py", 4)])

    def test_files_mode_respects_ignore_and_returns_stable_paths(self):
        result = self.lookup("hello world.py", mode="files", pattern_mode="literal", max_results=20)
        self.assertEqual(result["data"]["matches"], [{"path": "src/子目录/hello world.py", "kind": "file"}])
        self.assertEqual(result["data"]["truncated"], False)

    def test_no_matches_is_completed_empty_result(self):
        result = self.lookup("does-not-exist", mode="text", pattern_mode="literal")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["data"]["matches"], [])
        self.assertFalse(result["data"]["truncated"])

    def test_max_results_marks_truncation_and_bounds_rows(self):
        result = self.lookup("needle", mode="text", pattern_mode="literal",
                             max_results=2, context_lines=0)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(result["data"]["matches"]), 2)
        self.assertTrue(result["data"]["truncated"])
        self.assertTrue(any("truncated" in warning.lower() for warning in result["warnings"]))

    def test_missing_root_and_missing_rg_are_blocked(self):
        from token_saver_lib.lookup import lookup
        missing = lookup(self.root / "missing", "needle", mode="text", pattern_mode="literal").to_dict()
        self.assertEqual(missing["status"], "blocked")
        self.assertEqual(missing["data"]["outcome"], "unreadable-root")
        with patch.dict(os.environ, {"PATH": ""}):
            unavailable = lookup(self.root, "needle", mode="text", pattern_mode="literal").to_dict()
        self.assertEqual(unavailable["status"], "blocked")
        self.assertEqual(unavailable["data"]["outcome"], "missing-executable")

    def test_invalid_queries_and_modes_are_rejected(self):
        from token_saver_lib.lookup import lookup
        for kwargs in ({"mode": "bad"}, {"pattern_mode": "bad"}, {"max_results": 0},
                       {"context_lines": -1}, {"query": ""}):
            args = dict(query="needle", mode="text", pattern_mode="literal")
            args.update(kwargs)
            query = args.pop("query")
            with self.assertRaises((ValueError, TypeError)):
                lookup(self.root, query, **args)

    def test_cli_is_bounded_and_reports_missing_rg_without_shell(self):
        command = [sys.executable, str(ROOT / "scripts/token_saver.py"), "lookup",
                   "--root", str(self.root), "--query", "needle", "--mode", "text",
                   "--pattern-mode", "literal", "--max-results", "2", "--context-lines", "0"]
        run = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        payload = json.loads(run.stdout)
        self.assertEqual(len(payload["data"]["matches"]), 2)
        self.assertTrue(payload["data"]["truncated"])
        env = os.environ.copy()
        env["PATH"] = ""
        blocked = subprocess.run(command, env=env, capture_output=True, text=True,
                                 encoding="utf-8", timeout=10)
        self.assertEqual(blocked.returncode, 1)
        self.assertEqual(json.loads(blocked.stdout)["data"]["outcome"], "missing-executable")

    def test_cli_invalid_regex_is_usage_error(self):
        command = [sys.executable, str(ROOT / "scripts/token_saver.py"), "lookup",
                   "--root", str(self.root), "--query", "[", "--mode", "text",
                   "--pattern-mode", "regex"]
        run = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=10)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(run.stdout, "")
