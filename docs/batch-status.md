# Batch GitHub status

The `status` command performs bounded, read-only pull-request queries through
the existing authenticated GitHub CLI. It does not create monitors, edit PRs,
post comments, merge, install dependencies or select a repair.

```powershell
python scripts/token_saver.py status --provider github --repo OWNER/REPO --prs 11 12 13 --max-concurrency 4
```

`--provider github`, `--repo OWNER/REPO` and one or more positive `--prs`
numbers are required. `--max-concurrency` defaults to 4 and must be positive.
The helper deduplicates PR numbers while preserving their first-seen order, then
issues at most one `gh pr view` query per target. The command requests only
`number,url,state,statusCheckRollup` JSON fields. Results are returned in the
requested order even though queries run concurrently.

## Row and check states

Every readable row contains `identifier`, `number`, `url`, normalized uppercase
`state` (for example OPEN, CLOSED or MERGED) and a `checks` object. Check
`state` is `success` when all reported checks completed with SUCCESS, SKIPPED or
NEUTRAL; `failure` when any conclusion is FAILURE, CANCELLED, TIMED_OUT,
ACTION_REQUIRED or STARTUP_FAILURE; `pending` when a check is not completed; and
`unknown` when no rollup or an unrecognized conclusion is available. Counts for
`total`, `passed`, `failed`, `pending` and `unknown` remain in the object.

An inaccessible target remains a row with `state: UNKNOWN`, an unknown check
summary and `error.kind`. HTTP 401/403, forbidden, permission and inaccessible
messages use `permission`; not-found messages use `not-found`; malformed JSON
uses `invalid-response`; other CLI failures use `provider-error`. Error messages
are bounded to 500 characters. A permission error never means the object is
absent. One or more row errors makes the envelope `status: partial`; all rows
read makes it `completed`.

If `gh` is unavailable, the envelope is `blocked`, `data.outcome` is
`missing-executable`, no remote query is attempted, and the CLI exits 1. An
invalid provider, repository, PR list or concurrency value is a CLI usage error
and exits 2 without JSON. A normal completed query exits 0. Top-level
`exit_code` remains null because this is an aggregate; each `gh` response's
failure is recorded on its row.

The current executable adapter is GitHub only. GitLab and Linear may be queried
through tools available in the target environment by a parent, but this package
does not claim adapters until those environments are verified. The operation is
not a scheduler and does not create a recurring monitor.

Current local verification queried PRs 11, 12 and 13 in
`fws94/product9-token-saver`: all were OPEN with three successful checks. This is
one environment snapshot, not a guarantee about future status or permissions.
