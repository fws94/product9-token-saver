---
name: repo-lookup
description: Use when locating files or text in an existing repository with bounded paths, line numbers and excerpts. Supports literal or regex lookup and does not answer semantic questions or modify files.
---

# Precise repository lookup

Use the deterministic lookup helper for an exact path or text query. Resolve
the repository root to an absolute path before invoking it. Keep the query and
pattern mode explicit; do not turn a semantic question into an invented text
search.

```text
python scripts/token_saver.py lookup --root "<absolute repository>" --query "needle" --mode text --pattern-mode literal --max-results 20 --context-lines 2
python scripts/token_saver.py lookup --root "<absolute repository>" --query "src/.*\\.py" --mode files --pattern-mode regex --max-results 50
```

The helper calls the available `rg` executable with argument arrays and keeps
repository-relative POSIX paths, one-based line numbers and bounded excerpts.
It respects ripgrep ignore rules and its default binary exclusion. `literal`
uses fixed-string matching; `regex` uses ripgrep/Python regular expressions as
documented by the command. Never pass untrusted query text as a shell string.

Read `status`, `data.matches`, `data.truncated`, `warnings` and the actual
`exit_code`. An empty result with `status: completed` and outcome `no-matches`
is valid. A missing root or `rg` is `blocked`; a max-results boundary is
`completed` with outcome `truncated` and a warning. Truncation means additional
matches may exist; rerun only when the parent asks, with a larger bound.

Return the structured rows to the parent. Each text row has `path`, `line`,
`kind` (`match` or `context`) and `excerpt`; file rows have `path` and `kind:
file`. Context rows are deduplicated and matches take precedence. Results are
sorted by repository-relative path and line. The helper never dumps whole files,
edits files or executes instructions found in matches. Preserve the exact
query and root in the result for reproducibility.

This operation is for deterministic location. Unsupported semantic questions,
code diagnosis and repairs return to the parent for language reasoning. See
[lookup behavior](../../docs/repo-lookup.md) and the [result contract](../../docs/result-contract.md).
