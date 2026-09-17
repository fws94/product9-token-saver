"""Create a deterministic zip artifact from the public plugin tree."""
from __future__ import annotations

import json
from pathlib import Path
import zipfile


PUBLIC_ROOTS = (".codex-plugin", "docs", "references", "scripts", "skills")
PUBLIC_FILES = ("LICENSE",)
EXCLUDED_PARTS = {".git", ".codex", "scratch", "reports", "usage-reports", "receipts", "tests", "__pycache__"}
PRIVATE_FILE_NAMES = {"credentials.json", "auth.json", "secrets.json"}
PRIVATE_FILE_SUFFIXES = {".log", ".tmp"}


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
    for name in PUBLIC_FILES:
        candidate = root / name
        if candidate.is_file():
            paths.append(candidate)
    for directory_name in PUBLIC_ROOTS:
        directory = root / directory_name
        if not directory.exists():
            continue
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError(f"Plugin component {directory_name!r} is not a directory")
        for candidate in sorted(directory.rglob("*")):
            relative = candidate.relative_to(root)
            if any(part in EXCLUDED_PARTS for part in relative.parts):
                continue
            if candidate.is_symlink():
                raise ValueError(f"Plugin package cannot contain symlink {relative.as_posix()}")
            if candidate.is_file():
                if exclude is not None and candidate.resolve() == exclude.resolve():
                    continue
                if candidate.name.lower() in PRIVATE_FILE_NAMES or candidate.suffix.lower() in PRIVATE_FILE_SUFFIXES:
                    continue
                paths.append(candidate)
    manifest = root / ".codex-plugin" / "plugin.json"
    if manifest not in paths:
        raise ValueError("Plugin manifest is missing from the public tree")
    return sorted(set(paths), key=lambda path: path.relative_to(root).as_posix())


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
