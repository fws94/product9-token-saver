# Token Saver

[简体中文](README.zh-CN.md) · [Roadmap](docs/ROADMAP.md) · [Contributing](CONTRIBUTING.md) · [Release package](docs/release.md) · [MIT License](LICENSE)

Small skills and deterministic helpers for more efficient coding-agent workflows.

Token Saver aims to reduce noisy tool output, repeated context and unnecessary model work while keeping results verifiable. Codex is the first development integration; helpers should stay portable where practical.

> **Status: early development.** The development plugin, offline CLI, result contract, captured-output compaction, existing-check runner, repository lookup, batched GitHub status, authorized Luna submission guidance, explicit issue administration and local usage reports, deterministic release packaging and optional RTK measurement guidance are implemented. Remaining runtime operations and skills are planned in [issues #1–#10](https://github.com/fws94/product9-token-saver/issues). There is no published release yet; a development installation with compact-output, run-checks, repo-lookup, batch-status, luna-submit, issue-admin and usage-report skills is available.

## Capabilities and roadmap

| Capability | Intended behavior | Tracking |
| --- | --- | --- |
| Compact output | Implemented: compact captured logs with counts and diagnostic evidence | [#2](https://github.com/fws94/product9-token-saver/issues/2) |
| Run checks | Implemented: execute agreed commands with timeout and recoverable output | [#3](https://github.com/fws94/product9-token-saver/issues/3) |
| Repository lookup | Implemented: return bounded paths, line numbers and excerpts | [#4](https://github.com/fws94/product9-token-saver/issues/4) |
| Batch status | Implemented: collect read-only GitHub PR state and check summaries in one run | [#5](https://github.com/fws94/product9-token-saver/issues/5) |
| Routine operations | Submission and explicit issue administration guidance is implemented | [#6](https://github.com/fws94/product9-token-saver/issues/6), [#7](https://github.com/fws94/product9-token-saver/issues/7) |
| Usage reports | Implemented: collect and merge recorded local device usage with coverage warnings | [#8](https://github.com/fws94/product9-token-saver/issues/8) |
| Release package | Implemented: build a deterministic archive and run cross-platform CI; desktop discovery remains manual | [#9](https://github.com/fws94/product9-token-saver/issues/9) |
| Optional RTK | Detection and measurement guidance only; no adapter is enabled without platform evidence | [#10](https://github.com/fws94/product9-token-saver/issues/10) |

## Principles

- Use deterministic tools for well-defined work and small workers for bounded tasks that benefit from language understanding.
- Preserve the parent agent's model and reasoning settings. Model routing must use capabilities actually supported by the host.
- Keep authentication and model choices configurable. A contributor should not need the maintainer's account, filesystem layout or preferred model.
- Retain the complete evidence behind shortened output. Failed checks and uncertain writes must remain visible.
- Measure the whole task, including workers, handoffs and retries. A shorter command response is not proof of lower account usage.

## Explore and contribute today

Git, Python 3.11 or newer and ripgrep are enough to run the repository checks and
lookup helper. No API key is needed.

```bash
git clone https://github.com/fws94/product9-token-saver.git
cd product9-token-saver
python scripts/check_repository.py
python -m unittest discover -s tests -v
```

On systems where Python is named `python3`, use that command instead. These commands check the repository and helper contract. Try `python scripts/token_saver.py --help` or `python scripts/token_saver.py contract` offline. See the [result contract](docs/result-contract.md) and [development installation/removal](docs/development-install.md). Use `python scripts/token_saver.py compact --input LOG --format test --max-lines 80` for captured output; see [compaction behavior and limits](docs/compact-output.md). Run an existing check with `python scripts/token_saver.py checks --cwd . --timeout 60 -- python -m unittest discover -s tests -v`; see [runner behavior](docs/run-checks.md). Locate repository content with `python scripts/token_saver.py lookup --root . --query needle --mode text --pattern-mode literal`; see [lookup behavior](docs/repo-lookup.md). Collect known PR status with `python scripts/token_saver.py status --provider github --repo OWNER/REPO --prs 1 2`; see [batch status behavior](docs/batch-status.md). Other runtime operations remain planned. Windows CLI compaction, check execution and development installation were tested; desktop UI and other platforms remain unverified.

Start with [CONTRIBUTING.md](CONTRIBUTING.md), then choose a task from the [roadmap](docs/ROADMAP.md). Documentation improvements, reproducible examples, platform checks and measurement feedback are welcome. English and Chinese issues and pull requests are both welcome.

## Project layout

```text
.github/       Issue forms, PR template, ownership and CI
docs/          Roadmap, design direction and measurement rules
scripts/       Repository checks, CLI, result contract, compaction, checks, lookup, status and submission guidance helpers
skills/        compact-output, run-checks, repo-lookup, batch-status, luna-submit, issue-admin and usage-report skills; other skills remain planned
tests/         Tests for repository tooling
```

## Support and maintenance

- Bugs, questions and proposals: [open an issue](https://github.com/fws94/product9-token-saver/issues/new/choose).
- Sensitive security reports: follow [SECURITY.md](SECURITY.md).
- Maintainer responsibilities and review decisions: [GOVERNANCE.md](GOVERNANCE.md).
- Community expectations: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

Released under the [MIT License](LICENSE). Third-party integrations retain their own licenses, service terms and account requirements. This is an independent community project, not an official OpenAI product.
