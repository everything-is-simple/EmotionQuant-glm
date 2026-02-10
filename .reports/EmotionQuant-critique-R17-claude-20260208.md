# EmotionQuant 设计文档 Review — R17

**审查人**: Claude (Agent Mode)
**日期**: 2026-02-08
**范围**: 核心算法四位一体内部一致性（MSS/IRS/PAS/Integration 各自的 algorithm ↔ data-models ↔ api ↔ information-flow）
**累计**: R1-R16 = 149 issues，R17 = 10 issues（✅ 已闭环 10/10）
**复查结论**: ✅ 本轮 10 项问题均已修复并完成文档对齐

---

## 审查维度

逐模块对比 algorithm、data-models、api、information-flow 四份文档：
- 示例数据是否与算法公式匹配
- DDL 字段是否覆盖算法所有输出
- 依赖字段名是否与 DataClass 对齐
- API 方法归属是否与职责分层一致
- 枚举/注释是否与算法定义完全对应

---

## P1 Issues（必须修复）

### ~~P1-R17-01: MSS info-flow §4.2 示例周期判定错误~~ ✅ 已修复

**文件**: `docs/design/core-algorithms/mss/mss-information-flow.md` (line 337)

**现状**: 示例输出为 `cycle: "acceleration"`，对应温度 63.21、趋势 up。

**问题**: 根据 `mss-algorithm.md` §5.2 周期判定伪代码：
- temperature = 63.21 **不满足** `< 60`（acceleration 条件）
- temperature ∈ [60, 75) 且 trend == "up" → 应返回 **divergence**（分歧期）

acceleration 仅适用于 `45 ≤ temperature < 60 + up`。

**修复**: `cycle: "acceleration"` → `cycle: "divergence"`

---

### ~~P1-R17-02: IRS info-flow §5.2 PAS 协同阈值未同步~~ ✅ 已修复

**文件**: `docs/design/core-algorithms/irs/irs-information-flow.md` (line 359)

**现状**: "PAS 评分 ≥ 80 的个股优先从超配行业选择"

**问题**: `irs-algorithm.md` §10.2 在 R8（v3.2.5）已修复为 "PAS S级（评分 ≥ 85）的个股优先从超配行业中选择"。info-flow 遗漏同步，仍为旧值 ≥ 80。

**修复**: `PAS 评分 ≥ 80` → `PAS 评分 ≥ 85（S级）`

---

### ~~P1-R17-03: MSS DDL `mss_factor_intermediate` 单对 mean/std 无法覆盖 6 因子~~ ✅ 已修复

**文件**: `docs/design/core-algorithms/mss/mss-data-models.md` (lines 216-217)

**现状**: 表中仅有一对 `zscore_mean` / `zscore_std` 列。

**问题**: MSS 有 6 个因子（大盘系数、赚钱效应、亏钱效应、连续性、极端、波动），每个因子各自有独立的 mean/std 统计参数。单对 mean/std 列无法存储 6 个因子的独立参数。

**修复方案（二选一）**:
- A) 拆为 6 对列：`market_coefficient_mean`, `market_coefficient_std`, `profit_effect_mean`, `profit_effect_std`, ...
- B) 改为独立的 zscore_baseline 表：`(trade_date, factor_name, mean, std)` 一行一因子

---

### ~~P1-R17-04: MSS data-model `MssPanorama` 含 rank/percentile 但无算法计算定义~~ ✅ 已修复

**文件**: `docs/design/core-algorithms/mss/mss-data-models.md` (lines 128-129)

**现状**: `MssPanorama` 输出模型包含：
- `rank: int  # 历史排名`
- `percentile: float  # 百分位排名 0-100`

DDL `mss_panorama` 表也有对应列。

**问题**: `mss-algorithm.md` 和 `mss-information-flow.md` 的 7 个 Step 中均未定义 `rank` 和 `percentile` 的计算公式或来源（历史排名是对温度排名？对因子排名？百分位基于多长历史？）。字段存在但计算逻辑悬空。

