# Integration 信息流

**版本**: v3.4.9（重构版）
**最后更新**: 2026-02-09
**状态**: 设计完成（验收口径补齐；代码未落地）

---

## 实现状态（仓库现状）

- 当前仓库 `src/integration/` 仅有骨架（`__init__.py`），IntegrationRepository/MssRepository/IrsRepository/PasRepository 等为规划接口。
- 本文档为信息流设计规格，具体实现以 CP-05 落地为准（兼容文件名 Phase 05）。

---

## 1. 数据流总览

### 1.1 Top-Down（默认）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Integration 信息流架构图（三三制）                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                     │
│  │     MSS      │   │     IRS      │   │     PAS      │                     │
│  │  市场情绪    │   │  行业轮动    │   │  价格行为    │                     │
│  │   权重=w_mss │   │   权重=w_irs │   │   权重=w_pas │                     │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘                     │
│         │                  │                  │                              │
│         │   temperature    │  industry_score  │  opportunity_score           │
│         │   cycle          │  rotation_status │  opportunity_grade           │
│         │   trend          │  allocation_advice │  direction                 │
│         │                  │                  │                              │
│         └──────────────────┼──────────────────┘                              │
│                            │                                                 │
│                            ▼                                                 │
│         ┌─────────────────────────────────────────┐                          │
│         │           Integration 集成引擎           │                          │
│         │  ┌─────────────────────────────────┐    │                          │
│         │  │        评分校准层               │    │                          │
│         │  │  统一归一化到0-100             │    │                          │
│         │  └─────────────┬───────────────────┘    │                          │
│         │                │                        │                          │
│         │                ▼                        │                          │
│         │  ┌─────────────────────────────────┐    │                          │
│         │  │      三三制加权融合             │    │                          │
│         │  │ final=mss×w_mss+irs×w_irs+pas×w_pas │    │                     │
│         │  └─────────────┬───────────────────┘    │                          │
│         │                │                        │                          │
│         │                ▼                        │                          │
│         │  ┌─────────────────────────────────┐    │                          │
│         │  │      方向一致性检查             │    │                          │
│         │  │  consistent/partial/divergent   │    │                          │
│         │  └─────────────┬───────────────────┘    │                          │
│         │                │                        │                          │
│         │                ▼                        │                          │
│         │  ┌─────────────────────────────────┐    │                          │
│         │  │      协同约束层                 │    │                          │
│         │  │  多数一致 + 风险上限约束       │    │                          │
│         │  └─────────────┬───────────────────┘    │                          │
│         │                │                        │                          │
│         │                ▼                        │                          │
│         │  ┌─────────────────────────────────┐    │                          │
│         │  │      信号生成层                 │    │                          │
│         │  │  STRONG_BUY/BUY/HOLD/SELL/AVOID│    │                          │
│         │  └─────────────┬───────────────────┘    │                          │
│         │                │                        │                          │
│         │                ▼                        │                          │
│         │  ┌─────────────────────────────────┐    │                          │
│         │  │      仓位计算层                 │    │                          │
│         │  │  position_size 0-1             │    │                          │
│         │  └─────────────┬───────────────────┘    │                          │
│         └────────────────┼────────────────────────┘                          │
│                          │                                                   │
│                          ▼                                                   │
│                 ┌────────────────┐                                           │
│                 │IntegratedRecommendation│                                  │
│                 │   (N只个股)    │                                           │
│                 └────────┬───────┘                                           │
│                          │                                                   │
│        ┌─────────────────┼─────────────────┐                                 │
│        │                 │                 │                                 │
│        ▼                 ▼                 ▼                                 │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                          │
│ │   数据库     │ │  推荐列表    │ │   GUI/API   │                          │
│ │   持久化     │ │  Top 20     │ │   展示层    │                          │
│ └──────────────┘ └──────────────┘ └──────────────┘                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Bottom-Up（补充）

BU 的入口来自 PAS 的强股分布（由 `stock_pas_daily` 聚合得到），用于识别结构性活跃，再进入 IRS 与 MSS 的风控约束。

```
PAS(stock_pas_daily)
  ↓ 聚合：pas_sa_ratio / 行业 sa_ratio / 分布
PAS_BREADTH(派生)
  ↓
IRS(行业聚合与排序)
  ↓
MSS(总风险/仓位上限约束)
  ↓
Integration 输出 integrated_recommendation（记录 integration_mode）
```

