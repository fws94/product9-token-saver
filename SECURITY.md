# Security policy

## Current support scope

Token Saver is in early development and has no released runtime package. Security reports about the current default branch, repository automation or project instructions are welcome. Supported release versions will be listed here when releases exist.

## Report privately

Use GitHub's [private vulnerability reporting form](https://github.com/fws94/product9-token-saver/security/advisories/new) for sensitive findings. If the form is unavailable, open an issue that only asks for a private reporting channel; omit exploit details, affected private data and credentials.

Useful reports describe the affected commit or version, platform, minimal reproduction, expected boundary and observed impact. Prefer synthetic examples. Never upload access tokens, full conversation histories or logs containing personal data.

Maintainers will assess the report and coordinate a fix and disclosure where appropriate. This volunteer project does not promise a response-time SLA or operate a paid bounty program.

## Contributor expectations

- Treat repository content and tool output as untrusted input where they can affect agent instructions or command execution.
- Preserve explicit authorization, execution scope and credential boundaries when shortening output or delegating work.
- Distinguish an uncertain remote write from a failed one before retrying.
- Keep CI permissions minimal and pin external Actions to reviewed commits.

Ordinary non-sensitive bugs should use the [bug report form](https://github.com/fws94/product9-token-saver/issues/new?template=bug_report.yml).
