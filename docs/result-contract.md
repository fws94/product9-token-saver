# Helper result contract (version 1)

`python scripts/token_saver.py contract` prints the contract description inside
an example result envelope. It performs no command execution, authentication,
network access or filesystem writes. `--help` describes available commands.
The [compact command](compact-output.md) uses the same envelope for captured-output views.
The [checks command](run-checks.md) records an executed check's actual exit code and duration. The [lookup command](repo-lookup.md) returns bounded paths and excerpts. The [status command](batch-status.md) returns aggregate read-only provider rows. The issue-admin skill uses this envelope for explicit issue writes and read-backs. The usage and usage-merge commands use it for local reports.

Helpers import `Result` from `scripts/token_saver_lib/result.py`. Construct with
keyword arguments and call `to_dict()` or `to_json()` to validate and serialize.
Invalid values raise `TypeError` or `ValueError` at serialization time. The
constructor does not validate; serialization revalidates mutable data.

| Field | Type and meaning |
| --- | --- |
| `schema_version` | Integer `1`, added by the serializer |
| `operation` | Non-empty operation name |
| `status` | One of the five outcomes below |
| `summary` | Non-empty human-readable summary |
| `data` | Operation-specific JSON object; default `{}` |
| `identifiers` | Object mapping non-empty names to non-empty string IDs, URLs or SHAs; default `{}` |
| `evidence` | Array of non-empty full-artifact references; default `[]` |
| `warnings` | Array of non-empty warnings or limitations; default `[]` |
| `exit_code` | Observed child-command integer exit code, including negative codes, or `null` when unavailable/not applicable |
| `duration_ms` | Finite non-negative elapsed milliseconds, or `null` when unknown |

| Status | Meaning |
| --- | --- |
| `completed` | All requested work completed with confirming evidence |
| `failed` | A known failure prevented completion |
| `partial` | Some requested targets/actions completed; others did not |
| `blocked` | A required input, permission or capability was unavailable |
| `uncertain` | The outcome cannot be established, for example a remote write timed out |

The producer chooses the status using operation-specific evidence. The envelope
never infers it from words in output or from a command exit code. A successfully
queried failed check can therefore have `status: completed` and `exit_code: 1`.
An unknown exit code remains `null`, not zero. Do not retry uncertain writes
until their remote state has been reconciled.

All fields are always present. `to_dict()` returns a deep independent snapshot;
`to_json()` returns deterministic JSON with sorted keys, literal Unicode and no
trailing newline. CLI output is UTF-8 JSON followed by one newline. Data must
use ordinary JSON objects with string keys, arrays, strings, booleans, null and
finite numbers. Tuples, arbitrary objects, NaN and infinity are rejected.

Evidence references are supplied by the caller and preserved verbatim. Relative
paths must be interpreted against the operation's explicitly documented working
directory; absolute paths are permitted in private local results. Serialization
does not test file existence or read evidence. Retain the original full artifact,
including distinct errors, whenever a later helper provides a shortened view.

CLI process exit codes are separate from `exit_code` in the result: `0` means a
completed helper operation, `1` is reserved for other operational outcomes, and
`2` means invalid invocation. Usage errors go to stderr without a JSON envelope.
The current `contract` command only returns `0`; no command and unknown commands
return `2`. The `compact` command returns `1` for unreadable or invalid input.
The `checks` command returns `1` for a failed, timed-out, blocked or uncertain check.
Future operations must document their own data fields.

Consumers should reject unsupported schema versions and tolerate additional
object fields in version 1. Breaking envelope changes require a new version.

## Public and private files

Source code, synthetic tests, metadata and documentation belong in Git. Full
logs, real conversations, usage reports, response receipts, credentials and local
installation state do not. Use ignored `reports/`, `usage-reports/`, `receipts/`
or `scratch/` for local artifacts. Ignore rules are not a redaction mechanism:
review new files before staging, and never embed private data into fixtures.
