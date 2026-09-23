# Development installation

This development plugin includes compact-output, run-checks, repo-lookup, batch-status, luna-submit, issue-admin and usage-report skills with standard-library helpers, packaging and submission references.
It adds no MCP servers, hooks or connectors; other runtime skills remain planned.
Authorized submission and issue-write workers default to `gpt-6-luna` at `xhigh`
reasoning when the host supports it. Explicit user model choices take precedence;
the parent task keeps its own model and reasoning settings.
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
python scripts/token_saver.py usage --start 2026-09-01 --end 2026-09-07 --utc-offset 8 --device laptop --input .codex/sessions --output usage-reports/laptop.json
python scripts/token_saver.py usage-merge --inputs usage-reports/laptop.json --output usage-reports/all.json
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
# Build a reviewed archive, then copy its complete public tree.
python scripts/token_saver.py package --plugin-root . --output scratch/token-saver-install.zip
$reviewDir = Join-Path (Get-Location) ('scratch/reviewed-' + [Guid]::NewGuid().ToString('N'))
Expand-Archive -LiteralPath scratch/token-saver-install.zip -DestinationPath $reviewDir
$reviewedSource = Join-Path $reviewDir 'token-saver'
Get-ChildItem -LiteralPath $reviewedSource -Force | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $pluginDestination -Recurse -Force
}
& ./scratch/manifest-validator/Scripts/python.exe "$env:TOKEN_SAVER_PLUGIN_CREATOR/scripts/validate_plugin.py" $pluginDestination
# Continue only if validation succeeded.
$marketplaceName = python "$env:TOKEN_SAVER_PLUGIN_CREATOR/scripts/read_marketplace_name.py"
# Continue only if marketplace-name validation succeeded.
codex plugin add "token-saver@$marketplaceName"
codex plugin list --marketplace $marketplaceName --json
```

The installed folder is `token-saver`, matching the plugin identifier. The source
checkout can have a different name. Copy only the reviewed archive contents; do not
copy local reports, sessions or credentials. Only `scripts/token_saver.py` is the supported entry point.
Start a new Codex task to load changes. From a different directory, verify
the relocated installed CLI through its absolute path:

```powershell
$installedScript = Join-Path $pluginDestination 'scripts/token_saver.py'
python $installedScript --help
python $installedScript contract
python $installedScript lookup --root $pluginDestination --query token_saver --mode files --pattern-mode literal
```

The checkout-only repository tests shown above are not included in the
release archive. Desktop UI visibility should also be checked in the new task;
CLI discovery alone does not prove desktop presentation.

## Update and remove

Build a new archive and copy its complete public tree to the existing installed
source. Validate it, then use plugin-creator's cachebuster rather than editing
marketplace JSON:

```powershell
$pluginDestination = Join-Path $HOME 'plugins/token-saver'
python scripts/token_saver.py package --plugin-root . --output scratch/token-saver-install.zip
$reviewDir = Join-Path (Get-Location) ('scratch/reviewed-' + [Guid]::NewGuid().ToString('N'))
Expand-Archive -LiteralPath scratch/token-saver-install.zip -DestinationPath $reviewDir
$reviewedSource = Join-Path $reviewDir 'token-saver'
Get-ChildItem -LiteralPath $reviewedSource -Force | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $pluginDestination -Recurse -Force
}
& ./scratch/manifest-validator/Scripts/python.exe "$env:TOKEN_SAVER_PLUGIN_CREATOR/scripts/validate_plugin.py" $pluginDestination
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
version `0.1.0-dev.12`, installed and enabled it, then removed the installation and
marketplace. No credentials or network were needed for these local plugin
operations. This was a temporary verification, not a persistent personal install.
Linux/macOS and desktop UI discovery are not claimed verified by this check.
