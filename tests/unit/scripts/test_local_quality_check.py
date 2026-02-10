from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.quality.local_quality_check import (
    SELF_FILE,
    find_hardcoded_paths,
    iter_scan_files,
)


def test_shebang_is_ignored(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("#!/usr/bin/env python3\nprint('ok')\n", encoding="utf-8")
    assert find_hardcoded_paths(target) == []


def test_windows_path_literal_is_detected(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text('p = "C:\\\\data\\\\cache"\n', encoding="utf-8")
    hits = find_hardcoded_paths(target)
    assert len(hits) == 1


def test_scan_files_excludes_env_and_self() -> None:
    files = list(iter_scan_files())
    assert SELF_FILE not in files
    assert not any(p.name == ".env" for p in files)
    assert not any("tests" in p.parts for p in files)
    assert any(p.name == ".env.example" for p in files)
