# EmotionQuant 设计文档审查报告 — R18

**审查轮次**: R18（第 18 轮）
**日期**: 2026-02-08
**审查人**: Claude
**审查角度**: 跨模块数值常量/阈值/DDL追溯字段一致性
**累计**: R1-R17 已修复 159 issues；本轮 10 issues 已闭环（10/10）
**复查结论**: ✅ R18 全部问题已完成修复并同步文档

---

## 审查范围

- 核心算法四模块（MSS / IRS / PAS / Integration）的 algorithm、data-models、api、information-flow 共 16 份文档
- `docs/naming-conventions.md` 权威命名规范
- 交叉比对重点：示例数值与算法公式一致性、因子中间表 DDL 跨模块设计对称性、集成输出追溯字段完整性

---

## P1 Issues（5）

### ~~P1-R18-01: Integration info-flow §4.2 示例 `cycle: "acceleration"` 与温度不匹配~~ ✅ 已修复

**文件**: `docs/design/core-algorithms/integration/integration-information-flow.md:397`
**现状**: 示例 `MssInput: {temperature: 65.3, cycle: "acceleration", trend: "up"}`
**问题**: temperature=65.3 属于 60-75°C 区间，trend="up"，按 MSS 周期判定伪代码应为 **divergence**（分歧期），而非 acceleration（加速期，45-60°C）。
**影响**: R17 已修复 MSS info-flow 的同类错误（P1-R17-01），但 Integration info-flow 的示例未同步修正。
**建议**: `cycle: "acceleration"` → `cycle: "divergence"`

---

### ~~P1-R18-02: IRS/PAS 因子中间表 DDL 缺少 factor-specific mean/std~~ ✅ 已修复

**文件**:
- `docs/design/core-algorithms/irs/irs-data-models.md:196-213`（irs_factor_intermediate）
- `docs/design/core-algorithms/pas/pas-data-models.md:203-221`（pas_factor_intermediate）

**现状**: R17 将 MSS `mss_factor_intermediate` 扩展为 6 因子独立 mean/std（12 个统计参数列），使归一化参数可追溯。但 IRS 和 PAS 的因子中间表仍只存储 raw 值，无 mean/std。
**问题**: 跨模块中间表设计不对称——MSS 可追溯每次归一化使用的统计参数，IRS/PAS 不可。
**影响**: 事后审计 IRS/PAS 因子得分时无法确认当时使用的 baseline mean/std 是否正确。
**建议**:
- IRS: 补充 `relative_strength_mean/std`、`continuity_factor_mean/std`、`capital_flow_mean/std`、`valuation_mean/std`、`leader_score_mean/std`、`gene_score_mean/std`（12 列）
- PAS: 补充 `bull_gene_mean/std`、`structure_mean/std`、`behavior_mean/std`（6 列）

---

### ~~P1-R18-03: PAS 因子中间表存储粒度与 MSS/IRS 不一致~~ ✅ 已修复

**文件**: `docs/design/core-algorithms/pas/pas-data-models.md:203-221`

**现状**:
- MSS intermediate 存储**组合 raw 值**：`market_coefficient_raw`、`profit_effect_raw` 等
- IRS intermediate 存储**组合 raw 值**：`relative_strength_raw`、`continuity_factor_raw` 等
- PAS intermediate 存储**个体输入值**：`limit_up_count_120d`、`price_position`、`volume_ratio` 等

**问题**: PAS 未存储 `bull_gene_raw`、`structure_raw`、`behavior_raw` 三个因子组合 raw 值（zscore 前的加权合成值），与 MSS/IRS 的中间表设计模式不一致。
**影响**: 无法直接追溯 PAS 三因子的组合 raw 值（需从个体输入重新计算）。
**建议**: 补充 `bull_gene_raw DECIMAL(12,6)`、`structure_raw DECIMAL(12,6)`、`behavior_raw DECIMAL(12,6)` 三列。

---

### ~~P1-R18-04: PAS 因子中间表 DDL 缺少 `consecutive_down_days`~~ ✅ 已修复

**文件**: `docs/design/core-algorithms/pas/pas-data-models.md:203-221`

