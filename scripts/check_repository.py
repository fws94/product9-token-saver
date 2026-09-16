#!/usr/bin/env python3
"""Check required community files and local Markdown file links, offline.

This is a deliberately small repository check, not a complete Markdown parser.
It checks inline links and reference definitions, not external URLs or anchors.
"""
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

REQUIRED_FILES = (
    "README.md", "README.zh-CN.md", "LICENSE", "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md", "SECURITY.md", "GOVERNANCE.md", "AGENTS.md",
    "docs/ROADMAP.md", "docs/design.md", "docs/measurement.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/ISSUE_TEMPLATE/question.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/PULL_REQUEST_TEMPLATE.md", ".github/CODEOWNERS",
    ".github/workflows/repository-checks.yml",
)
SKIP_DIRECTORIES = {".git", ".venv", "venv", "__pycache__", "node_modules",
                    "reports", "scratch", "build", "dist", ".worktrees"}
INLINE_LINK = re.compile(r'!?\[[^\]\n]*\]\((<[^>\n]+>|[^\s)]+)(?:\s+"[^"\n]*")?\)')
REFERENCE_LINK = re.compile(r'^\s{0,3}\[[^\]\n]+\]:\s*(<[^>\n]+>|\S+)', re.MULTILINE)


def prose_only(text):
    """Exclude fenced blocks and ordinary inline code examples."""
    lines = []
    fence = None
    for line in text.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if marker:
            run = marker.group(1)
            if fence is None:
                fence = run
            elif run[0] == fence[0] and len(run) >= len(fence):
                fence = None
            continue
        if fence is None:
            lines.append(line)
    return re.sub(r"`[^`\n]+`", "", "\n".join(lines))


def check_links(path, root):
    root = root.resolve()
    label = path.relative_to(root).as_posix()
    try:
        text = prose_only(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError) as error:
        return [f"{label}: cannot read as UTF-8 ({type(error).__name__})"]
    errors = []
    destinations = [match.group(1) for pattern in (INLINE_LINK, REFERENCE_LINK)
                    for match in pattern.finditer(text)]
    for destination in destinations:
        destination = destination.strip("<>")
        try:
            parsed = urlsplit(destination)
        except ValueError:
            errors.append(f"{label}: malformed link {destination}")
            continue
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        target = (path.parent / unquote(parsed.path)).resolve()
        if not target.is_relative_to(root):
            errors.append(f"{label}: link outside repository: {destination}")
        elif not target.exists():
            errors.append(f"{label}: missing link target: {destination}")
    return errors


def check_repository(root):
    root = root.resolve()
    errors = [f"Missing required file: {name}" for name in REQUIRED_FILES
              if not (root / name).is_file()]
    for path in sorted(root.rglob("*.md")):
        if not any(part in SKIP_DIRECTORIES for part in path.relative_to(root).parts):
            errors.extend(check_links(path, root))
    return errors


def main():
    errors = check_repository(Path(__file__).resolve().parents[1])
    if errors:
        print("Repository checks failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Repository checks passed: required files and local Markdown targets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
