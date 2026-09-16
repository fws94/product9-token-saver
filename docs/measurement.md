# Measuring efficiency

No account-wide savings percentage has been established for this repository. Report results for the task and environment actually measured.

## Distinct metrics

| Metric | What it measures | What it does not establish |
| --- | --- | --- |
| Output bytes/lines | Deterministic reduction in a command's displayed output | Exact model tokens or account allowance |
| Tokenizer estimate | Tokens estimated with a named tokenizer and version | The provider's measured request usage |
| Recorded token usage | Input, cached input and output reported in available records | Complete account or cross-device coverage |
| Credits/cost/allowance | A provider-specific accounting measure | A fixed conversion from raw total tokens |

Cached input is part of input tokens; reasoning output is generally reported as part of output. Follow the actual provider schema and do not add subsets a second time.

## Comparing a change

- Keep task, repository revision, intended outcome and verification comparable.
- Record model, reasoning setting, tool versions and whether the cache is cold or warm.
- Count parent and worker usage, coordination and retries; deduplicate repeated response records before selecting the reporting period.
- Repeat a small representative set of tasks. Report sample size, variability, failures and rework along with any mean reduction.
- Preserve exit codes, diagnostic quality and task completion. A smaller but unusable result is a regression.
- Separate measured fields from estimates. Missing devices or deleted logs are unknown coverage, not zero usage.

For positive baselines, reduction is `(baseline - candidate) / baseline`. Negative values mean the candidate used more. A zero baseline has no meaningful percentage reduction.

## Sharing evidence

Publish only synthetic fixtures or aggregated, anonymized reports that you are authorized to share. Do not publish raw conversations, private repository paths, credentials or complete device logs. If reports from multiple devices cannot be deduplicated, state that limitation instead of presenting an exact combined total.
