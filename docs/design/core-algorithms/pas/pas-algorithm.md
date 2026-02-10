# PAS 价格行为信号算法设计

**版本**: v3.1.11（重构版）
**最后更新**: 2026-02-09
**状态**: 设计完成（验收口径补齐；代码未落地）

---

## 1. 算法概述

### 1.1 设计目标

PAS（Price Action Signals）是个股价格行为信号系统，用于在符合行业配置的个股中筛选最具投资价值的标的，并评估买入时机和风险收益比。

### 1.2 核心输出

| 输出 | 说明 | 范围 |
|------|------|------|
| opportunity_score | 机会评分 | 0-100 |
| opportunity_grade | 机会等级 | S/A/B/C/D |
| direction | 方向判断 | bullish/bearish/neutral |
| risk_reward_ratio | 风险收益比 | ≥1.0（执行最低门槛） |
| neutrality | 中性度 | 0-1（越接近1越中性，越接近0信号越极端） |

命名规范：PAS机会等级与方向命名详见 [naming-conventions.md](../../../naming-conventions.md) §4-5。

### 1.3 单指标不得独立决策合规声明

**重要**：本算法遵守“单指标不得独立决策”铁律：

| 禁止使用 | 替代方案 |
|----------|----------|
| MA/EMA/SMA 均线 | 价格相对N日高低点位置 |
| MACD/RSI/KDJ | 涨跌幅分布、涨停频率 |
| BOLL/ATR | 价格振幅、波动率 |

---

## 2. 因子体系

### 2.1 因子架构

**三大核心因子（100%）**

| 因子名称 | 权重 | 说明 |
|----------|------|------|
| 牛股基因因子 | 20% | 历史强势特征 |
| 结构位置因子 | 50% | 价格位置与突破强度 |
| 行为确认因子 | 30% | 量价配合验证 |

### 2.2 因子语义边界（跨模块澄清）

> **背景**：涨停/成交量在 MSS/IRS/PAS 三模块都有使用，但**视角和粒度不同**，不构成信息重复。

| 数据来源 | PAS 使用角度 | 粒度 | 回答的问题 |
|----------|--------------|------|----------------|
| **涨停** | 牛股基因（个股历史涨停次数） + 行为确认（当日涨停状态） | 个股特征 | 这只股票爆发力如何？ |
| **成交量** | 行为确认因子（量比 = 当日/20日均量） | 个股特征 | 这只股票放量了吗？ |

**与 MSS/IRS 的区别**：
- MSS 看全市场涨停家数，IRS 看行业龙头涨停，PAS 看个股历史涨停频率
- MSS 看全市场成交波动，IRS 看行业资金流入，PAS 看个股量比
- 同一数据，三个视角：**全局统计 vs 行业局部 vs 个股特征**

---

### 2.3 外部实践参考（GitHub）

用于“有理有据”地校准 PAS 因子归类（仅作参考，不引入技术指标）：

- **突破/整理区间 → 结构位置因子**：
  - Screeni-py：强调“整理区间 + 潜在突破”的筛选。
  - PKScreener：强调“整理后潜在突破”的筛选。
- **相对量能 → 行为确认因子**：
  - Screeni-py：以成交量相对均量（volume ratio）衡量放量突破。
  - PKScreener：提供 volume/MA20 相对量能指标。

> 注：仅采纳“结构位置/突破/相对量能”的概念归类；若引入技术指标，仅可作为辅助特征，不能单独触发交易。

---

### 2.4 宏观方向（验收用“观测归属表”）

> 说明：宏观方向是 **raw 观测口径** 的分类（用于稽核“语义是否重复覆盖”），不是额外打分层。

| 宏观方向 | raw 观测（必须互斥归属） | 主要影响的因子 |
|---------|--------------------------|----------------|
| 历史惯性/基因 | limit_up_120d_ratio、new_high_60d_ratio、max_pct_chg_history | 牛股基因因子 |
| 结构位置/突破 | price_position、trend_continuity_ratio、breakout_strength | 结构位置因子 |
| 行为确认/量价 | volume_ratio、pct_chg、limit_up_flag | 行为确认因子 |

### 2.5 互斥边界说明（允许的“复用”仅限分母/派生）

