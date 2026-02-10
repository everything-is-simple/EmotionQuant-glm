# EmotionQuant 设计文档批判性审查 — 第 30 轮

**审查人**: Claude  
**日期**: 2026-02-09  
**范围**: R29 回归验证 + ValidatedFactor 跨模块对齐 + 表清单收口  
**累计**: R1-R29 共 281 项已修复；本轮新增 5 项  

---

## 审查摘要

本轮为回归验证 + 最终边缘扫描。R29 的 10 项修复全部验证通过，但 R29 新增的 Validation DDL 引入了 1 个 P1 回归问题（dataclass 与 DDL 字段不对齐 — trade_date 缺失），另有 2 个 P2 和 2 个 P3 收口项。整体设计文档已接近实现就绪。

---

## R29 验证结果

| 编号 | 状态 | 说明 |
|------|------|------|
| P1-R29-01 | ✅ 已修复 | system-overview / naming-conventions / 系统铁律 / CORE-PRINCIPLES 四文档技术指标边界统一 |
| P1-R29-02 | ✅ 已修复 | Validation 5 张 DDL 补齐；DuckDB 为权威存储；Data Layer §4.6 已收录 |
| P1-R29-03 | ✅ 已修复 | ValidationWeightPlan 桥接模型 + resolve_weight_plan + build_integration_inputs |
| P2-R29-04 | ✅ 已修复 | Integration §2.6 补充 created_at |
| P2-R29-05 | ✅ 已修复 | run_daily_gate/run_spiral_full 返回 ValidationRunManifest + get_run_manifest API |
| P2-R29-06 | ✅ 已修复 | 全部改为 @dataclass 代码块 |
| P2-R29-07 | ✅ 已修复 | ValidationConfig dataclass + 算法全文引用 config.xxx |
| P2-R29-08 | ✅ 已修复 | info-flow §4.1 因子→数据源映射表 |
| P2-R29-09 | ✅ 已修复 | ValidatedFactor 枚举 15 因子，与 MSS(6)/IRS(6)/PAS(3) 完全对齐 |
| P2-R29-10 | ✅ 已修复 | DuckDB 权威 + .reports 仅 summary.md + 禁止 parquet 契约 |

---

## P1 问题（高优先级）

### P1-R30-01 · Validation DDL vs dataclass 回归 — trade_date / created_at 缺失

| 项目 | 内容 |
|------|------|
| 文件 | `docs/design/validation/factor-weight-validation-data-models.md` §1.2, §1.3, §1.6 vs §3.1, §3.2, §3.5 |
| 性质 | R29 新增 DDL 时引入的回归问题，与 R28 同类型 |

R29 为 Validation 补齐了 5 张 DDL，但其中 3 个 dataclass 与对应 DDL 存在字段差异：

**1. FactorValidationResult (§1.2) vs validation_factor_report (§3.1)**
- DDL 有 `trade_date VARCHAR(8) NOT NULL`，dataclass 无
- DDL 有 `id INTEGER PRIMARY KEY`，dataclass 无（id 为 DDL 约定，可忽略）

**2. WeightValidationResult (§1.3) vs validation_weight_report (§3.2)**
- DDL 有 `trade_date VARCHAR(8) NOT NULL`，dataclass 无

**3. ValidationRunManifest (§1.6) vs validation_run_manifest (§3.5)**
- DDL 有 `trade_date VARCHAR(8) NOT NULL`，dataclass 无
- DDL 有 `created_at DATETIME DEFAULT CURRENT_TIMESTAMP`，dataclass 无

**建议修复**：
- FactorValidationResult 增加 `trade_date: str`
- WeightValidationResult 增加 `trade_date: str`
- ValidationRunManifest 增加 `trade_date: str` 和 `created_at: datetime`

> 注意：`id` 字段为 DDL 自增主键惯例，不需要在 dataclass 中出现（与其他模块一致）。

---

## P2 问题（中优先级）

### P2-R30-02 · Validation info-flow 因子映射表缺少 6 个因子

| 项目 | 内容 |
|------|------|
| 文件 | `docs/design/validation/factor-weight-validation-information-flow.md` §4.1 |

info-flow §4.1 的"因子名→数据源映射"表只列出了 9 个因子，但 ValidatedFactor 枚举定义了 15 个。缺少的 6 个：

