# Local usage report format

The usage collector reads one file or a directory of synthetic or authorized
local logs. Supported records are JSON objects with a timestamp, response ID
(`response_id`, `responseId` or `id`) and usage values. A `usage` object uses
`input_tokens`, optional `cached_input_tokens`, `output_tokens` and optional
`reasoning_output_tokens`; missing subset fields are zero. Legacy records may
put these fields at the top level and use `time`, `id`, `input`, `cached_input`
and `output`. Unknown or malformed lines are skipped with bounded warnings; when many lines are skipped, the report states that additional warnings were omitted.

```powershell
python scripts/token_saver.py usage --start 2026-09-01 --end 2026-09-07 --utc-offset 8 --device laptop --input .codex/sessions --output usage-reports/laptop.json
python scripts/token_saver.py usage-merge --inputs usage-reports/laptop.json usage-reports/desktop.json --output usage-reports/all.json
```

`--start` and `--end` are local calendar dates. `--end` is inclusive; the
report writes `period.start` at local midnight and `period.end_exclusive` at
midnight on the following date, both with the requested fixed UTC offset.
`--utc-offset` is a finite number from -24 through 24. `--device` and
`--output` are required. `--input` defaults to `~/.codex/sessions`, and
`--hash-receipts` is opt-in.

## Deduplication and subsets

All valid records are parsed and deduplicated by response ID before date
filtering. A duplicate on another date is still removed before selecting the
period. Normal totals exclude `automatic_approval` records; those are in the
separate `automatic_approval` object. Cached input is a subset of input, and
reasoning output is a subset of output; do not add either field to its parent.
`deduplication.records_seen` and `duplicates_removed` expose the local result.

Device reports set `coverage.known` and include source-file/record counts and
warnings. A missing source returns a blocked result with unknown (`null`)
totals. Mixed `responses-v1` and `legacy-v0` formats remain usable but produce
a mixed-format warning. Hash receipts are SHA-256 values of response IDs and
never include prompts or raw IDs; without trusted provenance they cannot prove
which physical device produced a record.

`usage-merge` accepts schema version 1 device results with identical periods.
It sums known totals and approval subsets, includes all input and coverage
warnings, and reports `devices`. It always sets
`deduplication.cross_device_provable` to false; if receipts are present it only
counts duplicate receipt hashes and does not silently subtract their tokens.
Unknown device totals cannot be merged as zero. Schema or period mismatches are
usage errors (CLI exit 2).

## Measurement limits

This report measures recorded fields in the supplied artifacts. It does not
query account usage, tokenizer counts, cost, credits or subscription allowance.
Use [measurement.md](measurement.md) to compare equivalent tasks with parent
and worker usage, success, repair rate, elapsed time and cache conditions.
Missing logs and unavailable devices are unknown coverage, not zero. Never
commit real logs, prompts, response IDs, credentials or personal paths; use
ignored `usage-reports/`, `receipts/` and `scratch/` directories for local data.
