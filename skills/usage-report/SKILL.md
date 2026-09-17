---
name: usage-report
description: Use when measuring recorded local usage for an explicit date range or merging device reports while preserving unknown coverage, cached-input subsets and reasoning-output subsets.
---

# Local usage reports

Use the local collector only with an identified log file/directory and device
label. It reads JSONL/JSON/log records; it does not access provider accounts,
estimate missing usage or publish prompts. The input source defaults to
`~/.codex/sessions` only when the parent has not supplied one.

```text
python scripts/token_saver.py usage --start 2026-09-01 --end 2026-09-07 --utc-offset 8 --device laptop --input <log-dir> --output <report.json>
python scripts/token_saver.py usage-merge --inputs laptop.json desktop.json --output all-devices.json
```

The end date is inclusive in the request and is returned as an explicit
half-open interval `[start, end_exclusive)`. Records are deduplicated by
response ID across every source date before that interval is filtered. Cached
input is included within input tokens; reasoning output is included within
output tokens and is reported as a subset. Records marked automatic approval
are counted separately from normal totals.

Read `coverage`, `deduplication`, `totals`, `automatic_approval`, warnings and
the report evidence path. Missing logs, unreadable files and unknown coverage
remain `blocked`/unknown; never render them as zero. Mixed formats produce a
warning. `--hash-receipts` stores SHA-256 response receipts without IDs or
prompts, but receipts cannot prove a physical device or repair cross-device
duplicates.

`usage-merge` validates schema and identical periods, sums known device totals,
retains every warning and sets `cross_device_provable: false`. Aggregate totals
are not evidence of subscription, credit or account savings. Report only
bytes/tokens recorded in the supplied artifacts; unavailable actual usage must
remain unavailable rather than an estimate.

See [usage report behavior](../../docs/usage-report.md), [measurement rules](../../docs/measurement.md)
and the [result contract](../../docs/result-contract.md).
