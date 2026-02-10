from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass(frozen=True)
class MarketSnapshot:
    trade_date: str
    total_stocks: int = 0
    rise_count: int = 0
    fall_count: int = 0
    flat_count: int = 0
    strong_up_count: int = 0
    strong_down_count: int = 0
    limit_up_count: int = 0
    limit_down_count: int = 0
    touched_limit_up: int = 0
    new_100d_high_count: int = 0
    new_100d_low_count: int = 0
    continuous_limit_up_2d: int = 0
    continuous_limit_up_3d_plus: int = 0
    continuous_new_high_2d_plus: int = 0
    high_open_low_close_count: int = 0
    low_open_high_close_count: int = 0
    pct_chg_std: float = 0.0
    amount_volatility: float = 0.0
    yesterday_limit_up_today_avg_pct: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_storage_record(self) -> dict[str, object]:
        return {
            "trade_date": self.trade_date,
            "total_stocks": self.total_stocks,
            "rise_count": self.rise_count,
            "fall_count": self.fall_count,
            "flat_count": self.flat_count,
            "strong_up_count": self.strong_up_count,
            "strong_down_count": self.strong_down_count,
            "limit_up_count": self.limit_up_count,
            "limit_down_count": self.limit_down_count,
            "touched_limit_up": self.touched_limit_up,
            "new_100d_high_count": self.new_100d_high_count,
            "new_100d_low_count": self.new_100d_low_count,
            "continuous_limit_up_2d": self.continuous_limit_up_2d,
            "continuous_limit_up_3d_plus": self.continuous_limit_up_3d_plus,
            "continuous_new_high_2d_plus": self.continuous_new_high_2d_plus,
            "high_open_low_close_count": self.high_open_low_close_count,
            "low_open_high_close_count": self.low_open_high_close_count,
            "pct_chg_std": self.pct_chg_std,
            "amount_volatility": self.amount_volatility,
            "yesterday_limit_up_today_avg_pct": self.yesterday_limit_up_today_avg_pct,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class IndustrySnapshot:
    trade_date: str
    industry_code: str
    industry_name: str = ""
    stock_count: int = 0
    rise_count: int = 0
    fall_count: int = 0
    flat_count: int = 0
    industry_close: float = 0.0
    industry_pct_chg: float = 0.0
    industry_amount: float = 0.0
    industry_turnover: float = 0.0
    industry_pe_ttm: float = 0.0
    industry_pb: float = 0.0
    limit_up_count: int = 0
    limit_down_count: int = 0
    new_100d_high_count: int = 0
    new_100d_low_count: int = 0
    top5_codes: list[str] = field(default_factory=list)
    top5_pct_chg: list[float] = field(default_factory=list)
    top5_limit_up: int = 0
    yesterday_limit_up_today_avg_pct: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_storage_record(self) -> dict[str, object]:
        return {
            "trade_date": self.trade_date,
            "industry_code": self.industry_code,
            "industry_name": self.industry_name,
            "stock_count": self.stock_count,
            "rise_count": self.rise_count,
            "fall_count": self.fall_count,
            "flat_count": self.flat_count,
            "industry_close": self.industry_close,
            "industry_pct_chg": self.industry_pct_chg,
            "industry_amount": self.industry_amount,
            "industry_turnover": self.industry_turnover,
            "industry_pe_ttm": self.industry_pe_ttm,
            "industry_pb": self.industry_pb,
            "limit_up_count": self.limit_up_count,
            "limit_down_count": self.limit_down_count,
            "new_100d_high_count": self.new_100d_high_count,
            "new_100d_low_count": self.new_100d_low_count,
            # Explicit JSON serialization avoids implicit DB-driver conversions.
            "top5_codes": json.dumps(self.top5_codes, ensure_ascii=False),
            "top5_pct_chg": json.dumps(self.top5_pct_chg, ensure_ascii=False),
            "top5_limit_up": self.top5_limit_up,
            "yesterday_limit_up_today_avg_pct": self.yesterday_limit_up_today_avg_pct,
            "created_at": self.created_at.isoformat(),
        }
