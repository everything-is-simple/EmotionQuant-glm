# ROADMAP Phase 04｜个股精准分析（PAS）

**版本**: v4.0.2
**创建日期**: 2026-01-31
**最后更新**: 2026-02-06
**时间范围**: Phase 04
**核心交付**: PAS算法实现、价格位置、换手强度、波动节奏
**前置依赖**: Phase 01 (Data Layer)
**实现状态**: 未实现（截至 2026-02-06：`src/` 仅有 Skeleton/占位与少量基础骨架，详见 `Governance/ROADMAP/ROADMAP-OVERVIEW.md`）

---
## 文档对齐声明

> **权威设计文档**: `docs/design/core-algorithms/pas/`
> - 算法：`pas-algorithm.md`
> - 数据模型：`pas-data-models.md`
> - API：`pas-api.md`
> - 信息流：`pas-information-flow.md`

---

## 1. Phase 目标与量化验收标准

> **一句话**: 在选定行业内精选个股

### 1.1 量化验收指标

| 指标项 | 验收标准 | 测量方法 | 优先级 |
|--------|----------|----------|--------|
| 零技术指标合规 | 代码中无MA/EMA/SMA/RSI/MACD等 | 代码扫描+pre-commit hook | P0 |
| 机会评分范围 | opportunity_score ∈ [0,100] | 边界测试 | P0 |
| 三因子权重验证 | 20%+50%+30% = 100% | 单元测试权重断言 | P0 |
| 等级分布合理性 | S/A/B/C/D 分布符合正态 | 统计分布检查 | P0 |
| 方向判断准确率 | bullish/bearish/neutral判断≥95% | 历史回测 | P0 |
| 股票覆盖率 | 每日~5000只可交易股票全覆盖 | COUNT检查 | P0 |
| 代码覆盖率 | ≥ 80% | pytest-cov | P1 |
| 计算延迟 | 全市场计算 ≤ 5分钟 | 性能测试 | P1 |

### 1.2 里程碑检查点

| 里程碑 | 交付物 | 验收条件 | 预期时间 |
|--------|--------|----------|----------|
| M4.1 | 牛股基因因子 | 涨停统计/新高统计/最大涨幅测试通过 | Task 1 |
| M4.2 | 结构位置因子 | 价格位置计算测试通过（无MA） | Task 2 |
| M4.3 | 行为确认因子 | 量比/涨跌幅/涨停判断测试通过 | Task 3 |
| M4.4 | 落库与API | stock_pas_daily全量落库 | Task 4 |

### 1.3 铁律约束（零容忍）

| 铁律 | 要求 | 检查方式 | 违反后果 |
|------|------|----------|----------|
| **零技术指标** | 禁止使用MA/EMA/SMA/RSI/MACD/BOLL/KDJ等 | 代码扫描 + pre-commit hook | 立即回滚 |
| **情绪优先** | 只使用价格位置、涨跌幅、涨停等情绪数据 | 代码审查 | 立即回滚 |
| **价格区间计算** | 使用(close-low)/(high-low)而非close/MA | 单元测试 | 立即回滚 |

---

## 2. 输入规范

### 2.1 数据依赖矩阵

| 输入表/接口 | 来源 | 关键字段 | 更新频率 | 必需 |
|-------------|------|----------|----------|------|
| raw_daily | Phase 01 L1 | open, high, low, close, vol, amount, pct_chg | 每交易日 | ✅ |
| raw_daily_basic | Phase 01 L1 | turnover_rate | 每交易日 | ✅ |
| raw_limit_list | Phase 01 L1 | limit_up, touched_limit_up | 每交易日 | ✅ |
| raw_stock_basic | Phase 01 L1 | ts_code, name, industry | 月度 | ✅ |
| raw_trade_cal | Phase 01 L1 | is_open | 年度 | ✅ |

### 2.2 输入字段规范

