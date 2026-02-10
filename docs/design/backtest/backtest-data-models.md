# Backtest 数据模型

**版本**: v3.4.10（重构版）
**最后更新**: 2026-02-09
**状态**: 设计完成（代码未落地）

---

## 实现状态（仓库现状）

- `src/backtest/` 当前仅有 `__init__.py` 占位；回测引擎与接口尚未落地。
- 本文档为设计口径；实现阶段需以此为准并同步更新记录。

---

## 1. 核心数据结构

### 1.1 BacktestConfig 回测配置

```python
@dataclass
class AShareFeeConfig:
    """A股费率统一配置（共享来源）"""
    commission_rate: float = 0.0003
    stamp_duty_rate: float = 0.001
    transfer_fee_rate: float = 0.00002
    min_commission: float = 5.0

@dataclass
class BacktestConfig:
    """回测配置"""
    # 引擎与模式
    engine_type: str = "qlib"           # qlib/local_vectorized/backtrader_compat
    integration_mode: str = "top_down"  # top_down/bottom_up/dual_verify/complementary

    # 时间范围
    start_date: str                     # 开始日期 YYYYMMDD
    end_date: str                       # 结束日期 YYYYMMDD
    initial_cash: float = 1000000.0     # 初始资金
    risk_free_rate: float = 0.015       # 年化无风险利率（Sharpe/Sortino）

    # 信号筛选
    min_recommendation: str = "BUY"     # 最低推荐等级（仅纳入该等级及以上）；Recommendation: STRONG_BUY > BUY > HOLD > SELL > AVOID
    min_final_score: float = 55.0       # 综合评分下限
    top_n: int = 20                     # 取前N推荐
    min_pas_breadth_ratio: float = 0.03 # BU 活跃度下限（S/A占比）

    # 交易与成本
    order_type: str = "auction"         # auction/limit
    slippage_type: str = "auction"      # auction/fixed/variable
    slippage_value: float = 0.001
    fee_config: AShareFeeConfig = field(default_factory=AShareFeeConfig)

    # 风控与仓位
    max_positions: int = 10
    max_position_pct: float = 0.20      # 与 Trading 全局硬上限口径一致
    max_holding_days: int = 10
    stop_loss_pct: float = 0.08
    take_profit_pct: float = 0.15     # 与 Trading 默认止盈口径一致
```

### 1.2 BacktestSignal 回测信号

```python
@dataclass
class BacktestSignal:
    """回测信号"""
    signal_id: str            # 信号ID（建议: SIG_{signal_date}_{stock_code}）
    signal_date: str          # 信号生成日（收盘后）
    stock_code: str
    stock_name: str
    industry_code: str

    # 集成输出
    final_score: float
    recommendation: str      # STRONG_BUY/BUY/HOLD/SELL/AVOID
    position_size: float     # 建议仓位 0-1
    integration_mode: str    # top_down/bottom_up/dual_verify/complementary

    # 交易参考
    entry: float
    stop: float
    target: float
    risk_reward_ratio: float

    # 追溯信息
    mss_score: float
    irs_score: float
    pas_score: float
    direction: str           # Integration 原始方向 bullish/bearish/neutral（追溯字段，不直接决定买卖）
    neutrality: float        # 0-1
    source: str              # integrated / pas_fallback
```

### 1.3 BacktestTrade 交易记录

```python
@dataclass
class BacktestTrade:
    """回测交易记录"""
    trade_id: str
    signal_date: str          # 信号生成日
    execute_date: str         # 成交执行日（下一交易日）
    signal_id: str            # 对应集成信号ID（追溯键）
    stock_code: str
    stock_name: str
    direction: str           # buy/sell（执行方向）
    order_type: str          # auction/limit

    # 价格
    signal_price: float
    filled_price: float

    # 数量
    shares: int
    amount: float

    # 费用
    commission: float
    slippage: float
    stamp_tax: float
    transfer_fee: float
    total_fee: float

    # 状态
    status: str              # pending/filled/partially_filled/rejected
    filled_time: str
    filled_reason: str

    # 盈亏（卖出时）
    pnl: float
    pnl_pct: float
    hold_days: int

    # 信号追溯
    signal_score: float
    signal_source: str       # integrated / pas_fallback
    integration_mode: str
    recommendation: str
```

### 1.4 Position 持仓

```python
@dataclass
class Position:
    """持仓记录"""
    stock_code: str
    stock_name: str
    industry_code: str
    direction: str = "long"
    shares: int
    cost_price: float
    cost_amount: float
    market_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    buy_date: str
    can_sell_date: str
    is_frozen: bool
    stop_price: float
    target_price: float
    signal_id: str
```

