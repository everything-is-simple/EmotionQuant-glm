from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_duckdb_storage_policy_is_single_db_first_across_docs_and_env_example() -> None:
    env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
    system_overview = (PROJECT_ROOT / "docs/system-overview.md").read_text(
        encoding="utf-8"
    )
    data_models = (
        PROJECT_ROOT / "docs/design/data-layer/data-layer-data-models.md"
    ).read_text(encoding="utf-8")

    assert "默认单库" in env_example
    assert "单库优先" in system_overview
    assert "单库优先" in data_models


def test_env_example_includes_full_backtest_fee_parameters() -> None:
    env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "BACKTEST_COMMISSION_RATE=" in env_example
    assert "BACKTEST_STAMP_DUTY_RATE=" in env_example
    assert "BACKTEST_TRANSFER_FEE_RATE=" in env_example
    assert "BACKTEST_MIN_COMMISSION=" in env_example