```python
@dataclass
class PasStockInput:
    """PAS 股票输入数据"""
    trade_date: str              # 交易日期 YYYYMMDD
    stock_code: str              # 股票代码（L2+）
    stock_name: str              # 股票名称
    industry_code: str           # 所属行业
    
    # 当日行情
    open: float                  # 开盘价
    high: float                  # 最高价
    low: float                   # 最低价
    close: float                 # 收盘价
    vol: float                   # 成交量
    amount: float                # 成交额
    pct_chg: float               # 涨跌幅 %
    
    # 涨停信息
    is_limit_up: bool            # 是否涨停
    is_touched_limit_up: bool    # 是否触板
    
    # 历史统计（需历史数据计算）
    high_60d: float              # 60日最高价
    low_60d: float               # 60日最低价
    high_60d_prev: float         # 前60日最高价（不含当日）
    low_20d: float               # 20日最低价
    volume_avg_20d: float        # 近20日平均成交量（统计基准）
    limit_up_count_120d: int     # 近120日涨停次数
    new_high_count_60d: int      # 近60日创新高次数
    max_pct_chg_history: float   # 历史单日最大涨幅
    consecutive_up_days: int     # 连续上涨天数
```

### 2.3 输入验证规则

| 验证项 | 规则 | 错误处理 |
|--------|------|----------|
| close | > 0 | 跳过该股票 |
| high_60d - low_60d | > 0 | 价格位置设为50 |
| volume_avg_20d | > 0 | 量比设为1 |
| pct_chg | ∈ [-20, 20] | 截断并记录警告 |
| trade_date | 必须是交易日 | 跳过计算 |
| 股票状态 | 非停牌、非ST | 跳过该股票 |

---

## 3. 核心算法（权威口径）

### 3.1 三因子体系

| 因子名称 | 权重 | 取值范围 | 说明 |
|----------|------|----------|------|
| 牛股基因因子 | 20% | [0,100] | 历史强势特征 |
| 结构位置因子 | 50% | [0,100] | 价格位置与突破强度（⚠️铁律） |
| 行为确认因子 | 30% | [0,100] | 量价配合验证 |

### 3.2 牛股基因因子（20%）

```python
def calculate_bull_gene_score(
    limit_up_count_120d: int,
    new_high_count_60d: int,
    max_pct_chg_history: float
) -> float:
    """
    牛股基因因子：历史强势股更容易继续表现强势
    """
    # ratio 化（先将 count 转为 ratio）
    limit_up_120d_ratio = limit_up_count_120d / limit_up_window
    new_high_60d_ratio = new_high_count_60d / new_high_window
    
    # 组合后再做 Z-Score 归一化
    bull_gene_raw = (
        0.4 * limit_up_120d_ratio
        + 0.3 * new_high_60d_ratio
        + 0.3 * max_pct_chg_history
    )
    bull_gene_score = zscore_normalize(bull_gene_raw)
    
    return max(0.0, min(100.0, bull_gene_score))
```

### 3.3 结构位置因子（50%）—— ⚠️ 铁律合规

```python
def calculate_structure_score(
    close: float,
    high_60d: float,
    low_60d: float,
    high_60d_prev: float,
    consecutive_up_days: int
) -> float:
    """
    结构位置因子：使用价格区间而非均线
    
    ⚠️ 铁律合规：禁止使用 MA/EMA/SMA
    ✅ 正确做法：使用价格相对位置 (close-low)/(high-low)
    """
    # 子因子1：价格位置（当前价格在60日高低点区间中的位置）
    price_range = high_60d - low_60d
    if price_range > 0:
        price_position = (close - low_60d) / price_range  # [0, 1]
    else:
        price_position = 0.5
    
    # 子因子2：趋势延续性（基于涨跌天数统计，非技术指标）
    trend_continuity_ratio = min(consecutive_up_days / trend_window, 1.0)
    
    # 子因子3：突破强度（相对前60日最高价的突破幅度）
    if high_60d_prev > 0:
        breakout_strength = (close - high_60d_prev) / high_60d_prev
    else:
        breakout_strength = 0
    
    # 组合后再做 Z-Score 归一化
    structure_raw = (
        0.4 * price_position
        + 0.3 * trend_continuity_ratio
        + 0.3 * breakout_strength
    )
    structure_score = zscore_normalize(structure_raw)
    
    return max(0.0, min(100.0, structure_score))
```

