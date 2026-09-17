"""Real subprocess tests using only synthetic commands and temporary artifacts."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class ChecksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="checks 工作目录 ")
        self.addCleanup(self.temp.cleanup)
        self.cwd = Path(self.temp.name)

    def run_check(self, code, **kwargs):
        self.assertIsNotNone(importlib.util.find_spec("token_saver_lib.checks"),
                             "checks helper must exist")
        from token_saver_lib.checks import run_checks
        return run_checks([sys.executable, "-c", code], cwd=self.cwd,
                          timeout=kwargs.pop("timeout", 5), **kwargs).to_dict()

    def test_exit_zero_is_success_even_when_output_says_error(self):
        result = self.run_check("import sys; print('error count: 0'); print('warning: synthetic', file=sys.stderr)")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["data"]["outcome"], "passed")
        self.assertFalse(result["data"]["timed_out"])
        self.assertGreaterEqual(result["duration_ms"], 0)
        self.assertIn("error count: 0", result["data"]["stdout"]["data"]["text"])
        self.assertEqual(Path(result["data"]["artifacts"]["stderr"]).read_bytes(), b"warning: synthetic\r\n" if sys.platform == "win32" else b"warning: synthetic\n")

    def test_failure_preserves_exit_code_streams_and_compacted_view(self):
        code = "import sys; print('PASS synthetic\\n' * 200, end=''); print('FAILED synthetic check', file=sys.stderr); sys.exit(7)"
        result = self.run_check(code, max_lines=5)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["exit_code"], 7)
        self.assertEqual(result["data"]["outcome"], "failed")
        self.assertIn("FAILED synthetic check", result["data"]["stderr"]["data"]["text"])
        self.assertLess(result["data"]["stdout"]["data"]["after"]["bytes"],
                        result["data"]["stdout"]["data"]["before"]["bytes"])
        for stream in ("stdout", "stderr"):
            self.assertIn(result["data"]["artifacts"][stream], result["evidence"])

    def test_timeout_preserves_partial_output_and_is_not_test_failure(self):
        started = time.monotonic()
        result = self.run_check("import time; print('partial output', flush=True); time.sleep(30)", timeout=0.5)
        self.assertLess(time.monotonic() - started, 10)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["data"]["outcome"], "timeout")
        self.assertTrue(result["data"]["timed_out"])
        self.assertTrue(result["data"]["termination_confirmed"])
        self.assertIn(b"partial output", Path(result["data"]["artifacts"]["stdout"]).read_bytes())
        self.assertIsNotNone(result["exit_code"])

    def test_missing_executable_is_blocked_and_not_an_exit_code(self):
        self.assertIsNotNone(importlib.util.find_spec("token_saver_lib.checks"))
        from token_saver_lib.checks import run_checks
        result = run_checks([str(self.cwd / "nonexistent-executable")], cwd=self.cwd, timeout=1).to_dict()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["data"]["outcome"], "not-started")
        self.assertIsNone(result["exit_code"])
        self.assertFalse(result["data"]["timed_out"])

    def test_cwd_is_explicit_and_arguments_are_not_shell_expanded(self):
        self.assertIsNotNone(importlib.util.find_spec("token_saver_lib.checks"))
        from token_saver_lib.checks import run_checks
        args = ["space value", "中文", "& echo injected", "*.txt", ""]
        result = run_checks([sys.executable, "-c", "import json,os,sys; print(json.dumps([os.getcwd(),sys.argv[1:]]))", *args],
                            cwd=self.cwd, timeout=5).to_dict()
        raw = Path(result["data"]["artifacts"]["stdout"]).read_text(encoding="utf-8")
        actual_cwd, actual_args = json.loads(raw)
        self.assertEqual(Path(actual_cwd), self.cwd)
        self.assertEqual(actual_args, args)

    def test_binary_stdout_keeps_raw_bytes_and_does_not_change_exit_success(self):
        result = self.run_check("import sys; sys.stdout.buffer.write(bytes([255,254]))")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(Path(result["data"]["artifacts"]["stdout"]).read_bytes(), bytes([255,254]))
        self.assertEqual(result["data"]["stdout"]["status"], "failed")
        self.assertTrue(result["warnings"])

    def test_runs_have_distinct_artifacts_and_do_not_overwrite(self):
        first = self.run_check("print('first')")
        second = self.run_check("print('second')")
        first_path = Path(first["data"]["artifacts"]["stdout"])
        second_path = Path(second["data"]["artifacts"]["stdout"])
        self.assertNotEqual(first_path, second_path)
        self.assertIn("first", first_path.read_text())
        self.assertIn("second", second_path.read_text())
        self.assertTrue(first_path.is_relative_to(self.cwd / "reports/checks"))

    def test_invalid_cwd_does_not_execute_command(self):
        self.assertIsNotNone(importlib.util.find_spec("token_saver_lib.checks"))
        from token_saver_lib.checks import run_checks
        marker = self.cwd / "must-not-exist"
        code = f"from pathlib import Path; Path({str(marker)!r}).touch()"
        result = run_checks([sys.executable, "-c", code], cwd=self.cwd / "missing", timeout=1).to_dict()
        self.assertEqual(result["status"], "blocked")
        self.assertIsNone(result["exit_code"])
        self.assertFalse(marker.exists())

    def test_cli_requires_command_cwd_and_finite_positive_timeout(self):
        cases = [([], "required"), (["--cwd", str(self.cwd), "--timeout", "1", "--"], "command"),
                 (["--cwd", str(self.cwd), "--timeout", "nan", "--", sys.executable], "positive"),
                 (["--cwd", str(self.cwd), "--timeout", "0", "--", sys.executable], "positive")]
        for args, error in cases:
            with self.subTest(args=args):
                run = subprocess.run([sys.executable, str(ROOT / "scripts/token_saver.py"), "checks", *args],
                                     capture_output=True, text=True, timeout=10)
                self.assertEqual(run.returncode, 2)
                self.assertEqual(run.stdout, "")
                self.assertIn(error, run.stderr.lower())

    def test_cli_preserves_command_arguments_after_separator(self):
        run = subprocess.run([sys.executable, str(ROOT / "scripts/token_saver.py"), "checks", "--cwd", str(self.cwd),
                              "--timeout", "5", "--", sys.executable, "-c", "import sys; print(sys.argv[1]); sys.exit(3)", "--max-lines"],
                             capture_output=True, text=True, encoding="utf-8", timeout=10)
        self.assertEqual(run.returncode, 1)
        result = json.loads(run.stdout)
        self.assertEqual(result["exit_code"], 3)
        self.assertIn("--max-lines", result["data"]["stdout"]["data"]["text"])

    def test_timeout_stops_a_spawned_child_before_delayed_write(self):
        marker = self.cwd / "late-child-output"
        child_code = f"import time; from pathlib import Path; time.sleep(1.5); Path({str(marker)!r}).touch()"
        parent_code = f"import subprocess,sys,time; subprocess.Popen([sys.executable, '-c', {child_code!r}]); print('spawned', flush=True); time.sleep(30)"
        result = self.run_check(parent_code, timeout=0.5)
        self.assertTrue(result["data"]["termination_confirmed"])
        time.sleep(1.5)
        self.assertFalse(marker.exists(), "timed-out descendant must not continue its delayed check")

    def test_unwritable_artifact_destination_prevents_execution(self):
        self.assertIsNotNone(importlib.util.find_spec("token_saver_lib.checks"))
        from token_saver_lib.checks import run_checks
        destination = self.cwd / "file-not-directory"
        destination.write_text("keep")
        marker = self.cwd / "not-executed"
        code = f"from pathlib import Path; Path({str(marker)!r}).touch()"
        result = run_checks([sys.executable, "-c", code], cwd=self.cwd, timeout=1, output_dir=destination).to_dict()
        self.assertEqual(result["status"], "blocked")
        self.assertIsNone(result["exit_code"])
        self.assertFalse(marker.exists())
        self.assertEqual(destination.read_text(), "keep")

    def test_denied_tree_cleanup_is_uncertain_even_when_direct_child_stops(self):
        self.assertIsNotNone(importlib.util.find_spec("token_saver_lib.checks"))
        import token_saver_lib.checks
        if os.name == "nt":
            denied = patch("token_saver_lib.checks.subprocess.run", return_value=subprocess.CompletedProcess([], 1))
        else:
            denied = patch("token_saver_lib.checks.os.killpg", side_effect=PermissionError("synthetic denial"))
        with denied:
            result = self.run_check("import time; time.sleep(30)", timeout=0.1)
        self.assertEqual(result["status"], "uncertain")
        self.assertEqual(result["data"]["outcome"], "timeout")
        self.assertTrue(result["data"]["termination_confirmed"])
        self.assertFalse(result["data"]["tree_cleanup_confirmed"])
        self.assertTrue(result["warnings"])

    def test_relative_path_entries_use_check_cwd_not_wrapper_cwd(self):
        self.assertIsNotNone(importlib.util.find_spec("token_saver_lib.checks"))
        from token_saver_lib.checks import run_checks
        wrapper = self.cwd / "wrapper"
        project_tools = self.cwd / "tools"
        wrapper_tools = wrapper / "tools"
        project_tools.mkdir()
        wrapper_tools.mkdir(parents=True)
        if os.name == "nt":
            executable = Path(os.environ["COMSPEC"])
            name = "synthetic-check.exe"
            arguments = ["/d", "/c", "echo synthetic-path-check"]
        else:
            executable = Path(shutil.which("sh"))
            name = "synthetic-check"
            arguments = ["-c", "printf synthetic-path-check"]
        shutil.copy2(executable, project_tools / name)
        (wrapper_tools / name).write_text("not an executable")
        (wrapper_tools / name).chmod(0o755)
        original_cwd = Path.cwd()
        try:
            os.chdir(wrapper)
            with patch.dict(os.environ, {"PATH": "tools"}):
                result = run_checks([name, *arguments], cwd=self.cwd, timeout=5).to_dict()
        finally:
            os.chdir(original_cwd)
        self.assertEqual(result["status"], "completed", result)
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("synthetic-path-check", result["data"]["stdout"]["data"]["text"])
