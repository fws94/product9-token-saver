"""Read-only, bounded GitHub pull-request status collection."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import re
import shutil
import subprocess
import time
from typing import Any, Callable

from .result import Result

Runner = Callable[[list[str]], subprocess.CompletedProcess]
CHECK_STATES = ("success", "failure", "pending", "unknown")
FAILURE_CONCLUSIONS = {"FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE"}
SUCCESS_CONCLUSIONS = {"SUCCESS", "SKIPPED", "NEUTRAL"}
COMPLETED_STATUSES = {"COMPLETED", "SUCCESS"}


def _unknown_checks() -> dict[str, int | str]:
    return {"state": "unknown", "total": 0, "passed": 0,
            "failed": 0, "pending": 0, "unknown": 0}


def _summarize_checks(value: Any) -> dict[str, int | str]:
    if not isinstance(value, list) or not value:
        return _unknown_checks()
    summary = {"state": "unknown", "total": len(value), "passed": 0,
               "failed": 0, "pending": 0, "unknown": 0}
    for item in value:
        if not isinstance(item, dict):
            summary["unknown"] += 1
            continue
        if "state" in item and "status" not in item and "conclusion" not in item:
            context_state = str(item.get("state") or "").upper()
            if context_state in {"FAILURE", "ERROR"}:
                summary["failed"] += 1
            elif context_state == "SUCCESS":
                summary["passed"] += 1
            elif context_state in {"PENDING", "EXPECTED"}:
                summary["pending"] += 1
            else:
                summary["unknown"] += 1
            continue
        status = str(item.get("status") or "").upper()
        conclusion = str(item.get("conclusion") or "").upper()
        if conclusion in FAILURE_CONCLUSIONS:
            summary["failed"] += 1
        elif status not in COMPLETED_STATUSES:
            summary["pending"] += 1
        elif conclusion in SUCCESS_CONCLUSIONS:
            summary["passed"] += 1
        else:
            summary["unknown"] += 1
    if summary["failed"]:
        summary["state"] = "failure"
    elif summary["pending"]:
        summary["state"] = "pending"
    elif summary["unknown"]:
        summary["state"] = "unknown"
    else:
        summary["state"] = "success"
    return summary


def _error_kind(message: str) -> str:
    lowered = message.lower()
    if any(term in lowered for term in ("403", "forbidden", "permission", "not accessible", "401")):
        return "permission"
    if "not found" in lowered or "could not resolve" in lowered:
        return "not-found"
    return "provider-error"


def _error_row(number: int, kind: str, message: str) -> dict[str, Any]:
    return {"identifier": f"#{number}", "number": number, "url": None,
            "state": "UNKNOWN", "checks": _unknown_checks(),
            "error": {"kind": kind, "message": message[:500]}}


def _query_one(repo: str, number: int, gh_path: str, runner: Runner) -> dict[str, Any]:
    command = [gh_path, "pr", "view", str(number), "--repo", repo,
               "--json", "number,url,state,statusCheckRollup"]
    try:
        completed = runner(command)
    except Exception as error:  # a provider failure becomes a row-level partial result
        return _error_row(number, "provider-error", f"GitHub CLI invocation failed ({type(error).__name__})")
    stdout = completed.stdout
    stderr = completed.stderr
    if isinstance(stdout, bytes):
        stdout = stdout.decode("utf-8", errors="replace")
    if isinstance(stderr, bytes):
        stderr = stderr.decode("utf-8", errors="replace")
    stderr = str(stderr or "").strip()
    if completed.returncode != 0:
        return _error_row(number, _error_kind(stderr), stderr or "GitHub CLI returned a non-zero status")
    try:
        payload = json.loads(stdout)
    except (TypeError, json.JSONDecodeError) as error:
        return _error_row(number, "invalid-response", f"GitHub CLI returned invalid JSON ({type(error).__name__})")
    if not isinstance(payload, dict):
        return _error_row(number, "invalid-response", "GitHub CLI response was not a JSON object")
    response_number = payload.get("number", number)
    if type(response_number) is not int:
        return _error_row(number, "invalid-response", "GitHub CLI response has an invalid pull-request number")
    return {"identifier": f"#{response_number}", "number": response_number,
            "url": payload.get("url") if isinstance(payload.get("url"), str) else None,
            "state": str(payload.get("state") or "UNKNOWN").upper(),
            "checks": _summarize_checks(payload.get("statusCheckRollup"))}


def _default_runner(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=30,
                          shell=False)


def collect_github_status(repo: str, prs: list[int], *, runner: Runner | None = None,
                          gh_path: str | None = None, max_concurrency: int = 4) -> Result:
    """Query each unique PR once; never issue a GitHub write command."""
    if not isinstance(repo, str) or re.fullmatch(r"[^/\s]+/[^/\s]+", repo) is None:
        raise ValueError("repo must be OWNER/REPO")
    if not isinstance(prs, list) or not prs:
        raise ValueError("prs must be a non-empty list")
    if any(type(number) is not int or number < 1 for number in prs):
        raise ValueError("prs must contain positive integers")
    if type(max_concurrency) is not int or max_concurrency < 1:
        raise ValueError("max_concurrency must be a positive integer")
    requested: list[int] = []
    seen: set[int] = set()
    for number in prs:
        if number not in seen:
            requested.append(number)
            seen.add(number)
    data: dict[str, Any] = {"provider": "github", "repo": repo,
                            "requested": requested, "rows": [],
                            "outcome": "not-started", "max_concurrency": max_concurrency}
    gh = (gh_path or "fixture-gh") if runner is not None else shutil.which(gh_path or "gh")
    if not gh:
        data["outcome"] = "missing-executable"
        data["deduplicated"] = requested
        return Result(operation="status", status="blocked",
                      summary="GitHub CLI executable is unavailable", data=data,
                      warnings=["Install or expose the authenticated gh CLI before requesting status"])
    query_runner = runner or _default_runner
    started = time.monotonic()
    rows: dict[int, dict[str, Any]] = {}
    workers = min(max_concurrency, len(requested))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="token-saver-status") as pool:
        futures = {pool.submit(_query_one, repo, number, gh, query_runner): number
                   for number in requested}
        for future in as_completed(futures):
            number = futures[future]
            try:
                rows[number] = future.result()
            except Exception as error:
                rows[number] = _error_row(number, "provider-error", f"Status worker failed ({type(error).__name__})")
    ordered = [rows[number] for number in requested]
    errors = [row["error"] for row in ordered if "error" in row]
    data["deduplicated"] = requested
    data["rows"] = ordered
    data["outcome"] = "partial" if errors else "completed"
    warnings = [f"#{number}: {row['error']['kind']}" for number, row in zip(requested, ordered) if "error" in row]
    if errors:
        warnings.insert(0, "One or more GitHub status targets could not be read")
    return Result(operation="status", status="partial" if errors else "completed",
                  summary="GitHub pull-request status collected" if not errors else "GitHub status partially collected",
                  data=data, duration_ms=(time.monotonic() - started) * 1000,
                  warnings=warnings)
