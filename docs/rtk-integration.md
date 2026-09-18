# Optional RTK integration

RTK (Rust Token Killer) is optional. Token Saver's built-in compactor and check
runner remain the default and work when RTK is absent. This repository does not
install RTK, change PATH, run `rtk init`, or claim a transparent RTK adapter.

## Verification snapshot

On 2026-09-17, the development host had no `rtk` executable on PATH. The RTK
project documents a Codex CLI integration and lists native Windows limitations;
its open Windows support issue discusses safe hook syntax and command invocation.
Packaged Windows hosts also have reported restrictions around bundled `rg` and
RTK analytics storage. Treat those as platform conditions to verify, not as a
guaranteed Token Saver capability. See the [RTK supported agents guide](https://github.com/rtk-ai/rtk/blob/develop/docs/guide/getting-started/supported-agents.md),
[RTK installation guide](https://github.com/rtk-ai/rtk/blob/develop/docs/guide/getting-started/installation.md),
[native Windows Codex issue](https://github.com/rtk-ai/rtk/issues/1864) and
[packaged-host issue](https://github.com/rtk-ai/rtk/issues/1577).

## Detect without installing

Detection is a read-only preflight. On PowerShell use `Get-Command rtk`; in a
helper use `shutil.which("rtk")`. If no executable is found, continue with the
built-in commands and report RTK as unavailable. If one is found, record
`rtk --version` from the selected environment before comparing behavior. Do not
run `rtk init`, modify Codex hooks, install packages, or change the user's
configuration automatically. A user can explicitly choose and configure RTK
outside this repository, then supply the tested executable path.

## Safe comparison

Compare equivalent synthetic and real-authorized tasks with the same revision,
model, reasoning setting, repository, cache state and timeout. Capture raw
stdout/stderr and the Token Saver result separately. Report output bytes/lines,
recorded usage, task success, repair rate, elapsed time and retries. Include
parent and worker overhead. A shorter RTK view is not proof of token, cost or
subscription savings.

When RTK is selected, keep the original command and complete artifact available.
If RTK fails, returns an unknown format, or hides a diagnostic, fall back to the
built-in compactor and preserve the raw artifact. Never mark the original check
successful from a compacted view. Provider-specific tests belong in a separate
verified environment; no RTK adapter tests are claimed here.

## Current decision

The current release documents RTK detection and measurement only. No adapter is
enabled because this Windows/Codex host has no installed RTK and native packaged
host behavior is not verified. Revisit this decision after a representative
comparison demonstrates retained diagnostics and task outcomes on the target
platform.
