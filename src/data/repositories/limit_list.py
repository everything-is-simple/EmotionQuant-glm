from __future__ import annotations

from typing import Any

from .base import BaseRepository


class LimitListRepository(BaseRepository):
    """涨跌停数据仓库（占位实现）。"""

    def fetch(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("LimitListRepository.fetch is not implemented")