- **强制互斥**：同一类 raw 观测不能被拆成多个因子重复加权。
- **允许复用**：仅限作为分母/派生变量（例如 limit_up_count 仅用于构造比例/连续性）。
- **验收标准**：新增/调整 raw 观测必须更新 §2.4 并说明归属理由。

## 3. 因子计算公式

### 3.1 牛股基因因子（Bull Gene Factor）

**核心思想**：历史强势股更容易继续表现强势。

```text
定义（ratio）：
- limit_up_120d_ratio = limit_up_count_120d / 120
- new_high_60d_ratio = new_high_count_60d / 60
- max_pct_chg_history_ratio = max_pct_chg_history / 100  # 输入口径为百分数（15 表示 15%）

公式：
bull_gene_raw = 0.4×limit_up_120d_ratio
              + 0.3×new_high_60d_ratio
              + 0.3×max_pct_chg_history_ratio
bull_gene_score = normalize_zscore(bull_gene_raw)

数据来源：raw_daily + raw_limit_list
权重：20%
```

- **强制前置**：count → ratio/per-stock → zscore（禁止 count × 常数 的硬编码缩放）

### 3.2 结构位置因子（Structure Position Factor）

**核心思想**：价格位置决定买入时机和风险收益比。

**⚠️ 铁律合规**：使用价格相对位置替代均线指标

```text
定义（ratio）：
- price_position = (close - low_60d) / max(high_60d - low_60d, ε)
- trend_continuity_ratio = consecutive_up_days / trend_window
- breakout_strength = (close - high_60d_prev) / max(high_60d_prev, ε)

公式：
structure_raw = 0.4×price_position
              + 0.3×trend_continuity_ratio
              + 0.3×breakout_strength
structure_score = normalize_zscore(structure_raw)

数据来源：raw_daily
权重：50%
```

**与旧版对比**：

| 旧版（违反铁律） | 新版（合规） |
|------------------|--------------|
| MA5>MA10>MA20>MA60 多头排列 | 连续上涨天数 + 价格位置 |
| 相对MA60位置 | 相对60日高低点位置 |
| 突破MA20 | 突破60日前高 |

### 3.3 行为确认因子（Action Confirmation Factor）

**核心思想**：量能和涨跌停行为验证价格突破的有效性。

```text
定义（ratio）：
- volume_ratio = vol / max(volume_avg_20d, ε)
- limit_up_flag = is_limit_up ? 1.0 : (is_touched_limit_up ? 0.7 : 0.0)
- volume_ratio_norm = clip(volume_ratio / 3.0, 0, 1)
- pct_chg_norm = clip((pct_chg + 20) / 40, 0, 1)

公式：
behavior_raw = 0.4×volume_ratio_norm
             + 0.3×pct_chg_norm
             + 0.3×limit_up_flag
behavior_score = normalize_zscore(behavior_raw)

数据来源：raw_daily + raw_daily_basic + raw_limit_list
权重：30%
```

---

## 4. 综合评分计算

### 4.1 加权求和公式

```text
opportunity_score = bull_gene_score × 0.20
                  + structure_score × 0.50
                  + behavior_score × 0.30
```

### 4.2 归一化方法

统一使用 Z-Score 归一化（与 MSS/IRS 保持一致）：

```python
def normalize_zscore(value: float, mean: float, std: float) -> float:
    """Z-Score归一化并映射到 0-100（与 v2.0 基线统一）"""
    if std == 0:
        return 50.0
    z = (value - mean) / std
    # 映射规则：[-3σ, +3σ] → [0, 100]
    score = (z + 3) / 6 * 100
    return max(0.0, min(100.0, score))  # 裁剪到 [0, 100]
```

### 4.3 Z-Score 冷启动与基线参数

```text
基线参数文件：
- ${DATA_PATH}/config/pas_zscore_baseline.parquet

冷启动策略：
1. 首次部署：加载离线 baseline（建议覆盖完整牛熊周期）
2. 日常更新：按交易日滚动更新 mean/std（窗口默认 120 日）
3. 缺失兜底：任一因子缺 mean/std 时，因子得分返回 50（中性）

说明：
- 仅允许对已完成 ratio/标准化映射后的 raw 值做 Z-Score
- baseline 版本变更需记录到数据版本日志（Data Layer）
```

---

## 5. 机会等级划分

### 5.1 等级定义

