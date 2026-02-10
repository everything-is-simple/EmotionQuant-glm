# Integration 三三制集成算法设计

**版本**: v3.4.7（重构版）
**最后更新**: 2026-02-09
**状态**: 设计完成（验收口径补齐；代码未落地）

---

## 1. 算法概述

### 1.1 设计目标

Integration（三三制集成算法）将 MSS、IRS、PAS 三个子系统的输出进行融合，生成最终的交易信号和推荐列表。

### 1.2 三三制原则

**baseline 等权融合**：默认 MSS、IRS、PAS 各占 1/3 权重；允许在 Validation Gate 通过后切换到候选权重（约束：非负、和为 1、单模块上限）。

```python
BASELINE_WEIGHTS = {
    "mss": 1/3,  # 大盘情绪权重
    "irs": 1/3,  # 行业轮动权重
    "pas": 1/3   # 价格行为权重
}
```

### 1.3 核心输出

| 输出 | 说明 | 范围 |
|------|------|------|
| final_score | 综合评分 | 0-100 |
| recommendation | 交易信号 | STRONG_BUY/BUY/HOLD/SELL/AVOID |
| position_size | 仓位建议 | 0-1 |
| neutrality | 综合中性度 | 0-1（越接近1越中性，越接近0信号越极端） |

命名规范：周期/趋势/推荐等级/PAS方向详见 [naming-conventions.md](../../../naming-conventions.md) §1-5。

---

## 2. 输入规范

### 2.1 MSS 输入

| 字段 | 类型 | 说明 |
|------|------|------|
| temperature | float | 市场温度 0-100 |
| cycle | string | 情绪周期（英文） |
| trend | string | 趋势方向 up/down/sideways |
| position_advice | string | 仓位建议 |
| neutrality | float | 中性度 0-1（越接近1越中性，越接近0信号越极端） |

### 2.2 IRS 输入

| 字段 | 类型 | 说明 |
|------|------|------|
| industry_code | string | 行业代码 |
| industry_score | float | 行业评分 0-100 |
| rotation_status | string | 轮动状态 IN/OUT/HOLD |
| allocation_advice | string | 配置建议 |
| quality_flag | string | 质量标记 normal/cold_start/stale |
| sample_days | int | 有效样本天数（用于识别冷启动） |
| neutrality | float | 中性度 0-1（越接近1越中性，越接近0信号越极端） |

### 2.3 PAS 输入

| 字段 | 类型 | 说明 |
|------|------|------|
| stock_code | string | 股票代码 |
| opportunity_score | float | 机会评分 0-100 |
| opportunity_grade | string | 机会等级 S/A/B/C/D |
| direction | string | 方向 bullish/bearish/neutral |
| risk_reward_ratio | float | 风险收益比 |
| neutrality | float | 中性度 0-1（越接近1越中性，越接近0信号越极端） |

### 2.4 Validation Gate 输入（前置必需）

| 字段 | 类型 | 说明 |
|------|------|------|
| final_gate | string | PASS/WARN/FAIL |
| selected_weight_plan | string | baseline / candidate_id |
| fallback_plan | string | WARN/FAIL 时回退方案标识 |
| reason | string | 门禁决策说明 |

---

### 2.5 宏观方向（验收用“职责边界表”）

> 说明：Integration 只做“融合与协同约束”，不重算 MSS/IRS/PAS 的原始因子。

| 分层职责 | 主要输入 | 输出/约束 |
|---------|----------|----------|
| 市场层（MSS） | temperature / cycle / trend | 市场风险上限与仓位约束 |
| 行业层（IRS） | industry_score / rotation_status / allocation_advice | 行业配置权重与方向参考 |
| 个股层（PAS） | opportunity_score / grade / direction / risk_reward_ratio | 个股机会强度与交易参考 |
| 集成层（Integration） | 三者评分 + 方向一致性 | final_score / recommendation / position_size |

### 2.6 互斥边界说明（不得重复覆盖）

- 集成层**不得重新计算** MSS/IRS/PAS 的原始因子。
- 集成层仅允许使用：评分、方向、周期/状态、等级与风险收益比等“上游输出字段”。
- 新增任何协同约束或加权逻辑，必须说明“作用层级”，避免跨层重复。

## 3. 综合评分计算