**禁止行为（零容忍）**：
```python
# ❌ 严禁 - 使用任何均线
ma20 = df['close'].rolling(20).mean()
price_position = close / ma20  # 违规！

ma5 = df['close'].rolling(5).mean()
ma10 = df['close'].rolling(10).mean()
trend = ma5 > ma10  # 违规！

# ❌ 严禁 - 使用任何技术指标
rsi = ta.RSI(close, 14)  # 违规！
macd = ta.MACD(close)  # 违规！
```

### 3.4 行为确认因子（30%）

```python
def calculate_behavior_score(
    vol: float,
    volume_avg_20d: float,
    pct_chg: float,
    is_limit_up: bool,
    is_touched_limit_up: bool
) -> float:
    """
    行为确认因子：量价配合验证价格突破的有效性
    """
    # 子因子1：量比（放量突破更有效）
    if volume_avg_20d > 0:
        volume_ratio = vol / volume_avg_20d
    else:
        volume_ratio = 1.0
    
    # 子因子2：当日涨幅强度
    pct_chg_raw = pct_chg
    
    # 子因子3：涨停/触板状态
    if is_limit_up:
        limit_up_flag = 1.0
    elif is_touched_limit_up:
        limit_up_flag = 0.7
    else:
        limit_up_flag = 0.0
    
    # 组合后再做 Z-Score 归一化
    behavior_raw = (
        0.4 * volume_ratio
        + 0.3 * pct_chg_raw
        + 0.3 * limit_up_flag
    )
    behavior_score = zscore_normalize(behavior_raw)
    
    return max(0.0, min(100.0, behavior_score))
```

### 3.5 综合评分计算

```python
# 加权求和公式
opportunity_score = bull_gene_score * 0.20 \
                  + structure_score * 0.50 \
                  + behavior_score * 0.30

# 边界约束
opportunity_score = max(0.0, min(100.0, opportunity_score))
```

### 3.6 机会等级划分

| 等级 | 英文代码 | 评分区间 | 特征 | 操作建议 |
|------|----------|----------|------|----------|
| S | S | ≥ 85 | 极佳机会，强势突破+量价配合 | 重仓买入 |
| A | A | 70-84 | 优质机会，突破有效+量能放大 | 标准仓位 |
| B | B | 55-69 | 普通机会，可以但缺乏催化 | 轻仓试探 |
| C | C | 40-54 | 观望，信号不明确 | 不操作 |
| D | D | < 40 | 回避，技术面恶化 | 减仓/清仓 |

```python
def determine_grade(opportunity_score: float) -> str:
    if opportunity_score >= 85:
        return "S"
    elif opportunity_score >= 70:
        return "A"
    elif opportunity_score >= 55:
        return "B"
    elif opportunity_score >= 40:
        return "C"
    else:
        return "D"
```

### 3.7 方向判断（铁律合规版）

```python
def determine_direction(
    close: float,
    high_20d_prev: float,
    low_20d_prev: float,
    consecutive_up_days: int,
    consecutive_down_days: int
) -> str:
    """
    方向判断：使用价格位置而非均线
    
    ⚠️ 铁律合规：不使用均线判断方向
    """
    # bullish: 价格突破前20日高点 且 连续上涨≥3日
    if close > high_20d_prev and consecutive_up_days >= 3:
        return "bullish"
    
    # bearish: 价格跌破前20日低点 且 连续下跌≥3日
    if close < low_20d_prev and consecutive_down_days >= 3:
        return "bearish"
    
    # neutral: 其他情况
    return "neutral"
```

### 3.8 风险收益比计算