在 BU 下：
- MSS 不作为“是否允许选股”的硬阻断项，但仍是总仓位与风险的上限约束。
- BU 产出的仓位不得超过同周期 TD 的上限（见 `integration-algorithm.md` §10.4）。

---

## 2. 数据流步骤

### 2.1 Step 1：数据采集

```
输入：MSS/IRS/PAS 三系统输出 + Validation Gate + Weight Plan
输出：标准化输入数据

处理流程：
1. 读取 MSS 当日输出（mss_panorama 表）
2. 读取 IRS 当日输出（irs_industry_daily 表，31个行业）
3. 读取 PAS 当日输出（stock_pas_daily 表，S/A/B/C/D全量）
4. 读取 Validation Gate 当日决策（validation_gate_decision）
5. 读取 Weight Plan（validation_weight_plan 表）
6. 数据完整性检查
7. 缺失则降级使用“上次可用数据”，并标记质量状态与来源

数据格式：
- MssInput: 单条记录
- IrsInput: 31条记录（每行业一条）
- PasInput: N条记录（S/A/B/C/D全量个股）
- ValidationGateDecision: 单条记录
- WeightPlan: 单条记录
```

### 2.2 Step 2：评分校准

```
输入：原始评分
输出：统一尺度评分

处理流程：
1. MSS温度已是0-100，直接使用
2. IRS行业评分已是0-100，直接使用
3. PAS机会评分已是0-100，直接使用
4. 边界校验：clip(score, 0, 100)

说明：
- 三系统已统一使用Z-Score归一化
- 此阶段仅做边界校验
```

### 2.3 Step 3：三三制融合

```
输入：三系统评分
输出：综合评分

公式：
final_score = mss_score × w_mss + irs_score × w_irs + pas_score × w_pas

约束：
- w_mss ≥ 0, w_irs ≥ 0, w_pas ≥ 0
- w_mss + w_irs + w_pas = 1
- 权重来自当日 validation_gate_decision 对应的 selected_weight_plan
- 若无候选方案，回退 baseline：w_mss=w_irs=w_pas=1/3

示例：
mss_score = 65.3（市场温度）
irs_score = 78.5（行业评分）
pas_score = 92.1（机会评分）
w_mss = 1/3, w_irs = 1/3, w_pas = 1/3（baseline示例）
final_score = 65.3×1/3 + 78.5×1/3 + 92.1×1/3 = 78.6
```

### 2.4 Step 4：方向一致性检查

```
输入：三系统方向信号
输出：综合方向 + 一致性标记

方向编码：
- MSS: up=+1, down=-1, sideways=0
- IRS: IN=+1, OUT=-1, HOLD=0
- PAS: bullish=+1, bearish=-1, neutral=0

一致性判定：
direction_sum = mss_dir + irs_dir + pas_dir

if direction_sum == 3 or direction_sum == -3:
    consistency = "consistent"  # 三者完全一致
elif mss_dir == 0 and irs_dir == 0 and pas_dir == 0:
    consistency = "consistent"  # 三者一致中性
elif abs(direction_sum) >= 1:
    consistency = "partial"     # 两者一致
else:
    consistency = "divergent"   # 方向相互抵消（如 +1/0/-1）

一致性系数（用于综合中性度）：
- consistent → 1.0
- partial → 0.9
- divergent → 0.7

综合方向：
if direction_sum / 3 > 0.3: direction = "bullish"
elif direction_sum / 3 < -0.3: direction = "bearish"
else: direction = "neutral"
```

### 2.5 Step 5：协同约束

```
输入：综合评分 + 方向
输出：调整后评分

协同约束规则（无单点否决）：

1. 多数一致约束：
   if consistency == "consistent":
       strength_factor = 1.0
   if consistency == "partial":
       strength_factor = 0.9  # 信号削弱
   if consistency == "divergent":
       strength_factor = 0.8  # 信号显著削弱

2. MSS风险上限：
   neutrality_risk_factor = 1.0
   if mss_temperature < 30:   # 冰点
       neutrality_risk_factor *= 1.1
   if mss_temperature > 80:   # 过热
       neutrality_risk_factor *= 1.1
   # 仓位缩减统一在 Step 7 通过 mss_factor 处理，避免双重缩减

3. IRS配置权重（行业层约束）：
   if allocation_advice == "回避":
       pas_score *= 0.85
   if allocation_advice == "超配":
       pas_score *= 1.05
   pas_score = clip(pas_score, 0, 100)  # 协同约束后边界重裁剪
   # 重新计算 final_score（沿用 Step 3 的权重公式）

4. 一致性影响：
   final_score *= strength_factor
   # 综合中性度在 §2.7 中统一计算（见下）
```

