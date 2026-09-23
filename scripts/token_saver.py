#!/usr/bin/env python3
"""Offline Token Saver CLI for contracts, compaction, checks and lookup."""
import argparse
import math
from pathlib import Path
import sys

from package_plugin import package_plugin
from token_saver_lib.checks import run_checks
from token_saver_lib.compact import compact_file
from token_saver_lib.lookup import lookup
from token_saver_lib.usage import collect_usage, merge_usage
from token_saver_lib.status import collect_github_status
from token_saver_lib.result import Result, SCHEMA_VERSION, STATUSES


def positive_integer(value: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def non_negative_integer(value: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a non-negative integer") from error
    if number < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
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
    lookup_parser = commands.add_parser("lookup", help="find bounded paths or text excerpts")
    lookup_parser.add_argument("--root", required=True, help="repository root to search")
    lookup_parser.add_argument("--query", required=True, help="literal or regex query")
    lookup_parser.add_argument("--mode", choices=("files", "text"), required=True)
    lookup_parser.add_argument("--pattern-mode", choices=("literal", "regex"), required=True)
    lookup_parser.add_argument("--max-results", type=positive_integer, default=50)
    lookup_parser.add_argument("--context-lines", type=non_negative_integer, default=0)
    status_parser = commands.add_parser("status", help="collect read-only pull-request status")
    status_parser.add_argument("--provider", choices=("github",), required=True)
    status_parser.add_argument("--repo", required=True, help="repository OWNER/REPO")
    status_parser.add_argument("--prs", type=positive_integer, nargs="+", required=True, metavar="NUMBER")
    status_parser.add_argument("--max-concurrency", type=positive_integer, default=4)
    usage_parser = commands.add_parser("usage", help="collect a local device usage report")
    usage_parser.add_argument("--start", required=True, help="inclusive local date YYYY-MM-DD")
    usage_parser.add_argument("--end", required=True, help="inclusive local date YYYY-MM-DD")
    usage_parser.add_argument("--utc-offset", required=True, type=float, metavar="HOURS")
    usage_parser.add_argument("--device", required=True, help="device label")
    usage_parser.add_argument("--input", default=None, help="usage log file or directory; default: ~/.codex/sessions")
    usage_parser.add_argument("--output", required=True, help="report JSON path")
    usage_parser.add_argument("--hash-receipts", action="store_true", help="store hashed response receipts without IDs")
    merge_parser = commands.add_parser("usage-merge", help="merge local device usage reports")
    merge_parser.add_argument("--inputs", nargs="+", required=True, metavar="PATH")
    merge_parser.add_argument("--output", required=True, help="aggregate report JSON path")
    package_parser = commands.add_parser("package", help="create a deterministic plugin archive")
    package_parser.add_argument("--plugin-root", default=Path(__file__).resolve().parents[1])
    package_parser.add_argument("--output", required=True, help="zip artifact path")
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
    if args.command == "package":
        try:
            result = package_plugin(args.plugin_root, args.output)
        except ValueError as error:
            package_parser.error(str(error))
        print(f"Packaged {result.name} {result.version}: {result.path}")
        return 0
    if args.command == "usage":
        try:
            source = args.input or (Path.home() / ".codex" / "sessions")
            result = collect_usage(source=source, start=args.start, end=args.end,
                                   utc_offset=args.utc_offset, device=args.device,
                                   output=args.output, hash_receipts=args.hash_receipts)
        except ValueError as error:
            usage_parser.error(str(error))
        print(result.to_json())
        return 0 if result.status == "completed" else 1
    if args.command == "usage-merge":
        try:
            result = merge_usage(args.inputs, args.output)
        except ValueError as error:
            merge_parser.error(str(error))
        print(result.to_json())
        return 0 if result.status == "completed" else 1
    if args.command == "status":
        try:
            result = collect_github_status(args.repo, args.prs,
                                           max_concurrency=args.max_concurrency)
        except ValueError as error:
            status_parser.error(str(error))
        print(result.to_json())
        return 0 if result.status == "completed" else 1
    if args.command == "lookup":
        try:
            result = lookup(args.root, args.query, mode=args.mode, pattern_mode=args.pattern_mode,
                            max_results=args.max_results, context_lines=args.context_lines)
        except ValueError as error:
            lookup_parser.error(str(error))
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
                  "warnings": "array of non-empty warnings",
                  "exit_code": "observed command exit code or null",
                  "duration_ms": "finite non-negative milliseconds or null"},
              "cli_exit_codes": {"0": "completed", "1": "non-completed outcome",
                                 "2": "invalid invocation"}})
    print(result.to_json())
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