**修复**: 在 `mss-algorithm.md` 中补充 rank/percentile 的计算定义（建议放在 §6 中性度计算 之后），或从数据模型和 DDL 中移除这两个字段。

---

### ~~P1-R17-05: IRS data-models §1.2 依赖字段名 `turnover_rate` 与实际字段 `industry_turnover` 不一致~~ ✅ 已修复

**文件**: `docs/design/core-algorithms/irs/irs-data-models.md` (line 30)

**现状**: §1.2 数据字段依赖表中，资金流向因子的依赖字段写为 `industry_amount, turnover_rate`。

**问题**:
1. `IrsIndustrySnapshot` 中实际字段名为 `industry_turnover`（非 `turnover_rate`）
2. `irs-algorithm.md` §3.3 资金流向因子公式 `net_inflow_10d = Σ(industry_amount_delta, window=10)` **不直接使用** turnover/industry_turnover（仅成交额增量）
3. `relative_volume` 使用的是 `industry_amount / industry_amount_avg_20d`，也不是 turnover

**修复**: §1.2 将 `turnover_rate` 改为 `industry_amount`（移除 turnover 依赖，因因子公式未使用）；如果 `industry_turnover` 字段仍需保留在 Snapshot 供协同层使用，添加注释说明用途。

---

## P2 Issues（建议修复）

### ~~P2-R17-06: MSS DDL `mss_alert_log.alert_type` 枚举缺少 `tail_activity`~~ ✅ 已修复

**文件**: `docs/design/core-algorithms/mss/mss-data-models.md` (line 234)

**现状**: DDL 注释 `'预警类型：overheat/overcool/divergence'`（3 种）

**问题**: `mss-algorithm.md` §9 定义了 **4** 种预警规则：
- 过热预警 → overheat ✓
- 过冷预警 → overcool ✓
- **尾部活跃** → 缺失（应为 `tail_activity`）
- 趋势背离 → divergence ✓

**修复**: DDL 注释补充 `tail_activity`：`'预警类型：overheat/overcool/tail_activity/divergence'`

---

### ~~P2-R17-07: PAS API `get_by_industry` 在 Calculator 而非 Repository~~ ✅ 已修复

**文件**: `docs/design/core-algorithms/pas/pas-api.md` (lines 61-63 vs 80-87)

**现状**: `PasCalculator` 包含 `get_by_industry(trade_date, industry_code)` 方法。`PasRepository` 仅有 `get_by_date` 和 `get_by_stock`。

**问题**: 按数据查询行业是数据访问职责，应归属 Repository。对比 IRS 模块：`IrsRepository` 有 `get_by_industry` 方法（line 79）。PAS 的设计与 IRS 不一致。

**修复**: 将 `get_by_industry` 从 `PasCalculator` 移至 `PasRepository`。

---

### ~~P2-R17-08: Integration API `weight_plan` 参数类型与 data-model `WeightPlan` 不一致~~ ✅ 已修复

**文件**: `docs/design/core-algorithms/integration/integration-api.md` (line 37)

**现状**: `IntegrationEngine.calculate()` 的参数 `weight_plan: dict[str, float]`

**问题**: `integration-data-models.md` §2.5 定义了 `WeightPlan` dataclass（含 `plan_id`, `w_mss`, `w_irs`, `w_pas`），但 API 使用 raw `dict` 而非 `WeightPlan`。丢失了 `plan_id` 追溯信息，且类型安全性不足。

**修复**: 将参数类型改为 `weight_plan: WeightPlan`。

---

### ~~P2-R17-09: PAS data-model `PasGrade` 枚举注释边界表述含糊~~ ✅ 已修复

**文件**: `docs/design/core-algorithms/pas/pas-data-models.md` (lines 134-138)

**现状**: `A = "A"    # 70-84，优质机会`

**问题**: "70-84" 不明确 84.5 归入 A 还是 S。`pas-algorithm.md` §5.1 和 `pas-information-flow.md` §2.4 均使用精确边界 `70 ≤ score < 85`。枚举注释应与算法一致。

**修复**: 统一为半开区间表述：
- `S = "S"  # ≥85`
- `A = "A"  # [70, 85)`
- `B = "B"  # [55, 70)`
- `C = "C"  # [40, 55)`
- `D = "D"  # <40`

