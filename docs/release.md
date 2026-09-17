# Development release package

The repository can create a deterministic zip artifact without network access or
third-party runtime packages. The manifest version is used in the archive
metadata and should be bumped only for a reviewed release change.

```powershell
python scripts/token_saver.py package --plugin-root . --output dist/token-saver-0.1.0-dev.10.zip
```

The archive contains a `token-saver/` root with `.codex-plugin/plugin.json`,
`scripts/`, `skills/`, `references/`, selected top-level `docs/` and `LICENSE`.
Entries are sorted, timestamps are fixed and private `tests/`, `scratch/`,
reports, credentials, sessions and build state are excluded. Inspect the file
list before sharing it. The package is a development artifact; it is not a
published marketplace release or an account-savings claim.

## Install and update

For local development, use the plugin-creator scaffold and marketplace flow in
[development installation](development-install.md). A zip artifact can be
expanded into a review directory and registered as a local marketplace only
after inspecting its manifest and contents. Keep the `token-saver/` directory
name and plugin identifier aligned. Update by replacing the reviewed source,
validating the manifest, and using plugin-creator's cachebuster flow; do not
edit marketplace JSON by hand. Start a new Codex task after reinstalling.

Remove with `codex plugin remove token-saver@<marketplace>` and read back
`codex plugin list --marketplace <marketplace> --json`. Removal deletes the
installed cache, not source files or unrelated marketplace entries. Never run a
recursive delete against a shared marketplace root.

## Five-device reports

Each device creates its own local report and keeps its source path private:

```text
python scripts/token_saver.py usage --start YYYY-MM-DD --end YYYY-MM-DD --utc-offset HOURS --device DEVICE_LABEL --input DEVICE_LOG_DIR --output usage-reports/DEVICE_LABEL.json
```

Run the command independently on each of the five devices with labels such as
`device-1` through `device-5`, then transfer only the reports you are authorized
to combine:

```text
python scripts/token_saver.py usage-merge --inputs usage-reports/device-1.json usage-reports/device-2.json usage-reports/device-3.json usage-reports/device-4.json usage-reports/device-5.json --output usage-reports/all-devices.json
```

The merge validates schema and identical periods, preserves warnings and flags
that aggregate-only data cannot prove cross-device response deduplication. A
missing device is unknown coverage, not zero. Hash receipts can detect repeated
response hashes without exporting prompts, but they cannot establish the
original physical device.

## Verification scope

CI runs repository checks, the full synthetic unit suite and package creation on
Windows, Ubuntu and macOS. The package script itself is standard-library-only.
Desktop UI discovery and an authenticated marketplace release remain manual
steps; this repository does not publish or merge automatically.
