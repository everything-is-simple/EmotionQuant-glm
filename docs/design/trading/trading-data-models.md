# Trading 数据模型

**版本**: v3.2.6（重构版）
**最后更新**: 2026-02-09
**状态**: 设计完成（代码未落地）

---

## 实现状态（仓库现状）

- `src/trading/` 当前仅有 `__init__.py` 占位；交易/风控实现尚未落地。
- 本文档为设计口径；实现阶段需以此为准并同步更新记录。

---

## 1. 核心数据结构

### 1.1 TradeSignal（交易信号）

```python
@dataclass
class TradeSignal:
    """交易信号（来自集成推荐）"""
    signal_id: str            # 信号ID（建议: SIG_{trade_date}_{stock_code}）
    trade_date: str           # 交易日期 (YYYYMMDD)
    stock_code: str           # 股票代码 (000001)
    stock_name: str           # 股票名称
    industry_code: str        # 行业代码（来自 Integration）
    direction: str            # buy/sell
    source_direction: str     # 原始方向 bullish/bearish/neutral
    source: str               # integrated（当前仅该值；其他来源预留）
    integration_mode: str     # top_down/bottom_up/dual_verify/complementary
    score: float              # final_score 或 opportunity_score [0-100]
    position_size: float      # 建议仓位 [0-1]
    entry: float              # 入场价（对齐 integrated_recommendation）
    stop: float               # 止损价
    target: float             # 目标价
    neutrality: float         # 中性度 [0-1]
    risk_reward_ratio: float  # 风险收益比
    recommendation: str       # 推荐标签（STRONG_BUY/BUY/HOLD/SELL/AVOID）
    mss_score: float          # MSS温度 [0-100]
    irs_score: float          # IRS行业评分 [0-100]
    pas_score: float          # PAS个股评分 [0-100]
```

### 1.2 Order（订单）

```python
@dataclass
class Order:
    """订单"""
    order_id: str             # 订单ID (ORD + date + seq)
    trade_date: str           # 交易日期
    stock_code: str           # 股票代码
    stock_name: str           # 股票名称
    industry_code: str        # 行业代码（由信号透传）
    signal_id: str            # 关联信号ID
    direction: str            # buy/sell
    order_type: str           # auction/market/limit/stop
    price: float              # 委托价格（市价单可为0）
    shares: int               # 委托股数
    amount: float             # 委托金额 = shares × price
    status: str               # pending/submitted/filled/partially_filled/cancelled/rejected
    filled_shares: int        # 成交股数
    filled_price: float       # 成交均价
    filled_amount: float      # 成交金额
    commission: float         # 佣金
    slippage: float           # 滑点
    created_at: datetime      # 创建时间
    filled_at: datetime       # 成交时间（可空）
    # v2.0新增
    position_reduce_ratio: float = 1.0  # 风控降仓系数
```

字段约束：
- `order_id`: 格式 `ORD{YYYYMMDD}{seq:06d}`，例如 `ORD20260131000001`
- `status`: 枚举值 `pending | submitted | filled | partially_filled | cancelled | rejected`
- `order_type`: 枚举值 `auction | market | limit | stop`
- `direction`: 枚举值 `buy | sell`

### 1.3 Position（持仓）

```python
@dataclass
class Position:
    """持仓"""
    stock_code: str           # 股票代码
    stock_name: str           # 股票名称
    direction: str = "long"   # 持仓方向（A股默认 long）
    shares: int               # 持仓股数
    cost_price: float         # 成本价
    cost_amount: float        # 成本金额 = shares × cost_price
    market_price: float       # 当前市价
    market_value: float       # 市值 = shares × market_price
    unrealized_pnl: float     # 未实现盈亏
    unrealized_pnl_pct: float # 未实现盈亏比例
    buy_date: str             # 买入日期
    can_sell_date: str        # 可卖日期（T+1后）
    is_frozen: bool           # 是否冻结（T+1期间）
    signal_id: str            # 关联信号ID
    industry_code: str        # 行业代码
    # 止损止盈
    stop_price: float         # 止损价
    target_price: float       # 目标价
```

### 1.4 TradeRecord（成交记录）

