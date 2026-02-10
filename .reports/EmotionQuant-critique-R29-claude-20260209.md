# EmotionQuant 设计文档批判性审查 — 第 29 轮

**审查人**: Claude  
**日期**: 2026-02-09  
**范围**: Validation 模块深度审查 + 跨模块边缘一致性  
**累计**: R1-R28 共 271 项已修复；本轮新增 10 项  

---

## 审查摘要

本轮聚焦 Validation 模块（因子与权重验证）的四位一体文档内审，以及 Validation ↔ Integration / 系统铁律 / 数据架构之间的跨模块边缘一致性。发现 3 个 P1 问题（含一个铁律口径矛盾）和 7 个 P2 问题。

---

## P1 问题（高优先级）

### P1-R29-01 · system-overview §2 与系统铁律矛盾 — 技术指标可否用作特征

| 项目 | 内容 |
|------|------|
| 文件 | `docs/system-overview.md` §2 (line 22)、`docs/naming-conventions.md` §4 (line 125) |
| 冲突方 | `Governance/steering/系统铁律.md` §铁律一、`Governance/steering/CORE-PRINCIPLES.md` §1.1 |

**矛盾描述**：

- `system-overview.md` §2: _"单指标不得独立决策：技术指标可用于对照/特征，但不能单独触发交易。"_
- `naming-conventions.md` §4 PAS 铁律合规注释: _"MA等技术指标可用于对照或特征，但不得单独触发交易决策。"_
- `系统铁律` §铁律一: _"**绝对禁止**使用任何传统技术分析指标作为信号或**特征来源**。"_
- `CORE-PRINCIPLES` §1.1: _"禁止任何传统技术指标作为信号/**特征**来源"_

system-overview 和 naming-conventions 均表示 TA 指标**可用于对照/特征**，系统铁律和核心原则则**绝对禁止**其作为特征来源。这是关于技术指标边界的根本性分歧，直接影响 MSS/IRS/PAS 算法实现时的合规判定。

**建议修复**：
- 若铁律为权威：修改 system-overview §2 和 naming-conventions §4，删除"技术指标可用于对照/特征"表述，改为"情绪因子为唯一信号来源；传统技术指标禁止用于任何信号或特征"。
- 若 system-overview 为权威（允许对照）：修改系统铁律，将"特征来源"改为"决策来源"，并明确"对照/参考"的使用边界。

---

### P1-R29-02 · Validation 模块无持久化 DDL — 数据架构断层

| 项目 | 内容 |
|------|------|
| 文件 | `docs/design/validation/factor-weight-validation-data-models.md` |
| 关联 | `docs/design/validation/factor-weight-validation-algorithm.md` §6、Data Layer data-models |

**问题描述**：

Validation 模块定义了 4 个数据模型（FactorValidationResult、WeightValidationResult、ValidationGateDecision、ValidationRunManifest），但**无任何 DDL/表结构定义**。所有其他 8 个模块（MSS/IRS/PAS/Integration/Data-Layer/Backtest/Trading/Analysis）均在 data-models 文档中包含 DDL。

algorithm §6 和 info-flow §7 仅说明产物存储为 `.reports/validation/{trade_date}/*.parquet`，但：
1. 这些产物未纳入 Data Layer 的 L3/L4 表清单。
2. Integration `calculate()` 的 `validation_gate_decision` 参数来源不明 — 是从 parquet 文件读取还是从 DuckDB 查询？
3. DuckDB 是系统唯一正式数据库，parquet 文件游离于正式数据架构之外。

**建议修复**：
1. 在 Validation data-models 中增加 DDL 节（至少 `validation_gate_decision` 需要 DDL，因为 Integration 强依赖它）。
2. 在 Data Layer data-models 中登记 Validation 表到 L3 或 L4 表清单。
3. 明确 `.reports/validation/` 下的 parquet 是临时文件还是持久化存储，以及它与 DuckDB 的关系。

---

### P1-R29-03 · Validation → Integration 权重桥接链路未闭合

| 项目 | 内容 |
|------|------|
| 文件 | `docs/design/validation/factor-weight-validation-api.md` §2-4、`docs/design/core-algorithms/integration/integration-api.md` §2.1、`integration-data-models.md` §2.5-2.6 |

**问题描述**：

Validation 输出的 `ValidationGateDecision.selected_weight_plan` 是一个**字符串 ID**（`"baseline"` 或 `"candidate_xxx"`），不含实际权重数值。