### 3.1 Gate 前置检查与权重方案选择

```python
def resolve_gate_and_weights(
    gate: ValidationGateDecision,
    candidate_weight_plans: dict[str, dict[str, float]],
    irs_quality_flag: str = "normal"
) -> tuple[dict[str, float], str]:
    if gate.final_gate == "FAIL":
        raise ValidationGateError("Gate=FAIL，不允许进入集成")

    if irs_quality_flag in {"cold_start", "stale"}:
        # IRS 处于冷启动/陈旧状态时，强制回退 baseline 并打 WARN
        return BASELINE_WEIGHTS, "WARN"

    if gate.selected_weight_plan == "baseline":
        return BASELINE_WEIGHTS, gate.final_gate

    selected = candidate_weight_plans.get(gate.selected_weight_plan)
    if selected is None:
        if gate.final_gate == "WARN":
            return BASELINE_WEIGHTS, "WARN"  # 候选缺失时降级回 baseline
        raise ValueError(f"missing candidate weight plan: {gate.selected_weight_plan}")

    return selected, gate.final_gate
```

执行规则：
- `final_gate = FAIL`：直接拒绝计算并抛出 `ValidationGateError`；
- `final_gate = WARN`：允许继续，但输出需保留 WARN 标记；
- `irs_quality_flag ∈ {cold_start, stale}`：强制回退 `BASELINE_WEIGHTS`，并将门禁状态提升为 `WARN`；
- `final_gate = PASS`：按 `selected_weight_plan` 使用 baseline/candidate 权重。

### 3.2 三三制加权公式

```text
final_score = mss_score × w_mss + irs_score × w_irs + pas_score × w_pas

其中：
- mss_score = MssPanorama.temperature
- irs_score = IrsIndustryDaily.industry_score（对应行业）
- pas_score = StockPasDaily.opportunity_score
- (w_mss, w_irs, w_pas) 来自 §3.1 的 `resolve_gate_and_weights` 结果
```

### 3.3 评分校准

为保证三个系统的评分在同一尺度，使用统一的Z-Score归一化：

```python
def calibrate_score(score: float) -> float:
    """校准评分到统一尺度"""
    # 所有评分已在各自模块中归一化到0-100（count→ratio→zscore）
    # 此处仅做边界校验
    return max(0.0, min(100.0, score))
```

---

## 4. 方向一致性检查

### 4.1 方向映射

| MSS趋势 | IRS状态 | PAS方向 | 方向代码 |
|---------|---------|---------|----------|
| up | IN | bullish | +1（看涨） |
| down | OUT | bearish | -1（看跌） |
| sideways | HOLD | neutral | 0（中性） |

### 4.2 一致性计算

```text
公式：
direction_score = (mss_direction + irs_direction + pas_direction) / 3

判定：
- direction_score > 0.3  → bullish
- direction_score < -0.3 → bearish
- 其他 → neutral

一致性系数（用于中性度计算）：
- 三者方向一致 → consistency_factor = 1.0
- 三者均中性（MSS=sideways, IRS=HOLD, PAS=neutral）→ consistency_factor = 1.0
- 两者一致一者不同 → consistency_factor = 0.9
- 三者各不同 → consistency_factor = 0.7
```

---

## 5. 交易信号生成

### 5.1 信号映射规则

| 综合评分 | 附加条件 | 推荐等级 |
|----------|----------|----------|
| ≥75 | MSS周期∈{emergence,fermentation} | STRONG_BUY |
| ≥70 | 不满足 STRONG_BUY 附加条件 | BUY |
| 50-69 | - | HOLD |
| 30-49 | - | SELL |
| <30 | - | AVOID |

补充规则：
- 当 `mss_cycle = unknown` 时，推荐等级强制降级为 `HOLD`（观察模式，不产生积极买入信号）。

### 5.2 多数一致约束

```text
规则：
- consistency = consistent → strength_factor = 1.0
- consistency = partial → strength_factor = 0.9
- consistency = divergent → strength_factor = 0.8

使用方式：
- strength_factor 仅定义于此，应用时机在 §5.3 最后一步（重算 final_score 之后）
- neutrality 的一致性调整见 §7（综合中性度）
```

### 5.3 风险上限与配置权重（协同约束）

