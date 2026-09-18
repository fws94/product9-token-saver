# Submission worker handoff contract

The parent sends one packet to one `gpt-5.6-luna` worker. It is plain task data,
not permission beyond the `authorized_actions` field.

```json
{
  "role": "luna-submit-worker",
  "target": {
    "workspace": "absolute repository/workspace path",
    "remote": "verified remote URL",
    "source_branch": "exact branch",
    "target_branch": "exact branch or null",
    "issue": "issue identifier or null"
  },
  "authorized_actions": ["commit", "push", "create PR"],
  "excluded_actions": ["merge", "auto-merge", "issue comment"],
  "payload": {
    "files": ["repository-relative paths"],
    "summary": "problem and resulting behavior",
    "verification": ["commands and observed results"]
  },
  "rules": ["AGENTS.md and contribution constraints"],
  "evidence_required": ["SHA", "URL", "remote read-back", "CI"],
  "skill_path": "repository-relative or absolute luna-submit skill path",
  "delegation_depth": 0
}
```

The packet must state the model/effort requested by the host (`gpt-5.6-luna`,
`xhigh`) and the configured account/provider choice when relevant. It must not
contain tokens, cookies, credentials, full private logs or a request to broaden
authorization. The worker owns remote writes for the target until it returns.

The worker returns a packet shaped like:

```json
{
  "status": "completed | partial | uncertain | blocked",
  "actions_performed": ["exact writes and read-only checks"],
  "objects": [{"kind": "commit | PR | issue", "id": "...", "url": "...", "sha": "..."}],
  "remote_readback": {"branch": "...", "head": "...", "base": "...", "state": "..."},
  "verification": ["command/result evidence"],
  "remaining": ["unfinished work or blocker"],
  "retries": [{"action": "...", "reason": "remote reconciliation evidence"}]
}
```

`completed` means every requested write has a matching remote read-back. `partial`
means a subset is confirmed and the rest is explicitly listed. `uncertain` means
a write outcome cannot be established; it forbids another retry until the parent
reconciles it. `blocked` means a required tool, model capability, permission or
input is unavailable. A recursive delegation request is always `blocked` at this
boundary.
