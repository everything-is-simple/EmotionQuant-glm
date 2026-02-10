from __future__ import annotations

from typing import Any

from src.config.config import Config


class BaseRepository:
    """数据仓库基类（占位实现）。"""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config.from_env()

    def fetch(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("fetch is not implemented")

    def save_to_database(self, data: Any) -> None:
        raise NotImplementedError("save_to_database is not implemented")

    def save_to_parquet(self, data: Any) -> None:
        raise NotImplementedError("save_to_parquet is not implemented")
