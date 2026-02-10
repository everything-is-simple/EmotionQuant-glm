# Integration 数据模型

**版本**: v3.4.10（重构版）
**最后更新**: 2026-02-09
**状态**: 设计完成（验收口径补齐；代码未落地）

---

## 1. 数据依赖

### 1.1 上游系统依赖

| 系统 | 输出表 | 关键字段 |
|------|--------|----------|
| MSS | mss_panorama | temperature, cycle, trend, neutrality |
| IRS | irs_industry_daily | industry_score, rotation_status, allocation_advice, quality_flag, sample_days |
| PAS | stock_pas_daily | opportunity_score, opportunity_grade, direction |
| Validation | validation_gate_decision / weight_plan | final_gate, selected_weight_plan, w_mss, w_irs, w_pas |

---
### 1.2 BU 模式派生聚合（可选）

| 来源 | 派生表/视图 | 关键字段 |
|------|------------|----------|
| PAS | pas_breadth_daily（由 stock_pas_daily 聚合） | pas_sa_count, pas_sa_ratio, pas_grade_distribution, industry_sa_count, industry_sa_ratio, industry_top_k_concentration |

---

## 2. 输入数据模型

### 2.1 MSS输入（MssInput）

```python
@dataclass
class MssInput:
    """MSS输入数据"""
    trade_date: str              # 交易日期
    temperature: float           # 市场温度 0-100
    cycle: str                   # 周期（英文）
    trend: str                   # 趋势 up/down/sideways
    position_advice: str         # 仓位建议
    neutrality: float            # 中性度 0-1
```

### 2.2 IRS输入（IrsInput）

```python
@dataclass
class IrsInput:
    """IRS输入数据"""
    trade_date: str              # 交易日期
    industry_code: str           # 行业代码
    industry_name: str           # 行业名称
    industry_score: float        # 行业评分 0-100
    rotation_status: str         # 轮动状态 IN/OUT/HOLD
    allocation_advice: str       # 配置建议
    quality_flag: str            # 质量标记 normal/cold_start/stale
    sample_days: int             # 有效样本天数
    neutrality: float            # 中性度 0-1
```

### 2.3 PAS输入（PasInput）

```python
@dataclass
class PasInput:
    """PAS输入数据"""
    trade_date: str              # 交易日期
    stock_code: str              # 股票代码（L2+）
    stock_name: str              # 股票名称
    industry_code: str           # 所属行业
    opportunity_score: float     # 机会评分 0-100
    opportunity_grade: str       # 机会等级 S/A/B/C/D
    direction: str               # 方向 bullish/bearish/neutral
    risk_reward_ratio: float     # 风险收益比
    entry: float                 # 入场价
    stop: float                  # 止损价
    target: float                # 目标价
    neutrality: float            # 中性度 0-1
```

---
### 2.4 PAS广度聚合输入（BU入口，可选）

```python
@dataclass
class PasBreadthMarketInput:
    """PAS市场广度（全市场聚合）"""
    trade_date: str              # 交易日期
    pas_sa_count: int            # S/A数量
    pas_sa_ratio: float          # S/A占比
    pas_grade_distribution: dict # S/A/B/C/D分布


@dataclass
class PasBreadthIndustryInput:
    """PAS行业广度（行业聚合）"""
    trade_date: str              # 交易日期
    industry_code: str           # 行业代码
    industry_name: str           # 行业名称
    industry_sa_count: int       # 行业内S/A数量
    industry_sa_ratio: float     # 行业内S/A占比
    industry_top_k_concentration: float  # TopK行业S/A集中度
```

---
### 2.5 权重方案输入（WeightPlan）

```python
@dataclass
class WeightPlan:
    """Validation 通过后的权重方案"""
    plan_id: str                 # baseline / candidate_id
    w_mss: float                 # MSS权重
    w_irs: float                 # IRS权重
    w_pas: float                 # PAS权重
```

### 2.6 门禁决策输入（ValidationGateDecision）

```python
@dataclass
class ValidationGateDecision:
    """Validation Gate 决策结果（CP-05 前置输入）"""
    trade_date: str              # 交易日
    factor_gate: str             # PASS/WARN/FAIL
    weight_gate: str             # PASS/WARN/FAIL
    final_gate: str              # PASS/WARN/FAIL
    selected_weight_plan: str    # baseline / candidate_id
    stale_days: int              # 距离上次有效验证天数
    fallback_plan: str           # FAIL/WARN 时回退策略
    reason: str                  # 决策原因
    created_at: datetime         # 决策生成时间（审计追溯）
```

---

## 3. 输出数据模型

### 3.1 集成结果（IntegratedRecommendation）

