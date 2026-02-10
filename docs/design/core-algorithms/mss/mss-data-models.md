# MSS 数据模型

**版本**: v3.1.6（重构版）
**最后更新**: 2026-02-09
**状态**: 设计完成（验收口径补齐；代码未落地）

---

## 1. 数据依赖

### 1.1 Data Layer 输入依赖

| 输入表 | 更新频率 | 用途 |
|----------|----------|------|
| `raw_daily` | 每交易日 | 全市场日线行情（涨跌家数、涨跌幅分布） |
| `raw_daily_basic` | 每交易日 | 换手率、流通市值（波动因子计算） |
| `raw_limit_list` | 每交易日 | 涨跌停/炸板统计 |
| `raw_stock_basic` | 月度 | 股票列表/状态 |
| `raw_trade_cal` | 年度 | 交易日历 |

### 1.2 数据字段依赖

| 因子 | 依赖字段 | 来源 |
|------|----------|------|
| 大盘系数 | rise_count, total_stocks | `raw_daily` 聚合 |
| 赚钱效应 | limit_up_count, new_100d_high_count, strong_up_count, total_stocks | `raw_limit_list` + `raw_daily` |
| 亏钱效应 | touched_limit_up, limit_up_count, limit_down_count, strong_down_count, new_100d_low_count, total_stocks | `raw_limit_list` + `raw_daily` |
| 连续性因子 | continuous_limit_up_2d, continuous_limit_up_3d_plus, continuous_new_high_2d_plus | `raw_daily` rolling |
| 极端因子 | high_open_low_close_count, low_open_high_close_count | `raw_daily` |
| 波动因子 | pct_chg_std, amount_volatility | `raw_daily` |
| 辅助观测（非评分） | yesterday_limit_up_today_avg_pct | `market_snapshot` 聚合 |

---

## 2. 输入数据模型

### 2.1 市场日汇总（MssMarketSnapshot）

```python
@dataclass
class MssMarketSnapshot:
    """MSS 每日市场快照（输入）"""
    trade_date: str              # 交易日期 YYYYMMDD
    
    # 基础统计
    total_stocks: int            # 可交易股票总数
    rise_count: int              # 上涨家数（pct_chg > 0）
    fall_count: int              # 下跌家数（pct_chg < 0）
    flat_count: int              # 平盘家数
    
    # 涨跌停统计
    limit_up_count: int          # 涨停家数
    limit_down_count: int        # 跌停家数
    touched_limit_up: int        # 触及涨停家数（含炸板）
    
    # 新高新低统计
    new_100d_high_count: int     # 100日新高家数
    new_100d_low_count: int      # 100日新低家数
    
    # 大涨大跌统计
    strong_up_count: int         # 涨幅>5%家数
    strong_down_count: int       # 跌幅<-5%家数
    
    # 连续性统计
    continuous_limit_up_2d: int  # 连续2日涨停家数
    continuous_limit_up_3d_plus: int  # 连续3日+涨停家数
    continuous_new_high_2d_plus: int  # 连续2日+新高家数
    
    # 极端行为统计
    high_open_low_close_count: int  # 高开低走且跌幅<-6%
    low_open_high_close_count: int  # 低开高走且涨幅>6%
    
    # 波动统计
    pct_chg_std: float           # 全市场涨跌幅标准差
    amount_volatility: float     # 成交额波动率（相对20日均值）
    yesterday_limit_up_today_avg_pct: float  # 昨涨停今平均涨幅（兼容观测字段，当前不直接参与MSS评分）
```

### 2.2 字段计算口径

| 字段 | 计算口径 |
|------|----------|
| rise_count | `pct_chg > 0` 的股票数 |
| fall_count | `pct_chg < 0` 的股票数 |
| flat_count | `abs(pct_chg) <= 0.5%` 的股票数 |
| strong_up_count | `pct_chg > 5%` 的股票数 |
| strong_down_count | `pct_chg < -5%` 的股票数 |
| new_100d_high_count | 收盘价创100日新高的股票数 |
| new_100d_low_count | 收盘价创100日新低的股票数 |
| high_open_low_close_count | `open > pre_close * 1.02` 且 `close < open * 0.94` |
| low_open_high_close_count | `open < pre_close * 0.98` 且 `close > open * 1.06` |
| pct_chg_std | `df['pct_chg'].std()` |
| amount_volatility | `(当日成交额 - MA20成交额) / MA20成交额` |
| yesterday_limit_up_today_avg_pct | 昨日涨停股票在今日的平均 `pct_chg`（兼容观测字段） |

> 计数语义说明（避免歧义）：
> - `flat_count` 与 `rise_count`/`fall_count` **允许交叉覆盖**（例如 `pct_chg=0.3%` 同时计入 `rise_count` 与 `flat_count`）。
> - `rise_count + fall_count + flat_count` 不是互斥分桶总和，不应按 `== total_stocks` 断言。

---

## 3. 输出数据模型

### 3.1 MSS 计算结果（MssPanorama）

