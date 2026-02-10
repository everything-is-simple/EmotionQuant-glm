# 因子与权重验证数据模型

**版本**: v2.1.1  
**最后更新**: 2026-02-09  
**状态**: 设计完成（DuckDB 持久化为主，`.reports/validation/` 仅存放可读报告）

---

## 1. Python 数据模型（统一 `@dataclass` 风格）

### 1.1 ValidatedFactor（合法因子名枚举）

```python
class ValidatedFactor(Enum):
    """Validation 允许的因子名（跨 MSS/IRS/PAS）"""
    # MSS
    MSS_MARKET_COEFFICIENT = "mss_market_coefficient"
    MSS_PROFIT_EFFECT = "mss_profit_effect"
    MSS_LOSS_EFFECT = "mss_loss_effect"
    MSS_CONTINUITY_FACTOR = "mss_continuity_factor"
    MSS_EXTREME_FACTOR = "mss_extreme_factor"
    MSS_VOLATILITY_FACTOR = "mss_volatility_factor"

    # IRS
    IRS_RELATIVE_STRENGTH = "irs_relative_strength"
    IRS_CONTINUITY_FACTOR = "irs_continuity_factor"
    IRS_CAPITAL_FLOW = "irs_capital_flow"
    IRS_VALUATION = "irs_valuation"
    IRS_LEADER_SCORE = "irs_leader_score"
    IRS_GENE_SCORE = "irs_gene_score"

    # PAS
    PAS_BULL_GENE_SCORE = "pas_bull_gene_score"
    PAS_STRUCTURE_SCORE = "pas_structure_score"
    PAS_BEHAVIOR_SCORE = "pas_behavior_score"
```

### 1.2 FactorValidationResult

```python
@dataclass
class FactorValidationResult:
    trade_date: str              # 交易日 YYYYMMDD
    factor_name: str             # ValidatedFactor 枚举值
    factor_source: str           # mss/irs/pas
    window_id: str               # 验证窗口标识（如 2025Q4_w3）
    start_date: str              # YYYYMMDD
    end_date: str                # YYYYMMDD
    sample_count: int
    mean_ic: float
    mean_rank_ic: float
    icir: float
    positive_ic_ratio: float
    decay_1d: float
    decay_3d: float
    decay_5d: float
    decay_10d: float
    coverage_ratio: float
    decision: str                # PASS/WARN/FAIL
    reason: str
    created_at: datetime
```

### 1.3 WeightValidationResult

```python
@dataclass
class WeightValidationResult:
    trade_date: str              # 交易日 YYYYMMDD
    candidate_id: str            # 候选权重 ID
    window_id: str               # Walk-Forward 窗口
    w_mss: float
    w_irs: float
    w_pas: float
    oos_return: float
    max_drawdown: float
    sharpe: float
    turnover: float
    cost_sensitivity: float
    vs_baseline: str             # BETTER/EQUAL/WORSE
    decision: str                # PASS/WARN/FAIL
    reason: str
    created_at: datetime
```

### 1.4 ValidationGateDecision

```python
@dataclass
class ValidationGateDecision:
    trade_date: str              # 交易日 YYYYMMDD
    factor_gate: str             # PASS/WARN/FAIL
    weight_gate: str             # PASS/WARN/FAIL
    final_gate: str              # PASS/WARN/FAIL
    selected_weight_plan: str    # baseline/candidate_id（业务键）
    stale_days: int
    fallback_plan: str
    reason: str
    created_at: datetime
```

### 1.5 ValidationWeightPlan（Validation -> Integration 桥接对象）

```python
@dataclass
class ValidationWeightPlan:
    trade_date: str              # 交易日 YYYYMMDD
    plan_id: str                 # baseline/candidate_id
    w_mss: float
    w_irs: float
    w_pas: float
    source_candidate_id: str     # 来源候选（baseline 时可为空）
    created_at: datetime
```

### 1.6 ValidationRunManifest

```python
@dataclass
class ValidationRunManifest:
    trade_date: str              # 交易日 YYYYMMDD
    run_id: str
    run_type: str                # daily_gate/spiral_full/monthly_deep
    command: str
    test_command: str
    artifact_dir: str            # .reports/validation/{trade_date}/
    started_at: str
    finished_at: str
    status: str                  # SUCCESS/FAILED
    failed_reason: str
    created_at: datetime
```

### 1.7 ValidationConfig（配置注入，禁止阈值散落硬编码）

```python
@dataclass
class ValidationConfig:
    min_sample_count: int = 5000
    stale_days_threshold: int = 3

    ic_pass: float = 0.02
    ic_warn: float = 0.00
    icir_pass: float = 0.20
    icir_warn: float = 0.10
    positive_ic_ratio_pass: float = 0.55
    positive_ic_ratio_warn: float = 0.50
    coverage_pass: float = 0.95
    coverage_warn: float = 0.90

    wfa_train_days: int = 252
    wfa_validate_days: int = 63
    wfa_oos_days: int = 63
    max_weight_per_module: float = 0.60
    max_drawdown_tolerance: float = 0.02
```

---

## 2. 业务键与桥接规则