```python
@dataclass
class IntegratedRecommendation:
    """集成推荐输出"""
    trade_date: str              # 交易日期
    stock_code: str              # 股票代码（L2+）
    stock_name: str              # 股票名称
    industry_code: str           # 所属行业
    industry_name: str           # 行业名称
    
    # 追溯信息
    integration_mode: str        # top_down/bottom_up/dual_verify/complementary
    weight_plan_id: str          # baseline/candidate_id
    w_mss: float                 # 当次权重快照
    w_irs: float                 # 当次权重快照
    w_pas: float                 # 当次权重快照
    validation_gate: str         # PASS/WARN/FAIL
    
    # 三系统输入评分
    mss_score: float             # MSS评分（温度）
    mss_cycle: str               # MSS周期（追溯 STRONG_BUY 条件）
    irs_score: float             # IRS行业评分
    pas_score: float             # PAS机会评分
    opportunity_grade: str       # PAS机会等级快照 S/A/B/C/D
    
    # 集成输出
    final_score: float           # 综合评分 0-100
    direction: str               # 综合方向 bullish/bearish/neutral
    consistency: str             # 方向一致性 consistent/partial/divergent
    recommendation: str          # 推荐等级 STRONG_BUY/BUY/HOLD/SELL/AVOID
    position_size: float         # 仓位建议 0-1
    
    # 交易参考
    entry: float                 # 入场价
    stop: float                  # 止损价
    target: float                # 目标价
    risk_reward_ratio: float     # 风险收益比
    
    # 辅助信息
    neutrality: float            # 综合中性度
```

### 3.2 推荐等级枚举

```python
class Recommendation(Enum):
    """推荐等级枚举（大写存储）"""
    STRONG_BUY = "STRONG_BUY"   # ≥75分 + MSS周期∈{emergence,fermentation}
    BUY = "BUY"                  # ≥70分且不满足 STRONG_BUY 附加条件
    HOLD = "HOLD"                # 50-69分
    SELL = "SELL"                # 30-49分
    AVOID = "AVOID"              # <30分
```

### 3.3 方向一致性枚举

```python
class DirectionConsistency(Enum):
    """方向一致性枚举"""
    CONSISTENT = "consistent"    # 三者一致
    PARTIAL = "partial"          # 两者一致
    DIVERGENT = "divergent"      # 各不相同
```

---

## 4. 数据库表结构

> 以下为 **MySQL 风格逻辑DDL（伪代码）**，用于表达字段与约束语义，**不可直接在 DuckDB 执行**。  
> DuckDB 落地时请改写为 `CREATE TABLE ...` + `CREATE INDEX ...`，字段注释改为独立文档或 `COMMENT ON` 形式。

### 4.1 主表：integrated_recommendation

> **命名规范**：与顶层架构统一，详见 [naming-conventions.md](../../../naming-conventions.md)

```sql
CREATE TABLE integrated_recommendation (
    id INTEGER PRIMARY KEY,
    trade_date VARCHAR(8) NOT NULL COMMENT '交易日期 YYYYMMDD',
    stock_code VARCHAR(20) NOT NULL COMMENT '股票代码',
    stock_name VARCHAR(50) COMMENT '股票名称',
    industry_code VARCHAR(10) COMMENT '行业代码',
    industry_name VARCHAR(50) COMMENT '行业名称',
    
    -- 三系统输入
    mss_score DECIMAL(8,4) COMMENT 'MSS温度',
    irs_score DECIMAL(8,4) COMMENT 'IRS行业评分',
    pas_score DECIMAL(8,4) COMMENT 'PAS机会评分',
    
    -- 集成输出
    final_score DECIMAL(8,4) COMMENT '综合评分 0-100',
    direction VARCHAR(20) COMMENT '综合方向',
    consistency VARCHAR(20) COMMENT '方向一致性 consistent/partial/divergent',
    integration_mode VARCHAR(20) COMMENT '集成模式 top_down/bottom_up/dual_verify/complementary',
    weight_plan_id VARCHAR(40) COMMENT '权重方案ID（baseline/candidate）',
    w_mss DECIMAL(6,4) COMMENT 'MSS权重快照',
    w_irs DECIMAL(6,4) COMMENT 'IRS权重快照',
    w_pas DECIMAL(6,4) COMMENT 'PAS权重快照',
    validation_gate VARCHAR(10) COMMENT '验证门禁 PASS/WARN/FAIL',
    recommendation VARCHAR(20) COMMENT '推荐等级',
    position_size DECIMAL(8,4) COMMENT '仓位建议',
    mss_cycle VARCHAR(20) COMMENT '当日MSS周期（追溯STRONG_BUY条件）',
    opportunity_grade VARCHAR(10) COMMENT 'PAS机会等级快照 S/A/B/C/D',
    
    -- 交易参考
    entry DECIMAL(12,4) COMMENT '入场价',
    stop DECIMAL(12,4) COMMENT '止损价',
    target DECIMAL(12,4) COMMENT '目标价',
    risk_reward_ratio DECIMAL(8,4) COMMENT '风险收益比',
    
    -- 辅助信息
    neutrality DECIMAL(8,4) COMMENT '综合中性度 0-1（越接近1越中性，越接近0信号越极端）',
    
    -- 元数据
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_trade_date_stock_code (trade_date, stock_code),
    KEY idx_final_score (final_score),
    KEY idx_recommendation (recommendation),
    KEY idx_validation_gate (validation_gate)
);
```