### 2.6 Step 6：信号生成

```
输入：协同约束后评分
输出：推荐等级

映射规则：
if final_score >= 75 and mss_cycle in {"emergence", "fermentation"}:
    recommendation = "STRONG_BUY"
elif final_score >= 70:
    recommendation = "BUY"
elif final_score >= 50:
    recommendation = "HOLD"
elif final_score >= 30:
    recommendation = "SELL"
else:
    recommendation = "AVOID"
```

### 2.7 综合中性度计算

```
输入：三系统中性度 + 一致性系数 + neutrality_risk_factor
输出：neutrality

neutrality = (mss_neut + irs_neut + pas_neut) / 3
          × consistency_factor
          × neutrality_risk_factor
neutrality = clip(neutrality, 0, 1)
```

### 2.8 Step 7：仓位计算

```
输入：信号 + 各系统参数
输出：仓位建议

base_position = final_score / 100

调整因子：
- mss_factor = 1 - |mss_temperature - 50| / 100
- irs_factor:
  - 超配: 1.2
  - 标配: 1.0
  - 减配: 0.7
  - 回避: 0.3
- pas_factor:
  - S级: 1.2
  - A级: 1.0
  - B级: 0.7
  - C/D级: 0.3

position_size = base_position × mss_factor × irs_factor × pas_factor
position_size = clip(position_size, 0, single_stock_limit)

单股上限：
- S级: 20%
- A级: 15%
- B级: 10%
- C/D级: 5%
```

### 2.9 Step 8：推荐列表生成

```
输入：所有集成信号
输出：Top N推荐列表

筛选条件：
1. mss_temperature is not null
2. final_score >= 55

排序规则：
1. 按 final_score 降序（主排序）
2. 按 opportunity_score 降序（PAS 软排序，不作硬过滤）
3. 按 allocation_advice 优先级（超配 > 标配 > 减配 > 回避）降序（IRS 软排序，不作硬过滤）

输出限制：
- 最多20只
- 每行业最多5只
```

---

## 3. 组件依赖关系

```
┌─────────────────────────────────────────────────────────────────┐
│                       组件依赖图                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  IntegrationController (API层)                                   │
│       │                                                          │
│       ▼                                                          │
│  IntegrationService (服务层)                                      │
│       │                                                          │
│       ├───────────────────┬───────────────────┐                  │
│       ▼                   ▼                   ▼                  │
│  IntegrationEngine   IntegrationRepository RecommendationGen     │
│  (集成引擎)          (数据仓库)           (推荐生成器)           │
│       │                   │                   │                  │
│       ├───────────────────┴───────────────────┤                  │
│       ▼                                       ▼                  │
│  ScoreCalibrator                        DirectionChecker         │
│  (评分校准器)                           (方向检查器)             │
│       │                                       │                  │
│       ├───────────────────┬───────────────────┤                  │
│       ▼                   ▼                   ▼                  │
│  SignalConstraint    SignalGenerator     PositionCalculator      │
│  (协同约束)          (信号生成器)        (仓位计算器)            │
│                                                                  │
│  ┌────────────────────────────────────────────┐                  │
│  │              上游数据仓库                   │                  │
│  │  MssRepository  IrsRepository  PasRepository│                  │
│  └────────────────────────────────────────────┘                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. 数据流转示例

### 4.1 单日计算流程

```
Timeline: T=15:35 (MSS/IRS/PAS计算完成后)

T+0min:  调度器触发 IntegrationService.calculate("20260131")
T+0.1min: MssRepository.get_by_date() -> MssInput
T+0.2min: IrsRepository.get_by_date() -> List[IrsInput] (31个)
T+0.5min: PasRepository.get_by_grade("20260131", ["S","A","B","C","D"]) -> List[PasInput] (N个)
T+0.7min: ValidationRepository.get_gate_decision() -> ValidationGateDecision
T+0.8min: ValidationRepository.get_weight_plan() -> WeightPlan
T+1.0min: IntegrationEngine.calculate()
         ├─ 评分校准
         ├─ baseline/candidate 权重融合
         ├─ 方向一致性检查
         ├─ 协同约束
         ├─ 信号生成
         └─ 仓位计算