```python
def calculate_risk_reward(
    close: float,
    low_20d: float,
    default_stop_pct: float = 0.08,
    target_ratio: float = 2.0
) -> tuple:
    """
    风险收益比计算
    
    ⚠️ 铁律合规：使用价格高低点而非ATR计算止损止盈
    """
    entry = close
    
    # 止损：20日最低 或 8%止损，取较小者
    stop_by_low = low_20d
    stop_by_pct = close * (1 - default_stop_pct)
    stop = min(stop_by_low, stop_by_pct)
    
    # 目标：基于风险收益比计算（默认2:1）
    risk = entry - stop
    target = entry + risk * target_ratio
    
    # 风险收益比
    if risk > 0:
        risk_reward_ratio = (target - entry) / risk
    else:
        risk_reward_ratio = 0.0
    
    return entry, stop, target, risk_reward_ratio
```

### 3.9 中性度计算

```python
neutrality = 1 - abs(opportunity_score - 50) / 50
# 语义：越接近50越中性（中性度高），越极端越低
# 取值范围: [0, 1]
```

---

## 4. 输出规范

### 4.1 StockPasDaily 输出字段规范

```python
@dataclass
class StockPasDaily:
    """PAS 股票每日评分（输出）"""
    trade_date: str              # 交易日期 YYYYMMDD
    stock_code: str              # 股票代码（L2+）
    stock_name: str              # 股票名称
    industry_code: str           # 所属行业
    
    # 核心输出
    opportunity_score: float     # 机会评分 [0,100]
    opportunity_grade: str       # 机会等级 S/A/B/C/D
    direction: str               # 方向 bullish/bearish/neutral
    risk_reward_ratio: float     # 风险收益比 ≥0
    
    # 因子得分
    bull_gene_score: float       # 牛股基因得分 [0,100]
    structure_score: float       # 结构位置得分 [0,100]
    behavior_score: float        # 行为确认得分 [0,100]
    
    # 交易参考
    entry: float                 # 建议入场价
    stop: float                  # 建议止损价
    target: float                # 建议目标价
    
    # 辅助信息
    neutrality: float            # 中性度 [0,1]
```

### 4.2 数据库表结构（DuckDB DDL）

```sql
CREATE TABLE stock_pas_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date VARCHAR(8) NOT NULL,
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(50),
    industry_code VARCHAR(10),
    
    -- 核心输出
    opportunity_score DECIMAL(8,4) NOT NULL CHECK(opportunity_score >= 0 AND opportunity_score <= 100),
    opportunity_grade VARCHAR(10) NOT NULL CHECK(opportunity_grade IN ('S','A','B','C','D')),
    direction VARCHAR(10) NOT NULL CHECK(direction IN ('bullish','bearish','neutral')),
    risk_reward_ratio DECIMAL(8,4),
    
    -- 因子得分
    bull_gene_score DECIMAL(8,4) CHECK(bull_gene_score >= 0 AND bull_gene_score <= 100),
    structure_score DECIMAL(8,4) CHECK(structure_score >= 0 AND structure_score <= 100),
    behavior_score DECIMAL(8,4) CHECK(behavior_score >= 0 AND behavior_score <= 100),
    
    -- 交易参考
    entry DECIMAL(12,4),
    stop DECIMAL(12,4),
    target DECIMAL(12,4),
    
    -- 辅助信息
    neutrality DECIMAL(8,4) CHECK(neutrality >= 0 AND neutrality <= 1),
    
    -- 元数据
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME,
    
    UNIQUE(trade_date, stock_code)
);

CREATE INDEX idx_pas_trade_date ON stock_pas_daily(trade_date);
CREATE INDEX idx_pas_opportunity_score ON stock_pas_daily(opportunity_score);
CREATE INDEX idx_pas_grade ON stock_pas_daily(opportunity_grade);
CREATE INDEX idx_pas_direction ON stock_pas_daily(direction);
CREATE INDEX idx_pas_industry ON stock_pas_daily(industry_code);
```

