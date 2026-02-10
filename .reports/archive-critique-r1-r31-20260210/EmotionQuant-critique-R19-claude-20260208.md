# EmotionQuant 第十九轮审查报告（R19）

**审查人**: Claude
**日期**: 2026-02-08
**审查角度**: 细节检查 — 跨模块依赖声明一致性、API/DDL/枚举精确对齐、边界与默认值缺口
**累计问题数**: R1-R18 共 169 项已修复 + R19 新增 10 项

---

## 审查摘要

本轮聚焦文档间**细节一致性**，重点检查：
1. 跨模块依赖声明（info-flow §5 交互章节）是否互认
2. 算法文档 §10 协同章节 vs 信息流 §5 交互章节 的职责边界
3. API 方法签名 vs 信息流调用链 精确对齐
4. 枚举/边界/默认值覆盖完整性

发现 **5 项 P1 + 5 项 P2** 共 10 项问题。

---

## P1 问题（5 项）

### ~~P1-R19-01: MSS info-flow §5.1+§5.2 仍声明 MSS→IRS/PAS 直接依赖，与 IRS/PAS info-flow 矛盾~~

**位置**: `docs/design/core-algorithms/mss/mss-information-flow.md` §5.1 (line 349-354) + §5.2 (line 359-363)

**现状**:
- MSS info-flow §5.1: "MSS -> IRS: MssPanorama.temperature, MssPanorama.cycle; 用途：IRS 根据市场整体情绪调整行业轮动策略"
- MSS info-flow §5.2: "MSS -> PAS: MssPanorama.temperature, MssPanorama.trend; 用途：PAS 根据市场环境调整个股评分阈值"

**矛盾**:
- IRS info-flow §5.1（R14 已修）: "MSS -> Integration（非 IRS 直接输入）; IRS 算法本身不直接消费 MSS 字段做因子计算"
- PAS info-flow §5.1（R14 已修）: "MSS -> Integration（非 PAS 直接输入）; PAS 算法本身不直接消费 MSS 字段做评分/分级"

**根因**: R14 修复了 IRS/PAS info-flow 的依赖声明，但 MSS info-flow 的对称侧未同步更新。

**修复建议**: MSS info-flow §5.1 改为 "MSS -> Integration（非 IRS 直接输入）"，§5.2 改为 "MSS -> Integration（非 PAS 直接输入）"，与 IRS/PAS info-flow 对称。

---

### ~~P1-R19-02: Integration info-flow §2.1 Step 1 遗漏 Validation Gate 和 Weight Plan 数据采集~~

**位置**: `docs/design/core-algorithms/integration/integration-information-flow.md` §2.1 Step 1 (line 117-134)

**现状**: Step 1 仅列出：
1. 读取 MSS（mss_panorama）
2. 读取 IRS（irs_industry_daily）
3. 读取 PAS（stock_pas_daily）
4. 数据完整性检查
5. 缺失降级

**缺失**: 未包含读取 `ValidationGateDecision` 和 `WeightPlan`，但这是 Integration 的必需前置输入（算法 §3.1 明确、API 签名也包含此参数）。

**佐证**: §4.1 单日计算 timeline（line 379-380）正确包含了 `ValidationRepository.get_gate_decision()` 和 `ValidationRepository.get_weight_plan()`，但 Step 定义遗漏了。

**修复建议**: Step 1 补充第 4、5 步："读取 Validation Gate 决策（validation_gate_decision）" 和 "读取权重方案（weight_plan）"，原步骤顺延。

---

### ~~P1-R19-03: PAS algorithm §10.1 描述 MSS 依赖行为，与 PAS info-flow §5.1 矛盾~~

**位置**: `docs/design/core-algorithms/pas/pas-algorithm.md` §10.1 (line 351-356)

**现状**:
```
- MSS 提供市场温度与风险上限参考
- 当 MSS 温度 < 30（冰点），PAS 信号强度与仓位建议下调
- 当 MSS 温度 > 80（过热），PAS 信号强度与仓位建议下调
```

**矛盾**: PAS info-flow §5.1 明确声明 "PAS 算法本身不直接消费 MSS 字段做评分/分级"。上述 MSS 温度依赖的信号/仓位调整实际发生在 **Integration 协同约束层**（integration-algorithm.md §5.3），非 PAS 算法自身。

