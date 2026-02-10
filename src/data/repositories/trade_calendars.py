from __future__ import annotations

from typing import Any

from .base import BaseRepository


class TradeCalendarsRepository(BaseRepository):
    """交易日历数据仓库（占位实现）。"""

    def fetch(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("TradeCalendarsRepository.fetch is not implemented")
