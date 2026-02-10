from __future__ import annotations

from typing import Any

from .base import BaseRepository


class StockBasicRepository(BaseRepository):
    """股票基础数据仓库（占位实现）。"""

    def fetch(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("StockBasicRepository.fetch is not implemented")
