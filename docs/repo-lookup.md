# Precise repository lookup

`lookup` uses the host's `rg` (ripgrep) executable to return bounded file paths
or text locations. It performs no writes and skips binary content using rg's
default ignore and binary behavior. It does not infer semantic answers, inspect
git history, diagnose matches or edit files.

```powershell
python scripts/token_saver.py lookup --root . --query "needle" --mode text --pattern-mode literal --max-results 20 --context-lines 2
python scripts/token_saver.py lookup --root . --query "src/.*\\.py" --mode files --pattern-mode regex --max-results 50
```

`--root`, `--query`, `--mode`, and `--pattern-mode` are required. `--mode` is
`text` or `files`; `--pattern-mode` is `literal` or `regex`. `--max-results`
must be positive and defaults to 50. `--context-lines` must be non-negative
and defaults to 0. Literal text uses fixed-string matching. Text mode delegates
matching and context selection to rg's JSON output. Files mode enumerates rg's
ignored-aware file list, then applies the explicit literal substring or regex
to repository-relative paths.

Text rows contain a POSIX `path` relative to root, one-based `line`, `kind` of
`match` or `context`, and one-line `excerpt`. File rows contain `path` and
`kind: file`. Rows are stable-sorted by path, line and context before match.
Context rows around overlapping matches are deduplicated. Paths containing
spaces or Unicode remain valid; binary content is not returned.

The result envelope keeps `root`, `query`, mode settings, `matches`, and a
`truncated` flag. At most `max-results` matches or file rows are returned. A
larger matching set stops the rg process after the boundary and returns
`status: completed`, `data.outcome: truncated`, and a warning. `no-matches` is
also `completed` with an empty array. `missing-executable` and `unreadable-root`
are `blocked`; malformed arguments and invalid regexes are invocation errors.
An rg error is blocked with its exit code and stderr warning. CLI exit code is
0 for completed lookup, 1 for blocked lookup and 2 for invalid invocation.

The helper does not materialize an entire file or a full match dump, but rg may
still scan a large repository. Output is bounded; work is not a replacement for
the caller's timeout policy. The full repository root is recorded for local
reproducibility and may contain private paths. Do not publish private roots,
logs or matching contents without authorization.
