#!/usr/bin/env python3
"""
Local quality checks migrated from historical .claude hooks.

Checks:
1) Session status (git branch, dirty tree)
2) Hardcoded absolute path detection in code/config files
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SELF_FILE = Path(__file__).resolve()

# Detect obvious absolute path literals.
WINDOWS_ABS_RE = re.compile(
    r"(?:[\"'](?:[A-Za-z]:[\\/]|\\\\)[^\"']*[\"'])|(?<![\w/])(?:[A-Za-z]:[\\/]|\\\\)[^\s\"'#]+"
)
UNIX_ABS_RE = re.compile(
    r"(?:[\"']/(?:home|usr|var|opt|etc|tmp)/[^\"']*[\"'])|(?<![\w:])/(?:home|usr|var|opt|etc|tmp)/[^\s\"'#]+"
)

SCAN_EXTS = {".py", ".toml", ".yaml", ".yml", ".json", ".ini", ".cfg"}
# Keep scan focused on runtime/config code; test fixtures may intentionally
# embed path literals for detector assertions.
SCAN_DIRS = ("src", "scripts")


def run_cmd(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        args,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout.strip()


def check_session_status() -> int:
    rc_branch, branch = run_cmd(["git", "branch", "--show-current"])
    rc_status, status = run_cmd(["git", "status", "--porcelain"])
    if rc_branch != 0 or rc_status != 0:
        print("[session] unable to read git status")
        return 1

    is_clean = not status
    print(f"[session] branch={branch or 'unknown'} clean={is_clean}")
    return 0


def iter_scan_files() -> Iterable[Path]:
    for rel_dir in SCAN_DIRS:
        root = PROJECT_ROOT / rel_dir
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in SCAN_EXTS:
                if p.resolve() == SELF_FILE:
                    continue
                yield p

    # Include root-level project configs.
    for name in ("pyproject.toml", "requirements.txt", ".env.example"):
        p = PROJECT_ROOT / name
        if p.exists() and p.is_file():
            yield p


def find_hardcoded_paths(path: Path) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return hits

    for lineno, line in enumerate(text.splitlines(), start=1):
        if line.startswith("#!"):
            continue
        # Allow comments in .env.example to show absolute examples.
        if path.name == ".env.example" and line.strip().startswith("#"):
            continue
        if WINDOWS_ABS_RE.search(line) or UNIX_ABS_RE.search(line):
            hits.append((lineno, line.strip()))
    return hits


def check_hardcoded_paths() -> int:
    violations: list[tuple[Path, int, str]] = []
    for f in iter_scan_files():
        for lineno, line in find_hardcoded_paths(f):
            violations.append((f, lineno, line))

    if not violations:
        print("[scan] hardcoded path check passed")
        return 0

    print("[scan] hardcoded path violations found:")
    for f, lineno, line in violations:
        rel = f.relative_to(PROJECT_ROOT)
        print(f"  - {rel}:{lineno}: {line}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local quality checks.")
    parser.add_argument("--session", action="store_true", help="Check git session status")
    parser.add_argument("--scan", action="store_true", help="Scan hardcoded absolute paths")
    args = parser.parse_args()

    if not args.session and not args.scan:
        parser.print_help()
        return 2

    exit_code = 0
    if args.session:
        exit_code = max(exit_code, check_session_status())
    if args.scan:
        exit_code = max(exit_code, check_hardcoded_paths())
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