**修复建议**: §10.1 改为 "MSS 温度不直接进入 PAS 评分/分级；MSS 驱动的仓位调整与风险约束由 Integration 协同约束层执行（见 integration-algorithm.md §5.3）"。

---

### ~~P1-R19-04: IRS algorithm §10.1 描述 MSS 依赖行为，与 IRS info-flow §5.1 矛盾~~

**位置**: `docs/design/core-algorithms/irs/irs-algorithm.md` §10.1 (line 422-424)

**现状**:
```
- 当 MSS 温度高（市场过热）时，IRS 配置偏向防御性行业并下调风险敞口
- 当 MSS 温度低（市场冷淡）时，IRS 配置偏向进攻性行业但仍受仓位上限约束
```

**矛盾**: IRS info-flow §5.1 明确声明 "IRS 算法本身不直接消费 MSS 字段做因子计算"。MSS 温度驱动的配置调整发生在 Integration 层。

**修复建议**: §10.1 改为 "MSS 温度不直接进入 IRS 因子计算；MSS 驱动的配置/风险调整由 Integration 协同约束层执行"。

---

### ~~P1-R19-05: Integration algorithm §6.1 注释 "仅取 S/A/B" 与 §9.1 实际筛选条件矛盾~~

**位置**: `docs/design/core-algorithms/integration/integration-algorithm.md` §6.1 (line 253)

**现状**: §6.1 注释："注：集成计算可覆盖 S/A/B/C/D，推荐列表筛选仍按 §9.1 **仅取 S/A/B**。"

**矛盾**: §9.1 实际筛选条件（line 343-351）为：
1. MSS temperature is not null
2. `final_score ≥ 55`

筛选条件中**无 PAS 等级硬过滤**。C 级（score 40-55）或 D 级（<40）个股如果因 MSS/IRS 高分拉升 final_score ≥ 55，也可入选。"仅取 S/A/B" 与实际规则不一致。

**修复建议**: 二选一：
- (a) 删除 §6.1 注释中的 "仅取 S/A/B" 描述，明确以 `final_score ≥ 55` 为唯一筛选门槛
- (b) 若确需 PAS 等级过滤，在 §9.1 筛选条件中显式添加 `opportunity_grade IN ('S','A','B')`

---

## P2 问题（5 项）

### ~~P2-R19-06: PAS algorithm §5.1 等级边界使用整数记法，与命名规范/数据模型半开区间不一致~~

**位置**: `docs/design/core-algorithms/pas/pas-algorithm.md` §5.1 (line 222-228)

**现状**:
| 等级 | 算法文档 §5.1 | naming-conventions §5.2 | PAS data-models PasGrade |
|------|--------------|------------------------|--------------------------|
| S | ≥85 | [85, +∞) | ≥85 |
| A | **70-84** | [70, 85) | [70, 85) |
| B | **55-69** | [55, 70) | [55, 70) |
| C | **40-54** | [40, 55) | [40, 55) |
| D | <40 | <40 | <40 |

"70-84" 对于非整数评分（如 84.5）存在边界歧义。

**修复建议**: PAS algorithm §5.1 统一为半开区间：A=[70, 85)、B=[55, 70)、C=[40, 55)。

---

### ~~P2-R19-07: Integration info-flow §4.1 调用 `PasRepository.get_by_grade()` 但 PAS API 未定义此方法~~

**位置**: `docs/design/core-algorithms/integration/integration-information-flow.md` §4.1 (line 378)

**现状**:
```
PasRepository.get_by_grade(["S","A","B","C","D"]) -> List[PasInput] (N个)
```

**缺失**: PAS API (pas-api.md) 的 `PasRepository` 仅定义：`save`、`save_batch`、`get_by_date`、`get_by_stock`、`get_by_industry`。无 `get_by_grade` 方法。

**修复建议**: 二选一：
- (a) PAS API `PasRepository` 补充 `get_by_grade(trade_date, grades) -> List[StockPasDaily]` 方法
- (b) Integration info-flow 改用 `PasRepository.get_by_date(trade_date)` + 代码侧过滤

---

### ~~P2-R19-08: MSS 周期判定返回 "unknown" 时无对应 position_advice 映射~~