```text
规则（不做单点否决，仅影响风险与权重）：
- MSS 温度极端（<30 或 >80） → position_size 下调、neutrality_risk_factor 上调（中性度在 §7 一次性计算）
- MSS 周期为 `unknown` → 推荐等级上限为 `HOLD`（不允许 `STRONG_BUY/BUY`）
- IRS allocation_advice = \"回避\" → pas_score 轻度折扣（例如 ×0.85）
- IRS allocation_advice = \"超配\" → pas_score 轻度上浮（例如 ×1.05）
- IRS 约束后必须执行边界裁剪：`pas_score = clip(pas_score, 0, 100)`
- 协同约束执行顺序（必须）：  
  1) 调整 `pas_score`  
  2) `pas_score = clip(pas_score, 0, 100)`  
  3) `final_score = mss_score×w_mss + irs_score×w_irs + pas_score×w_pas`  
  4) `final_score *= strength_factor`（§5.2）
```

> 说明：STRONG_BUY 在 `emergence/fermentation` 周期属于高置信稀缺信号，实际触发频率应显著低于 BUY。

---

## 6. 仓位建议计算

### 6.1 基础仓位公式

```text
base_position = final_score / 100

调整因子：
- MSS温度调整: position × (1 - |temperature - 50| / 100)
- IRS配置调整: 
  - 超配行业 × 1.2
  - 标配行业 × 1.0
  - 减配行业 × 0.7
  - 回避行业 × 0.3
- PAS等级调整:
  - S级 × 1.2
  - A级 × 1.0
  - B级 × 0.7
  - C/D级 × 0.3

最终仓位 = base_position × 各调整因子
边界: 0 ≤ position_size ≤ 1

注：集成计算可覆盖 S/A/B/C/D，推荐列表筛选按 §9.1 以 `final_score ≥ 55` 为主门槛（PAS/IRS 仅软排序）。
```

### 6.2 仓位上限约束

```text
单股仓位上限：
- S级机会：20%
- A级机会：15%
- B级机会：10%
- C/D级：5%
```

---

## 7. 中性度计算

### 7.1 综合中性度公式

```text
neutrality = (mss_neut × w_mss + irs_neut × w_irs + pas_neut × w_pas)
          × consistency_factor
          × mss_neutrality_risk_factor

其中：
- mss_neut = MssPanorama.neutrality
- irs_neut = IrsIndustryDaily.neutrality
- pas_neut = StockPasDaily.neutrality
- (w_mss, w_irs, w_pas) = §3.1 Gate 解析后的权重三元组（baseline/candidate）
- consistency_factor = 方向一致性惩罚系数（consistent=1.0 / partial=0.9 / divergent=0.7）
- mss_neutrality_risk_factor:
  - 默认 1.0
  - MSS 温度 <30 或 >80 时取 1.1

输出边界：`neutrality = clip(neutrality, 0, 1)`
```

### 7.2 中性度语义（重要澄清）

**注意**：中性度反映的是信号的"中性程度"，而非信号强度。

```text
参考口径（仅在上游未提供 neutrality 时使用）：
neutrality = 1 - |score - 50| / 50
```

说明：Integration 默认使用三系统 neutrality 加权均值（权重与 `final_score` 保持一致），并叠加一致性系数与 MSS 风险因子（见 7.1）。

语义解释：
- neutrality 接近 0 → 信号极端（评分接近0或100）
- neutrality 接近 1 → 信号中性（评分接近50）

实际使用：
- 极端信号（低 neutrality）更适合作为交易触发
- 中性信号（高 neutrality）建议观望

---

## 8. 周期命名映射

### 8.1 中英文映射表

| 英文代码 | 中文名称 | 阶段描述 |
|----------|----------|----------|
| emergence | 萌芽期 | 情绪开始复苏 |
| fermentation | 发酵期 | 情绪逐渐升温 |
| acceleration | 加速期 | 情绪快速上升 |
| divergence | 分歧期 | 多空分歧加大 |
| climax | 高潮期 | 情绪达到顶峰 |
| diffusion | 扩散期 | 情绪开始扩散 |
| recession | 退潮期 | 情绪回落 |
| unknown | 异常兜底 | 输入异常或不可判定 |