> 推荐输出统一为 `integrated_recommendation`，不再单列 `daily_recommendation` 表。

---

## 5. 数据验证规则

### 5.1 输入验证

| 字段 | 验证规则 |
|------|----------|
| mss_score | 0 ≤ x ≤ 100 |
| irs_score | 0 ≤ x ≤ 100 |
| pas_score | 0 ≤ x ≤ 100 |
| w_mss / w_irs / w_pas | 各自 ≥ 0，且总和 = 1，且单模块权重 ≤ MAX_MODULE_WEIGHT（0.60） |
| validation_gate_decision.final_gate | IN ('PASS', 'WARN', 'FAIL')；`FAIL` 时不得进入 Integration |
| irs_input.quality_flag | IN ('normal', 'cold_start', 'stale') |
| irs_input.sample_days | x ≥ 0 |

### 5.2 输出验证

| 字段 | 验证规则 |
|------|----------|
| final_score | 0 ≤ x ≤ 100 |
| integration_mode | IN ('top_down', 'bottom_up', 'dual_verify', 'complementary') |
| validation_gate | IN ('PASS', 'WARN', 'FAIL') |
| mss_cycle | IN ('emergence', 'fermentation', 'acceleration', 'divergence', 'climax', 'diffusion', 'recession', 'unknown') |
| recommendation | IN ('STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'AVOID') |
| position_size | 0 ≤ x ≤ 1 |
| neutrality | 0 ≤ x ≤ 1 |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.4.10 | 2026-02-09 | 修复 R29：`ValidationGateDecision` 补齐 `created_at` 字段，与 Validation 模块定义一致 |
| v3.4.9 | 2026-02-09 | 修复 R28：主表 DDL 的 `trade_date` 统一为 `VARCHAR(8)`；`stock_code/stock_name/industry_name/opportunity_grade` 宽度与 Data Layer 对齐；时间戳命名统一为 `created_at` 并移除 `update_time` |
| v3.4.8 | 2026-02-09 | 修复 R26：§1.1/§2.2 增补 IRS `quality_flag/sample_days` 输入契约；§5.1 增加质量字段校验规则；§5.2 输出验证补齐 `mss_cycle=unknown` 合法值 |
| v3.4.7 | 2026-02-08 | 修复 R18：`IntegratedRecommendation` 与 DDL 补齐 `mss_cycle`、`w_mss/w_irs/w_pas`、`opportunity_grade` 追溯字段，提升 STRONG_BUY 与权重审计能力 |
| v3.4.6 | 2026-02-08 | 修复 R17：`IntegratedRecommendation` 与 DDL 补齐 `consistency` 追溯字段（consistent/partial/divergent） |
| v3.4.5 | 2026-02-08 | 修复 R11：补充 `MAX_MODULE_WEIGHT` 数值口径（0.60），避免跨文档常量悬空 |
| v3.4.4 | 2026-02-07 | 修复 P2：DDL 明确标注为 DuckDB 不可直接执行的逻辑伪代码 |
| v3.4.3 | 2026-02-07 | 修复 P2：补齐 Validation Gate 与 weight_plan 数据模型（输入类型、追溯字段、验证规则）并与 v3.4.x 对齐 |
| v3.3.1 | 2026-02-07 | 同步 STRONG_BUY 阈值口径（75 分） |
| v3.3.0 | 2026-02-04 | 同步 Integration v3.3.0：验收口径与协同约束语义对齐 |
| v3.0.0 | 2026-01-31 | 重构版：统一数据模型、添加方向一致性字段 |

---

**关联文档**：
- 算法设计：[integration-algorithm.md](./integration-algorithm.md)
- API接口：[integration-api.md](./integration-api.md)
- 信息流：[integration-information-flow.md](./integration-information-flow.md)
- 验证模块数据模型：[factor-weight-validation-data-models.md](../../validation/factor-weight-validation-data-models.md)