---

### ~~P2-R17-10: Integration DDL `integrated_recommendation` 缺少 `consistency` 追溯字段~~ ✅ 已修复

**文件**: `docs/design/core-algorithms/integration/integration-data-models.md` (lines 209-248)

**现状**: DDL 中有 `direction`、`integration_mode`、`validation_gate` 等追溯字段，但缺少 `consistency`（方向一致性）。

**问题**: `integration-algorithm.md` §4.2 和 info-flow §2.4 定义了方向一致性判定 `consistent/partial/divergent`，其结果影响 `strength_factor` 和 `neutrality`。data-model 也定义了 `DirectionConsistency` 枚举（§3.3），但 DDL 未持久化该字段。调试或回溯时无法直接查询某日某股的方向一致性。

**修复**: 在 DDL `integrated_recommendation` 表中添加：
```sql
consistency VARCHAR(20) COMMENT '方向一致性 consistent/partial/divergent',
```

---

## 汇总

| ID | 严重度 | 模块 | 文件对 | 问题简述 |
|----|--------|------|--------|----------|
| P1-R17-01 | P1 | MSS | algorithm ↔ info-flow | 示例 cycle 判定错误（acceleration→divergence） |
| P1-R17-02 | P1 | IRS | algorithm ↔ info-flow | PAS 协同阈值 ≥80 未同步为 ≥85 |
| P1-R17-03 | P1 | MSS | algorithm ↔ DDL | factor_intermediate 单对 mean/std 不够 6 因子 |
| P1-R17-04 | P1 | MSS | data-model ↔ algorithm | rank/percentile 无算法定义 |
| P1-R17-05 | P1 | IRS | data-model §1.2 ↔ DataClass ↔ algorithm | turnover_rate 字段名不一致且未被使用 |
| P2-R17-06 | P2 | MSS | DDL ↔ algorithm | alert_type 枚举缺少 tail_activity |
| P2-R17-07 | P2 | PAS | API Calculator ↔ Repository | get_by_industry 方法归属不一致 |
| P2-R17-08 | P2 | Integration | API ↔ data-model | weight_plan 参数类型 dict vs WeightPlan |
| P2-R17-09 | P2 | PAS | data-model ↔ algorithm | PasGrade 注释边界含糊 |
| P2-R17-10 | P2 | Integration | DDL ↔ algorithm/enum | 缺少 consistency 追溯字段 |

---

**累计统计**: R1-R17 共 159 issues（R1-R16: 149 + R17: 10）

---

## 复查纠偏记录（2026-02-08）

- ~~P1-R17-01~~：`mss-information-flow.md` 示例周期由 `acceleration` 修正为 `divergence`。
- ~~P1-R17-02~~：`irs-information-flow.md` IRS→PAS 协同阈值由 `PAS≥80` 修正为 `PAS≥85（S级）`。
- ~~P1-R17-03~~：`mss-data-models.md` `mss_factor_intermediate` 扩展为 6 因子独立 `mean/std` 列。
- ~~P1-R17-04~~：`mss-algorithm.md` 新增 `rank/percentile` 的历史计算定义与约束。
- ~~P1-R17-05~~：`irs-data-models.md` 资金流向依赖改为 `industry_amount` 相关字段，并补充 `industry_turnover` 辅助观测说明。
- ~~P2-R17-06~~：`mss-data-models.md` `mss_alert_log.alert_type` 补齐 `tail_activity` 枚举值。
- ~~P2-R17-07~~：`pas-api.md` 将 `get_by_industry` 从 `PasCalculator` 迁移至 `PasRepository`。
- ~~P2-R17-08~~：`integration-api.md` `weight_plan` 参数类型由 `dict` 统一为 `WeightPlan`。
- ~~P2-R17-09~~：`pas-data-models.md` `PasGrade` 注释改为半开区间（如 `[70,85)`）。
- ~~P2-R17-10~~：`integration-data-models.md` 数据类与 DDL 同步补齐 `consistency` 追溯字段。
