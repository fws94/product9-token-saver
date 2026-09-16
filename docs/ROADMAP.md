# Roadmap

The linked issues are the source of current task status and acceptance criteria. Entries below describe planned work; none is completed merely by adding this roadmap or the community foundation.

| Task | Scope | Depends on | Priority |
| --- | --- | --- | --- |
| [T01 / #1](https://github.com/fws94/project9-token-saver/issues/1) | Installable plugin and helper result contract | None | P0 |
| [T02 / #2](https://github.com/fws94/project9-token-saver/issues/2) | Deterministic command output compaction | T01 | P0 |
| [T03 / #3](https://github.com/fws94/project9-token-saver/issues/3) | Existing test, build and lint execution | T01, T02 | P0 |
| [T04 / #4](https://github.com/fws94/project9-token-saver/issues/4) | Bounded repository lookup | T01 | P0 |
| [T05 / #5](https://github.com/fws94/project9-token-saver/issues/5) | Batch status; GitHub first | T01 | P0; additional providers P1 |
| [T06 / #6](https://github.com/fws94/project9-token-saver/issues/6) | Submission delegation and continuation | T01 | P0 |
| [T07 / #7](https://github.com/fws94/project9-token-saver/issues/7) | Explicit issue administration | T01, T06 handoff contract | P0 for verified providers |
| [T08 / #8](https://github.com/fws94/project9-token-saver/issues/8) | Token measurement and local device reports | T01 | P0 |
| [T09 / #9](https://github.com/fws94/project9-token-saver/issues/9) | Runtime integration checks and first release | T02–T08 | P0 |
| [T10 / #10](https://github.com/fws94/project9-token-saver/issues/10) | Optional RTK integration after measurement | T02, T08, T09 | P1; optional |

## Suggested contribution order

1. Establish T01's interfaces; then work on T02/T03 and T04. Start T08 early so comparisons have a baseline.
2. Add T05/T06 and then T07. Keep read-only queries separate from authorized writes.
3. Complete T09's runtime and installation acceptance criteria before releasing an installable plugin. Repository documentation checks alone do not satisfy T09.
4. Consider T10 only after representative measurements support the integration.

## Deliberate boundaries

The first version does not require a hosted routing service, centralized credentials, automatic remote access to devices or an autonomous code-repair system. Runtime providers and platforms should be listed as supported only after verification.

The initial task discussions use particular Luna configurations as compatibility examples. Public interfaces must support explicit user choices and must not hardcode the original maintainer's account or directories. See [design direction](design.md), [measurement rules](measurement.md) and the [contribution process](../CONTRIBUTING.md).