### 4.3 输出验证规则

| 字段 | 验证规则 | 错误处理 |
|------|----------|----------|
| opportunity_score | ∈ [0, 100] | 截断到边界 |
| opportunity_grade | ∈ {S, A, B, C, D} | 根据评分重新计算 |
| direction | ∈ {bullish, bearish, neutral} | 设为 neutral |
| risk_reward_ratio | ≥ 0 | 设为 0 |
| neutrality | ∈ [0, 1] | 截断到边界 |
| 每日股票数 | ~5000 | 记录警告如低于4500 |

---

## 5. API 接口规范

### 5.1 核心接口定义

```python
class PasCalculator:
    """PAS 计算器接口"""
    
    def calculate(self, trade_date: str, stock_code: str) -> StockPasDaily:
        """
        计算单只股票的 PAS 评分
        
        Args:
            trade_date: 交易日期 YYYYMMDD
            stock_code: 股票代码
        Returns:
            StockPasDaily 对象
        Raises:
            ValueError: 非交易日或数据缺失
        """
        pass
    
    def batch_calculate(self, trade_date: str, stock_codes: List[str] = None) -> List[StockPasDaily]:
        """
        批量计算股票 PAS 评分
        
        Args:
            trade_date: 交易日期
            stock_codes: 股票代码列表，None表示全市场
        Returns:
            StockPasDaily 列表（按评分降序）
        """
        pass
    
    def get_top_opportunities(self, trade_date: str, top_n: int = 100, min_grade: str = "B") -> List[StockPasDaily]:
        """获取评分前N的机会"""
        pass
    
    def get_by_industry(self, trade_date: str, industry_code: str) -> List[StockPasDaily]:
        """获取指定行业的股票评分"""
        pass


class PasRepository:
    """PAS 数据仓库接口"""
    
    def save(self, pas_daily: StockPasDaily) -> None:
        """保存单条记录（幂等）"""
        pass
    
    def save_batch(self, pas_dailies: List[StockPasDaily]) -> int:
        """批量保存"""
        pass
    
    def get_by_date(self, trade_date: str) -> List[StockPasDaily]:
        """按日期查询所有股票"""
        pass
    
    def get_by_stock(self, stock_code: str, limit: int = 30) -> List[StockPasDaily]:
        """按股票查询历史"""
        pass
```

---

## 6. 错误处理策略

### 6.1 错误分类与处理

| 错误场景 | 错误码 | 严重等级 | 处理策略 | 重试 |
|----------|--------|----------|----------|------|
| 股票日线数据缺失 | PAS_E001 | P1 | 跳过该股票，记录警告 | 否 |
| 价格区间为零 | PAS_E002 | P2 | 价格位置设为50，记录警告 | 否 |
| 成交量为零 | PAS_E003 | P2 | 量比设为1，记录警告 | 否 |
| 评分越界 | PAS_E004 | P1 | 截断到[0,100]，记录警告 | 否 |
| 止损价超过入场价 | PAS_E005 | P1 | 使用默认止损，记录警告 | 否 |
| 数据库写入失败 | PAS_E006 | P0 | 重试3次后抛出异常 | ✅(3次) |
| 代码检测到MA等技术指标 | PAS_E007 | P0 | 立即终止，抛出 IronLawViolationError | 否 |

### 6.2 铁律违规检测

```python
class IronLawViolationError(Exception):
    """铁律违规异常"""
    pass

FORBIDDEN_PATTERNS = [
    r"\.rolling\([^)]*\)\.mean\(",  # MA
    r"\.ewm\(",  # EMA
    r"ta\.SMA\(", r"ta\.EMA\(", r"ta\.WMA\(",  # TA-Lib均线
    r"ta\.RSI\(", r"ta\.MACD\(", r"ta\.BOLL\(",  # TA-Lib指标
    r"ta\.KDJ\(", r"ta\.ATR\(",
]

def check_iron_law_compliance(code: str) -> bool:
    """检查代码是否违反铁律"""
    import re
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, code):
            return False
    return True
```