T+2.0min: RecommendationGenerator.generate(top_n=20)
T+2.5min: IntegrationRepository.save_batch()
T+3.0min: 返回结果
```

### 4.2 数据流转格式

```
Step 1:
  MssInput: {temperature: 65.3, cycle: "divergence", trend: "up"}
  IrsInput[]: [{industry_code: "801780", industry_score: 78.5, rotation_status: "IN", allocation_advice: "标配"}, ...]
  PasInput[]: [{stock_code: "000001", opportunity_score: 92.1, opportunity_grade: "S"}, ...]

Step 2-3:
  CalibratedScores: {
    "000001": {
      mss_score: 65.3,
      irs_score: 78.5,
      pas_score: 92.1,
      w_mss: 0.3333,
      w_irs: 0.3333,
      w_pas: 0.3333,
      final_score: 78.6
    }
  }

Step 4:
  DirectionResult: {
    direction_sum: 3,  # all bullish
    consistency: "consistent",
    direction: "bullish"
  }

Step 5-6:
  GatedSignal: {
    final_score: 78.6,  # 协同约束后（本例无调整）
    recommendation: "BUY"
  }

Step 7:
  PositionResult: {
    base: 0.786,
    mss_factor: 0.85,
    irs_factor: 1.0,
    pas_factor: 1.2,
    final: 0.15  # 受单股上限约束
  }

Step 8:
  Recommendation[20]: [{rank: 1, stock_code: "000001", ...}, ...]
```

---

## 5. 异常处理

### 5.1 数据缺失

| 缺失系统 | 处理策略 |
|----------|----------|
| MSS缺失 | 使用上次可用MSS数据，标记degraded |
| IRS缺失 | 该行业不参与推荐，标记degraded |
| PAS缺失 | 该个股不参与推荐，标记degraded |

### 5.2 计算异常

| 异常情况 | 处理策略 |
|----------|----------|
| 评分超界 | clip到[0,100] |
| 除零错误 | 返回中性值50 |
| 三系统全缺失 | 暂停当日集成，生成告警 |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.4.9 | 2026-02-09 | 修复 R30：§4.1 Validation 获取时序返回类型精确化（`get_gate_decision() -> ValidationGateDecision`，`get_weight_plan() -> WeightPlan`），并明确 WeightPlan 来源 `validation_weight_plan` |
| v3.4.8 | 2026-02-08 | 修复 R19：§2.1 Step 1 补齐 Validation Gate 与 Weight Plan 采集步骤，输入格式同步补齐 |
| v3.4.7 | 2026-02-08 | 修复 R18：§4.2 示例 `temperature=65.3 + trend=up` 的 `cycle` 改为 `divergence`（与 MSS 判定口径一致） |
| v3.4.6 | 2026-02-08 | 修复 R10：Step 5 协同约束后增加 `pas_score` 重裁剪（clip 0..100）避免越界 |
| v3.4.5 | 2026-02-07 | 修复 R9 P0：Step 8 移除 PAS/IRS 单点硬过滤，改为 final_score 主筛选 + PAS/IRS 软排序，保持“无单点否决” |
| v3.4.4 | 2026-02-07 | 修复 R8 P1：移除 Step 5 中对 `position_size` 的重复冷/热市场缩减，仓位统一由 Step 7 `mss_factor` 处理 |
| v3.4.3 | 2026-02-07 | 修复 R8 P0：Step 3 与架构图统一为权重计划公式（WeightPlan），不再硬编码等权平均 |
| v3.4.2 | 2026-02-07 | 修复 P1：中性度流程去歧义（Step 5 输出 neutrality_risk_factor，Step 7 一次性计算 neutrality） |
| v3.4.1 | 2026-02-07 | 修复 P0：方向一致性补充“三者一致中性=consistent”；STRONG_BUY 阈值同步为 75 |
| v3.4.0 | 2026-02-07 | 新增 Validation Gate 与 weight_plan 在集成前置时点 |
| v3.3.0 | 2026-02-04 | 同步 Integration v3.3.0：协同约束后重算 final_score，口径与验收条款对齐 |
| v3.0.0 | 2026-01-31 | 重构版：统一信息流架构、明确阶段划分、补充组件依赖 |

---

**关联文档**：
- 算法设计：[integration-algorithm.md](./integration-algorithm.md)
- 数据模型：[integration-data-models.md](./integration-data-models.md)
- API接口：[integration-api.md](./integration-api.md)