```python
@dataclass
class TradeRecord:
    """成交记录（对齐 data-layer trade_records 表）"""
    trade_id: str             # 成交ID
    trade_date: str           # 交易日期
    stock_code: str           # 股票代码
    stock_name: str           # 股票名称
    industry_code: str        # 行业代码
    direction: str            # buy/sell
    order_type: str           # auction/market/limit/stop
    price: float              # 成交价格
    shares: int               # 成交股数
    amount: float             # 成交金额
    # 费用明细
    commission: float         # 佣金
    stamp_tax: float          # 印花税（仅卖出）
    transfer_fee: float       # 过户费
    slippage: float           # 滑点
    total_fee: float          # 总费用
    # 状态
    status: str               # filled/partially_filled/rejected
    signal_id: str            # 关联信号ID
    # 时间戳
    created_at: datetime
    updated_at: datetime
```

---

## 2. 配置数据结构

### 2.1 TradeConfig（交易配置）

```python
@dataclass
class TradeConfig:
    """交易配置"""
    # 信号门控
    min_final_score: float = 55.0        # final_score 主门槛（与 Integration/Backtest 对齐）
    top_n: int = 20                      # 每日最大推荐数
    # 仓位
    max_position_pct: float = 0.20       # Trading 全局硬上限（不低于 Integration S级20%）
    # 止损止盈
    stop_loss_pct: float = 0.08          # 默认止损比例
    take_profit_pct: float = 0.15        # 默认止盈比例
```

### 2.2 RiskConfig（风控配置）

```python
@dataclass
class RiskConfig:
    """风控配置"""
    max_position_ratio: float = 0.20     # 单股最大仓位20%
    max_industry_ratio: float = 0.30     # 行业最大仓位30%
    max_total_position: float = 0.80     # 总仓位上限80%
    stop_loss_ratio: float = 0.08        # 止损线8%
    max_drawdown_limit: float = 0.15     # 最大回撤限制15%
```

### 2.3 RiskConfigV2（v2.0风控配置）

```python
@dataclass
class RiskConfigV2(RiskConfig):
    """v2.0风控配置（继承基础配置）"""
    # v2.0新增
    min_quality_score: float = 55.0      # 最低信号质量评分
    high_risk_reduce_ratio: float = 0.6  # 高风险仓位系数
    mid_risk_reduce_ratio: float = 0.8   # 中风险仓位系数
```

### 2.4 CommissionConfig（费用配置）

```python
@dataclass
class AShareFeeConfig:
    """A股费率统一配置（共享来源）"""
    commission_rate: float = 0.0003      # 佣金: 万三
    stamp_duty_rate: float = 0.001       # 印花税: 千一（仅卖出）
    transfer_fee_rate: float = 0.00002   # 过户费: 万0.2
    min_commission: float = 5.0          # 最低佣金5元

@dataclass
class CommissionConfig(AShareFeeConfig):
    """Trading 费用配置（继承统一 AShareFeeConfig）"""
    pass
```

---

## 3. 验证与结果数据结构

### 3.1 ValidationResult（信号验证结果）

```python
@dataclass
class ValidationResult:
    """信号质量验证结果（v2.0统一结构）"""
    is_tradeable: bool        # 是否可交易
    risk_level: str           # 风险等级 (low/medium/high)
    position_adjustment: float # 仓位调整系数 [0-1]
    reasons: List[str]        # 验证失败原因列表
```

风险分级规则（基于中性度，越低信号越极端）：
| neutrality | risk_level | position_adjustment | 说明 |
|------------|------------|---------------------|------|
| ≤ 0.3 | low | 1.0 | 中性度低→信号极端→全仓位 |
| 0.3 - 0.6 | medium | 0.8 | 中性度中等→8折仓位 |
| > 0.6 | high | 0.6 | 中性度高→信号不明确→6折仓位 |

### 3.2 RiskCheckResult（风控检查结果）

```python
@dataclass
class RiskCheckResult:
    """风控检查结果"""
    passed: bool              # 是否通过
    reason: str               # 拒绝原因（通过时为空）
    validation: ValidationResult  # 信号验证结果（v2.0）
```

---

## 4. 业务表映射（Business Tables / DuckDB 单库优先，阈值触发分库）

> 说明：`trade_records` / `positions` / `t1_frozen` 为业务运行表，
> 归类为 Business Tables（非 L1-L4）。

