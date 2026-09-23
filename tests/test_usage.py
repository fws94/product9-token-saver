"""Synthetic usage-log and multi-device report tests."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def write_jsonl(path, records):
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")


class UsageTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="usage 报告 "))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.logs = self.root / "logs"
        self.logs.mkdir()
        self.output = self.root / "reports/device.json"

    def collect(self, **kwargs):
        from token_saver_lib.usage import collect_usage
        return collect_usage(source=self.logs, device="device-a", output=self.output,
                             **kwargs).to_dict()

    def test_half_open_local_date_boundary_and_global_response_dedupe(self):
        write_jsonl(self.logs / "2026-09.jsonl", [
            {"format": "responses-v1", "timestamp": "2026-08-31T23:30:00+08:00", "response_id": "outside", "usage": {"input_tokens": 99, "cached_input_tokens": 9, "output_tokens": 10}},
            {"format": "responses-v1", "timestamp": "2026-09-01T00:30:00+08:00", "response_id": "inside", "usage": {"input_tokens": 100, "cached_input_tokens": 40, "output_tokens": 20, "reasoning_output_tokens": 5}},
            {"format": "responses-v1", "timestamp": "2026-09-01T01:00:00+08:00", "response_id": "inside", "usage": {"input_tokens": 999, "cached_input_tokens": 1, "output_tokens": 999}},
            {"format": "responses-v1", "timestamp": "2026-09-02T00:00:00+08:00", "response_id": "end", "usage": {"input_tokens": 7, "cached_input_tokens": 2, "output_tokens": 3}},
        ])
        result = self.collect(start="2026-09-01", end="2026-09-01", utc_offset=8)
        self.assertEqual(result["status"], "completed")
        period = result["data"]["period"]
        self.assertEqual(period["start"], "2026-09-01T00:00:00+08:00")
        self.assertEqual(period["end_exclusive"], "2026-09-02T00:00:00+08:00")
        self.assertEqual(result["data"]["totals"], {
            "responses": 1, "input_tokens": 100, "cached_input_tokens": 40,
            "output_tokens": 20, "reasoning_output_tokens": 5})
        self.assertEqual(result["data"]["deduplication"]["records_seen"], 4)
        self.assertEqual(result["data"]["deduplication"]["duplicates_removed"], 1)

    def test_cached_and_reasoning_subsets_and_automatic_approval_are_separate(self):
        write_jsonl(self.logs / "events.jsonl", [
            {"format": "responses-v1", "timestamp": "2026-09-10T00:00:00Z", "response_id": "normal", "usage": {"input_tokens": 10, "cached_input_tokens": 3, "output_tokens": 8, "reasoning_output_tokens": 2}},
            {"format": "responses-v1", "timestamp": "2026-09-10T01:00:00Z", "response_id": "approval", "automatic_approval": True, "usage": {"input_tokens": 50, "cached_input_tokens": 5, "output_tokens": 6, "reasoning_output_tokens": 1}},
        ])
        data = self.collect(start="2026-09-10", end="2026-09-10", utc_offset=0)["data"]
        self.assertEqual(data["totals"], {"responses": 1, "input_tokens": 10, "cached_input_tokens": 3, "output_tokens": 8, "reasoning_output_tokens": 2})
        self.assertEqual(data["automatic_approval"]["records"], 1)
        self.assertEqual(data["automatic_approval"]["input_tokens"], 50)
        self.assertEqual(data["automatic_approval"]["reasoning_output_tokens"], 1)

    def test_mixed_format_warning_and_missing_source_are_not_zero(self):
        write_jsonl(self.logs / "mixed.jsonl", [
            {"format": "responses-v1", "timestamp": "2026-09-10T00:00:00Z", "response_id": "new", "usage": {"input_tokens": 1, "output_tokens": 1}},
            {"format": "legacy-v0", "time": "2026-09-10T01:00:00Z", "id": "old", "input": 2, "cached_input": 0, "output": 2},
        ])
        result = self.collect(start="2026-09-10", end="2026-09-10", utc_offset=0)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(any("mixed" in warning.lower() for warning in result["warnings"]))
        from token_saver_lib.usage import collect_usage
        missing = collect_usage(source=self.root / "missing", device="device-a", output=self.output,
                                start="2026-09-10", end="2026-09-10", utc_offset=0).to_dict()
        self.assertEqual(missing["status"], "blocked")
        self.assertFalse(missing["data"]["coverage"]["known"])
        self.assertNotEqual(missing["data"].get("totals", {}).get("input_tokens", 0), 0)

    def test_hashed_receipts_avoid_prompt_export_but_do_not_prove_device(self):
        write_jsonl(self.logs / "events.jsonl", [
            {"format": "responses-v1", "timestamp": "2026-09-10T00:00:00Z", "response_id": "secret-response-id", "usage": {"input_tokens": 1, "output_tokens": 2}},
        ])
        from token_saver_lib.usage import collect_usage
        result = collect_usage(source=self.logs, device="device-a", output=self.output,
                               start="2026-09-10", end="2026-09-10", utc_offset=0,
                               hash_receipts=True).to_dict()
        text = self.output.read_text(encoding="utf-8")
        self.assertNotIn("secret-response-id", text)
        self.assertEqual(len(result["data"]["response_receipts"]), 1)
        self.assertFalse(result["data"]["deduplication"]["cross_device_provable"])

    def test_transferable_device_report_omits_local_absolute_output_path(self):
        write_jsonl(self.logs / "events.jsonl", [{
            "timestamp": "2026-09-10T00:00:00Z", "response_id": "first",
            "usage": {"input_tokens": 2, "output_tokens": 1}
        }])
        result = self.collect(start="2026-09-10", end="2026-09-10", utc_offset=0)
        stored = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertIn(str(self.output.resolve()), result["evidence"])
        self.assertNotIn(str(self.output.resolve()), json.dumps(stored, ensure_ascii=False))
        self.assertEqual(stored["evidence"], [self.output.name])

    def test_merge_five_reports_keeps_warnings_and_flags_cross_device_limit(self):
        from token_saver_lib.usage import merge_usage
        reports = []
        for index in range(5):
            path = self.root / f"device-{index}.json"
            payload = {"schema_version": 1, "operation": "usage", "status": "completed",
                       "data": {"schema_version": 1, "device": f"d{index}", "period": {"start": "2026-09-01T00:00:00+00:00", "end_exclusive": "2026-09-02T00:00:00+00:00"},
                                "totals": {"responses": 1, "input_tokens": index + 1, "cached_input_tokens": 0, "output_tokens": 2, "reasoning_output_tokens": 1},
                                "automatic_approval": {"records": 0, "input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "reasoning_output_tokens": 0},
                                "coverage": {"known": True, "warnings": [f"device {index} synthetic gap"]},
                                "deduplication": {"cross_device_provable": False}}, "warnings": [f"device {index} warning"]}
            path.write_text(json.dumps(payload), encoding="utf-8")
            reports.append(path)
        output = self.root / "reports/merged.json"
        result = merge_usage(reports, output).to_dict()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["data"]["devices"], 5)
        self.assertEqual(result["data"]["totals"]["input_tokens"], 15)
        self.assertFalse(result["data"]["deduplication"]["cross_device_provable"])
        self.assertGreaterEqual(len(result["warnings"]), 5)
        self.assertTrue(any("cross-device" in warning.lower() for warning in result["warnings"]))

    def test_merge_rejects_same_device_report_path_twice(self):
        from token_saver_lib.usage import merge_usage
        write_jsonl(self.logs / "events.jsonl", [{
            "timestamp": "2026-09-10T00:00:00Z", "response_id": "first",
            "usage": {"input_tokens": 2, "output_tokens": 1}
        }])
        report = self.collect(start="2026-09-10", end="2026-09-10", utc_offset=0)
        self.assertEqual(report["status"], "completed")
        with self.assertRaises(ValueError):
            merge_usage([self.output, self.output], self.root / "reports/duplicate.json")

    def test_merge_rejects_same_device_label_in_two_files(self):
        from token_saver_lib.usage import merge_usage
        write_jsonl(self.logs / "events.jsonl", [{
            "timestamp": "2026-09-10T00:00:00Z", "response_id": "first",
            "usage": {"input_tokens": 2, "output_tokens": 1}
        }])
        report = self.collect(start="2026-09-10", end="2026-09-10", utc_offset=0)
        self.assertEqual(report["status"], "completed")
        second = self.root / "reports/renamed-copy.json"
        shutil.copyfile(self.output, second)
        with self.assertRaises(ValueError):
            merge_usage([self.output, second], self.root / "reports/two-copies.json")

    def test_merge_rejects_aggregate_even_with_device_label(self):
        from token_saver_lib.usage import merge_usage
        write_jsonl(self.logs / "events.jsonl", [{
            "timestamp": "2026-09-10T00:00:00Z", "response_id": "first",
            "usage": {"input_tokens": 2, "output_tokens": 1}
        }])
        self.collect(start="2026-09-10", end="2026-09-10", utc_offset=0)
        aggregate_path = self.root / "reports/aggregate.json"
        merge_usage([self.output], aggregate_path)
        aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
        aggregate["data"]["device"] = "misleading-device"
        aggregate_path.write_text(json.dumps(aggregate), encoding="utf-8")
        with self.assertRaises(ValueError):
            merge_usage([aggregate_path], self.root / "reports/double-counted.json")

    def test_merge_rejects_schema_or_period_mismatch(self):
        from token_saver_lib.usage import merge_usage
        first = self.root / "first.json"
        first.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
        with self.assertRaises(ValueError):
            merge_usage([first], self.root / "out.json")

    def test_cli_usage_and_merge_write_json_without_credentials(self):
        script = ROOT / "scripts" / "token_saver.py"
        run = subprocess.run([sys.executable, str(script), "usage", "--start", "2026-09-10", "--end", "2026-09-10", "--utc-offset", "0", "--device", "d", "--input", str(self.logs), "--output", str(self.output)], capture_output=True, text=True, encoding="utf-8", timeout=10)
        self.assertEqual(run.returncode, 1)
        self.assertEqual(json.loads(run.stdout)["status"], "blocked")
        self.assertTrue(self.output.is_file())

    def test_cli_usage_error_stderr_is_utf8_for_unicode_paths(self):
        missing = self.root / "不存在.json"
        run = subprocess.run([
            sys.executable, str(ROOT / "scripts/token_saver.py"), "usage-merge",
            "--inputs", str(missing), "--output", str(self.output)
        ], capture_output=True, text=True, encoding="utf-8", timeout=10)
        self.assertEqual(run.returncode, 2)
        self.assertIn("不存在.json", run.stderr)

    def test_cli_merge_returns_aggregate_report(self):
        report = self.root / "device.json"
        report.write_text(json.dumps({
            "schema_version": 1,
            "operation": "usage",
            "status": "completed",
            "data": {
                "device": "cli-device",
                "period": {"start": "2026-09-10T00:00:00+00:00", "end_exclusive": "2026-09-11T00:00:00+00:00"},
                "totals": {"responses": 1, "input_tokens": 2, "cached_input_tokens": 1, "output_tokens": 3, "reasoning_output_tokens": 1},
                "automatic_approval": {"records": 0, "input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "reasoning_output_tokens": 0},
                "coverage": {"known": True, "warnings": []},
            },
            "warnings": [],
        }), encoding="utf-8")
        output = self.root / "reports/aggregate.json"
        run = subprocess.run([sys.executable, str(ROOT / "scripts/token_saver.py"), "usage-merge", "--inputs", str(report), "--output", str(output)], capture_output=True, text=True, encoding="utf-8", timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        payload = json.loads(run.stdout)
        self.assertEqual(payload["operation"], "usage-merge")
        self.assertFalse(payload["data"]["deduplication"]["cross_device_provable"])
        self.assertTrue(output.is_file())

    def test_legacy_records_and_pretty_json_are_counted_and_mixed_warning_is_kept(self):
        (self.logs / "pretty.json").write_text(json.dumps({
            "format": "responses-v1", "timestamp": "2026-09-10T00:00:00Z", "response_id": "modern",
            "usage": {"input_tokens": 2, "output_tokens": 3}
        }, indent=2), encoding="utf-8")
        write_jsonl(self.logs / "legacy.jsonl", [{
            "format": "legacy-v0", "time": "2026-09-10T01:00:00Z", "id": "legacy",
            "input": 5, "cached_input": 1, "output": 4
        }])
        result = self.collect(start="2026-09-10", end="2026-09-10", utc_offset=0)
        self.assertEqual(result["data"]["totals"]["responses"], 2)
        self.assertEqual(result["data"]["totals"]["input_tokens"], 7)
        self.assertTrue(any("mixed" in warning.lower() for warning in result["warnings"]))

    def test_period_without_selected_records_is_unknown_not_known_zero(self):
        write_jsonl(self.logs / "events.jsonl", [{
            "format": "responses-v1", "timestamp": "2026-09-09T23:59:59Z", "response_id": "outside",
            "usage": {"input_tokens": 4, "output_tokens": 4}
        }])
        result = self.collect(start="2026-09-10", end="2026-09-10", utc_offset=0)
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["data"]["coverage"]["known"])
        self.assertIsNone(result["data"]["totals"]["input_tokens"])

    def test_merge_rejects_raw_receipts_malformed_period_and_negative_totals(self):
        from token_saver_lib.usage import merge_usage
        report = self.root / "report.json"
        report.write_text(json.dumps({
            "schema_version": 1, "operation": "usage", "data": {
                "period": {"start": "bad"},
                "totals": {"responses": -1, "input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "reasoning_output_tokens": 0},
                "automatic_approval": {"records": 0, "input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "reasoning_output_tokens": 0},
                "coverage": {"known": True}, "response_receipts": ["raw-response-id"]
            }
        }), encoding="utf-8")
        with self.assertRaises(ValueError):
            merge_usage([report], self.root / "out.json")

    def test_naive_timestamp_is_not_silently_assigned_a_timezone(self):
        write_jsonl(self.logs / "naive.jsonl", [{
            "format": "responses-v1", "timestamp": "2026-09-10T00:00:00", "response_id": "naive",
            "usage": {"input_tokens": 1, "output_tokens": 1}
        }])
        result = self.collect(start="2026-09-10", end="2026-09-10", utc_offset=8)
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["data"]["coverage"]["known"])
        self.assertTrue(any("timestamp" in warning.lower() for warning in result["warnings"]))

    def test_merge_accepts_valid_hashed_receipts_and_counts_duplicates(self):
        from token_saver_lib.usage import merge_usage
        common = "a" * 64
        reports = []
        for index in range(2):
            report = self.root / f"receipt-{index}.json"
            report.write_text(json.dumps({
                "schema_version": 1, "operation": "usage", "data": {
                    "device": f"receipt-device-{index}",
                    "period": {"start": "2026-09-10T00:00:00+00:00", "end_exclusive": "2026-09-11T00:00:00+00:00"},
                    "totals": {"responses": 1, "input_tokens": 1, "cached_input_tokens": 0, "output_tokens": 1, "reasoning_output_tokens": 0},
                    "automatic_approval": {"records": 0, "input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "reasoning_output_tokens": 0},
                    "coverage": {"known": True, "warnings": []}, "response_receipts": [common]
                }, "warnings": []}), encoding="utf-8")
            reports.append(report)
        result = merge_usage(reports, self.root / "reports/receipts.json").to_dict()
        self.assertEqual(result["data"]["deduplication"]["duplicate_receipts_detected"], 1)
        self.assertEqual(result["data"]["response_receipts"], [common])