| 等级 | 评分区间 | 特征 | 操作建议 |
|------|----------|------|----------|
| S | ≥85 | 极佳机会，强势突破+量价配合 | 重仓买入 |
| A | [70, 85) | 优质机会，突破有效+量能放大 | 标准仓位 |
| B | [55, 70) | 普通机会，技术面可以但缺乏催化 | 轻仓试探 |
| C | [40, 55) | 观望，信号不明确 | 不操作 |
| D | <40 | 回避，技术面恶化 | 减仓/清仓 |

### 5.2 方向判断（铁律合规版）

| 方向 | 判定条件 | 说明 |
|------|----------|------|
| bullish | `close > high_20d_prev` 且 `consecutive_up_days >= 3` | 价格位置判定，非均线 |
| bearish | `close < low_20d_prev` 且 `consecutive_down_days >= 3` | 价格位置判定，非均线 |
| neutral | 其他情况 | 观望 |

**注意**：不使用均线判断方向，而是使用价格相对位置和趋势延续性。

```python
if close > high_20d_prev and consecutive_up_days >= 3:
    direction = "bullish"
elif close < low_20d_prev and consecutive_down_days >= 3:
    direction = "bearish"
else:
    direction = "neutral"
```

---

## 6. 风险收益比计算

```text
公式：
entry = close
stop_loss_pct = 0.08
stop = min(low_20d, close × (1 - stop_loss_pct))  # 20日最低或8%止损
target_ref = max(high_20d_prev, high_60d_prev)  # 历史阻力位参考
risk = max(entry - stop, ε)
breakout_floor = entry + risk                   # 突破新高时至少保证 RR≥1 的目标下限
if close > target_ref:
    target = max(target_ref, breakout_floor, entry × (1 + stop_loss_pct))
else:
    target = max(target_ref, entry × 1.03)
reward = max(target - entry, 0)
risk_reward_ratio = reward / risk

判断：
- risk_reward_ratio ≥ 2 → 高质量机会
- 1 ≤ risk_reward_ratio < 2 → 可交易但需结合仓位约束
- risk_reward_ratio < 1 → 回避
```

**铁律合规说明**：使用价格高低点而非ATR计算止损止盈。

---

## 7. 中性度计算

```text
公式：
neutrality = 1 - |opportunity_score - 50| / 50
```

**语义说明**：
- 此公式计算的是**中性程度**（非信号强度）
- opportunity_score = 50 时，neutrality = 1（最中性）
- opportunity_score = 0 或 100 时，neutrality = 0（最极端）
- 用于表示"评分接近中性的程度"，越极端信号越明确但也越需谨慎

---

## 8. 参数配置

### 8.1 因子参数

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| limit_up_window | 120（锁定） | 固定120 | 与 `limit_up_count_120d` 字段耦合，MVP 不开放可调 |
| new_high_window | 60（锁定） | 固定60 | 与 `new_high_count_60d` 字段耦合，MVP 不开放可调 |
| price_range_window | 60（锁定） | 固定60 | 与 `high_60d/low_60d/high_60d_prev` 字段耦合 |
| volume_ma_window | 20（锁定） | 固定20 | 与 `volume_avg_20d` 字段耦合 |
| trend_window | 20 | 5-40 | 趋势延续判断窗口 |

### 8.2 权重参数

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| bull_gene_weight | 0.20 | 0.10-0.30 | 牛股基因权重 |
| structure_weight | 0.50 | 0.40-0.60 | 结构位置权重 |
| behavior_weight | 0.30 | 0.20-0.40 | 行为确认权重 |

---

## 9. 验收与验证（可执行口径）

### 9.1 数据就绪（PasStockSnapshot 必须提供）

- 必备字段：
  - 计数类：limit_up_count_120d、new_high_count_60d、max_pct_chg_history、consecutive_up_days、consecutive_down_days
  - 连续类：open/high/low/close、vol、volume_avg_20d、pct_chg、high_60d、low_60d、high_60d_prev、high_20d_prev、low_20d_prev、low_20d
  - 状态类：is_limit_up、is_touched_limit_up
- 约束（零容忍）：
  - high_60d ≥ low_60d
  - volume_avg_20d > 0
  - max_pct_chg_history 输入口径为百分数（15 表示 15%），进入 bull_gene 前必须先 `/100` 转为 ratio
  - 所有 ratio 必须落在 [0, 1] 或合理区间；使用 max(分母, ε) 防止除零