| 缺失因子 | 来源模块 | 推测数据源 |
|-----------|----------|------------|
| mss_continuity_factor | MSS | L2 market_snapshot (continuous_limit_up_* 等) |
| mss_extreme_factor | MSS | L2 market_snapshot (high_open_low_close_count 等) |
| mss_volatility_factor | MSS | L2 market_snapshot (pct_chg_std / amount_volatility) |
| irs_continuity_factor | IRS | L2 industry_snapshot (rise_count/fall_count/new_100d_high_count) |
| irs_leader_score | IRS | L2 industry_snapshot (top5_pct_chg / top5_limit_up) |
| irs_gene_score | IRS | L2 stock_gene_cache (聚合到行业级) |

**建议**：补齐 6 行，与 ValidatedFactor 枚举 1:1 对应。

---

### P2-R30-03 · naming-conventions §8.2 核心表命名未收录 Validation 表

| 项目 | 内容 |
|------|------|
| 文件 | `docs/naming-conventions.md` §8.2 (line 229-234) |

naming-conventions 作为"唯一权威命名规范"，§8.2 列出了 4 个核心表（MSS/IRS/PAS/Integration），但 Validation 的 5 张表均未列出。

Data Layer data-models §4.6 已收录，但 naming-conventions 作为命名权威应同步。

**建议**：§8.2 补充 Validation 模块核心表（至少 `validation_gate_decision` 和 `validation_weight_plan`），§8.3 中间表补充 `validation_factor_report`、`validation_weight_report`、`validation_run_manifest`。

---

## P3 问题（低优先级）

### P3-R30-04 · Data Layer §1.1 总览图 L3 未列 Validation 表

| 项目 | 内容 |
|------|------|
| 文件 | `docs/design/data-layer/data-layer-data-models.md` §1.1 (line 40-45) |

§1.1 的 ASCII 总览图 L3 列出 5 张表（mss_panorama / irs_industry_daily / stock_pas_daily / integrated_recommendation / pas_breadth_daily），未包含 `validation_*` 表。但 §4.6 已详细收录全部 5 张 Validation 表。

**建议**：在 §1.1 L3 区块补充一行 `├── validation_*  Validation运行时表（5张，详见§4.6）`。

---

### P3-R30-05 · Integration info-flow §4.1 时序中 "weight_plan" 引用可更精确

| 项目 | 内容 |
|------|------|
| 文件 | `docs/design/core-algorithms/integration/integration-information-flow.md` §4.1 (line 384) |

当前表述：`ValidationRepository.get_weight_plan() -> (w_mss,w_irs,w_pas)`

Validation API 已定义 `resolve_weight_plan()` 返回 `WeightPlan` 对象（非裸 tuple），且数据源为 `validation_weight_plan` 表。

**建议**：改为 `ValidationRepository.get_weight_plan() -> WeightPlan`，与 Validation API §4.3 保持一致。

---

## 统计

| 优先级 | 数量 | 编号 |
|--------|------|------|
| P1 | 1 | R30-01 |
| P2 | 2 | R30-02, R30-03 |
| P3 | 2 | R30-04, R30-05 |
| **合计** | **5** | |

**累计（R1-R30）**: 281 + 5 = **286 项**

---

## 完工评估

| 维度 | 状态 | 说明 |
|------|------|------|
| 模块内一致性 | ✅ 已达标 | 9 模块 × 4 文档 + Validation 内部一致 |
| 跨模块接口对齐 | ✅ 已达标 | MSS/IRS/PAS → Integration → Backtest/Trading/Analysis 信号链完整 |
| DDL vs dataclass | ⚠️ 差 1 轮 | R30-01 修复后达标（3 个字段补齐） |
| 枚举/命名一致性 | ✅ 已达标 | naming-conventions 为权威，各模块引用 |
| 铁律/治理口径 | ✅ 已达标 | 4 文档已统一技术指标边界 |
| 数据架构完整性 | ⚠️ 差 1 轮 | R30-02/03/04 补齐后 L1-L4 全覆盖 |

**结论**：修复本轮 5 项后，再做一轮最终验证（R31），预计 0-2 个微小遗留，即可宣布设计文档实现就绪。

**预计剩余：1 轮修复 + 1 轮验证 = 最多 2 轮完工。**