```python
@dataclass
class MssPanorama:
    """MSS 每日计算结果（输出）"""
    trade_date: str              # 交易日期 YYYYMMDD
    
    # 核心输出
    temperature: float           # 市场温度 0-100
    cycle: str                   # 情绪周期（英文代码）
    trend: str                   # 趋势方向 up/down/sideways
    position_advice: str         # 仓位建议（固定格式："{min}%-{max}%"）
    
    # 因子得分
    market_coefficient: float    # 大盘系数得分 0-100
    profit_effect: float         # 赚钱效应得分 0-100
    loss_effect: float           # 亏钱效应得分 0-100
    continuity_factor: float     # 连续性因子得分 0-100
    extreme_factor: float        # 极端因子得分 0-100
    volatility_factor: float     # 波动因子得分 0-100
    
    # 辅助信息
    neutrality: float            # 中性度 0-1（越接近1越中性，越接近0信号越极端）
    rank: int                    # 历史排名
    percentile: float            # 百分位排名 0-100
```

### 3.2 周期枚举

```python
class MssCycle(Enum):
    """情绪周期枚举"""
    EMERGENCE = "emergence"         # 萌芽期
    FERMENTATION = "fermentation"   # 发酵期
    ACCELERATION = "acceleration"   # 加速期
    DIVERGENCE = "divergence"       # 分歧期
    CLIMAX = "climax"               # 高潮期
    DIFFUSION = "diffusion"         # 扩散期
    RECESSION = "recession"         # 退潮期
    UNKNOWN = "unknown"             # 未知
```

### 3.3 趋势枚举

```python
class MssTrend(Enum):
    """趋势方向枚举"""
    UP = "up"           # 上升
    DOWN = "down"       # 下降
    SIDEWAYS = "sideways"  # 横盘
```

### 3.4 仓位建议枚举（PositionAdvice）

```python
class PositionAdvice(Enum):
    """仓位建议枚举（固定百分比区间字符串）"""
    PA_80_100 = "80%-100%"
    PA_60_80 = "60%-80%"
    PA_50_70 = "50%-70%"
    PA_40_60 = "40%-60%"
    PA_30_50 = "30%-50%"
    PA_20_40 = "20%-40%"
    PA_0_20 = "0%-20%"
```

---

## 4. 数据库表结构

> 以下为 **MySQL 风格逻辑DDL（伪代码）**，用于表达字段与约束语义，**不可直接在 DuckDB 执行**。  
> DuckDB 落地时请改写为 `CREATE TABLE ...` + `CREATE INDEX ...`，字段注释改为独立文档或 `COMMENT ON` 形式。

### 4.1 主表：mss_panorama

```sql
CREATE TABLE mss_panorama (
    id INTEGER PRIMARY KEY,
    trade_date VARCHAR(8) NOT NULL COMMENT '交易日期 YYYYMMDD',
    
    -- 核心输出
    temperature DECIMAL(8,4) NOT NULL COMMENT '市场温度 0-100',
    cycle VARCHAR(20) NOT NULL COMMENT '情绪周期（英文代码）',
    trend VARCHAR(20) NOT NULL COMMENT '趋势方向',
    position_advice VARCHAR(20) COMMENT '仓位建议',
    
    -- 因子得分
    market_coefficient DECIMAL(8,4) COMMENT '大盘系数得分',
    profit_effect DECIMAL(8,4) COMMENT '赚钱效应得分',
    loss_effect DECIMAL(8,4) COMMENT '亏钱效应得分',
    continuity_factor DECIMAL(8,4) COMMENT '连续性因子得分',
    extreme_factor DECIMAL(8,4) COMMENT '极端因子得分',
    volatility_factor DECIMAL(8,4) COMMENT '波动因子得分',
    
    -- 辅助信息
    neutrality DECIMAL(8,4) COMMENT '中性度 0-1（越接近1越中性，越接近0信号越极端）',
    rank INT COMMENT '历史排名',
    percentile DECIMAL(8,4) COMMENT '百分位排名 0-100',
    
    -- 元数据
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_trade_date (trade_date),
    KEY idx_temperature (temperature),
    KEY idx_cycle (cycle)
);
```

### 4.2 因子中间表：mss_factor_intermediate

