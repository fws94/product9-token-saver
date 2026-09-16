# T01 implementation plan

Approved scope: issue #1 and the design confirmed in conversation.

Goal: provide the plugin manifest, offline CLI and version 1 result contract.
Architecture: a Python 3.11+ standard-library CLI imports a small result module;
Codex loads metadata from .codex-plugin/plugin.json. Later issues add operations.

- [x] Add tests for all five statuses, JSON round trips, evidence and identifiers,
  invalid values, independent result data, offline help and missing command.
- [x] Observe failing tests, then implement Result and the contract CLI command.
- [x] Generate metadata using plugin-creator, validate the final manifest.
- [x] Document the contract, development installation/removal and private data
  boundaries; keep both README status claims aligned.
- [x] Run repository checks, unit tests and diff checks. Verify a relocated
  development installation with an isolated Codex configuration and remove it.

Use completed/failed/partial/blocked/uncertain statuses. Preserve command exit
codes independently of helper process exit status. Evidence paths are explicit
caller-provided references, never guessed; JSON uses UTF-8 and disallows NaN.
No dependencies, account defaults, credential access or network in the CLI.