### 6.3 重试策略

```python
PAS_RETRY_CONFIG = {
    "db_write": {
        "max_retries": 3,
        "base_delay": 1.0,
        "exponential": True,
        "max_delay": 10.0
    }
}
```

---

## 7. 质量监控

### 7.1 每日质量检查项

| 检查项 | 检查方法 | 预期结果 | 告警阈值 |
|--------|----------|----------|----------|
| 铁律合规 | 代码扫描 | 无MA/EMA/RSI等 | 任何违规 |
| 股票数量 | COUNT(*) | ~5000 | < 4500 |
| 评分范围 | opportunity_score | ∈ [0, 100] | 越界 |
| 等级分布 | 各等级比例 | 近似正态分布 | S级>5% |
| 权重总和 | 20+50+30 | = 100 | ≠ 100 |
| 连续性 | 与前一交易日间隔 | ≤ 1个交易日 | 缺失 |

### 7.2 质量监控表

```sql
CREATE TABLE pas_quality_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date VARCHAR(8) NOT NULL,
    check_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- 铁律检查
    iron_law_compliant BOOLEAN NOT NULL,
    
    -- 检查结果
    stock_count INTEGER,
    score_range_valid BOOLEAN,
    grade_distribution_valid BOOLEAN,
    weight_sum_valid BOOLEAN,
    continuity_valid BOOLEAN,
    
    -- 等级分布
    grade_s_count INTEGER,
    grade_a_count INTEGER,
    grade_b_count INTEGER,
    grade_c_count INTEGER,
    grade_d_count INTEGER,
    
    -- 异常信息
    error_code VARCHAR(20),
    error_message TEXT,
    
    -- 状态
    status VARCHAR(20) DEFAULT 'PASS',
    
    UNIQUE(trade_date)
);
```

---

## 8. 执行计划

### 8.1 Task 级别详细计划

---

#### Task 1: 牛股基因因子

**目标**: 实现涨停统计、新高统计、最大涨幅三个子因子

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| raw_daily | Phase 01 | pct_chg/close存在 | 阻断 |
| raw_limit_list | Phase 01 | 涨停数据存在 | 阻断 |
| 历史数据120日 | Phase 01 | 用于涨停统计 | 缩短窗口 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| LimitUpCalculator | 代码 | 120日涨停统计 | `src/algorithms/pas/` |
| NewHighCalculator | 代码 | 60日新高统计 | `src/algorithms/pas/` |
| MaxGainCalculator | 代码 | 历史最大涨幅 | `src/algorithms/pas/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 因子范围 | [0,100] | 边界测试 |
| 权重分配 | 40%+30%+30%=100% | 单元测试 |
| 股票覆盖 | ~5000只 | COUNT检查 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 历史数据不足 | 缩短窗口 | 记录警告 |
| 涨停数据缺失 | 因子设为0 | 记录警告 |

**验收检查**

- [ ] 涨停统计因子正确（120日）
- [ ] 新高统计因子正确（60日）
- [ ] 最大涨幅因子正确
- [ ] 牛股基因因子=40%+30%+30%

---

#### Task 2: 结构位置因子（⚠️铁律合规）

**目标**: 实现价格位置、趋势延续、突破强度三个子因子（禁用MA）

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| raw_daily | Phase 01 | OHLC数据存在 | 阻断 |
| 历史数据60日 | Phase 01 | 用于高低点 | 阻断 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| PricePositionCalculator | 代码 | (close-low)/(high-low) | `src/algorithms/pas/` |
| TrendContinuityCalculator | 代码 | 连续上涨天数 | `src/algorithms/pas/` |
| BreakoutStrengthCalculator | 代码 | 相对前高突破 | `src/algorithms/pas/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 铁律合规 | 无MA/EMA/SMA | 代码扫描 |
| 因子范围 | [0,100] | 边界测试 |
| 权重分配 | 40%+30%+30%=100% | 单元测试 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 价格区间为零 | 位置设为50 | 记录警告 |
| 铁律违规 | 立即阻断 | 代码回滚 |