**位置**: `docs/design/core-algorithms/mss/mss-algorithm.md` §5.2 (line 279) + §5.1 (line 233-241)

**现状**: `detect_cycle()` 最末 fallback 返回 `"unknown"`。但 §5.1 的周期→仓位建议映射仅覆盖 7 个已知周期（emergence ~ recession），不包含 `unknown`。

**影响**: 当 cycle="unknown" 时，position_advice 无法确定，可能导致运行时空值或异常。

**修复建议**: 为 `unknown` 指定默认仓位建议（建议 "0%-20%"——最保守策略），或在周期判定伪代码中确保 unknown 不可达（移除 fallback、保证其他分支完整覆盖）。

---

### ~~P2-R19-09: IRS `rotation_detail` 有 6 个定义值但无枚举/输出验证规则~~

**位置**: `docs/design/core-algorithms/irs/irs-data-models.md` §4.1 DDL (line 169) + §6.2 输出验证 (line 304-311)

**现状**:
- DDL: `rotation_detail VARCHAR(50) COMMENT '轮动详情'`
- IRS 算法 §5.2 定义 6 个值：强势领涨/轮动加速/风格转换/热点扩散/高位整固/趋势反转
- 数据模型 §6.2 输出验证规则中无 `rotation_detail` 的合法值约束

**对比**: 同表的 `rotation_status` 有完整枚举（IrsRotationStatus）和输出验证规则（IN/OUT/HOLD）。

**修复建议**: 在 IRS data-models 中补充 `IrsRotationDetail` 枚举或在 §6.2 输出验证中添加 `rotation_detail IN (...)` 合法值约束。

---

### ~~P2-R19-10: PAS algorithm §9.1 数据就绪清单遗漏 `max_pct_chg_history` 字段~~

**位置**: `docs/design/core-algorithms/pas/pas-algorithm.md` §9.1 (line 319-322)

**现状**: §9.1 必备字段清单：
- 计数类：`limit_up_count_120d、new_high_count_60d、consecutive_up_days、consecutive_down_days`
- 连续类：`open/high/low/close、vol、volume_avg_20d、pct_chg、high_60d、low_60d、high_60d_prev、high_20d_prev、low_20d_prev、low_20d`
- 状态类：`is_limit_up、is_touched_limit_up`

**缺失**: `max_pct_chg_history` 未列入，但它是 §3.1 牛股基因因子的必需输入（`max_pct_chg_history_ratio = max_pct_chg_history / 100`），且已在 §5.1 中有验证规则。

**修复建议**: §9.1 计数类补充 `max_pct_chg_history`。

---

## 复查纠偏记录（2026-02-08）

- 复查结论：R19 共 10 项（5 P1 + 5 P2）均已完成修复并闭环。
- 已完成对齐的文档：
  - `docs/design/core-algorithms/mss/mss-information-flow.md`（P1-01）
  - `docs/design/core-algorithms/integration/integration-information-flow.md`（P1-02，P2-07）
  - `docs/design/core-algorithms/pas/pas-algorithm.md`（P1-03，P2-06，P2-10）
  - `docs/design/core-algorithms/irs/irs-algorithm.md`（P1-04）
  - `docs/design/core-algorithms/integration/integration-algorithm.md`（P1-05）
  - `docs/design/core-algorithms/pas/pas-api.md`（P2-07）
  - `docs/design/core-algorithms/mss/mss-algorithm.md`（P2-08）
  - `docs/design/core-algorithms/irs/irs-data-models.md`（P2-09）

---

## 附录：审查覆盖范围

| 文档 | 审查重点 |
|------|----------|
| mss-information-flow.md §5 | 跨模块交互声明 |
| irs-information-flow.md §5 | 跨模块交互声明 |
| pas-information-flow.md §5 | 跨模块交互声明 |
| integration-information-flow.md §2+§4 | Step 定义 vs 示例 timeline |
| mss-algorithm.md §5 | 周期→position_advice 完整性 |
| irs-algorithm.md §10 | MSS 协同描述 vs info-flow |
| pas-algorithm.md §5+§9+§10 | 等级记法、数据就绪、MSS 协同 |
| integration-algorithm.md §6+§9 | 筛选条件 vs 注释 |
| pas-api.md | Repository 方法完整性 |
| irs-data-models.md §4+§6 | rotation_detail 枚举/验证 |
