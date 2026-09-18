"""Collect synthetic/local usage records without exporting prompts or logs."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path
import math
import re
from typing import Any

from .result import Result

TOKEN_FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")
SCHEMA_VERSION = 1
MAX_WARNINGS = 12

def _add_warning(warnings: list[str], message: str) -> None:
    if len(warnings) < MAX_WARNINGS:
        warnings.append(message)
    elif len(warnings) == MAX_WARNINGS:
        warnings.append("Additional usage warnings omitted to keep the report bounded")


def _empty_totals(value: int | None = 0) -> dict[str, int | None]:
    return {"responses": value, **{field: value for field in TOKEN_FIELDS}}


def _period(start: str, end: str, utc_offset: float) -> tuple[datetime, datetime, dict[str, Any]]:
    try:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
    except (TypeError, ValueError) as error:
        raise ValueError("start and end must use YYYY-MM-DD") from error
    if start_date > end_date:
        raise ValueError("start must be on or before end")
    if type(utc_offset) not in (int, float) or not math.isfinite(utc_offset) or not -24 < utc_offset < 24:
        raise ValueError("utc_offset must be a finite number between -24 and 24")
    zone = timezone(timedelta(hours=utc_offset))
    start_at = datetime.combine(start_date, time.min, zone)
    end_at = datetime.combine(end_date + timedelta(days=1), time.min, zone)
    return start_at, end_at, {"start": start_at.isoformat(), "end_exclusive": end_at.isoformat(),
                              "inclusive_end_date": end_date.isoformat(), "utc_offset_hours": utc_offset}


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return None if parsed.tzinfo is None else parsed


def _token_value(value: Any) -> int | None:
    if type(value) is int and value >= 0:
        return value
    return None


def _canonical(record: dict[str, Any], source: str, line_number: int) -> tuple[dict[str, Any] | None, str | None]:
    timestamp = _parse_timestamp(record.get("timestamp") or record.get("time") or record.get("created_at"))
    response_id = record.get("response_id") or record.get("responseId") or record.get("id")
    if timestamp is None or not isinstance(response_id, str) or not response_id.strip():
        return None, f"Skipped record without a valid timestamp/response ID ({source}:{line_number})"
    usage = record.get("usage") if isinstance(record.get("usage"), dict) else record
    legacy_names = {"input_tokens": "input", "cached_input_tokens": "cached_input", "output_tokens": "output", "reasoning_output_tokens": "reasoning_output"}
    values = {field: _token_value(usage.get(field, usage.get(legacy_names[field], 0 if field in {"cached_input_tokens", "reasoning_output_tokens"} else None))) for field in TOKEN_FIELDS}
    if any(value is None for value in values.values()):
        return None, f"Skipped record with incomplete token fields ({source}:{line_number})"
    if values["cached_input_tokens"] > values["input_tokens"]:
        warning = f"Cached input exceeds input tokens ({source}:{line_number})"
    elif values["reasoning_output_tokens"] > values["output_tokens"]:
        warning = f"Reasoning output exceeds output tokens ({source}:{line_number})"
    else:
        warning = None
    format_name = str(record.get("format") or ("responses-v1" if "usage" in record else "legacy-v0"))
    automatic = bool(record.get("automatic_approval") or record.get("automaticApproval"))
    return {"timestamp": timestamp, "response_id": response_id.strip(), "format": format_name,
            "automatic_approval": automatic, **values}, warning


def _sources(source: str | Path) -> tuple[list[Path], str | None]:
    path = Path(source).expanduser().resolve()
    if not path.exists():
        return [], "Usage source is unavailable"
    if path.is_file():
        return [path], None
    try:
        files = sorted(path.rglob("*"))
    except OSError:
        return [], "Usage source cannot be read"
    candidates = [item for item in files if item.is_file() and item.suffix.lower() in {".jsonl", ".json", ".log"}]
    return candidates, None if candidates else "No supported usage logs were found"


def _write_report(output: Path, payload: dict[str, Any]) -> tuple[bool, str | None]:
    try:
        output.expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    except OSError as error:
        return False, f"Unable to write usage report ({type(error).__name__})"
    return True, None


def collect_usage(*, source: str | Path, start: str, end: str, utc_offset: float,
                  device: str, output: str | Path, hash_receipts: bool = False) -> Result:
    if not isinstance(device, str) or not device.strip():
        raise ValueError("device must be a non-empty label")
    start_at, end_at, period = _period(start, end, utc_offset)
    output_path = Path(output).expanduser().resolve()
    files, source_error = _sources(source)
    coverage_warnings: list[str] = []
    if source_error:
        data = {"device": device, "period": period, "coverage": {"known": False, "files": 0, "records": 0, "warnings": [source_error]},
                "totals": _empty_totals(None), "automatic_approval": _empty_totals(None),
                "deduplication": {"records_seen": 0, "duplicates_removed": 0, "cross_device_provable": False}}
        result = Result(operation="usage", status="blocked", summary=source_error, data=data,
                        evidence=[str(output_path)], warnings=[source_error])
        written, write_error = _write_report(output_path, result.to_dict())
        if write_error:
            result.warnings.append(write_error)
        return result

    all_records: list[dict[str, Any]] = []
    formats: set[str] = set()
    for file_path in files:
        try:
            document = file_path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as error:
            _add_warning(coverage_warnings, f"Unreadable usage log {file_path.name} ({type(error).__name__})")
            continue
        line_records: list[tuple[int, Any]] = []
        if file_path.suffix.lower() == ".json":
            try:
                parsed_document = json.loads(document)
            except json.JSONDecodeError:
                parsed_document = None
            else:
                if isinstance(parsed_document, dict):
                    line_records = [(1, parsed_document)]
                elif isinstance(parsed_document, list):
                    line_records = [(index, item) for index, item in enumerate(parsed_document, 1)]
                else:
                    _add_warning(coverage_warnings, f"Ignored non-object JSON document {file_path.name}")
                    continue
        if not line_records:
            for line_number, line in enumerate(document.splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    line_records.append((line_number, json.loads(line)))
                except json.JSONDecodeError:
                    _add_warning(coverage_warnings, f"Ignored non-JSON line {file_path.name}:{line_number}")
        for line_number, record in line_records:
            if not isinstance(record, dict):
                _add_warning(coverage_warnings, f"Ignored non-object record {file_path.name}:{line_number}")
                continue
            canonical, warning = _canonical(record, file_path.name, line_number)
            if canonical is None:
                _add_warning(coverage_warnings, warning or f"Ignored record {file_path.name}:{line_number}")
                continue
            all_records.append(canonical)
            formats.add(canonical["format"])
            if warning:
                _add_warning(coverage_warnings, warning)
    if len(formats) > 1:
        _add_warning(coverage_warnings, "Mixed usage log formats detected; coverage may differ by format")
    if not all_records:
        _add_warning(coverage_warnings, "No parseable usage records; coverage is unknown")
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    duplicates_removed = 0
    for record in all_records:
        if record["response_id"] in seen:
            duplicates_removed += 1
            continue
        seen.add(record["response_id"])
        unique.append(record)
    selected = [record for record in unique if start_at <= record["timestamp"] < end_at]
    if not selected:
        _add_warning(coverage_warnings, "No records in the requested period; coverage is unknown")
    normal = [record for record in selected if not record["automatic_approval"]]
    approvals = [record for record in selected if record["automatic_approval"]]

    def totals(records: list[dict[str, Any]]) -> dict[str, int]:
        return {"responses": len(records), **{field: sum(record[field] for record in records) for field in TOKEN_FIELDS}}

    normal_totals = totals(normal) if selected else _empty_totals(None)
    approval_totals = ({"records": len(approvals), **{field: sum(record[field] for record in approvals) for field in TOKEN_FIELDS}}
                       if selected else {"records": None, **{field: None for field in TOKEN_FIELDS}})
    data: dict[str, Any] = {"device": device, "period": period,
                            "coverage": {"known": bool(selected), "partial": bool(coverage_warnings), "files": len(files), "records": len(all_records), "warnings": coverage_warnings},
                            "totals": normal_totals, "automatic_approval": approval_totals,
                            "deduplication": {"records_seen": len(all_records), "duplicates_removed": duplicates_removed, "cross_device_provable": False}}
    if hash_receipts:
        data["response_receipts"] = [hashlib.sha256(record["response_id"].encode("utf-8")).hexdigest() for record in selected]
        data["deduplication"]["response_receipts_hashed"] = True
    result_status = "completed" if selected else "blocked"
    result_summary = "Usage report collected" if selected else "No records in the requested period; coverage is unknown"
    result = Result(operation="usage", status=result_status, summary=result_summary, data=data,
                    evidence=[str(output_path)], warnings=coverage_warnings)
    _, write_error = _write_report(output_path, result.to_dict())
    if write_error:
        result.status = "blocked"
        result.summary = write_error
        result.warnings.append(write_error)
    return result


def _validate_report_period(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Usage report period must be an object")
    start_text = value.get("start")
    end_text = value.get("end_exclusive")
    if not isinstance(start_text, str) or not isinstance(end_text, str):
        raise ValueError("Usage report period requires start and end_exclusive")
    try:
        start = datetime.fromisoformat(start_text.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_text.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("Usage report period timestamps are invalid") from error
    if start.tzinfo is None or end.tzinfo is None or start >= end:
        raise ValueError("Usage report period must be timezone-aware and increasing")
    return value


def _validate_totals(value: Any, *, approval: bool = False) -> dict[str, int]:
    fields = ("records", *TOKEN_FIELDS) if approval else ("responses", *TOKEN_FIELDS)
    if not isinstance(value, dict):
        raise ValueError("Usage report totals must be an object")
    result: dict[str, int] = {}
    for field in fields:
        amount = value.get(field)
        if type(amount) is not int or amount < 0:
            raise ValueError(f"Usage report total {field} must be a non-negative integer")
        result[field] = amount
    return result


def _validate_receipts(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) or re.fullmatch(r"[0-9a-f]{64}", item) is None for item in value):
        raise ValueError("response_receipts must contain lowercase SHA-256 hashes")
    return value


def merge_usage(inputs: list[str | Path], output: str | Path) -> Result:
    if not isinstance(inputs, list) or not inputs:
        raise ValueError("inputs must contain at least one report")
    reports: list[dict[str, Any]] = []
    for item in inputs:
        path = Path(item).expanduser().resolve()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ValueError(f"Unable to read usage report {path} ({type(error).__name__})") from error
        if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION or not isinstance(payload.get("data"), dict):
            raise ValueError(f"Usage report {path} has unsupported schema")
        data = payload["data"]
        _validate_report_period(data.get("period"))
        coverage = data.get("coverage")
        if not isinstance(coverage, dict) or type(coverage.get("known")) is not bool:
            raise ValueError(f"Usage report {path} has invalid coverage")
        if not isinstance(coverage.get("warnings", []), list) or any(not isinstance(item, str) for item in coverage.get("warnings", [])):
            raise ValueError(f"Usage report {path} has invalid coverage warnings")
        _validate_totals(data.get("totals"))
        _validate_totals(data.get("automatic_approval"), approval=True)
        _validate_receipts(data.get("response_receipts"))
        if not isinstance(payload.get("warnings", []), list) or any(not isinstance(item, str) for item in payload.get("warnings", [])):
            raise ValueError(f"Usage report {path} has invalid warnings")
        if coverage.get("known") is not True:
            raise ValueError(f"Usage report {path} has unknown coverage and cannot be merged as zero")
        reports.append(payload)
    periods = [report["data"]["period"] for report in reports]
    if any(period != periods[0] for period in periods[1:]):
        raise ValueError("Usage reports must use the same period")
    totals = _empty_totals(0)
    approvals = {"records": 0, **{field: 0 for field in TOKEN_FIELDS}}
    warnings: list[str] = ["Aggregate reports cannot prove cross-device response deduplication"]
    receipts: set[str] = set()
    duplicate_receipts = 0
    for report in reports:
        data = report["data"]
        coverage = data["coverage"]
        warnings.extend(report.get("warnings", []))
        warnings.extend(coverage.get("warnings", []))
        report_totals = _validate_totals(data["totals"])
        report_approvals = _validate_totals(data["automatic_approval"], approval=True)
        for field in totals:
            totals[field] += report_totals[field]
        for field in approvals:
            approvals[field] += report_approvals[field]
        for receipt in _validate_receipts(data.get("response_receipts")):
            if receipt in receipts:
                duplicate_receipts += 1
            receipts.add(receipt)
    data = {"report_type": "aggregate", "period": periods[0], "devices": len(reports),
            "totals": totals, "automatic_approval": approvals,
            "coverage": {"known": True, "warnings": warnings[1:]},
            "deduplication": {"cross_device_provable": False, "duplicate_receipts_detected": duplicate_receipts}}
    if receipts:
        data["response_receipts"] = sorted(receipts)
    output_path = Path(output).expanduser().resolve()
    result = Result(operation="usage-merge", status="completed", summary="Usage reports merged",
                    data=data, evidence=[str(output_path)], warnings=warnings)
    _, write_error = _write_report(output_path, result.to_dict())
    if write_error:
        result.status = "blocked"
        result.summary = write_error
        result.warnings.append(write_error)
    return result
