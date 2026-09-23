"""Synthetic provider fixtures for batched read-only status queries."""
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def completed(number, *, state="OPEN", checks=None):
    return subprocess.CompletedProcess(
        ["gh"], 0,
        json.dumps({"number": number, "url": f"https://github.com/acme/repo/pull/{number}",
                    "state": state, "statusCheckRollup": checks}), "")


class FixtureRunner:
    def __init__(self, responses, delay=0):
        self.responses = responses
        self.delay = delay
        self.calls = []
        self.active = 0
        self.max_active = 0
        self.lock = threading.Lock()

    def __call__(self, command):
        number = int(command[3])
        with self.lock:
            self.calls.append(tuple(command))
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            if self.delay:
                time.sleep(self.delay)
            return self.responses[number]
        finally:
            with self.lock:
                self.active -= 1


class StatusTests(unittest.TestCase):
    def test_deduplicates_targets_and_summarizes_check_states(self):
        from token_saver_lib.status import collect_github_status
        runner = FixtureRunner({
            1: completed(1, checks=[{"status": "COMPLETED", "conclusion": "SUCCESS"},
                                    {"status": "COMPLETED", "conclusion": "SKIPPED"}]),
            2: completed(2, checks=[{"status": "IN_PROGRESS", "conclusion": None}]),
            3: completed(3, state="MERGED", checks=[{"status": "COMPLETED", "conclusion": "FAILURE"}]),
        }, delay=0.01)
        result = collect_github_status("acme/repo", [1, 2, 1, 3], runner=runner,
                                       gh_path="fixture-gh", max_concurrency=2).to_dict()
        self.assertEqual(result["status"], "completed")
        self.assertEqual([row["number"] for row in result["data"]["rows"]], [1, 2, 3])
        self.assertEqual([row["state"] for row in result["data"]["rows"]], ["OPEN", "OPEN", "MERGED"])
        self.assertEqual([row["checks"]["state"] for row in result["data"]["rows"]],
                         ["success", "pending", "failure"])
        self.assertEqual(len(runner.calls), 3)
        self.assertLessEqual(runner.max_active, 2)
        self.assertTrue(all(command[:3] == ("fixture-gh", "pr", "view") for command in runner.calls))

    def test_legacy_status_contexts_use_state_not_check_run_fields(self):
        from token_saver_lib.status import collect_github_status
        runner = FixtureRunner({
            1: completed(1, checks=[{"__typename": "StatusContext", "state": "SUCCESS"}]),
            2: completed(2, checks=[{"__typename": "StatusContext", "state": "FAILURE"}]),
            3: completed(3, checks=[{"__typename": "StatusContext", "state": "ERROR"}]),
            4: completed(4, checks=[{"__typename": "StatusContext", "state": "PENDING"}]),
            5: completed(5, checks=[{"__typename": "StatusContext", "state": "EXPECTED"}]),
        })
        rows = collect_github_status("acme/repo", [1, 2, 3, 4, 5], runner=runner,
                                     gh_path="fixture-gh").to_dict()["data"]["rows"]
        self.assertEqual([row["checks"]["state"] for row in rows],
                         ["success", "failure", "failure", "pending", "pending"])
        self.assertEqual(rows[0]["checks"]["passed"], 1)
        self.assertEqual(rows[1]["checks"]["failed"], 1)

    def test_unknown_and_missing_check_data_stay_distinct(self):
        from token_saver_lib.status import collect_github_status
        runner = FixtureRunner({
            4: completed(4, checks=[]),
            5: completed(5, checks=[{"status": "COMPLETED", "conclusion": "NEUTRAL"},
                                    {"status": "COMPLETED"}]),
        })
        rows = collect_github_status("acme/repo", [4, 5], runner=runner,
                                     gh_path="fixture-gh").to_dict()["data"]["rows"]
        self.assertEqual(rows[0]["checks"], {"state": "unknown", "total": 0,
                                               "passed": 0, "failed": 0, "pending": 0, "unknown": 0})
        self.assertEqual(rows[1]["checks"]["state"], "unknown")
        self.assertEqual(rows[1]["checks"]["unknown"], 1)

    def test_permission_error_is_partial_unknown_not_nonexistent(self):
        from token_saver_lib.status import collect_github_status
        denied = subprocess.CompletedProcess(["gh"], 1, "", "HTTP 403: Resource not accessible")
        runner = FixtureRunner({1: completed(1), 9: denied})
        result = collect_github_status("acme/repo", [1, 9], runner=runner,
                                       gh_path="fixture-gh").to_dict()
        self.assertEqual(result["status"], "partial")
        row = result["data"]["rows"][1]
        self.assertEqual(row["state"], "UNKNOWN")
        self.assertEqual(row["checks"]["state"], "unknown")
        self.assertEqual(row["error"]["kind"], "permission")
        self.assertNotEqual(row["error"]["kind"], "not-found")

    def test_malformed_provider_json_is_partial_and_preserves_error(self):
        from token_saver_lib.status import collect_github_status
        malformed = subprocess.CompletedProcess(["gh"], 0, "{bad json", "")
        runner = FixtureRunner({7: malformed})
        result = collect_github_status("acme/repo", [7], runner=runner,
                                       gh_path="fixture-gh").to_dict()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["data"]["rows"][0]["error"]["kind"], "invalid-response")

    def test_missing_cli_is_blocked_without_remote_call(self):
        from token_saver_lib.status import collect_github_status
        result = collect_github_status("acme/repo", [1], gh_path="missing-gh").to_dict()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["data"]["outcome"], "missing-executable")
        self.assertEqual(result["data"]["rows"], [])

    def test_queries_are_read_only_and_bounded(self):
        from token_saver_lib.status import collect_github_status
        runner = FixtureRunner({1: completed(1)})
        result = collect_github_status("acme/repo", [1], runner=runner,
                                       gh_path="fixture-gh", max_concurrency=1).to_dict()
        command = runner.calls[0]
        self.assertIn("--json", command)
        self.assertTrue(any("statusCheckRollup" in argument for argument in command))
        self.assertNotIn("edit", command)
        self.assertNotIn("comment", command)
        self.assertNotIn("merge", command)
        self.assertEqual(result["data"]["requested"], [1])

    def test_cli_invalid_provider_and_missing_targets_are_usage_errors(self):
        script = ROOT / "scripts" / "token_saver.py"
        for args in (("status", "--provider", "gitlab", "--repo", "acme/repo", "--prs", "1"),
                     ("status", "--provider", "github", "--repo", "acme/repo")):
            run = subprocess.run([sys.executable, str(script), *args], capture_output=True,
                                 text=True, encoding="utf-8", timeout=10)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(run.stdout, "")
