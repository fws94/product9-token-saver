---
name: batch-status
description: Use when collecting read-only GitHub pull-request status for several known targets in one repository. Returns bounded rows and preserves pending, unknown and inaccessible states; does not write remotely or create monitors.
---

# Batch pull-request status

Use the deterministic GitHub status helper only after the parent identifies the
exact `OWNER/REPO` and PR numbers. It uses the existing authenticated `gh` CLI;
no token, account, provider or schedule is inferred. GitLab and Linear guidance
is provider-neutral only until an executable adapter is verified.

```text
python scripts/token_saver.py status --provider github --repo OWNER/REPO --prs 11 12 13 --max-concurrency 4
```

The command performs one `gh pr view NUMBER --repo OWNER/REPO --json
number,url,state,statusCheckRollup` per unique number, with a bounded thread
pool. It is read-only: never change the command into `edit`, `comment`, `merge`,
or another write operation. Duplicate input numbers are reported once in input
order. A positive concurrency bound is required by the helper and defaults to 4.

Read `data.rows` in requested order. Each row has the PR identifier, number,
URL, normalized state and a check summary. Check states are `success`, `failure`,
`pending` or `unknown`; an empty or incomplete rollup remains unknown. A row
error is preserved with a bounded kind/message. Permission errors are unknown
access, not proof that the PR does not exist.

Interpret the envelope separately from source state: top-level `completed` means
all targets were read, even when a PR state is CLOSED or its checks failed.
`partial` means at least one target could not be read; `blocked` means the `gh`
executable is unavailable. Do not retry an inaccessible target or create a
scheduled monitor automatically. Return provider errors and substantive status
interpretation to the parent.

See [batch-status behavior](../../docs/batch-status.md) and the [result contract](../../docs/result-contract.md).
