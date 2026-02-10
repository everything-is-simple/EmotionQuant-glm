from typing import Any, Dict


class TuShareFetcher:
    """TuShare 数据采集器（占位实现）。"""

    def fetch_with_retry(self, api_name: str, params: Dict[str, Any]) -> Any:
        raise NotImplementedError("TuShareFetcher is not implemented")