而 Integration `calculate()` 需要**两个独立参数**：
- `weight_plan: WeightPlan` — 包含 `plan_id, w_mss, w_irs, w_pas` 的完整对象
- `validation_gate_decision: ValidationGateDecision` — 包含门禁决策

**缺失环节**：谁负责将 `selected_weight_plan` 字符串 ID 解析为完整的 `WeightPlan` 对象？

- Validation API 的 `select_weight_plan()` 返回 `WeightValidationResult`（不是 `WeightPlan`）
- `run_daily_gate()` 返回 `ValidationGateDecision`（不含权重数值）
- `run_spiral_full_validation()` 返回三元组，也不含 `WeightPlan`
- Integration 端无 ID → WeightPlan 的查找方法

**建议修复**（任选一种）：
- **方案A**：Orchestrator 增加 `resolve_weight_plan(gate_decision) -> WeightPlan` 方法，从 `weight_validation_report` 查找并构造 WeightPlan。
- **方案B**：修改 `run_daily_gate()` 返回类型为 `tuple[ValidationGateDecision, WeightPlan]`。
- **方案C**：在 Integration 端增加从 Validation 存储读取 WeightPlan 的逻辑（需在 Integration API 中显式声明依赖）。

---

## P2 问题（中优先级）

### P2-R29-04 · Integration 侧 `ValidationGateDecision` 缺 `created_at` 字段

| 项目 | 内容 |
|------|------|
| 文件 | `integration-data-models.md` §2.6 (line 122-133) vs `factor-weight-validation-data-models.md` §3 (line 63) |

Validation 定义的 `ValidationGateDecision` 包含 9 个字段，最后一个是 `created_at: datetime`（用于审计与调试）。Integration §2.6 复制了该 dataclass 但只有 8 个字段，缺少 `created_at`。

**建议**：Integration §2.6 补充 `created_at: datetime` 字段，与 Validation 保持一致。

---

### P2-R29-05 · `ValidationRunManifest` 无 API 生产/消费入口

| 项目 | 内容 |
|------|------|
| 文件 | `factor-weight-validation-data-models.md` §4、`factor-weight-validation-api.md` 全文 |

data-models §4 定义了 `ValidationRunManifest`（9 个字段：run_id, run_type, command, test_command, artifact_dir, started_at, finished_at, status, failed_reason），但 API 中没有任何方法生产或返回该模型：

- `run_daily_gate()` → `ValidationGateDecision`
- `run_spiral_full_validation()` → `tuple[list[FactorValidationResult], WeightValidationResult, ValidationGateDecision]`

该模型成为孤立定义。

**建议**：在 Orchestrator API 中补充 Manifest 生成逻辑（例如 `run_daily_gate` 内部生成 Manifest 并持久化），或在 API 文档中说明 Manifest 的创建时机和存储方式。

---

### P2-R29-06 · Validation 数据模型使用表格格式，与其他模块 `@dataclass` 不一致

| 项目 | 内容 |
|------|------|
| 文件 | `factor-weight-validation-data-models.md` 全文 |

其余 8 个模块（MSS/IRS/PAS/Integration/Data-Layer/Backtest/Trading/Analysis）的 data-models 文档均使用 Python `@dataclass` 代码块定义数据结构。Validation 模块使用 markdown 表格格式（`| 字段 | 类型 | 说明 |`）。

虽然信息等价，但：
1. 实现时缺少可直接复制的 Python 代码骨架。
2. 无法一眼区分哪些字段有默认值、哪些是 Optional。
3. 与全仓库风格不统一。

**建议**：统一改为 `@dataclass` 代码块格式，与其他模块保持一致。

---

### P2-R29-07 · Validation 阈值/窗口常量未纳入配置注入

| 项目 | 内容 |
|------|------|
| 文件 | `factor-weight-validation-algorithm.md` §3.3, §4.2；`factor-weight-validation-information-flow.md` §6 |

以下关键参数以硬编码方式散落在文档中，未定义为 Config 常量：

| 参数 | 位置 | 当前写法 |
|------|------|----------|
| IC 门禁阈值 (`mean_ic > 0.02` 等) | algorithm §3.3 | 内嵌表格 |
| Walk-Forward 窗口 (train=252, validate=63, oos=63) | algorithm §4.2 | 正文描述 |
| 最小样本量 | algorithm §3.1 | "默认 5000" |
| stale_days 告警阈值 | info-flow §6 | "默认 3 天" |
| 候选权重单模块上限 | algorithm §4.1 | "max(w_i) <= 0.60" |

系统铁律要求路径/配置通过环境变量注入。虽然铁律主要针对路径，但这些算法参数同样应当可配置，而非硬编码在算法逻辑中。

