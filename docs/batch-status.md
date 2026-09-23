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
`unknown` when no rollup or an unrecognized conclusion is available. Legacy GitHub
`StatusContext` entries use their `state` field: SUCCESS passes, FAILURE/ERROR
fail, and PENDING/EXPECTED remain pending. Counts for
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

## GitLab and Linear through host tools

The packaged `status` CLI accepts only `--provider github`. For GitLab or Linear,
use an already available, authenticated **read-only** host tool. This is an agent
workflow, not a bundled executable adapter or a request to install/connect a
provider. Resolve the exact project or workspace and target identifiers first.
If that identity is unavailable, mark those targets `blocked` and ask the
parent for it rather than guessing a project or workspace. Deduplicate
identifiers in first-seen order; use one bounded batch call if the
host supports it, otherwise at most four concurrent reads. Return one row per
requested target in input order, including errors.

| Provider | Read-only source | Row and check interpretation |
| --- | --- | --- |
| GitLab merge request | Read `GET /projects/:id/merge_requests/:iid` for the explicit project and MR IID. Use its `head_pipeline` only when the provider identifies it as the current MR pipeline. See [GitLab's merge request API](https://docs.gitlab.com/api/merge_requests/). | Keep the MR IID, `web_url`, and provider `state`. Current `head_pipeline.status` maps success to passed, failed/canceled to failed, and running/pending to pending. If the current pipeline is absent, hidden or ambiguous, checks are unknown. `detailed_merge_status` describes mergeability, not a CI check. |
| Linear issue | Read the identified issue with an existing authenticated GraphQL host tool, requesting its identifier, URL and workflow state. See [Linear's GraphQL guide](https://linear.app/developers/graphql). | Keep the issue identifier and workflow state name. Linear issue state is not a CI rollup, so `checks.state` is unknown unless a separately verified tool supplies check evidence. An HTTP 200 response with GraphQL `errors` is not complete success. |

GitLab `:id` is the project ID or URL-encoded path, and `:iid` is scoped to
that project; do not substitute a global MR ID.

Use the same result contract as GitHub: `completed` means every target was read;
`partial` means at least one row could not be read; `blocked` means the requested
provider has no usable authenticated read-only tool. A mixed-provider batch
with any usable read tool and at least one unread target is `partial`, even if
all attempted reads fail; `blocked` applies when no target can be queried. Even when blocked,
return an unknown row for each requested target with
`error.kind: missing-capability`.
Permission failures keep `state: UNKNOWN`, an unknown check summary and
`error.kind: permission`; they never prove the target is absent. Mark `not-found`
only when the provider explicitly establishes absence. If Linear returns data
with a GraphQL `errors` array, keep verified identity/state fields but attach a
bounded row `error.kind: provider-error` and make the envelope `partial`; HTTP
200 alone does not establish a complete row. Preserve pending and unknown
separately. A pipeline list can contain newer reruns for the same source SHA,
and merged-results pipelines can use a temporary merge commit SHA; neither SHA
equality nor an arbitrary old success proves current CI. When the current run
cannot be established, report unknown. See [GitLab merge request pipelines](https://docs.gitlab.com/ci/pipelines/merge_request_pipelines/)
and [merged-results pipelines](https://docs.gitlab.com/ci/pipelines/merged_results_pipelines/). Do not write remotely,
install or enable a connector, retry inaccessible targets, or create a
scheduled monitor.

A 2026-09-17 local snapshot queried PRs 11, 12 and 13 in
`fws94/product9-token-saver`: all were OPEN with three successful checks at
that time. This is not a guarantee about current status or permissions.
