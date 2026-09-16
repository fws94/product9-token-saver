# Compact captured command output

Read an existing UTF-8 artifact and return a JSON result. No subprocess is
executed, input bytes are never changed, and no dependencies or credentials
are needed. `completed` describes preparing the view, not the original command.

```powershell
python scripts/token_saver.py compact --input tests/fixtures/compact/noisy-test.txt --format test --max-lines 6
python scripts/token_saver.py compact --input tests/fixtures/compact/noisy-test.txt --raw
```

`--input` is required. `--format` defaults to `generic`; `test` also collapses
recognized pass/progress runs, while `git-status` limits collapsing to identical
consecutive lines. Generic mode also recognizes common pass/progress runs.
Unknown format names fall back to generic rules and produce a warning.
`--max-lines` defaults to 80 and must be a positive integer. `--raw` ignores the
line budget and returns the complete decoded text, including carriage returns.

The helper collapses consecutive identical lines with occurrence counts. It
recognizes diagnostic markers such as failure, warning, exception, traceback,
conflict and exit information, including ANSI-colored markers. It retains entire
contiguous diagnostic blocks; blank lines and recognized success/progress lines
separate blocks. Other retained lines form a head/tail excerpt, in source order.
An omission notice includes the omitted input-line count and full artifact path.
Diagnostic blocks take priority over the budget, with an explicit warning when
the result exceeds it. This deliberately favors recoverable diagnostic context.

This is deterministic pattern matching, not a parser for every tool or language.
Unrecognized diagnostics can appear only in the full artifact. An artifact can
be arbitrarily large: the file is read into memory, and the line budget does not
bound input bytes, single-line length, raw views or protected diagnostic blocks.
Consult the full log before diagnosing or repairing unfamiliar output.

## Result data

The shared [result envelope](result-contract.md) contains an absolute evidence
path. `exit_code` stays null: command exit evidence is preserved in text without
inventing a subprocess result. A missing/unreadable input returns `blocked`; an
invalid UTF-8 input returns `failed` while preserving the original byte artifact.
Operational non-completion exits 1; argument errors exit 2.

| Field | Meaning |
| --- | --- |
| `text` | Displayed view or raw decoded text |
| `format`, `requested_format` | Applied and requested modes |
| `raw`, `max_lines` | Requested view controls |
| `budget_exceeded` | Protected diagnostics exceeded the non-raw line budget |
| `omitted_lines` | Original lines completely omitted from the displayed view |
| `collapsed_lines` | Redundant lines represented by counts in retained groups |
| `before.bytes`, `before.lines` | Original UTF-8 artifact bytes and logical lines |
| `after.bytes`, `after.lines` | UTF-8 bytes and logical lines in `text` |

Carriage returns delimit logical lines in compact views. Raw views retain their
original characters. Before/after bytes exclude JSON encoding, metadata, prompts,
worker overhead and subsequent use of raw evidence. Small inputs or large
omission notices can increase displayed bytes; reductions are not guaranteed.
No tokenizer estimates or account-savings claims are made.

## Synthetic validation

The fixture contains 100 setup passes, one failure, an exit-code line and 100
cleanup passes. Tests also cover distinct pass lines around a failure, repeated
errors, multiple diagnostic blocks, an unknown-format excerpt, Unicode paths,
carriage returns, an empty file, invalid UTF-8 and missing input. All fixture
contents are synthetic. Windows is verified locally; other platforms await CI.

The synthetic fixture measured 2447 bytes / 202 lines before and 113 bytes / 4
lines after `--format test --max-lines 6`, retaining the failure and exit-code
lines. This is a single deterministic output measurement, not a token or account
allowance measurement.