**验收检查**

- [ ] 价格位置因子正确（无MA）
- [ ] 趋势延续因子正确（天数统计）
- [ ] 突破强度因子正确（相对前高）
- [ ] **铁律检查通过**

---

#### Task 3: 行为确认因子

**目标**: 实现量比、涨跌幅、涨停判断三个子因子

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| raw_daily | Phase 01 | vol/pct_chg存在 | 阻断 |
| raw_daily_basic | Phase 01 | turnover_rate存在 | 用vol替代 |
| raw_limit_list | Phase 01 | 涨停标识存在 | 阻断 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| VolumeRatioCalculator | 代码 | 量比=当日/近20日均量 | `src/algorithms/pas/` |
| PctChgScoreCalculator | 代码 | 涨幅归一化 | `src/algorithms/pas/` |
| LimitUpJudge | 代码 | 涨停判断 | `src/algorithms/pas/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 因子范围 | [0,100] | 边界测试 |
| 权重分配 | 40%+30%+30%=100% | 单元测试 |
| 量比计算 | vol/volume_avg_20d | 单元测试 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 成交量为零 | 量比设为1 | 记录警告 |
| 涨跌幅异常 | 截断到[-20,20] | 记录警告 |

**验收检查**

- [ ] 量比因子正确
- [ ] 涨跌幅因子正确
- [ ] 涨停判断因子正确
- [ ] 行为确认因子=40%+30%+30%

---

#### Task 4: 综合评分与落库

**目标**: 实现三因子加权评分、等级判定、方向判断、数据落库

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| 牛股基因因子 | Task 1 | 测试通过 | 阻断 |
| 结构位置因子 | Task 2 | 测试通过+铁律通过 | 阻断 |
| 行为确认因子 | Task 3 | 测试通过 | 阻断 |
| DuckDB连接 | Phase 01 | 可连接 | 阻断 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| PasScoreCalculator | 代码 | 20%+50%+30%=100% | `src/algorithms/pas/` |
| GradeClassifier | 代码 | S/A/B/C/D | `src/algorithms/pas/` |
| DirectionJudge | 代码 | bullish/bearish/neutral | `src/algorithms/pas/` |
| PasRepository | 代码 | 幂等写入 | `src/algorithms/pas/` |
| stock_pas_daily表 | 数据 | ~5000股票/日 | L3 DuckDB（按年分库） |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 覆盖率 | ≥80% | `pytest --cov` |
| 股票数 | ~5000 | COUNT检查 |
| 幂等性 | 重复写入不报错 | 单元测试 |
| 铁律合规 | 无技术指标 | 代码扫描 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 评分越界 | 截断到[0,100] | 记录警告 |
| DB写入失败 | 重试3次 | 失败后抛异常 |
| 股票数不足 | 记录警告 | <4500时警告 |

**验收检查**

- [ ] 三因子权重合=100%（20%+50%+30%）
- [ ] 评分范围[0,100]
- [ ] 等级判定正确（S≥85, A≥70, B≥55, C≥40, D<40）
- [ ] 方向判断正确
- [ ] 测试覆盖率≥80%
- [ ] **M4里程碑完成**

### 8.2 每日执行时序

```text
17:00  raw_daily/raw_limit_list 数据就绪（Phase 01）
  ↓
17:16  IRS 计算完成（Phase 03）
  ↓
17:17  触发 PAS 计算
  ↓
17:17  加载 ~5000 只可交易股票日线数据
  ↓
17:18  计算历史统计数据（涨停次数、新高次数等）
  ↓
17:19  计算牛股基因因子
  ↓
17:20  计算结构位置因子（铁律合规）
  ↓
17:21  计算行为确认因子
  ↓