### 8.2 周期-信号关联（与 MSS 算法对齐）

| 周期 | 温度条件 | 适合操作 | 仓位建议 |
|------|----------|----------|----------|
| emergence | <30°C + up | 积极加仓，逢低买入 | 80%-100% |
| fermentation | 30-45°C + up | 稳健持仓，适度加仓 | 60%-80% |
| acceleration | 45-60°C + up | 维持仓位，择机调整 | 50%-70% |
| divergence | 60-75°C + up/sideways | 谨慎操作，逐步减仓 | 40%-60% |
| climax | ≥75°C | 防御为主，严控仓位 | 20%-40% |
| diffusion | 60-75°C + down | 减仓观望 | 30%-50% |
| recession | <60°C + down/sideways | 空仓等待 | 0%-20% |
| unknown | - | 仅观察，不开新仓 | 0%-20% |

---

## 9. 推荐列表生成

### 9.1 筛选条件

```text
入选条件：
1. MSS temperature is not null
2. final_score ≥ 55

排序规则：
1. 首先按 final_score 降序
2. 然后按 opportunity_score 降序（PAS 软排序，不作硬过滤）
3. 最后按 allocation_advice 优先级降序（IRS 软排序，不作硬过滤）
```

### 9.2 输出限制

```text
- 每日最多推荐 20 只
- 每行业最多推荐 5 只
- S级机会优先展示
```

---

## 10. 双模式集成（MVP 必选）

> **背景**：传统 Top-Down（TD）在系统性行情更稳健，但可能错过结构性行情；Bottom-Up（BU）用于捕捉结构性行情。
>
> **约束（铁律对齐）**：TD 为默认主流程，BU 仅作为补充信号；BU 的总仓位/风险不得突破 TD 的上限约束。

### 10.1 模式定义

| 模式 | 信息流 | 协同约束方向 | 设计理念 |
|------|--------|----------|----------|
| **top_down** | MSS→IRS→PAS | 大盘压制选股 | “大环境不好就休息” |
| **bottom_up** | PAS→IRS→MSS | 强股反推市场 | “强股多了就是机会” |

### 10.1.1 BU 模式所需的 PAS 聚合指标（由 L3 stock_pas_daily 聚合得到）

BU 的入口来自 PAS 的强股分布：先用个股分布形成市场/行业活跃度，再进入 IRS 与 MSS 的协同约束与风控。

- 全市场活跃度（Market）：
  - `pas_sa_count`：S/A 级股票数量
  - `pas_sa_ratio`：S/A 级占比（S/A 数量 / 可交易股票数）
  - `pas_grade_distribution`：S/A/B/C/D 分布
- 行业活跃度（Industry，供 IRS 使用）：
  - `industry_sa_count`：行业内 S/A 数量
  - `industry_sa_ratio`：行业内 S/A 占比
  - `industry_top_k_concentration`：TopK 行业的 S/A 集中度

这些指标可在集成时临时聚合，也可落库为派生表（见 `integration-data-models.md`）。

### 10.2 Top-Down 模式（默认）

```text
协同约束逻辑：
1. MSS 温度极端（<30 或 >80） → position_size 下调、neutrality_risk_factor 上调
2. IRS 回避行业 → pas_score 轻度折扣（例如 ×0.85）
3. 推荐列表筛选：MSS temperature is not null

特点：
- 风控优先，大盘低迷时显著削弱信号
- 适合系统性行情
```

### 10.3 Bottom-Up 模式（MVP）

```text
协同约束逻辑：
1. 从 stock_pas_daily 聚合 pas_sa_ratio / 行业 sa_ratio，作为“结构性活跃”证据
2. 选股顺序：先筛 PAS 强股（S/A/B），再做行业聚合（IRS），最后用 MSS 做总风险/仓位上限约束
3. MSS 不用于“是否允许选股”的硬阻断，但用于：
   - 总仓位上限（不突破 TD 上限）
   - 过热/过冷的仓位缩放
4. IRS 的“回避行业”在 BU 中默认作为强警告：
   - 不直接剔除，但会降低该行业股票的最终推荐/仓位

特点：
- 反应快，适合结构性行情
- 噪声更大，因此必须受 TD 上限与 MSS 风控约束
```

### 10.4 仓位控制差异

