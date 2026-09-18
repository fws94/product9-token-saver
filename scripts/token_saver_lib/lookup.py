"""Bounded repository lookup backed by the host's ripgrep executable."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any

from .result import Result

MODES = ("files", "text")
PATTERN_MODES = ("literal", "regex")


def _find_rg(root: Path) -> str | None:
    """Resolve PATH entries relative to the requested repository root."""
    for entry in os.get_exec_path():
        folder = Path(entry.strip('"'))
        folder = folder if folder.is_absolute() else root / folder
        for name in ("rg", "rg.exe") if os.name == "nt" else ("rg",):
            selected = shutil.which(str(folder / name))
            if selected:
                return str(Path(selected).resolve())
    return None


def _base_data(root: Path, query: str, mode: str, pattern_mode: str,
               max_results: int, context_lines: int) -> dict[str, Any]:
    return {"root": str(root), "query": query, "mode": mode,
            "pattern_mode": pattern_mode, "max_results": max_results,
            "context_lines": context_lines, "matches": [],
            "truncated": False, "outcome": "not-started"}


def _validate(root: str | Path, query: str, mode: str, pattern_mode: str,
              max_results: int, context_lines: int) -> tuple[Path, dict[str, Any]]:
    if not isinstance(query, str) or not query:
        raise ValueError("query must be a non-empty string")
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    if pattern_mode not in PATTERN_MODES:
        raise ValueError(f"pattern_mode must be one of {PATTERN_MODES}")
    if pattern_mode == "regex":
        try:
            re.compile(query)
        except re.error as error:
            raise ValueError(f"query is not a valid regex: {error}") from error
    if type(max_results) is not int or max_results < 1:
        raise ValueError("max_results must be a positive integer")
    if type(context_lines) is not int or context_lines < 0:
        raise ValueError("context_lines must be a non-negative integer")
    resolved = Path(root).expanduser().resolve()
    data = _base_data(resolved, query, mode, pattern_mode, max_results, context_lines)
    if not resolved.is_dir():
        data["outcome"] = "unreadable-root"
        return resolved, data
    try:
        next(resolved.iterdir(), None)
    except OSError:
        data["outcome"] = "unreadable-root"
        return resolved, data
    return resolved, data


def _result(root: Path, data: dict[str, Any], *, status: str, summary: str,
            exit_code: int | None = None, warnings: list[str] | None = None) -> Result:
    return Result(operation="lookup", status=status, summary=summary,
                  data=data, identifiers={"root": str(root)},
                  warnings=warnings or [], exit_code=exit_code)


def _finish_process(process: subprocess.Popen, *, terminate: bool) -> tuple[int | None, bytes]:
    """Close rg pipes on success and on parser errors alike."""
    if terminate and process.poll() is None:
        try:
            process.terminate()
        except OSError:
            try:
                process.kill()
            except OSError:
                pass
    try:
        _, stderr = process.communicate()
    except OSError:
        try:
            process.kill()
        except OSError:
            pass
        _, stderr = process.communicate()
    return process.returncode, stderr


def _text_lookup(rg: str, root: Path, query: str, pattern_mode: str,
                 max_results: int, context_lines: int,
                 data: dict[str, Any]) -> tuple[int | None, list[str]]:
    command = [rg, "--json", "--line-number", "--column", "--color", "never",
               "--context", str(context_lines)]
    if pattern_mode == "literal":
        command.append("--fixed-strings")
    command.extend(["--", query, str(root)])
    warnings: list[str] = []
    rows: dict[tuple[str, int], dict[str, Any]] = {}
    match_count = 0
    process = subprocess.Popen(command, cwd=root, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               shell=False)
    assert process.stdout is not None
    try:
        for raw_line in process.stdout:
            try:
                event = json.loads(raw_line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                warnings.append(f"ripgrep emitted an invalid JSON event ({type(error).__name__})")
                continue
            kind = event.get("type")
            if kind not in ("match", "context"):
                continue
            payload = event.get("data") or {}
            path_data = payload.get("path") or {}
            path_text = path_data.get("text")
            line_number = payload.get("line_number")
            line_data = payload.get("lines") or {}
            excerpt = line_data.get("text", "").rstrip("\r\n")
            if not isinstance(path_text, str) or type(line_number) is not int:
                continue
            try:
                relative = Path(path_text).resolve().relative_to(root).as_posix()
            except ValueError:
                continue
            key = (relative, line_number)
            if kind == "match":
                match_count += 1
                if match_count > max_results:
                    data["truncated"] = True
                    break
            row = {"path": relative, "line": line_number,
                   "kind": kind, "excerpt": excerpt}
            existing = rows.get(key)
            if existing is None or kind == "match":
                rows[key] = row
    finally:
        exit_code, stderr = _finish_process(
            process, terminate=data["truncated"] or sys.exc_info()[0] is not None)
    if stderr:
        warnings.append(stderr.decode("utf-8", errors="replace").strip())
    data["matches"] = sorted(rows.values(), key=lambda row: (row["path"], row["line"],
                                                               0 if row["kind"] == "context" else 1))
    if data["truncated"]:
        warnings.append(f"Results truncated after {max_results} matches")
    return exit_code, warnings


def _files_lookup(rg: str, root: Path, query: str, pattern_mode: str,
                  max_results: int, data: dict[str, Any]) -> tuple[int | None, list[str]]:
    command = [rg, "--files", str(root)]
    matcher = re.compile(query) if pattern_mode == "regex" else None
    warnings: list[str] = []
    process = subprocess.Popen(command, cwd=root, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               shell=False)
    assert process.stdout is not None
    rows: list[dict[str, str]] = []
    try:
        for raw_path in process.stdout:
            path_text = raw_path.decode("utf-8", errors="replace").rstrip("\r\n")
            try:
                relative = Path(path_text).resolve().relative_to(root).as_posix()
            except ValueError:
                continue
            matched = bool(matcher.search(relative)) if matcher else query in relative
            if not matched:
                continue
            rows.append({"path": relative, "kind": "file"})
            if len(rows) > max_results:
                data["truncated"] = True
                break
    finally:
        exit_code, stderr = _finish_process(
            process, terminate=data["truncated"] or sys.exc_info()[0] is not None)
    if stderr:
        warnings.append(stderr.decode("utf-8", errors="replace").strip())
    data["matches"] = rows[:max_results]
    if data["truncated"]:
        warnings.append(f"Results truncated after {max_results} matches")
    return exit_code, warnings


def lookup(root: str | Path, query: str, *, mode: str = "text",
           pattern_mode: str = "literal", max_results: int = 50,
           context_lines: int = 0) -> Result:
    """Return bounded paths and excerpts without dumping whole files."""
    resolved, data = _validate(root, query, mode, pattern_mode, max_results, context_lines)
    if data["outcome"] == "unreadable-root":
        return _result(resolved, data, status="blocked", summary="Repository root is unavailable")
    rg = _find_rg(resolved)
    if rg is None:
        data["outcome"] = "missing-executable"
        return _result(resolved, data, status="blocked", summary="ripgrep executable is unavailable")
    try:
        if mode == "text":
            exit_code, warnings = _text_lookup(rg, resolved, query, pattern_mode,
                                                max_results, context_lines, data)
        else:
            exit_code, warnings = _files_lookup(rg, resolved, query, pattern_mode,
                                                 max_results, data)
    except (OSError, UnicodeError) as error:
        data["outcome"] = "tool-error"
        return _result(resolved, data, status="blocked",
                       summary=f"ripgrep lookup could not complete ({type(error).__name__})",
                       warnings=[str(error)])
    if data["truncated"]:
        data["outcome"] = "truncated"
    elif exit_code == 1:
        data["outcome"] = "no-matches"
    elif exit_code == 0:
        data["outcome"] = "matches"
    else:
        data["outcome"] = "tool-error"
    if data["outcome"] == "tool-error":
        return _result(resolved, data, status="blocked", summary="ripgrep returned an error",
                       exit_code=exit_code, warnings=warnings)
    return _result(resolved, data, status="completed",
                   summary="Repository lookup completed", exit_code=exit_code,
                   warnings=warnings)
