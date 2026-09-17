# Existing test, build and lint runner

Run one explicitly selected command using an argument array and `shell=False`.
The caller supplies the working directory and timeout. The helper does not pick
checks, install dependencies, modify source, diagnose failures or retry commands.
It writes artifacts and launches the supplied command; that command can have its
own effects, so this is not a sandbox or a substitute for host authorization.

```powershell
python scripts/token_saver.py checks --cwd . --timeout 60 -- python -m unittest discover -s tests -v
```

Python 3.11+ is required. The check and its dependencies must already be available.
`--cwd` and finite positive `--timeout` seconds are mandatory. The `--` separator
is required so child flags cannot become runner options. A timeout applies to
waiting for the child after process creation; bounded termination cleanup can
add up to six seconds, and artifact compaction runs afterward. It is not a hard
wall-clock deadline for the entire helper invocation.

`--max-lines` defaults to 80 per stream and uses the [compactor](compact-output.md),
including its soft limit for protected diagnostic blocks. `--output-dir` selects
an artifact base directory; relative paths are resolved against the check's cwd.
By default it is `reports/checks` there. Each execution creates a unique
`check-*` directory with `stdout.log` and `stderr.log`, opened as binary files.
Runs never overwrite earlier artifacts. Output is streamed to disk during the
check rather than accumulated in pipes; compaction later reads each stream.
The views do not reconstruct ordering between stdout and stderr.

Arguments are passed separately without shell expansion. Explicit executable
paths are resolved against the check's cwd; bare executable names use the
host's PATH, with relative entries resolved against the check's cwd. The wrapper
working directory is not searched implicitly. On Windows, direct `.bat`/`.cmd` targets (including PATH-resolved
batch files) are blocked to avoid implicit shell parsing. Supply an explicitly
authorized interpreter command when the existing check genuinely needs one.
Stdin is closed, so checks should be non-interactive.

## Outcomes and evidence

| Top-level status / `data.outcome` | Meaning |
| --- | --- |
| `completed` / `passed` | Child exited 0, even if output includes the word error |
| `failed` / `failed` | Child exited nonzero; original exit code is retained |
| `failed` / `timeout` | Deadline elapsed and termination cleanup was confirmed |
| `uncertain` / `timeout` | Deadline elapsed but process-tree cleanup was not confirmed |
| `blocked` / `not-started` | Invalid cwd, artifact creation failure, unsupported batch target or executable launch failure |

The CLI exits 0 for a completed check, 1 for other operational outcomes and 2 for
invalid invocation. Top-level `exit_code` preserves the child's actual exit
code, including termination codes; null means no observed child exit. A timeout
is always distinct from a normal test failure, even if a late race produces an
exit code of 0. `duration_ms` measures spawn/wait/cleanup time, excluding artifact
creation and compaction; it is null when preflight prevented execution.

`data.command`, `cwd` and `timeout_seconds` record the requested invocation.
`timed_out` marks deadline expiry. On timeout, `termination_confirmed` describes
the direct child, while `tree_cleanup_confirmed` describes the cleanup operation;
both fields are null for ordinary completion. `artifacts` maps streams to full
paths. `stdout` and `stderr` contain complete nested compaction results. Top-level
`evidence` and warnings preserve access and problems independently of the views.
A non-UTF-8 stream makes its view fail and adds a warning; the raw bytes and
actual command exit status remain intact.

On Windows timeout cleanup uses `taskkill /PID ... /T /F`, then a bounded fallback
for the direct child. POSIX uses a new session and kills its process group. A
permission error or other unconfirmed cleanup produces `uncertain`; the caller
must inspect remaining processes before considering a retry. Processes which
escape their original tree/session are outside this cleanup guarantee. Commands
should run checks synchronously, not start persistent background services.
Windows tests cover a child process as well as denied tree cleanup. Some host
sandboxes deny `taskkill`; normal Windows permissions were used for the real
process-tree test. POSIX behavior awaits CI and is not locally verified.

Artifacts can contain private output and are not automatically removed or
redacted. Keep them in ignored local directories and never commit real logs or
credentials. Stored byte/line reductions describe output views only; they do not
measure token, cost or account-allowance savings.
