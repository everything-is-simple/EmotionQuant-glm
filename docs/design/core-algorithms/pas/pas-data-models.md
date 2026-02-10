# PAS 数据模型

**版本**: v3.1.8（重构版）
**最后更新**: 2026-02-09
**状态**: 设计完成（验收口径补齐；代码未落地）

---

## 1. 数据依赖

### 1.1 Data Layer 输入依赖

| 输入表 | 更新频率 | 用途 |
|----------|----------|------|
| `raw_daily` | 每交易日 | 个股日线行情（OHLCV、涨跌幅） |
| `raw_daily_basic` | 每交易日 | 换手率、市值 |
| `raw_limit_list` | 每交易日 | 涨跌停/炸板状态 |
| `raw_stock_basic` | 月度 | 股票基础信息 |
| `raw_trade_cal` | 年度 | 交易日历 |

### 1.2 数据字段依赖

| 因子 | 依赖字段 | 来源 |
|------|----------|------|
| 牛股基因 | limit_up_count_120d, new_high_count_60d, max_pct_chg_history | `raw_daily` + `raw_limit_list` |
| 结构位置 | close, high_60d, low_60d, high_60d_prev, high_20d_prev, low_20d_prev, low_20d, consecutive_up_days | `raw_daily` |
| 行为确认 | vol, volume_avg_20d, pct_chg, is_limit_up, is_touched_limit_up | `raw_daily` + `raw_limit_list` |
| 归一化基线 | mean/std 参数（按因子） | `${DATA_PATH}/config/pas_zscore_baseline.parquet` |

---

## 2. 输入数据模型

### 2.1 个股日快照（PasStockSnapshot）

```python
@dataclass
class PasStockSnapshot:
    """PAS 个股日快照（输入）"""
    trade_date: str              # 交易日期 YYYYMMDD
    stock_code: str              # 股票代码（L2+）
    stock_name: str              # 股票名称
    industry_code: str           # 所属行业代码
    
    # 基础行情
    open: float                  # 开盘价
    high: float                  # 最高价
    low: float                   # 最低价
    close: float                 # 收盘价
    vol: float                   # 成交量（手）
    amount: float                # 成交额（千元）
    pct_chg: float               # 涨跌幅 %
    
    # 历史统计（牛股基因）
    limit_up_count_120d: int     # 近120日涨停次数
    new_high_count_60d: int      # 近60日创新高次数
    max_pct_chg_history: float   # 历史单日最大涨幅（百分数口径，15 表示 15%）
    
    # 价格位置（结构位置）
    high_60d: float              # 60日最高价
    low_60d: float               # 60日最低价
    high_60d_prev: float         # 前60日最高价（不含今日）
    high_20d_prev: float         # 前20日最高价（不含今日，用于方向判断）
    low_20d_prev: float          # 前20日最低价（不含今日，用于方向判断）
    low_20d: float               # 近20日最低价（用于止损）
    consecutive_up_days: int     # 连续上涨天数
    consecutive_down_days: int   # 连续下跌天数
    
    # 量能数据（行为确认）
    volume_avg_20d: float        # 20日平均成交量
    turnover_rate: float         # 换手率 %
    
    # 涨跌停状态
    is_limit_up: bool            # 是否涨停
    is_limit_down: bool          # 是否跌停
    is_touched_limit_up: bool    # 是否触及涨停（含炸板）
```

### 2.2 字段计算口径

| 字段 | 计算口径 |
|------|----------|
| limit_up_count_120d | 近120个交易日 `is_limit_up = True` 的天数 |
| new_high_count_60d | 近60个交易日 `close >= max(close_60d_prev)` 的天数 |
| high_60d | `max(high, rolling=60)` |
| low_60d | `min(low, rolling=60)` |
| high_20d_prev | `max(high.shift(1), rolling=20)` |
| low_20d_prev | `min(low.shift(1), rolling=20)` |
| low_20d | `min(low, rolling=20)` |
| max_pct_chg_history | 历史窗口内 `max(pct_chg)`（百分数口径，15 表示 15%） |
| consecutive_up_days | 从今日往前连续 `pct_chg > 0` 的天数 |
| volume_avg_20d | `mean(vol, rolling=20)` |

---

## 3. 输出数据模型

### 3.1 PAS 计算结果（StockPasDaily）

