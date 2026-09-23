"""Deterministic, evidence-preserving views of already captured UTF-8 output."""
from dataclasses import dataclass
from pathlib import Path
import re

from .result import Result

FORMATS = ("generic", "git-status", "test")
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
DIAGNOSTIC = re.compile(
    r"\b(?:errors?|err|fail(?:ed|ure|ures|s)?|warn(?:ing)?s?|fatal|panic|traceback|"
    r"exceptions?|timeout|timed out|exit(?:ed)?(?:\s+with)?(?:\s+(?:code|status))?)\b"
    r"|\b\w*(?:Error|Exception)\b|^(?:E\s|not ok\b|CONFLICT\b)", re.IGNORECASE)
NOISE = re.compile(
    r"^(?:PASS(?:ED)?\b|ok\b|test\S*.*\.\.\. ok$|"
    r"(?:progress|download(?:ing)?|build(?:ing)?)[: ]+\d+(?:/\d+|%)|"
    r"\[\d+/\d+\])", re.IGNORECASE)


@dataclass
class _Record:
    text: str
    count: int
    diagnostic: bool


def _records(lines: list[str], format: str) -> list[_Record]:
    plain = [ANSI.sub("", line).lstrip("\ufeff") for line in lines]
    diagnostic = [bool(DIAGNOSTIC.search(line)) for line in plain]
    noise = [bool(NOISE.search(line)) and not important
             for line, important in zip(plain, diagnostic)]
    # Protect entire contiguous diagnostic blocks, including stack-frame context.
    # Known progress/success lines and blank lines delimit blocks.
    protected = diagnostic[:]
    block: list[int] = []
    def protect_block():
        if any(diagnostic[index] for index in block):
            for index in block:
                protected[index] = True
        block.clear()
    for index, line in enumerate(plain):
        if not line.strip() or noise[index]:
            protect_block()
        else:
            block.append(index)
    protect_block()
    records = []
    index = 0
    while index < len(lines):
        end = index + 1
        while end < len(lines) and lines[end] == lines[index]:
            end += 1
        count = end - index
        if count > 1:
            records.append(_Record(f"{lines[index]} [repeated {count} times]", count,
                                   any(protected[index:end])))
        elif format != "git-status" and noise[index]:
            while end < len(lines) and noise[end]:
                end += 1
            count = end - index
            text = lines[index] if count == 1 else f"[collapsed {count} progress/success lines]"
            records.append(_Record(text, count, False))
        else:
            records.append(_Record(lines[index], 1, protected[index]))
        index = end
    return records


def compact_file(input_path: str | Path, *, format: str = "generic",
                 max_lines: int = 80, raw: bool = False) -> Result:
    """Read one artifact; never execute its text or overwrite the input.

    The line budget is soft for recognized diagnostic blocks and ignored by raw.
    Unknown formats use a bounded generic excerpt with an explicit warning.
    """
    if type(max_lines) is not int or max_lines < 1:
        raise ValueError("max_lines must be a positive integer")
    source = Path(input_path).resolve()
    evidence = [str(source)]
    try:
        content = source.read_bytes()
    except OSError as error:
        return Result(operation="compact", status="blocked",
                      summary=f"Cannot read input artifact ({type(error).__name__})",
                      evidence=evidence)
    try:
        original = content.decode("utf-8")
    except UnicodeDecodeError:
        return Result(operation="compact", status="failed",
                      summary="Input artifact is not valid UTF-8; raw bytes remain at the evidence path",
                      evidence=evidence)
    lines = original.splitlines()
    warnings = []
    selected_format = format if format in FORMATS else "generic"
    if selected_format != format:
        warnings.append(f"Unknown format {format!r}; using a generic excerpt")
    omitted = collapsed = 0
    if raw:
        text = original
    else:
        records = _records(lines, selected_format)
        selected = set(range(len(records)))
        if len(records) > max_lines:
            selected = {index for index, record in enumerate(records) if record.diagnostic}
            # Reserve one line for the explicit omission notice. Fill remaining
            # slots alternately from the head and tail without disturbing order.
            slots = max(0, max_lines - 1 - len(selected))
            head, tail = 0, len(records) - 1
            while slots and head <= tail:
                for index in (head, tail):
                    if slots and index not in selected:
                        selected.add(index)
                        slots -= 1
                head += 1
                tail -= 1
        chosen = [record for index, record in enumerate(records) if index in selected]
        omitted = len(lines) - sum(record.count for record in chosen)
        collapsed = sum(record.count - 1 for record in chosen)
        view = [record.text for record in chosen]
        if omitted:
            view.append(f"[omitted {omitted} input lines; full log: {source}]")
        text = "\n".join(view) + ("\n" if view else "")
    after_lines = len(text.splitlines())
    budget_exceeded = not raw and after_lines > max_lines
    if budget_exceeded:
        warnings.append("Line budget exceeded to preserve diagnostic blocks; use the full log for evidence")
    return Result(
        operation="compact", status="completed", summary="Captured output view prepared",
        evidence=evidence, warnings=warnings,
        data={"text": text, "format": selected_format, "requested_format": format,
              "raw": raw, "max_lines": max_lines, "budget_exceeded": budget_exceeded,
              "omitted_lines": omitted, "collapsed_lines": collapsed,
              "before": {"bytes": len(content), "lines": len(lines)},
              "after": {"bytes": len(text.encode("utf-8")), "lines": after_lines}})