**现状**: `pas_factor_intermediate` 存储了 `consecutive_up_days`（结构因子输入），但未存储 `consecutive_down_days`。
**问题**: PAS 方向判断 bearish 条件为 `close < low_20d_prev AND consecutive_down_days >= 3`（见 pas-algorithm.md:243），`consecutive_down_days` 是决定方向的关键字段，但中间表无法追溯。
**影响**: 方向判断为 bearish 时，无法从中间表确认 `consecutive_down_days` 的实际值。
**建议**: 补充 `consecutive_down_days INT COMMENT '连续下跌天数'`。

---

### ~~P1-R18-05: Integration 输出缺少 `mss_cycle` 追溯字段~~ ✅ 已修复

**文件**:
- `docs/design/core-algorithms/integration/integration-data-models.md:140-174`（IntegratedRecommendation dataclass）
- `docs/design/core-algorithms/integration/integration-data-models.md:210-250`（integrated_recommendation DDL）

**现状**: `IntegratedRecommendation` 存储了 `mss_score`（温度）、`recommendation`（推荐等级），但未存储当时的 MSS 周期 `mss_cycle`。
**问题**: STRONG_BUY 的判定依赖 `mss_cycle ∈ {emergence, fermentation}`（见 integration-algorithm.md §5.1）。输出不存储 `mss_cycle`，事后审计 STRONG_BUY 推荐时无法直接确认当时的周期条件是否满足，必须 JOIN `mss_panorama` 表。
**影响**: 降低推荐等级的自描述性和独立审计能力。
**建议**:
- dataclass 补充 `mss_cycle: str`
- DDL 补充 `mss_cycle VARCHAR(20) COMMENT '当日MSS周期（追溯STRONG_BUY条件）'`

---

## P2 Issues（5）

### ~~P2-R18-06: naming-conventions §5.2 PAS 等级区间使用模糊闭区间~~ ✅ 已修复

**文件**: `docs/naming-conventions.md:141-147`

**现状**: PAS 等级区间表述为 `A: 70-84`、`B: 55-69` 等整数闭区间。
**对比**: PAS data-models 已在 R17 中修正为半开区间 `A: [70, 85)`、`B: [55, 70)`。
**问题**: 对于浮点评分（如 84.5），"70-84" 可能被误读为不包含 84.5，而实际规则 `[70, 85)` 包含该值。两份文档的表述不一致。
**建议**: naming-conventions 统一为半开区间写法：`A: [70, 85)`、`B: [55, 70)` 等。

---

### ~~P2-R18-07: MSS `position_advice` 字段缺少枚举/格式规范~~ ✅ 已修复

**文件**: `docs/design/core-algorithms/mss/mss-data-models.md:116`

**现状**: `MssPanorama.position_advice: str` 定义为字符串类型，但无处定义其合法值集合或格式。MSS 数据验证规则 §5.2 也未约束此字段。
**问题**: 该值来自周期→仓位映射（如"80%-100%"），但格式未标准化：是 "80%-100%" 还是 "80~100" 还是 "80-100" 还是中文"八成至满仓"？
**影响**: 下游消费（Integration MssInput.position_advice、GUI 展示）无法做格式校验。
**建议**: 定义 `position_advice` 枚举或格式规范，例如 `"80%-100%"` 统一格式，并在验证规则 §5.2 中补充约束。

---

### ~~P2-R18-08: Integration 输出缺少实际权重三元组~~ ✅ 已修复

**文件**: `docs/design/core-algorithms/integration/integration-data-models.md:151,228`

**现状**: `IntegratedRecommendation` 仅存储 `weight_plan_id: str`（如 "baseline" / "candidate_001"），DDL 中 `weight_plan_id VARCHAR(40)`。
**问题**: 若候选权重方案随时间调优更新（例如 candidate_001 的 w_mss 从 0.35 调整为 0.40），仅凭 plan_id 无法确定当次集成使用的精确权重值。
**影响**: 事后审计 final_score 的构成时可能因权重版本漂移而无法精确还原。
**建议**: 在 dataclass 与 DDL 中补充 `w_mss DECIMAL(6,4)`、`w_irs DECIMAL(6,4)`、`w_pas DECIMAL(6,4)` 三列实际权重快照。

