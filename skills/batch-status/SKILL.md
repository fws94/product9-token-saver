---
name: batch-status
description: Use when collecting read-only status for several known GitHub pull requests, GitLab merge requests or Linear issues.
---

# Batch status

For GitHub, use the deterministic helper only after the parent identifies the
exact `OWNER/REPO` and PR numbers. It uses the existing authenticated `gh` CLI;
no token, account, provider or schedule is inferred. For GitLab and Linear,
follow the [host-tool route](../../docs/batch-status.md#gitlab-and-linear-through-host-tools)
using tools already available to the parent. The CLI does not accept those
providers; do not claim an executable adapter before a target environment is
verified.

```text
python scripts/token_saver.py status --provider github --repo OWNER/REPO --prs 11 12 13 --max-concurrency 4
```

The command performs one `gh pr view NUMBER --repo OWNER/REPO --json
number,url,state,statusCheckRollup` per unique number, with a bounded thread
pool. It is read-only: never change the command into `edit`, `comment`, `merge`,
or another write operation. Duplicate input numbers are reported once in input
order. A positive concurrency bound is required by the helper and defaults to 4.

Read `data.rows` in requested order. GitHub rows have a PR identifier, number,
URL, normalized state and check summary. For host-tool GitLab/Linear queries,
retain each provider's identifier and state without pretending the GitHub CLI
returned them; use the same row and envelope semantics. Check states are
`success`, `failure`, `pending` or `unknown`; an empty or incomplete rollup remains unknown. A row
error is preserved with a bounded kind/message. Permission errors are unknown
access, not proof that the target does not exist.

Interpret the envelope separately from source state: top-level `completed` means
all targets were read, even when a PR state is CLOSED or its checks failed.
`partial` means at least one target could not be read after a provider tool
was available, even if every attempted read failed; `blocked` means no target
can be queried because the required GitHub CLI or GitLab/Linear host read tool
is unavailable. Do not retry an inaccessible target or create a scheduled
monitor automatically. Return provider errors and substantive status
interpretation to the parent.

See [batch-status behavior](../../docs/batch-status.md) and the [result contract](../../docs/result-contract.md).