### 4.1 trade_records 表（Business Tables）

| 字段 | 类型 | 说明 |
|------|------|------|
| trade_id | VARCHAR(50) PK | 成交ID |
| trade_date | VARCHAR(8) | 交易日期 |
| stock_code | VARCHAR(20) | 股票代码 |
| stock_name | VARCHAR(50) | 股票名称 |
| industry_code | VARCHAR(10) | 行业代码 |
| direction | VARCHAR(10) | buy/sell |
| order_type | VARCHAR(20) | auction/market/limit/stop |
| price | DECIMAL(12,4) | 成交价格 |
| shares | INTEGER | 成交股数 |
| amount | DECIMAL(16,2) | 成交金额 |
| commission | DECIMAL(12,2) | 佣金 |
| stamp_tax | DECIMAL(12,2) | 印花税 |
| transfer_fee | DECIMAL(12,4) | 过户费 |
| slippage | DECIMAL(12,4) | 滑点 |
| total_fee | DECIMAL(16,2) | 总费用 |
| status | VARCHAR(20) | 状态 filled/partially_filled/rejected |
| signal_id | VARCHAR(50) | 关联信号ID |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

索引：
- `idx_trade_date`: trade_date
- `idx_stock_code`: stock_code

### 4.2 positions 表（Business Tables）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| stock_code | VARCHAR(20) UNIQUE | 股票代码 |
| stock_name | VARCHAR(50) | 股票名称 |
| direction | VARCHAR(10) | 持仓方向（默认 long） |
| shares | INTEGER | 持仓股数 |
| cost_price | DECIMAL(12,4) | 成本价 |
| cost_amount | DECIMAL(16,2) | 成本金额 |
| market_price | DECIMAL(12,4) | 当前市价 |
| market_value | DECIMAL(16,2) | 市值 |
| unrealized_pnl | DECIMAL(16,2) | 未实现盈亏 |
| unrealized_pnl_pct | DECIMAL(8,4) | 盈亏比例 |
| buy_date | VARCHAR(8) | 买入日期 |
| can_sell_date | VARCHAR(8) | 可卖日期 |
| is_frozen | BOOLEAN | 是否冻结 |
| signal_id | VARCHAR(50) | 关联信号ID |
| industry_code | VARCHAR(10) | 行业代码 |
| stop_price | DECIMAL(12,4) | 止损价 |
| target_price | DECIMAL(12,4) | 目标价 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 4.3 t1_frozen 表（Business Tables）

| 字段 | 类型 | 说明 |
|------|------|------|
| stock_code | VARCHAR(20) | 股票代码 |
| buy_date | VARCHAR(8) | 买入日期 |
| frozen_shares | INTEGER | 冻结股数 |
| PRIMARY KEY | | (stock_code, buy_date) |

---

## 5. 输入数据依赖（L3算法输出）

### 5.1 mss_panorama

| 字段 | 说明 |
|------|------|
| temperature | 市场温度 [0-100] |
| cycle | 周期阶段 (emergence/fermentation/acceleration/divergence/climax/diffusion/recession) |
| trend | 趋势方向 (up/down/sideways) |
| position_advice | 仓位建议 |

### 5.2 irs_industry_daily

| 字段 | 说明 |
|------|------|
| industry_code | 行业代码 |
| industry_score | 行业评分 [0-100] |
| rank | 行业排名 [1-N] |
| rotation_status | 轮动状态 (IN/OUT/HOLD) |
| allocation_advice | 配置建议 |

### 5.3 stock_pas_daily

| 字段 | 说明 |
|------|------|
| stock_code | 股票代码 |
| opportunity_score | 机会评分 [0-100] |
| direction | 方向 (bullish/bearish/neutral) |
| neutrality | 中性度 [0-1]（越接近1越中性，越接近0信号越极端） |
| risk_reward_ratio | 风险收益比 |
| entry | 入场价 |
| stop | 止损价 |
| target | 目标价 |

### 5.4 integrated_recommendation