---

### ~~P2-R18-09: Integration DDL 缺少 `opportunity_grade` 字段~~ ✅ 已修复

**文件**: `docs/design/core-algorithms/integration/integration-data-models.md:210-250`

**现状**: `integrated_recommendation` DDL 存储了 `pas_score`，但未存储 PAS 的 `opportunity_grade`（S/A/B/C/D）。
**问题**: 仓位上限计算依赖 PAS 等级（S=20%, A=15%, B=10%, C/D=5%，见 integration-algorithm.md §6.2），但等级未在集成输出中持久化，审计时需从 `pas_score` 反推等级。
**影响**: 仓位截断审计需额外计算步骤；若 PAS 等级阈值后续调整，历史数据的等级反推可能不一致。
**建议**: 在 dataclass 与 DDL 中补充 `opportunity_grade VARCHAR(5) COMMENT 'PAS机会等级快照'`。

---

### ~~P2-R18-10: PAS info-flow §5.3 传递范围与 Integration 实际接收不一致~~ ✅ 已修复

**文件**:
- `docs/design/core-algorithms/pas/pas-information-flow.md:373-374`
- `docs/design/core-algorithms/integration/integration-information-flow.md:126,378`

**现状**:
- PAS info-flow §5.3: `PAS -> Integration: List[StockPasDaily] (S/A/B级机会)`
- Integration info-flow §2.1: `读取 PAS 当日输出（stock_pas_daily 表，S/A/B/C/D全量）`
- Integration info-flow §4.1: `PasRepository.get_by_grade(["S","A","B","C","D"])`
- Integration algorithm §6.1 注释: `集成计算可覆盖 S/A/B/C/D`

**问题**: PAS info-flow 声称只传递 S/A/B 三级，但 Integration 实际接收并计算全部五级（S/A/B/C/D）。
**影响**: PAS info-flow 描述误导阅读者以为 C/D 级不进入集成流程。
**建议**: PAS info-flow §5.3 修改为 `List[StockPasDaily] (S/A/B/C/D全量)`，与 Integration 实际接收口径一致。

---

## 统计

| 优先级 | 数量 | 涉及模块 |
|--------|------|----------|
| P1 | 5 | Integration(2), PAS(2), IRS/PAS(1) |
| P2 | 5 | Integration(3), PAS(1), naming-conventions(1) |
| **合计** | **10** | |

**累计**: R1-R18 共 169 issues（本轮已全部闭环）。

---

## 复查纠偏记录（2026-02-08）

- ~~P1-R18-01~~：`integration-information-flow.md` 示例 `cycle` 已从 `acceleration` 修正为 `divergence`。
- ~~P1-R18-02~~：`irs-data-models.md` 与 `pas-data-models.md` 的因子中间表均补齐 factor-specific `mean/std` 统计参数快照。
- ~~P1-R18-03~~：`pas-data-models.md` 已补齐 `bull_gene_raw/structure_raw/behavior_raw` 三个组合 raw 字段，与 MSS/IRS 粒度对齐。
- ~~P1-R18-04~~：`pas-data-models.md` 已补齐 `consecutive_down_days`。
- ~~P1-R18-05~~：`integration-data-models.md` dataclass + DDL 已补齐 `mss_cycle` 追溯字段。
- ~~P2-R18-06~~：`naming-conventions.md` PAS 等级区间改为半开区间（如 `[70,85)`）。
- ~~P2-R18-07~~：`mss-data-models.md` 新增 `PositionAdvice` 枚举与 `position_advice` 输出约束。
- ~~P2-R18-08~~：`integration-data-models.md` 已补齐 `w_mss/w_irs/w_pas` 实际权重快照。
- ~~P2-R18-09~~：`integration-data-models.md` 已补齐 `opportunity_grade` 快照字段。
- ~~P2-R18-10~~：`pas-information-flow.md` §5.3 已改为向 Integration 传递 `S/A/B/C/D` 全量。
