from dataclasses import dataclass


@dataclass(frozen=True)
class StockBasic:
    ts_code: str
    name: str
    industry: str = ""
    list_date: str = ""


@dataclass(frozen=True)
class TradeCalendar:
    trade_date: str
    is_open: int
    pretrade_date: str = ""