> **约束规则**：BU 仓位不得超过同周期 TD 仓位上限（风控优先）

| MSS周期 | Top-Down 仓位 | Bottom-Up 仓位 | 说明 |
|----------|---------------|----------------|------|
| 萌芽期 | 80%-100% | 60%-80% | BU更保守，防止假突破 |
| 发酵期 | 60%-80% | 70%-80% | BU更激进，但受TD上限约束 |
| 加速期 | 50%-70% | 60%-70% | BU略激进，但受TD上限约束 |
| 分歧期 | 40%-60% | 40%-60% | 相同 |
| 高潮期 | 20%-40% | 30%-40% | BU不急于出，但受TD上限约束 |
| 扩散期 | 30%-50% | 30%-50% | 相同 |
| **退潮期** | **0%-20%** | **5%-20%** | **核心差异：BU保留强股小仓，但受TD上限约束** |

### 10.5 双模式关系

#### 方案一：相互验证（推荐）

```text
信号强度 = (top_down_signal + bottom_up_signal) / 2

- 两套都看多 → 强信号，可加仓
- 两套都看空 → 强信号，应减仓
- 两套矛盾 → 弱信号，维持/观望
```

#### 方案二：相互补充

```text
- Top-Down 控制总仓位上限
- Bottom-Up 筛选具体标的

示例：
退潮期：
  - TD 说：总仓位不超 20%
  - BU 说：这 3 只强股值得关注
  - 结果：用 20% 仓位买这 3 只强股
```

#### 方案三：仲裁机制（复杂，待验证）

```text
冲突场景：TD 说空仓，BU 说加仓
仲裁规则：
  1. 计算 PAS S/A 级股票占比
  2. 占比 > 5% → 采纳 BU（结构性行情特征）
  3. 占比 < 2% → 采纳 TD（市场确实低迷）
  4. 2%-5% → 折中
```

### 10.6 实现方式

```python
class IntegrationEngine:
    def __init__(self, mode: str = "top_down"):
        """
        mode: "top_down" | "bottom_up" | "dual_verify" | "complementary"
        """
        self.mode = mode
    
    def integrate(self, mss: MssOutput, irs: IrsOutput, pas: PasOutput) -> Signal:
        if self.mode == "top_down":
            return self._top_down_integrate(mss, irs, pas)
        elif self.mode == "bottom_up":
            return self._bottom_up_integrate(mss, irs, pas)
        elif self.mode == "dual_verify":
            return self._dual_verify(mss, irs, pas)
        elif self.mode == "complementary":
            return self._complementary(mss, irs, pas)
```
#### 仲裁与约束（TD 为主，BU 为辅）

- **默认主流程**：`mode="top_down"`，BU 相关模式仅作为补充。
- **仓位上限**：BU 产出的 `position_size` 不得超过同周期 TD 仓位上限（风控优先）
- **方向冲突**：当 TD 与 BU 方向不一致时以 TD 为准
- **风险一致性**：BU 不得突破 TD 的风控阈值（止损、回撤、持仓集中度等）。
- **可追溯性**：集成输出必须记录 `integration_mode`（top_down/bottom_up/dual_verify/complementary）。

### 10.7 回测验证计划（CP-06，兼容文件名 Phase 06）

| 验证项 | 方法 | 预期结果 |
|--------|------|----------|
| 系统性牛市 | 2019-2020 | TD 胜出 |
| 震荡市 | 2021-2022 | BU 胜出 |
| 结构性行情 | 2023题材股 | BU 胜出 |
| 大崩盘 | 2015.6, 2018.10 | TD 胜出（风控） |
| 双模式验证 | 全周期 | 待验证 |

---

## 11. 参数配置

### 11.1 权重参数（baseline + candidate）

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| mss_weight | 1/3 | [0,1] | baseline 默认；候选需经 Validation Gate |
| irs_weight | 1/3 | [0,1] | baseline 默认；候选需经 Validation Gate |
| pas_weight | 1/3 | [0,1] | baseline 默认；候选需经 Validation Gate |
| MAX_MODULE_WEIGHT | 0.60 | [0,1] | 单模块权重上限（与 Validation 权重门一致） |

