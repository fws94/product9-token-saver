# Development installation

This development plugin includes compact-output, run-checks, repo-lookup, batch-status, luna-submit and issue-admin skills with standard-library helpers and submission references.
It adds no MCP servers, hooks or connectors; other runtime skills remain planned.
The checks helper runs only the supplied command; that command has its own requirements.
The offline helper CLI runs directly from the checkout with Python 3.11+ and no
third-party packages or credentials:

```powershell
python scripts/token_saver.py --help
python scripts/token_saver.py contract
python scripts/token_saver.py compact --input tests/fixtures/compact/noisy-test.txt --format test --max-lines 6
python scripts/token_saver.py checks --cwd . --timeout 60 -- python scripts/check_repository.py
python scripts/token_saver.py lookup --root . --query token_saver --mode files --pattern-mode literal --max-results 20
python scripts/token_saver.py status --provider github --repo OWNER/REPO --prs 11 12 13
python -m unittest discover -s tests -v
```

Run commands from the checkout root. The CLI also works via an absolute script
path from another directory. A missing command exits with code 2.

## Personal development installation (Windows PowerShell)

Requirements: Codex CLI with `plugin` commands and the installed plugin-creator
skill. Set `TOKEN_SAVER_PLUGIN_CREATOR` to that skill's directory (the directory
containing its `SKILL.md`). No contributor-specific skill path is required by
this repository. The validator additionally needs PyYAML; install it in a local
virtual environment if your skill runtime does not already provide it:

```powershell
python -m venv scratch/manifest-validator
& ./scratch/manifest-validator/Scripts/python.exe -m pip install PyYAML
& ./scratch/manifest-validator/Scripts/python.exe "$env:TOKEN_SAVER_PLUGIN_CREATOR/scripts/validate_plugin.py" .
```

This is development tooling only; the helper remains standard-library-only.

The following uses plugin-creator's default personal marketplace, discovered
implicitly by Codex. First check that `$HOME/plugins/token-saver` does not already
exist; if it does, inspect it before proceeding and use the update flow below for
an existing installation. Scaffold commands intentionally fail on a collision.

```powershell
python "$env:TOKEN_SAVER_PLUGIN_CREATOR/scripts/create_basic_plugin.py" token-saver --with-skills --with-marketplace
# Continue only if the scaffold command succeeded.
$pluginDestination = Join-Path $HOME 'plugins/token-saver'
Copy-Item -LiteralPath LICENSE -Destination (Join-Path $pluginDestination 'LICENSE')
Copy-Item -LiteralPath .codex-plugin/plugin.json -Destination (Join-Path $pluginDestination '.codex-plugin/plugin.json')
# Keep the repository's script layout in the installed copy.
New-Item -ItemType Directory -Force (Join-Path $pluginDestination 'scripts/token_saver_lib') | Out-Null
Copy-Item -LiteralPath scripts/token_saver.py -Destination (Join-Path $pluginDestination 'scripts/token_saver.py')
Copy-Item -Path scripts/token_saver_lib/*.py -Destination (Join-Path $pluginDestination 'scripts/token_saver_lib')
New-Item -ItemType Directory -Force (Join-Path $pluginDestination 'skills/compact-output'), (Join-Path $pluginDestination 'skills/run-checks'), (Join-Path $pluginDestination 'skills/repo-lookup'), (Join-Path $pluginDestination 'skills/batch-status'), (Join-Path $pluginDestination 'skills/luna-submit'), (Join-Path $pluginDestination 'skills/issue-admin'), (Join-Path $pluginDestination 'references'), (Join-Path $pluginDestination 'docs') | Out-Null
Copy-Item -LiteralPath skills/compact-output/SKILL.md -Destination (Join-Path $pluginDestination 'skills/compact-output/SKILL.md')
Copy-Item -LiteralPath skills/run-checks/SKILL.md -Destination (Join-Path $pluginDestination 'skills/run-checks/SKILL.md')
Copy-Item -LiteralPath skills/repo-lookup/SKILL.md -Destination (Join-Path $pluginDestination 'skills/repo-lookup/SKILL.md')
Copy-Item -LiteralPath skills/batch-status/SKILL.md -Destination (Join-Path $pluginDestination 'skills/batch-status/SKILL.md')
Copy-Item -LiteralPath skills/luna-submit/SKILL.md -Destination (Join-Path $pluginDestination 'skills/luna-submit/SKILL.md')
Copy-Item -LiteralPath skills/issue-admin/SKILL.md -Destination (Join-Path $pluginDestination 'skills/issue-admin/SKILL.md')
Copy-Item -LiteralPath references/worker-handoff.md -Destination (Join-Path $pluginDestination 'references/worker-handoff.md')
Copy-Item -LiteralPath docs/result-contract.md, docs/compact-output.md, docs/run-checks.md, docs/repo-lookup.md, docs/batch-status.md -Destination (Join-Path $pluginDestination 'docs')
$marketplaceName = python "$env:TOKEN_SAVER_PLUGIN_CREATOR/scripts/read_marketplace_name.py"
# Continue only if marketplace-name validation succeeded.
codex plugin add "token-saver@$marketplaceName"
codex plugin list --marketplace $marketplaceName --json
```

The installed folder is `token-saver`, matching the plugin identifier. The source
checkout can have a different name. Copy only the listed public files; do not
copy local reports, sessions or credentials. Only `scripts/token_saver.py` is the supported entry point.
Start a new Codex task to load changes. Desktop UI visibility still needs a
manual check; CLI discovery alone does not prove desktop presentation.

## Update and remove

Copy updated public helper files, skills, linked docs and the manifest to the same installed source,
then use plugin-creator's cachebuster rather than editing marketplace JSON:

```powershell
$marketplaceName = python "$env:TOKEN_SAVER_PLUGIN_CREATOR/scripts/read_marketplace_name.py"
python "$env:TOKEN_SAVER_PLUGIN_CREATOR/scripts/update_plugin_cachebuster.py" $pluginDestination
codex plugin add "token-saver@$marketplaceName"
```

Stop if either validation helper fails. Start a new task after reinstalling.
To remove the installed plugin and cache:

```powershell
codex plugin remove "token-saver@$marketplaceName"
codex plugin list --marketplace $marketplaceName --json
```

The personal marketplace still lists the source as available; uninstalling does
not delete source files or unrelated marketplace entries. Keep the source for
future development. Removing its marketplace entry is a separate action; do not
remove the entire shared personal marketplace to uninstall this plugin.

## Verification scope

Windows with Python 3.11 was exercised for the CLI and tests. A relocated local
marketplace was registered in an isolated Codex configuration: the CLI discovered
version `0.1.0-dev.7`, installed and enabled it, then removed the installation and
marketplace. No credentials or network were needed for these local plugin
operations. This was a temporary verification, not a persistent personal install.
Linux/macOS and desktop UI discovery are not claimed verified by this check.
