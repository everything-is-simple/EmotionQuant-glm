from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.models.snapshots import IndustrySnapshot, MarketSnapshot


def test_market_snapshot_serializes_created_at() -> None:
    snapshot = MarketSnapshot(trade_date="20260207")
    record = snapshot.to_storage_record()
    assert record["trade_date"] == "20260207"
    assert isinstance(record["created_at"], str)


def test_industry_snapshot_serializes_top5_fields_as_json() -> None:
    snapshot = IndustrySnapshot(
        trade_date="20260207",
        industry_code="801750",
        top5_codes=["000001", "000002"],
        top5_pct_chg=[1.2, 3.4],
    )
    record = snapshot.to_storage_record()
    assert record["top5_codes"] == json.dumps(["000001", "000002"], ensure_ascii=False)
    assert record["top5_pct_chg"] == json.dumps([1.2, 3.4], ensure_ascii=False)