- `validation_gate_decision.selected_weight_plan` 仅存 `plan_id`（`baseline`/`candidate_xxx`）。
- Integration 入参 `WeightPlan` 由 `validation_weight_plan` 表按 `(trade_date, plan_id)` 解析得到。
- 若 `plan_id` 缺失：`final_gate=WARN` 时回退 `baseline`；`final_gate=FAIL` 直接阻断。

---

## 3. 数据库表结构

> 以下为 **MySQL 风格逻辑 DDL（伪代码）**，用于表达字段与约束语义，**不可直接在 DuckDB 执行**。

### 3.1 validation_factor_report

```sql
CREATE TABLE validation_factor_report (
    id INTEGER PRIMARY KEY,
    trade_date VARCHAR(8) NOT NULL,
    factor_name VARCHAR(64) NOT NULL,
    factor_source VARCHAR(10) NOT NULL,
    window_id VARCHAR(40) NOT NULL,
    start_date VARCHAR(8) NOT NULL,
    end_date VARCHAR(8) NOT NULL,
    sample_count INTEGER,
    mean_ic DECIMAL(10,6),
    mean_rank_ic DECIMAL(10,6),
    icir DECIMAL(10,6),
    positive_ic_ratio DECIMAL(10,6),
    decay_1d DECIMAL(10,6),
    decay_3d DECIMAL(10,6),
    decay_5d DECIMAL(10,6),
    decay_10d DECIMAL(10,6),
    coverage_ratio DECIMAL(10,6),
    decision VARCHAR(10),
    reason VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_trade_factor_window (trade_date, factor_name, window_id)
);
```

### 3.2 validation_weight_report

```sql
CREATE TABLE validation_weight_report (
    id INTEGER PRIMARY KEY,
    trade_date VARCHAR(8) NOT NULL,
    candidate_id VARCHAR(40) NOT NULL,
    window_id VARCHAR(40) NOT NULL,
    w_mss DECIMAL(8,6) NOT NULL,
    w_irs DECIMAL(8,6) NOT NULL,
    w_pas DECIMAL(8,6) NOT NULL,
    oos_return DECIMAL(12,6),
    max_drawdown DECIMAL(12,6),
    sharpe DECIMAL(12,6),
    turnover DECIMAL(12,6),
    cost_sensitivity DECIMAL(12,6),
    vs_baseline VARCHAR(10),
    decision VARCHAR(10),
    reason VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_trade_candidate_window (trade_date, candidate_id, window_id)
);
```

### 3.3 validation_gate_decision

```sql
CREATE TABLE validation_gate_decision (
    id INTEGER PRIMARY KEY,
    trade_date VARCHAR(8) NOT NULL,
    factor_gate VARCHAR(10) NOT NULL,
    weight_gate VARCHAR(10) NOT NULL,
    final_gate VARCHAR(10) NOT NULL,
    selected_weight_plan VARCHAR(40) NOT NULL,
    stale_days INTEGER NOT NULL,
    fallback_plan VARCHAR(50),
    reason VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_trade_date (trade_date)
);
```

### 3.4 validation_weight_plan（桥接表）

```sql
CREATE TABLE validation_weight_plan (
    id INTEGER PRIMARY KEY,
    trade_date VARCHAR(8) NOT NULL,
    plan_id VARCHAR(40) NOT NULL,
    w_mss DECIMAL(8,6) NOT NULL,
    w_irs DECIMAL(8,6) NOT NULL,
    w_pas DECIMAL(8,6) NOT NULL,
    source_candidate_id VARCHAR(40),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_trade_plan (trade_date, plan_id)
);
```

### 3.5 validation_run_manifest

```sql
CREATE TABLE validation_run_manifest (
    run_id VARCHAR(64) PRIMARY KEY,
    trade_date VARCHAR(8) NOT NULL,
    run_type VARCHAR(20) NOT NULL,
    command VARCHAR(500) NOT NULL,
    test_command VARCHAR(500),
    artifact_dir VARCHAR(200) NOT NULL,
    started_at DATETIME NOT NULL,
    finished_at DATETIME,
    status VARCHAR(20) NOT NULL,
    failed_reason VARCHAR(1000),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. 存储策略

- 权威持久化：`DuckDB`（上述 5 张表）。
- 报告落盘：`.reports/validation/{trade_date}/summary_{YYYYMMDD_HHMMSS}.md`。
- 可选导出：仅调试场景导出 parquet，非正式契约，不作为 Integration 读取源。

---

## 5. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v2.1.1 | 2026-02-09 | 修复 R30：`FactorValidationResult/WeightValidationResult/ValidationRunManifest` 补齐 `trade_date`；`ValidationRunManifest` 补齐 `created_at`，与 Validation DDL 对齐 |
| v2.1.0 | 2026-02-09 | 修复 R29：统一为 `@dataclass` 风格；新增 `ValidatedFactor` 与 `ValidationConfig`；补齐 5 张 DDL（含桥接表 `validation_weight_plan` 与 `validation_run_manifest`）；明确 DuckDB 为权威存储、`.reports` 仅报告 |
| v2.0.1 | 2026-02-09 | 修复 R28：`ValidationGateDecision` 增加 `created_at`；`selected_weight_plan` 注释补充“可从 weight_validation_report 查询权重值” |
