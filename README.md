# Token Saver

[简体中文](README.zh-CN.md) · [Roadmap](docs/ROADMAP.md) · [Contributing](CONTRIBUTING.md) · [MIT License](LICENSE)

Small skills and deterministic helpers for more efficient coding-agent workflows.

Token Saver aims to reduce noisy tool output, repeated context and unnecessary model work while keeping results verifiable. Codex is the first development integration; helpers should stay portable where practical.

> **Status: early development.** The development plugin, offline CLI, result contract and captured-output compaction are implemented. Remaining runtime operations and skills are planned in [issues #1–#10](https://github.com/fws94/product9-token-saver/issues). There is no published release yet; a development installation with the compact-output skill is available.

## Capabilities and roadmap

| Capability | Intended behavior | Tracking |
| --- | --- | --- |
| Compact output | Implemented: compact captured logs with counts and diagnostic evidence | [#2](https://github.com/fws94/product9-token-saver/issues/2) |
| Run checks | Execute existing test, build and lint commands with concise results | [#3](https://github.com/fws94/product9-token-saver/issues/3) |
| Repository lookup | Return relevant paths, line numbers and bounded excerpts | [#4](https://github.com/fws94/product9-token-saver/issues/4) |
| Batch status | Collect PR, CI and issue status with fewer repeated calls | [#5](https://github.com/fws94/product9-token-saver/issues/5) |
| Routine operations | Delegate explicitly authorized submissions and issue updates | [#6](https://github.com/fws94/product9-token-saver/issues/6), [#7](https://github.com/fws94/product9-token-saver/issues/7) |
| Usage reports | Measure recorded input, cached input and output across local reports | [#8](https://github.com/fws94/product9-token-saver/issues/8) |

## Principles

- Use deterministic tools for well-defined work and small workers for bounded tasks that benefit from language understanding.
- Preserve the parent agent's model and reasoning settings. Model routing must use capabilities actually supported by the host.
- Keep authentication and model choices configurable. A contributor should not need the maintainer's account, filesystem layout or preferred model.
- Retain the complete evidence behind shortened output. Failed checks and uncertain writes must remain visible.
- Measure the whole task, including workers, handoffs and retries. A shorter command response is not proof of lower account usage.

## Explore and contribute today

Git and Python 3.11 or newer are enough to run the repository checks. No API key is needed.

```bash
git clone https://github.com/fws94/product9-token-saver.git
cd product9-token-saver
python scripts/check_repository.py
python -m unittest discover -s tests -v
```

On systems where Python is named `python3`, use that command instead. These commands check the repository and helper contract. Try `python scripts/token_saver.py --help` or `python scripts/token_saver.py contract` offline. See the [result contract](docs/result-contract.md) and [development installation/removal](docs/development-install.md). Use `python scripts/token_saver.py compact --input LOG --format test --max-lines 80` for captured output; see [compaction behavior and limits](docs/compact-output.md). Other runtime operations remain planned. Windows CLI compaction and development installation were tested; desktop UI and other platforms remain unverified.

Start with [CONTRIBUTING.md](CONTRIBUTING.md), then choose a task from the [roadmap](docs/ROADMAP.md). Documentation improvements, reproducible examples, platform checks and measurement feedback are welcome. English and Chinese issues and pull requests are both welcome.

## Project layout

```text
.github/       Issue forms, PR template, ownership and CI
docs/          Roadmap, design direction and measurement rules
scripts/       Repository checks, CLI, result contract and compaction helper
skills/        compact-output skill; other skills remain planned
tests/         Tests for repository tooling
```

## Support and maintenance

- Bugs, questions and proposals: [open an issue](https://github.com/fws94/product9-token-saver/issues/new/choose).
- Sensitive security reports: follow [SECURITY.md](SECURITY.md).
- Maintainer responsibilities and review decisions: [GOVERNANCE.md](GOVERNANCE.md).
- Community expectations: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

Released under the [MIT License](LICENSE). Third-party integrations retain their own licenses, service terms and account requirements. This is an independent community project, not an official OpenAI product.