### 9.2 尺度一致性（count→ratio→zscore）

- 任一因子的输入如果是“家数/次数”，必须先转为 ratio 或 per-stock 比率。
- 行为因子中的 `volume_ratio` / `pct_chg` 必须先映射到 `[0,1]` 再加权组合。
- 归一化只能通过 `normalize_zscore`（或等价实现）完成。

### 9.3 宏观方向稽核（不得重复覆盖）

- 每个 raw 观测必须且只能归属到 §2.4 的一个宏观方向。
- 不允许“同一 raw 观测”以分子语义重复进入不同因子。

### 9.4 输出合法性

- opportunity_score 与各因子得分必须位于 [0, 100]
- opportunity_grade 必须落在 S/A/B/C/D
- direction 必须落在 bullish/bearish/neutral
- risk_reward_ratio ≥ 1.0（低于该值仅可用于观察，不进入执行层）

---

## 10. 与其他模块协同

### 10.1 与 MSS 协同

- MSS 输出可作为市场风险上限参考，但不直接进入 PAS 因子或评分计算
- PAS 算法仅基于 PasStockSnapshot 字段完成评分与分级
- MSS 驱动的仓位调整与风险约束由 Integration 协同约束层执行（见 integration-algorithm.md §5.3）
- MSS 不作为 PAS 的单点否决

### 10.2 与 IRS 协同

- IRS 确定超配行业，PAS 优先在这些行业内选股
- IRS 超配行业的 PAS S/A 级机会优先考虑
- 协同为权重影响，不对 PAS 形成单点否决

### 10.3 与 Integration 协同

- PAS 输出 `opportunity_score` 和 `opportunity_grade`
- Integration 汇总 MSS + IRS + PAS 生成最终三三制信号，PAS 作为个股层机会强度输入

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.1.11 | 2026-02-09 | 修复 R26：核心输出与 §9.4 输出合法性统一为 `risk_reward_ratio ≥ 1.0` 的执行最低门槛 |
| v3.1.10 | 2026-02-08 | 修复 R19：§5.1 等级边界统一为半开区间；§9.1 数据就绪补齐 `max_pct_chg_history`；§10.1 明确 MSS 不直接进入 PAS 评分 |
| v3.1.9 | 2026-02-08 | 修复 R13：字段耦合窗口参数（120/60/20）改为锁定口径；§5.2 显式引用 `consecutive_down_days`；§6 增加突破场景目标价下限，避免风险收益比系统性低于 1 |
| v3.1.8 | 2026-02-08 | 修复 R10：行为因子 `pct_chg_norm` 映射区间扩展为 ±20%，避免创业板/科创板在 >10% 区间饱和 |
| v3.1.7 | 2026-02-07 | 修复 R8 P0：风险收益比目标价改为独立于止损的阻力位口径，移除恒等式 `RR=2` 问题 |
| v3.1.6 | 2026-02-07 | 修复 R5：行为因子先做量纲映射（volume_ratio_norm/pct_chg_norm）；补充 PAS Z-Score 冷启动规范 |
| v3.1.5 | 2026-02-07 | 修复 P1：统一 bull_gene 子因子单位（max_pct_chg_history 百分数先转 ratio 再加权） |
| v3.1.4 | 2026-02-07 | 修复 P0：补齐数据就绪口径中的 20 日方向/止损字段（high_20d_prev、low_20d_prev、low_20d） |
| v3.1.3 | 2026-02-06 | 数据来源表命名统一为 Data Layer raw_* 口径 |
| v3.1.2 | 2026-02-05 | 字段命名与路线图/命名规范对齐（limit_up_count_120d 等） |
| v3.1.1 | 2026-02-05 | 更新系统铁律引用 |
| v3.1.0 | 2026-02-04 | 补齐验收口径：宏观方向归属与稽核条款；统一 count→ratio→zscore；结构/行为因子改为 ratio 化；补充 GitHub 外部实践参考 |
| v3.0.0 | 2026-01-31 | 重构版：解决均线与铁律冲突，用价格位置替代技术指标 |

---

**关联文档**：
- 数据模型：[pas-data-models.md](./pas-data-models.md)
- API接口：[pas-api.md](./pas-api.md)
- 信息流：[pas-information-flow.md](./pas-information-flow.md)
- 系统铁律：[系统铁律.md](../../../../Governance/steering/系统铁律.md)