### 1.5 EquityPoint 净值点

```python
@dataclass
class EquityPoint:
    """净值曲线点"""
    trade_date: str
    equity: float
    cash: float
    positions_value: float
    daily_return: float
    cumulative_return: float
    drawdown: float
```

### 1.6 BacktestMetrics 绩效指标

```python
@dataclass
class BacktestMetrics:
    """回测绩效指标"""
    # 收益
    total_return: float
    annual_return: float

    # 风险
    max_drawdown: float
    volatility: float

    # 风险调整收益
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float

    # 交易统计
    total_trades: int
    win_rate: float
    profit_factor: float
    avg_trade: float
    avg_win: float
    avg_loss: float
    max_win: float
    max_loss: float

    # 成交统计
    fill_rate: float
    limit_up_rejected: int
    auction_failed: int
```

### 1.7 BacktestResult 回测结果

```python
@dataclass
class BacktestResult:
    """回测结果"""
    id: int                     # 数据库自增代理键（写入后生成）
    backtest_id: str
    backtest_name: str
    engine_type: str
    integration_mode: str
    start_date: str
    end_date: str
    final_value: float            # 期末权益（通常等于 equity_curve[-1].equity）

    config: BacktestConfig
    trades: List[BacktestTrade]
    equity_curve: List[EquityPoint]
    metrics: BacktestMetrics
    position_summary: Dict        # 仅运行态汇总，不持久化到 backtest_results
```

---

## 2. 数据库表结构

> 口径说明（与 Data Layer 对齐）：
> - Backtest 持久化输出仅包含 `backtest_trade_records` 与 `backtest_results`（Business Tables）。
> - `positions` 在回测中用于运行态快照，不占用交易侧 `positions` 业务表名。
> - 如需持久化回测持仓，请使用 `backtest_positions`（扩展表），避免与 Trading 持仓表冲突。

### 2.1 backtest_trade_records 回测交易记录表

| 字段 | 类型 | 说明 |
|------|------|------|
| trade_id | VARCHAR(50) | 交易ID |
| signal_date | VARCHAR(8) | 信号日期 |
| execute_date | VARCHAR(8) | 成交日期 |
| stock_code | VARCHAR(20) | 股票代码 |
| stock_name | VARCHAR(50) | 股票名称 |
| direction | VARCHAR(10) | buy/sell |
| order_type | VARCHAR(20) | auction/limit |
| signal_price | DECIMAL(12,4) | 信号价格 |
| filled_price | DECIMAL(12,4) | 成交价格 |
| shares | INTEGER | 股数 |
| amount | DECIMAL(16,2) | 金额 |
| commission | DECIMAL(12,2) | 佣金 |
| stamp_tax | DECIMAL(12,2) | 印花税 |
| transfer_fee | DECIMAL(12,4) | 过户费 |
| slippage | DECIMAL(12,4) | 滑点 |
| total_fee | DECIMAL(16,2) | 总费用 |
| status | VARCHAR(20) | 状态 |
| filled_time | VARCHAR(20) | 成交时间 |
| filled_reason | VARCHAR(50) | 成交原因 |
| pnl | DECIMAL(16,2) | 盈亏 |
| pnl_pct | DECIMAL(8,4) | 盈亏比例 |
| hold_days | INTEGER | 持仓天数 |
| signal_score | DECIMAL(8,4) | 信号评分 |
| signal_source | VARCHAR(20) | 信号来源 |
| integration_mode | VARCHAR(20) | 集成模式 |
| recommendation | VARCHAR(20) | 推荐等级 |
| signal_id | VARCHAR(50) | 信号ID |
| created_at | DATETIME | 创建时间 |

**索引**：
- `PRIMARY KEY (trade_id)`
- `INDEX idx_execute_date (execute_date)`
- `INDEX idx_signal_date (signal_date)`
- `INDEX idx_stock (stock_code)`
- `INDEX idx_status (status)`

### 2.2 positions（回测运行态快照，非 Business Tables 持久化表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| stock_code | VARCHAR(20) | 股票代码 (UNIQUE) |
| stock_name | VARCHAR(50) | 股票名称 |
| industry_code | VARCHAR(10) | 行业代码 |
| direction | VARCHAR(10) | 方向 |
| shares | INTEGER | 股数 |
| cost_price | DECIMAL(12,4) | 成本价 |
| cost_amount | DECIMAL(16,2) | 成本金额 |
| market_price | DECIMAL(12,4) | 市价 |
| market_value | DECIMAL(16,2) | 市值 |
| unrealized_pnl | DECIMAL(16,2) | 未实现盈亏 |
| unrealized_pnl_pct | DECIMAL(8,4) | 盈亏比例 |
| buy_date | VARCHAR(8) | 买入日期 |
| can_sell_date | VARCHAR(8) | 可卖日期 |
| is_frozen | BOOLEAN | 是否冻结 |
| stop_price | DECIMAL(12,4) | 止损价 |
| target_price | DECIMAL(12,4) | 目标价 |
| signal_id | VARCHAR(50) | 信号ID |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