```python
@dataclass
class StockPasDaily:
    """PAS 个股每日计算结果（输出）"""
    trade_date: str              # 交易日期 YYYYMMDD
    stock_code: str              # 股票代码（L2+）
    stock_name: str              # 股票名称
    industry_code: str           # 所属行业代码
    
    # 核心输出
    opportunity_score: float     # 机会评分 0-100
    opportunity_grade: str       # 机会等级 S/A/B/C/D
    direction: str               # 方向 bullish/bearish/neutral
    risk_reward_ratio: float     # 风险收益比
    
    # 因子得分
    bull_gene_score: float       # 牛股基因得分
    structure_score: float       # 结构位置得分
    behavior_score: float        # 行为确认得分
    
    # 交易参考
    entry: float                 # 建议入场价
    stop: float                  # 建议止损价
    target: float                # 建议目标价
    
    # 辅助信息
    neutrality: float            # 中性度 0-1（越接近1越中性，越接近0信号越极端）
```

### 3.2 机会等级枚举

```python
class PasGrade(Enum):
    """机会等级枚举"""
    S = "S"    # [85, +∞)，极佳机会
    A = "A"    # [70, 85)，优质机会
    B = "B"    # [55, 70)，普通机会
    C = "C"    # [40, 55)，观望
    D = "D"    # <40，回避
```

### 3.3 方向枚举

```python
class PasDirection(Enum):
    """方向枚举"""
    BULLISH = "bullish"   # 看涨
    BEARISH = "bearish"   # 看跌
    NEUTRAL = "neutral"   # 中性
```

---

## 4. 数据库表结构

> 以下为 **MySQL 风格逻辑DDL（伪代码）**，用于表达字段与约束语义，**不可直接在 DuckDB 执行**。  
> DuckDB 落地时请改写为 `CREATE TABLE ...` + `CREATE INDEX ...`，字段注释改为独立文档或 `COMMENT ON` 形式。

### 4.1 主表：stock_pas_daily

> **命名规范**：与数据层统一，详见 [naming-conventions.md](../../../naming-conventions.md)

```sql
CREATE TABLE stock_pas_daily (
    id INTEGER PRIMARY KEY,
    trade_date VARCHAR(8) NOT NULL COMMENT '交易日期 YYYYMMDD',
    stock_code VARCHAR(20) NOT NULL COMMENT '股票代码',
    stock_name VARCHAR(50) COMMENT '股票名称',
    industry_code VARCHAR(10) COMMENT '所属行业代码',
    
    -- 核心输出
    opportunity_score DECIMAL(8,4) COMMENT '机会评分 0-100',
    opportunity_grade VARCHAR(10) COMMENT '机会等级 S/A/B/C/D',
    direction VARCHAR(20) COMMENT '方向判断',
    risk_reward_ratio DECIMAL(8,4) COMMENT '风险收益比',
    
    -- 因子得分
    bull_gene_score DECIMAL(8,4) COMMENT '牛股基因得分',
    structure_score DECIMAL(8,4) COMMENT '结构位置得分',
    behavior_score DECIMAL(8,4) COMMENT '行为确认得分',
    
    -- 交易参考
    entry DECIMAL(12,4) COMMENT '建议入场价',
    stop DECIMAL(12,4) COMMENT '建议止损价',
    target DECIMAL(12,4) COMMENT '建议目标价',
    
    -- 辅助信息
    neutrality DECIMAL(8,4) COMMENT '中性度 0-1（越接近1越中性，越接近0信号越极端）',

    -- 元数据
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_trade_date_stock_code (trade_date, stock_code),
    KEY idx_opportunity_score (opportunity_score),
    KEY idx_opportunity_grade (opportunity_grade),
    KEY idx_industry_code (industry_code)
);
```

### 4.2 因子中间表：pas_factor_intermediate

```sql
CREATE TABLE pas_factor_intermediate (
    id INTEGER PRIMARY KEY,
    trade_date VARCHAR(8) NOT NULL COMMENT '交易日期 YYYYMMDD',
    stock_code VARCHAR(20) NOT NULL COMMENT '股票代码',
    
    -- 原始因子值
    limit_up_count_120d INT COMMENT '近120日涨停次数',
    new_high_count_60d INT COMMENT '近60日新高次数',
    max_pct_chg_history DECIMAL(8,4) COMMENT '历史最大涨幅',
    price_position DECIMAL(8,4) COMMENT '价格位置（0-1）',
    consecutive_up_days INT COMMENT '连续上涨天数',
    consecutive_down_days INT COMMENT '连续下跌天数',
    breakout_strength DECIMAL(8,4) COMMENT '突破强度',
    volume_ratio DECIMAL(8,4) COMMENT '量比',

    -- 因子组合 raw（zscore 前）
    bull_gene_raw DECIMAL(12,6) COMMENT '牛股基因组合原始值',
    structure_raw DECIMAL(12,6) COMMENT '结构位置组合原始值',
    behavior_raw DECIMAL(12,6) COMMENT '行为确认组合原始值',

    -- 归一化统计参数快照（3 因子独立 mean/std）
    bull_gene_mean DECIMAL(12,6) COMMENT '牛股基因滚动均值',
    bull_gene_std DECIMAL(12,6) COMMENT '牛股基因滚动标准差',
    structure_mean DECIMAL(12,6) COMMENT '结构位置滚动均值',
    structure_std DECIMAL(12,6) COMMENT '结构位置滚动标准差',
    behavior_mean DECIMAL(12,6) COMMENT '行为确认滚动均值',
    behavior_std DECIMAL(12,6) COMMENT '行为确认滚动标准差',
    
    -- 元数据
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_trade_date_stock_code (trade_date, stock_code)
);
```