```sql
CREATE TABLE mss_factor_intermediate (
    id INTEGER PRIMARY KEY,
    trade_date VARCHAR(8) NOT NULL COMMENT '交易日期 YYYYMMDD',
    
    -- 原始因子值（归一化前）
    market_coefficient_raw DECIMAL(12,6) COMMENT '大盘系数原始值',
    profit_effect_raw DECIMAL(12,6) COMMENT '赚钱效应原始值',
    loss_effect_raw DECIMAL(12,6) COMMENT '亏钱效应原始值',
    continuity_factor_raw DECIMAL(12,6) COMMENT '连续性因子原始值',
    extreme_factor_raw DECIMAL(12,6) COMMENT '极端因子原始值',
    volatility_factor_raw DECIMAL(12,6) COMMENT '波动因子原始值',
    
    -- 统计参数（6 因子独立 mean/std）
    market_coefficient_mean DECIMAL(12,6) COMMENT '大盘系数滚动均值',
    market_coefficient_std DECIMAL(12,6) COMMENT '大盘系数滚动标准差',
    profit_effect_mean DECIMAL(12,6) COMMENT '赚钱效应滚动均值',
    profit_effect_std DECIMAL(12,6) COMMENT '赚钱效应滚动标准差',
    loss_effect_mean DECIMAL(12,6) COMMENT '亏钱效应滚动均值',
    loss_effect_std DECIMAL(12,6) COMMENT '亏钱效应滚动标准差',
    continuity_factor_mean DECIMAL(12,6) COMMENT '连续性因子滚动均值',
    continuity_factor_std DECIMAL(12,6) COMMENT '连续性因子滚动标准差',
    extreme_factor_mean DECIMAL(12,6) COMMENT '极端因子滚动均值',
    extreme_factor_std DECIMAL(12,6) COMMENT '极端因子滚动标准差',
    volatility_factor_mean DECIMAL(12,6) COMMENT '波动因子滚动均值',
    volatility_factor_std DECIMAL(12,6) COMMENT '波动因子滚动标准差',
    
    -- 元数据
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_trade_date (trade_date)
);
```

### 4.3 预警日志表：mss_alert_log

```sql
CREATE TABLE mss_alert_log (
    id INTEGER PRIMARY KEY,
    trade_date VARCHAR(8) NOT NULL COMMENT '交易日期 YYYYMMDD',
    
    -- 预警信息
    alert_type VARCHAR(20) NOT NULL COMMENT '预警类型：overheat/overcool/tail_activity/divergence',
    alert_level VARCHAR(20) NOT NULL COMMENT '预警等级：info/warn/critical',
    alert_message VARCHAR(200) COMMENT '预警说明',
    
    -- 触发时状态
    temperature DECIMAL(8,4) COMMENT '触发时温度',
    cycle VARCHAR(20) COMMENT '触发时周期',
    trend VARCHAR(20) COMMENT '触发时趋势',
    
    -- 元数据
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    KEY idx_trade_date (trade_date),
    KEY idx_alert_type (alert_type)
);
```

---

## 5. 数据验证规则

### 5.1 输入验证

| 字段 | 验证规则 |
|------|----------|
| total_stocks | > 0 |
| rise_count + fall_count | ≤ total_stocks |
| flat_count | ≤ total_stocks |
| rise_count + fall_count + flat_count | 允许 > total_stocks（flat_count 与 rise/fall 可重叠） |
| limit_up_count | ≤ touched_limit_up |
| pct_chg_std | ≥ 0 |

### 5.2 输出验证

| 字段 | 验证规则 |
|------|----------|
| temperature | 0 ≤ x ≤ 100 |
| cycle | IN ('emergence', 'fermentation', 'acceleration', 'divergence', 'climax', 'diffusion', 'recession', 'unknown') |
| trend | IN ('up', 'down', 'sideways') |
| position_advice | IN ('80%-100%','60%-80%','50%-70%','40%-60%','30%-50%','20%-40%','0%-20%') |
| neutrality | 0 ≤ x ≤ 1 |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.1.6 | 2026-02-09 | 修复 R28：DDL 中 `trade_date` 统一为 `VARCHAR(8)`；时间戳命名统一为 `created_at`；移除 L3 主表 `update_time`（append-only 口径） |
| v3.1.5 | 2026-02-08 | 修复 R18：补充 `position_advice` 的固定格式与 `PositionAdvice` 枚举，并在输出验证中增加合法值约束 |
| v3.1.4 | 2026-02-08 | 修复 R17：`mss_factor_intermediate` 统计参数扩展为 6 因子独立 `mean/std`；`mss_alert_log.alert_type` 枚举补齐 `tail_activity` |
| v3.1.3 | 2026-02-08 | 修复 R10：输出验证 `cycle` 合法值补入 `unknown`，与枚举与算法 fallback 一致 |
| v3.1.2 | 2026-02-07 | 修复 P1/P2：补充兼容观测字段 `yesterday_limit_up_today_avg_pct`；显式声明 `flat_count` 与涨跌家数可交叉覆盖；DDL 标注为 DuckDB 不可直接执行的伪代码 |
| v3.1.1 | 2026-02-06 | 输入依赖命名统一为 Data Layer raw_* 表口径 |
| v3.1.0 | 2026-02-04 | 同步 MSS v3.1.0：补齐输入字段与依赖表（强涨跌、连续新高、极端行为、波动字段） |
| v3.0.0 | 2026-01-31 | 重构版：统一数据模型、添加枚举定义、完善验证规则 |

---

**关联文档**：
- 算法设计：[mss-algorithm.md](./mss-algorithm.md)
- API接口：[mss-api.md](./mss-api.md)
- 信息流：[mss-information-flow.md](./mss-information-flow.md)