### 11.2 阈值参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| STRONG_BUY_threshold | 75 | STRONG_BUY 阈值 |
| buy_threshold | 70 | buy阈值 |
| hold_threshold | 50 | hold阈值 |
| sell_threshold | 30 | sell阈值 |
| mss_cold_threshold | 30 | MSS冰点阈值 |
| mss_hot_threshold | 80 | MSS过热阈值 |

---

## 12. 验收与验证（可执行口径）

### 12.1 输入合法性

- mss_score / irs_score / pas_score ∈ [0, 100]
- neutrality ∈ [0, 1]
- integration_mode ∈ {top_down, bottom_up, dual_verify, complementary}
- recommendation ∈ {STRONG_BUY, BUY, HOLD, SELL, AVOID}

### 12.2 量纲一致性

- Integration 不得对评分做二次归一化，只允许边界裁剪。
- 协同约束调整仅影响 pas_score 与 position_size，不得引入新的“因子分值”。

### 12.3 方向一致性稽核

- 方向编码必须只取 {-1, 0, +1}。
- 方向一致性只影响中性度，不得直接反转推荐等级。

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.4.7 | 2026-02-09 | 修复 R26：§2.2/§3.1 增加 IRS `quality_flag/sample_days` 与冷启动回退 baseline 规则；§5 增加 `mss_cycle=unknown` 降级为 `HOLD`；§7.1 中性度改为按 `w_mss/w_irs/w_pas` 加权；§8 周期映射补齐 `unknown` |
| v3.4.6 | 2026-02-08 | 修复 R19：§6.1 筛选注释与 §9.1 对齐，明确主门槛为 `final_score ≥ 55`（PAS/IRS 软排序） |
| v3.4.5 | 2026-02-08 | 修复 R13：§2 增补 ValidationGateDecision 输入；§3 新增 Gate 前置检查（FAIL 拒绝 / WARN 标记）与 baseline/candidate 权重选择伪代码 |
| v3.4.4 | 2026-02-08 | 修复 R11：明确 `strength_factor` 必须在协同约束重算后应用；补充协同约束执行顺序；参数表新增 `MAX_MODULE_WEIGHT=0.60` |
| v3.4.3 | 2026-02-08 | 修复 R10：协同约束后增加 `pas_score` re-clip；并将 §9 推荐列表口径对齐“无单点否决”（仅保留 final_score 主筛选 + PAS/IRS 软排序） |
| v3.4.2 | 2026-02-07 | 修复 P1：中性度计算顺序显式化（风险因子并入 §7）；同步 MSS recession 边界为 <60 + down/sideways |
| v3.4.1 | 2026-02-07 | 修复 P0：STRONG_BUY 阈值下调为 75（提升早周期可达性）；方向一致性补充“三者均中性=consistent”口径 |
| v3.4.0 | 2026-02-07 | 权重口径从“固定1/3”升级为“baseline + candidate + validation gate” |
| v3.3.1 | 2026-02-05 | PAS输出命名对齐 StockPasDaily |
| v3.3.0 | 2026-02-04 | 补齐验收口径：职责边界与互斥条款；一致性惩罚与中性度口径对齐；协同约束后重算 final_score |
| v3.2.1 | 2026-02-03 | 补充 TD 主流程/BU 补充的仲裁与约束规则 |
| v3.2.0 | 2026-02-03 | **仓位约束**：统一BU仓位不超TD上限，退潮期BU 10%-30%→5%-20%，修复错字 |
| v3.1.0 | 2026-02-03 | **双模式集成**：新增 Top-Down/Bottom-Up 双模式设计，支持相互验证/相互补充 |
| v3.0.0 | 2026-01-31 | 重构版：统一周期命名、明确置信度语义、完善信号协同约束 |

### v3.0 与 v2.0 的差异说明

**已移除特性**：
- 增强权重模式（牛市/震荡市/行业轮动行情）
- 带方向加权的综合评分公式

**原因**：为保证系统的确定性和可解释性，v3.0 固定使用标准三三制权重（1:1:1）。

**v2.0 增强模式参考**：见归档文档 `docs/_archive/core-algorithms/integration/`

---

**关联文档**：
- 数据模型：[integration-data-models.md](./integration-data-models.md)
- API接口：[integration-api.md](./integration-api.md)
- 信息流：[integration-information-flow.md](./integration-information-flow.md)


