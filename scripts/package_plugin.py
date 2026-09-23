"""Create a deterministic zip artifact from the public plugin tree."""
from __future__ import annotations

import json
import stat
from pathlib import Path
import zipfile


# A reviewed allowlist keeps local, untracked files out of public artifacts.
PUBLIC_PATHS = (
    ".codex-plugin/plugin.json",
    "LICENSE", "README.md", "README.zh-CN.md", "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md", "GOVERNANCE.md", "SECURITY.md",
    "docs/ROADMAP.md", "docs/design.md", "docs/measurement.md",
    "docs/development-install.md", "docs/release.md", "docs/result-contract.md",
    "docs/compact-output.md", "docs/run-checks.md", "docs/repo-lookup.md",
    "docs/batch-status.md", "docs/usage-report.md", "docs/rtk-integration.md",
    "references/worker-handoff.md",
    "scripts/check_repository.py", "scripts/package_plugin.py", "scripts/token_saver.py",
    "scripts/token_saver_lib/__init__.py", "scripts/token_saver_lib/result.py",
    "scripts/token_saver_lib/compact.py", "scripts/token_saver_lib/checks.py",
    "scripts/token_saver_lib/lookup.py", "scripts/token_saver_lib/status.py",
    "scripts/token_saver_lib/usage.py",
    "skills/compact-output/SKILL.md", "skills/run-checks/SKILL.md",
    "skills/repo-lookup/SKILL.md", "skills/batch-status/SKILL.md",
    "skills/luna-submit/SKILL.md", "skills/issue-admin/SKILL.md",
    "skills/usage-report/SKILL.md",
)


def _safe_component(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Plugin manifest must contain a non-empty {field}")
    invalid = set("/\\:\x00<>|\"?*")
    if (value != value.strip() or value in {".", ".."}
            or any(character in invalid or ord(character) < 32 or ord(character) == 127
                   for character in value)):
        raise ValueError(f"Plugin manifest {field} must be a safe path component")
    return value


def _manifest(root: Path) -> tuple[str, str]:
    path = root / ".codex-plugin" / "plugin.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Plugin manifest cannot be read ({type(error).__name__})") from error
    if not isinstance(payload, dict):
        raise ValueError("Plugin manifest must be a JSON object")
    return (_safe_component(payload.get("name"), "name"),
            _safe_component(payload.get("version"), "version"))


def _public_paths(root: Path, *, exclude: Path | None = None) -> list[Path]:
    paths: list[Path] = []
    for relative in PUBLIC_PATHS:
        candidate = root
        for part in Path(relative).parts:
            candidate = candidate / part
            try:
                attributes = candidate.lstat()
            except OSError as error:
                raise ValueError(f"Required public plugin file is missing: {relative}") from error
            reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
            if (candidate.is_symlink()
                    or getattr(attributes, "st_file_attributes", 0) & reparse_flag
                    or not candidate.resolve().is_relative_to(root)):
                raise ValueError(f"Plugin package cannot contain linked path {relative}")
        if not candidate.is_file():
            raise ValueError(f"Required public plugin file is missing: {relative}")
        if exclude is not None and candidate.resolve() == exclude.resolve():
            continue
        paths.append(candidate)
    return sorted(paths, key=lambda item: item.relative_to(root).as_posix())


def package_plugin(plugin_root: str | Path, output: str | Path):
    """Write a reproducible archive and return a small result object."""
    root = Path(plugin_root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("plugin_root must be an existing directory")
    name, version = _manifest(root)
    destination = Path(output).expanduser().resolve()
    if destination.is_dir() or destination.suffix.lower() != ".zip":
        destination = destination / f"{name}-{version}.zip"
    paths = _public_paths(root, exclude=destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in paths:
            relative = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(f"{name}/{relative}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    return type("PackageResult", (), {"path": destination, "name": name, "version": version})()


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Package the public Token Saver plugin tree.")
    parser.add_argument("plugin_root")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        result = package_plugin(args.plugin_root, args.output)
    except ValueError as error:
        parser.error(str(error))
    print(f"Packaged {result.name} {result.version}: {result.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
