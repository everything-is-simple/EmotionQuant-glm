# MSS 市场情绪算法设计

**版本**: v3.1.5（重构版）
**最后更新**: 2026-02-09
**状态**: 设计完成（验收口径补齐；代码未落地）
**数据基线**: TuShare 5000积分

---

## 1. 算法概述

### 1.1 定位与职责

MSS（Market Sentiment System）是 EmotionQuant 系统的市场情绪基准，负责判断**市场整体情绪状态**，为集成层提供风险上限与情绪参考。

**核心输出**：
- 市场温度（0-100°C）
- 情绪周期（七大周期）
- 趋势方向（up/down/sideways）
- 仓位建议

命名规范：情绪周期与趋势命名详见 [naming-conventions.md](../../../naming-conventions.md) §1-2。

### 1.2 与其他模块协同

```text
MSS（市场状态）──► IRS（行业选择）──► PAS（个股精选）
      │                  │                  │
      └──────────────────┴──────────────────┘
                    三三制集成

协同原则：
- MSS/IRS/PAS 同权协同，集成层不以 MSS 单点否决信号
- MSS 主要提供市场风险上限与仓位约束
```

---

## 2. 因子体系

### 2.1 架构总览

采用「三大基础因子 + 三大增强因子」六因子体系：

| 类别 | 因子名称 | 组内权重 | 总权重 | 说明 |
|------|----------|----------|--------|------|
| **基础因子（组权重 85%）** | 大盘系数 | 20% | 17% | 市场参与度（上涨覆盖率） |
| | 赚钱效应 | 40% | 34% | 上行扩张强度（赚钱面/高度） |
| | 亏钱效应 | 40% | 34% | 下行压力强度（亏钱面/高度） |
| **增强因子（组权重 15%）** | 连续性因子 | 33.33% | 5% | 持续性（队列延续） |
| | 极端因子 | 33.33% | 5% | 尾部活跃（两端极端行为密度） |
| | 波动因子 | 33.33% | 5% | 离散度（收益/成交额波动） |

> **权重分配原则**：总权重 = 组内权重 × 组权重；基础因子组权重 85%，增强因子组权重 15%。

### 2.2 因子语义边界（跨模块澄清）

> **背景**：涨停/成交量在 MSS/IRS/PAS 三模块都有使用，但**视角和粒度不同**，不构成信息重复。

| 数据来源 | MSS 使用角度 | 粒度 | 回答的问题 |
|----------|--------------|------|----------------|
| **涨停** | 赚钱效应（全市场涨停占比/扩张） | 全局统计 | 市场整体多头力量如何？ |
| **成交量** | 波动因子（全市场成交额波动率） | 全局统计 | 市场情绪波动大不大？ |

**与 IRS/PAS 的区别**：
- MSS 用涨停衡量“市场整体赚钱效应”，IRS 用涨停衡量“行业龙头表现”，PAS 用涨停衡量“个股爆发力”
- 同一数据，三个视角：**全局统计 vs 行业局部 vs 个股特征**

### 2.3 外部实践参考（GitHub）

用于“有理有据”地校准 MSS 因子家族命名与边界（仅作参考，不引入技术指标）：