17:22  加权求和得到综合评分
  ↓
17:22  判定等级与方向
  ↓
17:22  计算风险收益比
  ↓
17:23  写入 stock_pas_daily
  ↓
17:24  质量检查（含铁律合规检查）
  ↓
17:24  PAS 计算完成，通知 Phase 05 (Integration)
```

---

## 9. 验收检查清单

### 9.1 铁律验收（零容忍）

- [ ] **零技术指标**: 代码中无 MA/EMA/SMA/RSI/MACD/BOLL/KDJ/ATR
- [ ] **价格区间计算**: 使用 (close-low)/(high-low) 而非 close/MA
- [ ] **pre-commit hook**: 配置技术指标检测
- [ ] **代码审查**: 人工确认铁律合规

### 9.2 功能验收

- [ ] 牛股基因因子计算正确（涨停×0.4 + 新高×0.3 + 最大涨幅×0.3）
- [ ] 结构位置因子计算正确（价格位置×0.4 + 趋势延续×0.3 + 突破强度×0.3）
- [ ] 行为确认因子计算正确（量比×0.4 + 涨幅×0.3 + 涨停×0.3）
- [ ] 综合评分计算正确（20%+50%+30%）
- [ ] 等级判定正确（S≥85, A≥70, B≥55, C≥40, D<40）
- [ ] 方向判断正确（价格位置+连续天数）
- [ ] 风险收益比计算正确（价格高低点，非ATR）

### 9.3 质量验收

- [ ] 测试覆盖率 ≥ 80%
- [ ] ~5000只可交易股票全覆盖
- [ ] 所有因子得分 ∈ [0, 100]
- [ ] opportunity_score ∈ [0, 100]
- [ ] opportunity_grade ∈ {S, A, B, C, D}
- [ ] direction ∈ {bullish, bearish, neutral}
- [ ] 历史数据回填完整

### 9.4 性能验收

- [ ] 全市场计算 ≤ 5分钟
- [ ] 批量计算（1年）≤ 30分钟
- [ ] 数据库写入幂等

---

## 10. 参数配置表

### 10.1 因子权重（固定）

| 因子 | 权重 | 说明 |
|------|------|------|
| 牛股基因 | 20% | 历史强势惯性 |
| 结构位置 | 50% | 价格位置决定风险收益比 |
| 行为确认 | 30% | 量价配合验证有效性 |

### 10.2 算法参数

| 参数名称 | 代码 | 默认值 | 可调范围 | 说明 |
|----------|------|--------|----------|------|
| 涨停统计窗口 | limit_up_window | 120 | 60-250 | 近120日涨停统计 |
| 新高统计窗口 | new_high_window | 60 | 20-120 | 近60日新高统计 |
| 价格区间窗口 | price_range_window | 60 | 20-120 | 60日高低点 |
| 量比窗口 | volume_ma_window | 20 | 10-60 | 20日平均量 |
| 趋势窗口 | trend_window | 20 | 5-40 | 趋势延续判断 |
| 默认止损比例 | default_stop_pct | 8% | 5%-15% | 止损百分比 |
| 目标风险收益比 | target_ratio | 2.0 | 1.5-3.0 | 默认2:1 |

### 10.3 等级阈值

| 等级 | 阈值 | 说明 |
|------|------|------|
| S | ≥ 85 | 极佳机会 |
| A | ≥ 70 | 优质机会 |
| B | ≥ 55 | 普通机会 |
| C | ≥ 40 | 观望 |
| D | < 40 | 回避 |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v4.0.2 | 2026-02-06 | 输入依赖与执行时序统一为 Data Layer raw_* 表命名 |
| v4.0.1 | 2026-02-04 | 术语去MA化并统一 DuckDB 存储口径 |
| v4.0.0 | 2026-02-02 | 完整重构：添加量化验收标准、I/O规范、错误处理、铁律检查 |
| v3.0.0 | 2026-01-31 | 重构版：移除MA计算，使用价格区间 |


