from __future__ import annotations

from typing import Any, Dict


class QualityMonitor:
    """质量监控占位实现。"""

    def check(self) -> Dict[str, Any]:
        raise NotImplementedError("QualityMonitor.check is not implemented")