### 4.3 机会日志表：pas_opportunity_log

```sql
CREATE TABLE pas_opportunity_log (
    id INTEGER PRIMARY KEY,
    trade_date VARCHAR(8) NOT NULL COMMENT '交易日期 YYYYMMDD',
    stock_code VARCHAR(20) NOT NULL COMMENT '股票代码',
    
    -- 机会信息
    opportunity_grade VARCHAR(10) NOT NULL COMMENT '机会等级',
    opportunity_score DECIMAL(8,4) COMMENT '机会评分',
    direction VARCHAR(20) COMMENT '方向',
    
    -- 状态变化
    prev_grade VARCHAR(10) COMMENT '前一日等级',
    grade_change VARCHAR(20) COMMENT '等级变化（upgrade/downgrade/unchanged）',
    
    -- 元数据
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    KEY idx_trade_date (trade_date),
    KEY idx_opportunity_grade (opportunity_grade)
);
```

---

## 5. 数据验证规则

### 5.1 输入验证

| 字段 | 验证规则 |
|------|----------|
| stock_code | 必须为有效A股代码 |
| close | > 0 |
| vol | ≥ 0 |
| high_60d | ≥ low_60d |
| high_20d_prev | ≥ low_20d_prev |
| volume_avg_20d | > 0 |
| max_pct_chg_history | 百分数口径输入（如 15 表示 15%）；进入 bull_gene 前需 `/100` 转 ratio |
| pas_zscore_baseline | 文件可读且覆盖三大因子；缺失时因子分数回退 50 |

### 5.2 输出验证

| 字段 | 验证规则 |
|------|----------|
| opportunity_score | 0 ≤ x ≤ 100 |
| opportunity_grade | IN ('S', 'A', 'B', 'C', 'D') |
| direction | IN ('bullish', 'bearish', 'neutral') |
| risk_reward_ratio | ≥ 0 |
| neutrality | 0 ≤ x ≤ 1 |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.1.8 | 2026-02-09 | 修复 R28：DDL 中 `trade_date` 统一为 `VARCHAR(8)`；`stock_code/stock_name/opportunity_grade` 宽度与 Data Layer 对齐；时间戳命名统一为 `created_at` 并移除 L3 主表 `update_time` |
| v3.1.7 | 2026-02-08 | 修复 R18：`pas_factor_intermediate` 补齐 `consecutive_down_days`、三因子组合 raw（`bull_gene_raw/structure_raw/behavior_raw`）及对应 `mean/std` 快照列 |
| v3.1.6 | 2026-02-08 | 修复 R17：`PasGrade` 注释区间改为半开区间表达（`[70,85)` 等），消除边界歧义 |
| v3.1.5 | 2026-02-07 | 修复 R5：补充 PAS Z-Score baseline 依赖与冷启动兜底校验口径；DDL 标注为 DuckDB 不可直接执行的伪代码 |
| v3.1.4 | 2026-02-07 | 修复 P1：明确 max_pct_chg_history 单位为百分数并约束进入因子前转换为 ratio |
| v3.1.3 | 2026-02-07 | 修复 P0：补齐 20 日方向/止损字段（high_20d_prev、low_20d_prev、low_20d），与算法/信息流一致 |
| v3.1.2 | 2026-02-06 | 输入依赖命名统一为 Data Layer raw_* 表口径 |
| v3.1.1 | 2026-02-05 | 输入/中间字段命名与路线图对齐，输出类统一为 StockPasDaily |
| v3.1.0 | 2026-02-04 | 同步 PAS v3.1.0：补齐因子依赖字段与验证口径（ratio 先行） |
| v3.0.0 | 2026-01-31 | 重构版：统一数据模型、添加枚举定义、完善验证规则 |

---

**关联文档**：
- 算法设计：[pas-algorithm.md](./pas-algorithm.md)
- API接口：[pas-api.md](./pas-api.md)
- 信息流：[pas-information-flow.md](./pas-information-flow.md)

