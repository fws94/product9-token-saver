"""Version 1 JSON result envelope. See docs/result-contract.md."""
from dataclasses import asdict, dataclass, field
import json
import math
from typing import Any

SCHEMA_VERSION = 1
STATUSES = ("completed", "failed", "partial", "blocked", "uncertain")


def _text(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _json_value(value: Any) -> None:
    """Reject lossy coercions as well as non-standard JSON numbers."""
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for item in value:
            _json_value(item)
        return
    if type(value) is dict:
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("JSON object keys must be strings")
            _json_value(item)
        return
    raise ValueError("data must contain only finite JSON values")


@dataclass(kw_only=True)
class Result:
    """Explicit outcome plus recoverable evidence; no filesystem or network IO."""

    operation: str
    status: str
    summary: str
    data: dict[str, Any] = field(default_factory=dict)
    identifiers: dict[str, str] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    exit_code: int | None = None
    duration_ms: float | None = None

    def _validate(self) -> None:
        _text(self.operation, "operation")
        _text(self.summary, "summary")
        if self.status not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}")
        if self.exit_code is not None and type(self.exit_code) is not int:
            raise TypeError("exit_code must be an integer or None")
        if self.duration_ms is not None:
            if (type(self.duration_ms) not in (int, float)
                    or not math.isfinite(self.duration_ms) or self.duration_ms < 0):
                raise ValueError("duration_ms must be finite and non-negative or None")
        for name in ("evidence", "warnings"):
            values = getattr(self, name)
            if not isinstance(values, list):
                raise TypeError(f"{name} must be a list")
            for value in values:
                _text(value, name)
        if not isinstance(self.identifiers, dict):
            raise TypeError("identifiers must be an object")
        for key, value in self.identifiers.items():
            _text(key, "identifier key")
            _text(value, "identifier value")
        if not isinstance(self.data, dict):
            raise TypeError("data must be an object")
        _json_value(self.data)

    def to_dict(self) -> dict[str, Any]:
        """Validate and return an independent snapshot with the schema version."""
        self._validate()
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}

    def to_json(self) -> str:
        """Return deterministic Unicode JSON, without a trailing newline."""
        return json.dumps(self.to_dict(), ensure_ascii=False, allow_nan=False,
                          sort_keys=True, separators=(",", ":"))