**索引**：
- `PRIMARY KEY (id)`
- `UNIQUE (stock_code)`
- `INDEX idx_frozen (is_frozen)`

### 2.3 backtest_results 回测结果表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| backtest_id | VARCHAR(50) | 业务回测ID（唯一） |
| engine_type | VARCHAR(20) | 回测引擎（qlib/local_vectorized/backtrader_compat） |
| integration_mode | VARCHAR(20) | 集成模式 top_down/bottom_up/dual_verify/complementary |
| backtest_name | VARCHAR(100) | 回测名称 |
| start_date | VARCHAR(8) | 开始日期 |
| end_date | VARCHAR(8) | 结束日期 |
| initial_cash | DECIMAL(16,2) | 初始资金 |
| final_value | DECIMAL(16,2) | 最终价值 |
| total_return | DECIMAL(10,4) | 总收益率 |
| annual_return | DECIMAL(10,4) | 年化收益率 |
| max_drawdown | DECIMAL(10,4) | 最大回撤 |
| volatility | DECIMAL(10,4) | 波动率 |
| sharpe_ratio | DECIMAL(10,4) | 夏普比率 |
| sortino_ratio | DECIMAL(10,4) | 索提诺比率 |
| calmar_ratio | DECIMAL(10,4) | 卡玛比率 |
| total_trades | INTEGER | 交易次数 |
| win_rate | DECIMAL(8,4) | 胜率 |
| profit_factor | DECIMAL(10,4) | 盈亏比 |
| avg_trade | DECIMAL(12,4) | 平均盈亏 |
| avg_win | DECIMAL(12,4) | 平均盈利 |
| avg_loss | DECIMAL(12,4) | 平均亏损 |
| max_win | DECIMAL(12,4) | 最大盈利 |
| max_loss | DECIMAL(12,4) | 最大亏损 |
| fill_rate | DECIMAL(8,4) | 成交率 |
| limit_up_rejected | INTEGER | 涨停拒单次数 |
| auction_failed | INTEGER | 集合竞价失败次数 |
| config_params | JSON | 配置参数（含 engine_type / integration_mode） |
| equity_curve | JSON | 净值曲线 |
| trades_detail | JSON | 交易明细（可含 integration_mode） |
| created_at | DATETIME | 创建时间 |

**索引**：
- `PRIMARY KEY (id)`
- `UNIQUE (backtest_id)`
- `INDEX idx_name (backtest_name)`
- `INDEX idx_dates (start_date, end_date)`

---

## 3. 枚举定义

### 3.1 OrderType 订单类型

```python
class OrderType(Enum):
    AUCTION = "auction"  # 集合竞价
    LIMIT = "limit"      # 限价单
```

### 3.2 TradeStatus 交易状态

```python
class TradeStatus(Enum):
    PENDING = "pending"              # 待成交
    FILLED = "filled"                # 已成交
    PARTIALLY_FILLED = "partially_filled"  # 部分成交
    REJECTED = "rejected"            # 被拒绝
```

### 3.3 FilledReason 成交原因

```python
class FilledReason(Enum):
    FILLED = "filled"                # 正常成交
    LIMIT_UP_REJECT = "limit_up_reject"    # 涨停被拒
    LIMIT_DOWN_REJECT = "limit_down_reject"  # 跌停被拒
    AUCTION_FAIL = "auction_fail"    # 竞价未成交
    NO_CASH = "no_cash"              # 资金不足
    MAX_POSITION = "max_position"    # 超持仓上限
```

### 3.4 SignalSource 信号来源

```python
class SignalSource(Enum):
    INTEGRATED = "integrated"     # 三三制集成
    PAS_FALLBACK = "pas_fallback" # 集成缺口回退
```

### 3.5 BacktestMode 回测模式

```python
class BacktestMode(Enum):
    TOP_DOWN = "top_down"
    BOTTOM_UP = "bottom_up"
    DUAL_VERIFY = "dual_verify"
    COMPLEMENTARY = "complementary"
```

### 3.6 EngineType 回测引擎

```python
class EngineType(Enum):
    QLIB = "qlib"
    LOCAL_VECTORIZED = "local_vectorized"
    BACKTRADER_COMPAT = "backtrader_compat"
```