| 字段 | 说明 |
|------|------|
| stock_code | 股票代码 |
| final_score | 最终评分 [0-100] |
| recommendation | 推荐标签 |
| position_size | 建议仓位 [0-1] |
| direction | 原始方向 (bullish/bearish/neutral) |
| integration_mode | 集成模式 top_down/bottom_up/dual_verify/complementary |
| neutrality | 中性度 [0-1] |
| risk_reward_ratio | 风险收益比 |
| entry | 入场价 |
| stop | 止损价 |
| target | 目标价 |
| irs_score | IRS评分 |
| pas_score | PAS评分 |
| industry_code | 行业代码 |

### 5.5 Trading 桥接规则（Integration → TradeSignal）

| Integration 字段 | TradeSignal 字段 | 规则 |
|------------------|------------------|------|
| trade_date + stock_code | signal_id | 默认 `SIG_{trade_date}_{stock_code}`（若上游已提供则透传） |
| industry_code | industry_code | 原样透传 |
| direction | source_direction | 原样保留（bullish/bearish/neutral） |
| direction | direction | bullish→buy；bearish→sell；neutral→hold（过滤，不下单） |
| integration_mode | integration_mode | 原样透传 |
| entry/stop/target | entry/stop/target | 优先透传；缺失时按风控参数补齐 |

---

## 6. 枚举定义

### 6.1 OrderStatus（订单状态）

```python
class OrderStatus(Enum):
    PENDING = "pending"                # 待处理
    SUBMITTED = "submitted"            # 已提交
    FILLED = "filled"                  # 已成交
    PARTIALLY_FILLED = "partially_filled"  # 部分成交
    CANCELLED = "cancelled"            # 已取消
    REJECTED = "rejected"              # 已拒绝
```

### 6.2 OrderType（订单类型）

```python
class OrderType(Enum):
    AUCTION = "auction"             # 集合竞价开盘单
    MARKET = "market"               # 市价单
    LIMIT = "limit"                 # 限价单
    STOP = "stop"                   # 止损单
```

### 6.3 Direction（交易方向）

```python
class Direction(Enum):
    BUY = "buy"
    SELL = "sell"
```

### 6.4 RiskLevel（风险等级）

```python
class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
```

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.2.6 | 2026-02-09 | 修复 R28：`trade_records/positions/t1_frozen` 类型体系由 `TEXT/REAL` 统一为 `VARCHAR/DECIMAL/BOOLEAN/DATETIME`，与 Data Layer 业务表口径一致 |
| v3.2.5 | 2026-02-09 | 修复 R20：`TradeSignal.source` 标注为当前仅 `integrated`；`TradeConfig` 移除 IRS/PAS 硬阈值并统一为 `min_final_score`；费用配置改为共享 `AShareFeeConfig` 统一来源 |
| v3.2.4 | 2026-02-08 | 修复 R15：`positions` DDL 对齐 Data Layer，改为 `id` 主键 + `stock_code UNIQUE`，并补充 `created_at` |
| v3.2.3 | 2026-02-08 | 修复 R12：统一 `OrderType` 为 `auction`；移除未启用的 `min_mss_temperature`；Trading Position 补齐 `cost_amount`（与 Backtest 更对齐） |
| v3.2.2 | 2026-02-08 | 修复 R10：Trading Position 增加 `direction`（默认 `long`），与 Backtest 持仓结构对齐 |
| v3.2.1 | 2026-02-07 | 修复 R7：TradeSignal 补齐 `signal_id/industry_code`；Order 补齐 `industry_code/signal_id`；`max_position_pct` 调整为 20% 全局硬上限 |
| v3.2.0 | 2026-02-06 | 增加 Integration 桥接字段（source_direction/integration_mode/neutrality/risk_reward_ratio）；统一 PAS 字段为 entry/stop/target |
| v3.1.1 | 2026-02-06 | 标注实现状态；明确业务表归类与字段补齐（positions/order_type） |
| v3.1.0 | 2026-02-04 | 增加 auction_open 订单类型与字段约束 |
| v3.0.0 | 2026-01-31 | 重构版：统一数据模型定义 |
| v2.1.0 | 2026-01-23 | 对齐三三制集成推荐 |
| v2.0.0 | 2026-01-20 | 增加ValidationResult |

---

**关联文档**：
- 核心算法：[trading-algorithm.md](./trading-algorithm.md)
- API接口：[trading-api.md](./trading-api.md)
- 信息流：[trading-information-flow.md](./trading-information-flow.md)
