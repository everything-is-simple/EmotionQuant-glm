from __future__ import annotations

import os
from pathlib import Path

from src.config.config import Config, _resolve_storage_paths


def test_config_uses_default_storage_paths_when_env_missing() -> None:
    tracked_keys = (
        "DATA_PATH",
        "DUCKDB_DIR",
        "PARQUET_PATH",
        "CACHE_PATH",
        "LOG_PATH",
        "BACKTEST_TRANSFER_FEE_RATE",
        "BACKTEST_MIN_COMMISSION",
    )
    backup = {k: os.environ.get(k) for k in tracked_keys}
    try:
        for key in tracked_keys:
            os.environ.pop(key, None)
        cfg = Config.from_env(env_file=None)
    finally:
        for key, value in backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    base = Path.home() / ".emotionquant" / "data"
    assert cfg.data_path == str(base)
    assert cfg.duckdb_dir == str(base / "duckdb")
    assert cfg.parquet_path == str(base / "parquet")
    assert cfg.cache_path == str(base / "cache")
    assert cfg.log_path == str(base / "logs")
    assert cfg.backtest_transfer_fee_rate == 0.00002
    assert cfg.backtest_min_commission == 5.0


def test_resolve_storage_paths_treats_whitespace_as_empty() -> None:
    paths = _resolve_storage_paths("   ", "  ", "\t", "\n", " ")
    base = Path.home() / ".emotionquant" / "data"
    assert paths["data_path"] == str(base)
    assert paths["duckdb_dir"] == str(base / "duckdb")
    assert paths["parquet_path"] == str(base / "parquet")
    assert paths["cache_path"] == str(base / "cache")
    assert paths["log_path"] == str(base / "logs")
