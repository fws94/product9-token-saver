#!/usr/bin/env python3
"""Offline Token Saver CLI for result contracts and captured output views."""
import argparse
import math
import sys

from token_saver_lib.checks import run_checks
from token_saver_lib.compact import compact_file
from token_saver_lib.result import Result, SCHEMA_VERSION, STATUSES


def positive_integer(value: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def positive_seconds(value: str) -> float:
    try:
        seconds = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be finite and positive") from error
    if not math.isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError("must be finite and positive")
    return seconds


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Token Saver development CLI (Python 3.11+; no credentials required).")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("contract", help="print the versioned JSON result contract")
    compact = commands.add_parser("compact", help="compact already captured UTF-8 output")
    compact.add_argument("--input", required=True, help="path to the original captured artifact")
    compact.add_argument("--format", default="generic", metavar="FORMAT",
                         help="generic, git-status or test; unknown formats use a generic excerpt")
    compact.add_argument("--max-lines", type=positive_integer, default=80,
                         help="positive line budget; diagnostics may exceed it (default: 80)")
    compact.add_argument("--raw", action="store_true", help="return the complete original text")
    checks = commands.add_parser("checks", help="run an agreed existing check once")
    checks.add_argument("--cwd", required=True, help="explicit working directory")
    checks.add_argument("--timeout", type=positive_seconds, required=True, help="positive timeout in seconds")
    checks.add_argument("--output-dir", help="artifact base directory; default: CWD/reports/checks")
    checks.add_argument("--max-lines", type=positive_integer, default=80, help="line budget per output stream")
    checks.add_argument("check_command", nargs=argparse.REMAINDER, help="-- COMMAND ARG...")
    args = parser.parse_args(argv)
    if args.command == "checks":
        command = args.check_command
        if not command or command[0] != "--" or len(command) == 1:
            checks.error("an explicit -- COMMAND ARG... is required")
        result = run_checks(command[1:], cwd=args.cwd, timeout=args.timeout,
                            output_dir=args.output_dir, max_lines=args.max_lines)
        print(result.to_json())
        return 0 if result.status == "completed" else 1
    if args.command == "compact":
        result = compact_file(args.input, format=args.format, max_lines=args.max_lines, raw=args.raw)
        print(result.to_json())
        return 0 if result.status == "completed" else 1
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
