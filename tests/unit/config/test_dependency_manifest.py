from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _read_pyproject() -> str:
    return (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_core_dependencies_include_duckdb() -> None:
    content = _read_pyproject()
    assert '"duckdb>=' in content


def test_backtest_optional_dependencies_include_pyqlib() -> None:
    content = _read_pyproject()
    assert "[project.optional-dependencies]" in content
    assert "backtest = [" in content
    assert '"pyqlib>=' in content
