# Token Saver

[简体中文](README.zh-CN.md) · [Roadmap](docs/ROADMAP.md) · [Contributing](CONTRIBUTING.md) · [MIT License](LICENSE)

Small skills and deterministic helpers for more efficient coding-agent workflows.

Token Saver aims to reduce noisy tool output, repeated context and unnecessary model work while keeping results verifiable. Codex is the first planned integration; helpers should stay portable where practical.

> **Status: early development.** This repository currently contains project documentation, collaboration templates and repository checks. The runtime helpers and installable plugin are planned in [issues #1–#10](https://github.com/fws94/product9-token-saver/issues). There is no installable release yet.

## Planned capabilities

| Capability | Intended behavior | Tracking |
| --- | --- | --- |
| Compact output | Reduce repetitive command output and retain diagnostic evidence | [#2](https://github.com/fws94/product9-token-saver/issues/2) |
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

On systems where Python is named `python3`, use that command instead. These commands check the repository foundation; they do not install or run the planned token-saving features.

Start with [CONTRIBUTING.md](CONTRIBUTING.md), then choose a task from the [roadmap](docs/ROADMAP.md). Documentation improvements, reproducible examples, platform checks and measurement feedback are welcome. English and Chinese issues and pull requests are both welcome.

## Project layout

```text
.github/       Issue forms, PR template, ownership and CI
docs/          Roadmap, design direction and measurement rules
scripts/       Repository checks; runtime helpers will be added through issues
skills/        Reserved for reviewed skills; currently empty
tests/         Tests for repository tooling
```

## Support and maintenance

- Bugs, questions and proposals: [open an issue](https://github.com/fws94/product9-token-saver/issues/new/choose).
- Sensitive security reports: follow [SECURITY.md](SECURITY.md).
- Maintainer responsibilities and review decisions: [GOVERNANCE.md](GOVERNANCE.md).
- Community expectations: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

Released under the [MIT License](LICENSE). Third-party integrations retain their own licenses, service terms and account requirements. This is an independent community project, not an official OpenAI product.
