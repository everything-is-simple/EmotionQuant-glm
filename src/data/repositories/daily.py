from __future__ import annotations

from typing import Any

from .base import BaseRepository


class DailyRepository(BaseRepository):
    """日线数据仓库（占位实现）。"""

    def fetch(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("DailyRepository.fetch is not implemented")
