---
name: issue-admin
description: Use when a user explicitly requests a read-only issue lookup or a narrowly scoped title, description, label, assignee, status or comment update on an identified issue.
---

# Explicit issue administration

This skill handles identified issue fields and explicitly requested comments only. It is separate from the
`luna-submit` skill: read-only lookups use a direct authenticated provider tool;
authorized writes use one `gpt-6-luna` worker at `xhigh` while the parent keeps
its own model settings.

## Before a write

1. Resolve the provider, repository/project and exact issue identifier. Read the
   current issue and the provider's allowed fields/states.
2. Build a packet naming exactly one requested field or comment and its value, excluded fields,
   current state, repository rules, evidence requirements and
   `delegation_depth: 0`. Group related fields only when the user explicitly
   names them together. Do not infer a title, label, assignee, state or
   completion from CI, tests or unrelated issue activity.
3. For a description request, send only the description body. For a comment request, send only the exact comment body and no field changes. For title, label,
   assignee or status, send only that field. Preserve all other fields.
4. If an assignee name has multiple matches, show stable account identifiers
   and ask the parent for a choice. If a requested state is unavailable or
   ambiguous, show the provider's choices and ask. A missing connector or
   unsupported write is `blocked`; do not install tools or substitute a label.

## Read-back and uncertain writes

Use one writer for an issue. After a write, read back only the requested field
and the issue identifier. A matching field is `completed`; an inaccessible
target with other targets confirmed is `partial`. A timeout or ambiguous result
requires a read-back by content, author and timing before retry. If the original
write cannot be reconciled, return `uncertain` and do not create a duplicate
comment or issue. The worker must not spawn another submission worker.

Return the shared [worker packet](../../references/worker-handoff.md) with the
provider action, requested field or comment, read-back evidence, status and remaining
question. Keep response fields bounded and preserve permission errors as
permission errors; they do not prove an issue is absent. The default write
effort is `xhigh`; a later low-effort comparison requires an explicit preference
change and is never implicit.

Do not schedule monitors or infer completion. Return semantic diagnosis,
provider-specific state mapping and unresolved choices to the parent.