---

## 4. 输入数据依赖

### 4.1 L3 算法输出依赖

| 数据源 | 读取方式 | 用途 | 必需字段 |
|--------|----------|------|----------|
| integrated_recommendation | 直接读取 | 集成信号主输入 | final_score, recommendation, position_size, entry, stop, target, integration_mode, mss_score, irs_score, pas_score, direction |
| pas_breadth_daily | 直接读取（BU） | BU 活跃度门控 | pas_sa_ratio, industry_sa_ratio |
| mss_panorama | 间接获取（经 integrated_recommendation 透传） | 风险上下文追溯 | mss_score（如需温度明细再直连） |
| irs_industry_daily | 间接获取（经 integrated_recommendation 透传） | 行业上下文追溯 | irs_score / industry_code（如需行业明细再直连） |

### 4.2 L1 市场数据依赖

| 数据源 | 用途 | 必需字段 |
|--------|------|----------|
| raw_daily | 行情数据 | open, high, low, close, pct_chg, vol |
| raw_limit_list | 涨跌停 | limit（U/D/Z） |
| raw_trade_cal | 交易日历 | is_open |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.4.10 | 2026-02-09 | 修复 R28：`BacktestResult` dataclass 补齐 `final_value`（与 DDL 对齐）；明确 `position_summary` 为运行态字段，不持久化到 `backtest_results` |
| v3.4.9 | 2026-02-09 | 同步 API 语义：`min_recommendation` 注释改为 Recommendation 枚举的“最低等级门槛”定义（含五级顺序） |
| v3.4.8 | 2026-02-09 | 修复 R20：`BacktestConfig` 费率改为共享 `AShareFeeConfig`；明确 `BacktestSignal.direction` 为追溯字段、`BacktestTrade.direction` 为执行方向；§4.1 区分 L3 依赖“直接读取/间接透传” |
| v3.4.7 | 2026-02-08 | 修复 R16：`BacktestTrade.status` 注释补齐 `partially_filled`，与 `TradeStatus` 枚举一致 |
| v3.4.6 | 2026-02-08 | 修复 R15：`backtest_trade_records.transfer_fee` 精度统一为 `DECIMAL(12,4)`；`BacktestResult` 与 DDL 新增 `backtest_id` 唯一键并保留 `id` 代理主键 |
| v3.4.5 | 2026-02-08 | 修复 R12：Backtest Position 补齐 `industry_code`（dataclass+DDL）；`backtest_results` DDL 补齐 `volatility/fill_rate/limit_up_rejected/auction_failed` |
| v3.4.4 | 2026-02-08 | 修复 R11：Backtest `Position` dataclass 补齐 `direction`（默认 `long`），与 positions DDL/Trading 持仓结构一致 |
| v3.4.3 | 2026-02-08 | 修复 R10：BacktestConfig 增加 `risk_free_rate`（年化 1.5%）用于 Sharpe/Sortino 复现口径 |
| v3.4.2 | 2026-02-07 | 修复 R9：BacktestSignal 补齐 `signal_id` 追溯起点；`take_profit_pct` 从 0.20 对齐 Trading 为 0.15 |
| v3.4.1 | 2026-02-07 | 修复 R8：BacktestConfig `max_position_pct` 同步为 0.20；BacktestTrade 补齐 `signal_id`；positions 表 `signal_id` 改为 `VARCHAR(50)` 与数据类一致 |
| v3.4.0 | 2026-02-07 | 统一引擎字段口径：Qlib 主选，增加 local_vectorized/backtrader_compat 枚举 |
| v3.3.2 | 2026-02-06 | 明确 Backtest 持仓口径：`positions` 为运行态快照；持久化输出仅 backtest_trade_records/backtest_results |
| v3.3.1 | 2026-02-06 | 标注实现状态；引擎口径明确 backtrader 优先，qlib 规划项 |
| v3.3.0 | 2026-02-05 | 增加 signal_date/execute_date 语义；结果表补充引擎与集成模式字段 |
| v3.2.0 | 2026-02-05 | 对齐 Integration 双模式与配置口径；补充 integration_mode 与集成追溯字段 |
| v3.1.0 | 2026-02-05 | 对齐 backtrader/qlib 与双模式：补充引擎/模式字段与信号扩展 |
| v3.0.0 | 2026-01-31 | 重构版：统一数据结构定义 |

---

**关联文档**：
- 算法设计：[backtest-algorithm.md](./backtest-algorithm.md)
- API接口：[backtest-api.md](./backtest-api.md)
- 信息流：[backtest-information-flow.md](./backtest-information-flow.md)
