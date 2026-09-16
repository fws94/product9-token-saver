#!/usr/bin/env python3
"""Offline Token Saver CLI foundation; runtime operations arrive in later issues."""
import argparse
import sys

from token_saver_lib.result import Result, SCHEMA_VERSION, STATUSES


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Token Saver development CLI (Python 3.11+; no credentials required).")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("contract", help="print the versioned JSON result contract")
    parser.parse_args(argv)
    result = Result(
        operation="contract", status="completed", summary="Token Saver result contract",
        data={"schema_version": SCHEMA_VERSION, "statuses": list(STATUSES),
              "fields": {
                  "schema_version": "integer; currently 1",
                  "operation": "non-empty string identifying the operation",
                  "status": "completed | failed | partial | blocked | uncertain",
                  "summary": "non-empty string",
                  "data": "object of finite JSON values",
                  "identifiers": "object of non-empty string identifiers",
                  "evidence": "array of non-empty artifact references",
                  "warnings": "array of non-empty strings",
                  "exit_code": "observed command exit code or null",
                  "duration_ms": "finite non-negative milliseconds or null"},
              "cli_exit_codes": {"0": "completed", "1": "non-completed outcome",
                                 "2": "invalid invocation"}})
    print(result.to_json())
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