**建议**：在 data-models 中增加 `ValidationConfig` dataclass，集中定义所有可调参数及其默认值。

---

### P2-R29-08 · Validation `factor_series` 输入语义歧义 — L2 vs L3

| 项目 | 内容 |
|------|------|
| 文件 | `factor-weight-validation-information-flow.md` §4 (line 50)、`factor-weight-validation-api.md` §1.1 |

info-flow §4 定义 `factor_series` 来源为：
> "Data Layer L2（market_snapshot / industry_snapshot / stock_gene_cache）—— 原始因子序列（计数/比率/聚合），非评分结果"

但同一文档 §4 也定义 `signals` 来源为：
> "Integration 输出（integrated_recommendation，历史窗口）"

这意味着因子验证使用 L2 原始特征，权重验证使用 L3 集成输出。然而：
1. "因子名" 如何映射到 L2 字段？`market_snapshot` 中的哪些列对应哪个 `factor_name`？
2. MSS 算法的"市场情绪系数 (market_coefficient)" 是 L2 原始数据还是 L3 算法输出？如果是后者，则"非评分结果"的描述有误。
3. API `validate_factor()` 接收 `factor_series` 但类型标注为裸名（无类型提示），无法判断预期格式。

**建议**：在 info-flow §4 或 algorithm §3.1 中增加"因子名 → 数据源映射表"，明确每个 factor_name 对应的 L2/L3 字段和表名。

---

### P2-R29-09 · `FactorValidationResult.factor_name` 合法值未枚举

| 项目 | 内容 |
|------|------|
| 文件 | `factor-weight-validation-data-models.md` §1 (line 12) |

`factor_name: str` 仅标注为"因子名"，未列出合法值集合。系统中因子分布在三个算法模块：

- MSS: market_coefficient, profit_effect, loss_effect, capital_flow_strength 等
- IRS: rotation_momentum, capital_flow, breadth_strength 等
- PAS: price_position, volume_activity 等

缺少因子名枚举意味着：
1. 验证结果无法自动追溯到来源算法。
2. 实现时可能出现 typo 导致因子名不匹配。
3. 下游（Integration/Analysis）无法校验因子名合法性。

**建议**：在 data-models 或 naming-conventions 中增加 `ValidatedFactor` 枚举或合法值列表，引用各算法模块的因子定义。

---

### P2-R29-10 · Validation 产物存储位置 `.reports/validation/` 与治理规范不匹配

| 项目 | 内容 |
|------|------|
| 文件 | `factor-weight-validation-algorithm.md` §6、`factor-weight-validation-information-flow.md` §7 |
| 关联 | `Governance/steering/GOVERNANCE-STRUCTURE.md` §2 |

Validation 产物存储在 `.reports/validation/{trade_date}/` 下：
```
.reports/validation/
  └─ {trade_date}/
      ├─ factor_validation_report.parquet
      ├─ weight_validation_report.parquet
      ├─ validation_gate_decision.parquet
      └─ summary.md
```

但治理规范（GOVERNANCE-STRUCTURE §2）定义 `.reports/` 为"报告统一存放点"，命名规则为 `报告名称_YYYYMMDD_HHMMSS.md`。

问题：
1. `.parquet` 文件不是报告，而是**运行时操作数据**（Integration 强依赖 `validation_gate_decision`）。
2. 目录结构 `{trade_date}/` 不符合命名规范（无时间戳）。
3. 操作数据放在 `.reports/` 会与人工报告混杂。

**建议**：
- `summary.md` 留在 `.reports/validation/`（符合报告定位）。
- `.parquet` 文件移入正式数据架构（DuckDB 表或专用 data 目录），与 P1-R29-02 一起解决。

---

## 统计

| 优先级 | 数量 | 编号 |
|--------|------|------|
| P1 | 3 | R29-01, R29-02, R29-03 |
| P2 | 7 | R29-04 ~ R29-10 |
| **合计** | **10** | |

**累计（R1-R29）**: 271 + 10 = **281 项**

---

## 下一步建议

1. **P1-R29-01（铁律口径矛盾）**是全系统层面的根本性问题，建议优先决策并统一所有文档口径。
2. **P1-R29-02 + P2-R29-10** 可合并修复：为 Validation 增加 DDL 并将操作数据纳入正式数据架构。
3. **P1-R29-03** 需要在 Validation 或 Integration 的 API 层新增桥接逻辑。
4. R30 建议进行回归验证（确认 R29 修复未引入新矛盾）+ 最终扫描。
