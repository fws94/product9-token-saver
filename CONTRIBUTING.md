# Contributing

Thanks for helping make Token Saver useful and maintainable. English and Chinese contributions are welcome. Read the [project status](README.md) before starting; the planned runtime and plugin are not released yet.

## Pick a focused change

1. Check the [roadmap](docs/ROADMAP.md) and existing issues to avoid duplicate work.
2. For an existing task, comment with the part you intend to implement and wait for coordination before doing substantial overlapping work. An issue comment is not an exclusive reservation.
3. For a small documentation or reproducibility improvement, a focused PR is welcome directly. Discuss new dependencies, public interfaces and broad changes in an issue first.

Useful early contributions include clearer docs, synthetic examples, Windows path handling and reproducible measurement cases. Keep one independently reviewable outcome per PR.

## Local setup

Fork the repository if you do not have write access. Clone your fork, create a branch and run:

```bash
python scripts/check_repository.py
python -m unittest discover -s tests -v
git diff --check
```

Use Python 3.11+ (`python3` where appropriate). The current checks have no third-party Python dependencies or account requirements. The repository checker verifies required community files and relative Markdown file links; it does not fetch external URLs or validate heading anchors.

## Implementation expectations

- Keep deterministic helpers small and use explicit inputs, bounded output and recoverable evidence.
- Preserve exit codes, distinct failures, unknown remote outcomes and the original full-log location.
- Use synthetic or carefully anonymized fixtures. Never commit credentials, real conversations, device logs or personal usage reports.
- Keep repository paths relative and make platform requirements explicit. Do not assume one person's GitHub account, model or home directory.
- Use the host's supported delegation API; instructions alone cannot change the running model.
- For a script or bug fix, include a focused test demonstrating meaningful behavior. Documentation-only edits normally need link and content checks, not artificial unit tests.
- Explain new dependencies and platform limitations. Windows is the first target; additional platforms must have evidence before being advertised as supported.

## Skills

A future skill should have a narrow trigger, clear inputs, a bounded execution path and an observable completion condition. Use existing tools for simple operations and batch related work when delegation is worthwhile.

Document the required host tools and supported models/efforts at implementation time. Keep defaults configurable, respect explicit user choices, and return tasks needing substantive judgment to the parent. A submission route does not authorize merging or additional remote actions.

## Pull requests

- Explain the problem and the resulting behavior, link the relevant issue and describe validation.
- Mention known limitations, changed interfaces and any untested platforms.
- Update both READMEs when a user-facing claim or command changes. If you cannot provide a translation, flag that clearly for review.
- PRs may be work in progress. The author remains responsible for understanding and checking AI-assisted contributions.
- Do not close a task merely because its documentation or skeleton was added. Completion requires its acceptance criteria.

By submitting a contribution, you agree that it can be distributed under this project's [MIT License](LICENSE). You retain ownership of your contribution. No separate CLA or DCO sign-off is currently required.

See [GOVERNANCE.md](GOVERNANCE.md) for review and maintainer responsibilities, and [SECURITY.md](SECURITY.md) for sensitive reports.
