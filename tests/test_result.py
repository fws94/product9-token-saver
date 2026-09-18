"""Behavioral tests for the public result envelope."""
import importlib.util
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


class ResultTests(unittest.TestCase):
    def result_type(self):
        spec = importlib.util.find_spec("token_saver_lib")
        self.assertIsNotNone(spec, "result package must exist")
        from token_saver_lib.result import Result
        return Result

    def test_statuses_preserve_evidence_and_command_exit(self):
        Result = self.result_type()
        for status in ("completed", "failed", "partial", "blocked", "uncertain"):
            with self.subTest(status=status):
                result = Result(operation="checks", status=status, summary="合成结果",
                                exit_code=7, duration_ms=12.5,
                                evidence=["reports/测试 log.txt"],
                                identifiers={"target": "example"},
                                warnings=["coverage unknown"], data={"count": 2})
                payload = json.loads(result.to_json())
                self.assertEqual(payload, {
                    "schema_version": 1, "operation": "checks", "status": status,
                    "summary": "合成结果", "exit_code": 7, "duration_ms": 12.5,
                    "evidence": ["reports/测试 log.txt"], "identifiers": {"target": "example"},
                    "warnings": ["coverage unknown"], "data": {"count": 2}})
                self.assertIn("合成结果", result.to_json())

    def test_unknown_evidence_is_null_not_success(self):
        Result = self.result_type()
        payload = Result(operation="status", status="uncertain", summary="Unknown").to_dict()
        self.assertIsNone(payload["exit_code"])
        self.assertIsNone(payload["duration_ms"])
        self.assertEqual(payload["evidence"], [])

    def test_invalid_values_are_rejected(self):
        Result = self.result_type()
        cases = [
            {"status": "success"}, {"operation": " "}, {"summary": ""},
            {"exit_code": True}, {"exit_code": "1"}, {"duration_ms": -1},
            {"duration_ms": float("nan")}, {"duration_ms": True},
            {"evidence": "log.txt"}, {"evidence": [""]},
            {"warnings": [1]}, {"identifiers": {"id": 3}},
            {"data": []}, {"data": {"bad": float("inf")}},
            {"data": {1: "bad key"}}, {"data": {"value": object()}},
        ]
        for override in cases:
            with self.subTest(override=override):
                args = dict(operation="example", status="completed", summary="Example")
                args.update(override)
                with self.assertRaises((ValueError, TypeError)):
                    Result(**args).to_json()

    def test_serialized_data_is_an_independent_snapshot(self):
        Result = self.result_type()
        result = Result(operation="example", status="completed", summary="Example", data={"items": [1]})
        payload = result.to_dict()
        payload["data"]["items"].append(2)
        self.assertEqual(result.to_dict()["data"], {"items": [1]})
        self.assertEqual(Result(operation="example", status="blocked", summary="Missing tool").to_dict()["data"], {})