- **参与度 / Advance–Decline（A/D）**：
  - [pulkitanchalia/NSE_ADVANCE_DECLINE_RATIO](https://github.com/pulkitanchalia/NSE_ADVANCE_DECLINE_RATIO)（README 展示 Advance/Decline count & ratio）
  - [lakshaysinghal/bhavCopy](https://github.com/lakshaysinghal/bhavCopy)（README 展示 market breadth + advance/decline ratio 示例输出）
- **突破扩散 / Net New Highs–Lows（NH–NL）**：
  - [johnmuchow/Net-Highs-Net-Lows](https://github.com/johnmuchow/Net-Highs-Net-Lows)（README 展示 new highs / new lows / net highs-lows 的计算与示例输出）
- **Market Breadth 指标集合/可视化**：
  - [SamapanThongmee/SET50_SET_Market_Breadth_Indicators](https://github.com/SamapanThongmee/SET50_SET_Market_Breadth_Indicators)（README 汇总 breadth 指标与图示，包含新高/新低类指标）

> 注：GitHub Code Search API 需要认证，本次参考以 README/仓库说明为主；我们只提取“概念拆分方式”，不复用任何 TA 指标实现细节。

### 2.4 因子家族定义与互斥边界（MSS 内部验收口径）

> 目标：让六因子体系具备**可执行的验收口径**，避免“同一语义重复加分/扣分”。

#### 2.4.1 四大方向（宏观家族）——验收用“观测归属表”

> 说明：
> - 四大方向是对 **raw 观测口径** 的分类（用于稽核“语义是否重复覆盖”），不是额外的打分/加权层。
> - 每个 raw 观测必须且只能归属到一个宏观方向（见 §10.4）。

| 宏观方向 | GitHub 常见表述 | raw 观测（必须互斥归属） | 主要影响的因子 |
|---------|----------------|--------------------------|----------------|
| 参与度 | Advance/Decline Ratio | rise_ratio（可扩展：fall_ratio、net_breadth） | 大盘系数 |
| 突破扩散 | Net New Highs/Lows | new_high_ratio / new_low_ratio / strong_up_ratio / strong_down_ratio / continuous_limit_up_ratio / continuous_new_high_ratio | 赚钱效应 / 亏钱效应 / 连续性因子 |
| 极端事件 | Event Breadth | limit_up_ratio / limit_down_ratio / broken_rate / high_open_low_close_ratio / low_open_high_close_ratio | 赚钱效应 / 亏钱效应 / 极端因子 |
| 分歧风险 | Dispersion / Volatility | pct_chg_std / amount_volatility | 波动因子 |

#### 2.4.2 六因子 = 六个语义家族（互斥）

| 因子 | 语义家族 | 关心的对象 | 代表性观测 |
|------|----------|------------|------------|
| 大盘系数 | **参与度** | 涨跌覆盖面 | rise_ratio（上涨占比） |
| 赚钱效应 | **上行扩张** | 赚钱“高度/速度” | limit_up_ratio / new_high_ratio / strong_up_ratio |
| 亏钱效应 | **下行压力** | 亏钱“高度/速度” | broken_rate / limit_down_ratio / strong_down_ratio / new_low_ratio |
| 连续性因子 | **持续性** | 队列是否延续 | 连板占比、连续新高占比 |
| 极端因子 | **尾部活跃** | 两端极端行为密度 | 高开低走占比 + 低开高走占比 |
| 波动因子 | **离散度** | 截面分化/波动 | pct_chg_std / amount_volatility |

#### 2.4.3 互斥边界说明（允许的“复用”仅限分母/派生）

- **强制互斥**：同一类“计数语义”不能被拆成多个因子同时加权（例如不能同时用“涨停家数”既当上行扩张又当尾部活跃）。
- **允许复用（不算重复加分）**：
  - 作为**分母**参与比例构造（例如 limit_up_count 作为连续性因子的分母，用于刻画“队列延续率”而不是再次奖励“涨停数量”）。
  - 作为**派生变量**构造风险比率（例如 touched_limit_up 与 limit_up_count 仅用于 broken_rate）。
- **验收标准**：任何新增 MSS 因子必须明确归属到上述 6 个家族之一；如果无法归属，视为设计缺陷。

---

## 3. 核心公式（验收口径）

> **统一规则（零容忍）**：所有 count 必须先转为 ratio（0-1）或 per-stock 比率，再通过 Z-Score 映射到 0-100 分数；禁止使用 ×1000 等硬编码放大系数。
> Z-Score 映射函数见 §7。

### 3.1 大盘系数（参与度 / Breadth Participation）

原始值（ratio）：

```text
market_coefficient_raw = rise_count / total_stocks
```

得分（0-100）：

```text
market_coefficient = zscore_normalize(market_coefficient_raw, mean, std)
```

### 3.2 赚钱效应（上行扩张 / Upside Expansion）

原始值（ratio）：

```text
limit_up_ratio   = limit_up_count / total_stocks
new_high_ratio   = new_100d_high_count / total_stocks
strong_up_ratio  = strong_up_count / total_stocks

profit_effect_raw = 0.4×limit_up_ratio + 0.3×new_high_ratio + 0.3×strong_up_ratio
profit_effect     = zscore_normalize(profit_effect_raw, mean, std)
```

### 3.3 亏钱效应（下行压力 / Downside Pressure）

原始值（ratio）：

```text
broken_rate       = (touched_limit_up - limit_up_count) / max(touched_limit_up, 1)
limit_down_ratio  = limit_down_count / total_stocks
strong_down_ratio = strong_down_count / total_stocks
new_low_ratio     = new_100d_low_count / total_stocks

loss_effect_raw = 0.3×broken_rate + 0.2×limit_down_ratio + 0.3×strong_down_ratio + 0.2×new_low_ratio
loss_effect     = zscore_normalize(loss_effect_raw, mean, std)
```

语义：**loss_effect 越高表示下行压力越大**，因此在温度中使用 `(100 - loss_effect)`。

### 3.4 连续性因子（持续性 / Continuity）

原始值（ratio）：

```text
continuous_limit_up_ratio = (continuous_limit_up_2d + 2×continuous_limit_up_3d_plus) / max(limit_up_count, 1)
continuous_new_high_ratio = continuous_new_high_2d_plus / max(new_100d_high_count, 1)

continuity_factor_raw = 0.5×continuous_limit_up_ratio + 0.5×continuous_new_high_ratio
continuity_factor     = zscore_normalize(continuity_factor_raw, mean, std)
```

### 3.5 极端因子（尾部活跃 / Tail Activity）

原始值（ratio）：

```text
high_open_low_close_ratio  = high_open_low_close_count / total_stocks
low_open_high_close_ratio  = low_open_high_close_count / total_stocks

extreme_factor_raw = high_open_low_close_ratio + low_open_high_close_ratio
extreme_factor     = zscore_normalize(extreme_factor_raw, mean, std)
```

### 3.6 波动因子（离散度 / Dispersion）

原始值（continuous）：

```text
volatility_factor_raw = 0.5×pct_chg_std + 0.5×amount_volatility
volatility_factor     = zscore_normalize(volatility_factor_raw, mean, std)
```

---

## 4. 温度计算

### 4.1 基础温度（必选）

```text
base_temperature = 大盘系数 × 0.2 + 赚钱效应 × 0.4 + (100 - 亏钱效应) × 0.4
```

### 4.2 完整温度（含增强因子）

```text
temperature = base_temperature × 0.85 + 连续性因子 × 0.05 + 极端因子 × 0.05 + 波动因子 × 0.05
```

等价总权重表达（便于实现）：

```text
temperature = 大盘系数 × 0.17 + 赚钱效应 × 0.34 + (100 - 亏钱效应) × 0.34 + 连续性因子 × 0.05 + 极端因子 × 0.05 + 波动因子 × 0.05
```

- **取值范围**：0°C - 100°C
- **设计原则**：增强因子为可选，不启用时直接使用基础温度

---

## 5. 情绪周期状态机

### 5.1 周期定义（含兜底）

| 周期 | 温度条件 | 趋势条件 | 仓位建议 | 判定优先级 |
|------|----------|----------|----------|------------|
| 高潮期 | ≥75°C | any | 20%-40% | 1（最高） |
| 萌芽期 | <30°C | up | 80%-100% | 2 |
| 发酵期 | 30-45°C | up | 60%-80% | 3 |
| 加速期 | 45-60°C | up | 50%-70% | 4 |
| 分歧期 | 60-75°C | up/sideways | 40%-60% | 5 |
| 扩散期 | 60-75°C | down | 30%-50% | 6 |
| 退潮期 | <60°C | down/sideways | 0%-20% | 7（最低） |
| unknown | 其他异常输入 | 非 up/down/sideways | 0%-20% | 8（兜底） |

> **判定规则**：按优先级从高到低依次匹配，匹配成功即返回

### 5.2 周期判定伪代码

```python
def detect_cycle(temperature: float, trend: str) -> str:
    """
    周期判定逻辑（按优先级顺序）
    trend取值: "up" | "down" | "sideways"
    """
    # 优先级1：高潮期
    if temperature >= 75:
        return "climax"  # 高潮期
    
    # 优先级2-4：上升趋势
    if trend == "up":
        if temperature < 30:
            return "emergence"  # 萌芽期
        if temperature < 45:
            return "fermentation"  # 发酵期
        if temperature < 60:
            return "acceleration"  # 加速期
        return "divergence"  # 分歧期（60-75，上升）
    
    # 优先级5：横盘
    if trend == "sideways":
        if temperature >= 60:
            return "divergence"  # 分歧期（60-75，横盘）
        return "recession"  # 退潮期（<60，横盘）
    
    # 优先级6-7：下降趋势
    if trend == "down":
        if temperature >= 60:
            return "diffusion"  # 扩散期
        return "recession"  # 退潮期
    
    return "unknown"  # 输入异常兜底（仓位按 0%-20%）
```

### 5.3 周期中英文映射（与集成层统一）

| 中文名称 | 英文代码 | 说明 |
|----------|----------|------|
| 萌芽期 | emergence | 低温上升 |
| 发酵期 | fermentation | 温和上升 |
| 加速期 | acceleration | 快速上升 |
| 分歧期 | divergence | 高位震荡 |
| 高潮期 | climax | 极热 |
| 扩散期 | diffusion | 高位下降 |
| 退潮期 | recession | 持续下降 |

### 5.4 趋势判定

| 趋势 | 英文代码 | 判定条件 |
|------|----------|----------|
| 上升 | up | `temperature[t-2] < temperature[t-1] < temperature[t]`（严格递增） |
| 下降 | down | `temperature[t-2] > temperature[t-1] > temperature[t]`（严格递减） |
| 横盘 | sideways | 其他情况 |

> 说明：若最近 3 日温度存在相等（如 `50, 50, 50`），归类为 `sideways`，不计入 up/down。

---

## 6. 中性度计算

```text
neutrality = 1 - |temperature - 50| / 50
```

**语义说明**：
- 此公式计算的是**中性程度**（非信号强度）
- temperature = 50 时，neutrality = 1（最中性）
- temperature = 0 或 100 时，neutrality = 0（最极端）
- 用于表示"评分接近中性的程度"，越极端信号越明确但也越需谨慎

### 6.1 历史排名与百分位（rank / percentile）

```text
输入：
- temperature_t: 当日温度
- T_hist: 截至当日（含当日）的历史温度序列，按时间升序

定义：
- rank = 1 + count(T_hist > temperature_t)
  （温度越高 rank 越靠前；并列按同分同名次处理）
- percentile = 100 × count(T_hist <= temperature_t) / len(T_hist)
  （取值 0-100，表示当日温度在历史中的累计分位）
```

实现约束：
- 历史窗口默认使用全量可用历史；若采用滚动窗口，必须在运行配置中显式声明窗口长度并保持跨文档一致。
- `rank` 与 `percentile` 均基于 `temperature` 计算，不基于单因子得分。
- 当 `len(T_hist)=1`（首日冷启动）时，`rank=1`，`percentile=100`。

---

## 7. 归一化方法

统一采用 Z-Score 归一化（并作为 MSS 因子验收口径的一部分）：

```python
def zscore_normalize(value: float, mean: float, std: float) -> float:
    """Z-Score归一化并映射到0-100"""
    if std == 0:
        return 50.0
    z = (value - mean) / std
    return max(0.0, min(100.0, (z + 3) / 6 * 100))
```

- **映射规则**：[-3σ, +3σ] → [0, 100]
- **统计参数**：基于 2015-2025 历史样本计算
- **强制前置**：count → ratio/per-stock → zscore（禁止 count × 常数 的硬编码缩放）

### 7.1 冷启动与参数来源

```text
参数文件：${DATA_PATH}/config/mss_zscore_baseline.parquet
字段：factor_name, mean, std, sample_start, sample_end, updated_at
```

- 首次部署：使用离线 baseline 文件（2015-2025）初始化 mean/std。
- 热启动：每日收盘后按滚动窗口（默认 120 日）增量更新统计参数。
- 冷启动兜底：
  - 若某因子缺失 mean/std，直接返回 50（中性分）。
  - 若样本窗口 < 60 交易日，沿用 baseline 参数，不启用在线更新。

---

## 8. 参数配置

### 8.1 基础参数

| 参数名称 | 代码 | 默认值 | 可调范围 |
|----------|------|--------|----------|
| 新高统计窗口 | new_high_window | 100 | 60-120 |
| 大涨阈值 | strong_move_threshold | 5% | 3%-7% |
| 炸板率阈值 | broken_rate_threshold | 20% | 10%-30% |

### 8.2 增强因子参数

| 参数名称 | 代码 | 默认值 | 可调范围 |
|----------|------|--------|----------|
| 连续性窗口 | continuity_window | 3 | 2-5 |
| 尾部活跃预警阈值（ratio） | tail_activity_threshold | 0.06 | 0.02-0.12 |
| 波动窗口 | volatility_windows | (20, 60) | (10, 120) |
| Z-Score窗口 | zscore_window | 120 | 60-240 |

### 8.3 权重参数

| 参数名称 | 代码 | 默认值 | 可调范围 |
|----------|------|--------|----------|
| 基础因子权重 | base_weight | 0.85 | 0.70-0.90 |
| 增强因子权重 | enhanced_weight | 0.15 | 0.10-0.30 |

---

## 9. 预警规则

| 预警类型 | 条件 | 说明 |
|----------|------|------|
| 过热预警 | temperature ≥ 80 | 建议降低风险暴露 |
| 过冷预警 | temperature ≤ 20 | 关注反转机会 |
| 尾部活跃 | extreme_factor_raw ≥ tail_activity_threshold | 极端行为密度偏高，需谨慎（不直接等同方向） |
| 趋势背离 | trend 与 cycle 不一致 | 需人工复核 |

---

## 10. 验收与验证（可执行口径）

### 10.1 数据就绪（L2 market_snapshot 必须提供）

- 必备字段：
  - 计数类：total_stocks、rise_count、limit_up_count、limit_down_count、touched_limit_up、new_100d_high_count、new_100d_low_count、strong_up_count、strong_down_count、continuous_limit_up_2d、continuous_limit_up_3d_plus、continuous_new_high_2d_plus、high_open_low_close_count、low_open_high_close_count
  - 连续类：pct_chg_std、amount_volatility
  - 质量类：data_quality（normal/stale/cold_start）、stale_days、source_trade_date
- 约束（零容忍）：
  - total_stocks > 0
  - 0 ≤ rise_count, fall_count, flat_count ≤ total_stocks
  - rise_count + fall_count ≤ total_stocks（`flat_count` 允许与 rise/fall 交叉覆盖）
  - 0 ≤ limit_up_count ≤ touched_limit_up
  - 所有 ratio 必须落在 [0, 1]；使用 max(分母, 1) 防止除零
  - stale_days ≤ 3（>3 视为陈旧数据，阻断 MSS 主流程）

### 10.2 尺度一致性（count→ratio→zscore）

- 任一因子的输入如果是“家数/数量”，必须先转为 ratio 或 per-stock 比率。
- 归一化只能通过 `zscore_normalize`（或等价实现）完成；禁止 ×1000、×100 等硬编码放大。

### 10.3 输出合法性

- 因子分数与 temperature 必须位于 [0, 100]
- neutrality 必须位于 [0, 1]
- cycle/trend 必须落在枚举集合内

### 10.4 宏观方向稽核条款（四大方向：不得重复覆盖）

宏观方向用于对 raw 观测做语义稽核（不引入额外加权层），验收要求如下：

1. **唯一归属**：每个 raw 观测必须且只能归属到一个宏观方向（见 §2.4.1）。
2. **不得重复覆盖**：同一 raw 观测不得以“分子语义”形式出现在两个不同因子里；允许复用仅限 §2.4.3 所述的分母/派生。
3. **变更约束**：新增/调整 raw 观测口径时，必须同步更新 §2.4.1，并在变更记录中说明原因（例如市场结构变化、数据字段口径变化）。
4. **可追溯性**：实现层（L2→L3）应能追溯每个 raw 观测属于哪个宏观方向（用于解释温度变化的主驱动）。

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.1.5 | 2026-02-09 | 修复 R26：§10.1 数据就绪增加 `data_quality/stale_days/source_trade_date` 质量字段与 `stale_days ≤ 3` 约束，防止陈旧快照继续计算 |
| v3.1.4 | 2026-02-08 | 修复 R19：§5.1 周期映射补齐 `unknown` 的仓位建议（0%-20%）；§5.2 fallback 注释显式兜底语义 |
| v3.1.3 | 2026-02-08 | 修复 R17：补充 `rank/percentile` 的计算定义与实现约束（基于 `temperature` 的历史排序与累计分位） |
| v3.1.2 | 2026-02-08 | 修复 R13：趋势判定明确为严格递增/递减（相等归入 sideways）；§10.1 输入约束对齐数据模型，`flat_count` 允许交叉覆盖 |
| v3.1.1 | 2026-02-07 | 修复 P0：sideways 周期判定补充温度分支（<60 归入 recession，避免低温误判 divergence） |
| v3.1.0 | 2026-02-04 | 补齐验收口径：四大方向观测归属表与稽核条款；因子家族互斥边界；统一 count→ratio→zscore；修正“亏钱效应=下行压力”的语义定义；补充 GitHub 外部实践参考 |
| v3.0.0 | 2026-01-31 | 重构版：统一公式口径、修复权重不一致、统一周期命名 |
| v2.0.0 | 2026-01-22 | 增强版：六因子体系 |
| v1.0.0 | 2026-01-10 | 初始版本 |

---

**关联文档**：
- 数据模型：[mss-data-models.md](./mss-data-models.md)
- API接口：[mss-api.md](./mss-api.md)
- 信息流：[mss-information-flow.md](./mss-information-flow.md)


