# IRS 行业轮动算法设计

**版本**: v3.2.9（重构版）
**最后更新**: 2026-02-09
**状态**: 设计完成（验收口径补齐；代码未落地）

---

## 1. 算法概述

### 1.1 设计目标

IRS（Industry Rotation System）是行业轮动评分系统，通过多因子分析识别当前市场中最具投资价值的行业，并提供配置建议。

### 1.2 核心输出

| 输出 | 说明 | 范围 |
|------|------|------|
| industry_score | 行业综合评分 | 0-100 |
| rotation_status | 轮动状态 | IN/OUT/HOLD |
| rotation_detail | 轮动详情 | 强势领涨/轮动加速/风格转换/热点扩散/高位整固/趋势反转 |
| allocation_advice | 配置建议 | 超配/标配/减配/回避 |
| neutrality | 中性度 | 0-1（越接近1越中性，越接近0信号越极端） |

命名规范：轮动状态命名详见 [naming-conventions.md](../../../naming-conventions.md) §3。

### 1.3 行业范围

申万一级31个行业（使用 `raw_index_classify` 表获取）

---

## 2. 因子体系

### 2.1 因子架构

**四大基础因子（80%）+ 两大增强因子（20%）**

| 因子类别 | 因子名称 | 权重 | 说明 |
|----------|----------|------|------|
| 基础因子 | 相对强度 | 25% | 行业相对市场的强弱 |
| 基础因子 | 连续性因子 | 20% | 行业情绪/广度的持续性 |
| 基础因子 | 资金流向 | 20% | 资金进出情况 |
| 基础因子 | 估值因子 | 15% | 行业估值水平 |
| 增强因子 | 龙头因子 | 12% | 行业龙头股表现 |
| 增强因子 | 行业基因库 | 8% | 行业历史强势惯性 |

### 2.2 因子语义边界（跨模块澄清）

> **背景**：涨停/成交量在 MSS/IRS/PAS 三模块都有使用，但**视角和粒度不同**，不构成信息重复。

| 数据来源 | IRS 使用角度 | 粒度 | 回答的问题 |
|----------|--------------|------|----------------|
| **涨停** | 龙头因子（行业 Top5 中涨停数量） | 行业局部 | 行业龙头表现如何？ |
| **成交量** | 资金流向（行业成交额增量） | 行业局部 | 资金在进入这个行业吗？ |

**与 MSS/PAS 的区别**：
- MSS 看全市场涨停占比，IRS 看行业内龙头涨停，PAS 看个股历史涨停频率
- MSS 看全市场成交波动，IRS 看行业资金净流入，PAS 看个股量比
- 同一数据，三个视角：**全局统计 vs 行业局部 vs 个股特征**

---

### 2.3 外部实践参考（GitHub）

用于“有理有据”地校准 IRS 因子归类（仅作参考，不引入技术指标）：

- **相对强度 / 新高维度**：
  - iArpanK/RS-Screener：强调“相对强度新高（RS New High）”与 RS Score 排序。
- **新高/新低扩散（NH–NL）**：
  - johnmuchow/Net-Highs-Net-Lows：输出 New highs / New lows / Net highs-lows。
- **相对强度 vs 基准 + 相对量能（RVol）**：
  - Brigadirk/sector_strength_2026-01-16 gist：给出 RS vs SPY 与 RVol（相对成交量）的定义与示例。
- **行业/ETF 轮动倾向（动量轮动的外部实践）**：
  - markymark5127/stock_bot：ETF 动量轮动策略，强调“多周期动量”轮动。
  - RLDiary/sector-rotation-strategy：行业轮动策略基于动量/ROC；用于说明外部常见做法，但 IRS 内部 **不使用技术指标**。

---

### 2.4 宏观方向（验收用“观测归属表”）

> 说明：宏观方向是 **raw 观测口径** 的分类（用于稽核“语义是否重复覆盖”），不是额外打分层。

| 宏观方向 | raw 观测（必须互斥归属） | 主要影响的因子 |
|---------|--------------------------|----------------|
| 相对强度/轮动 | industry_pct_chg、benchmark_pct_chg | 相对强度 |
| 行业广度/扩散 | rise_ratio、fall_ratio、net_new_high_ratio | 连续性因子 |
| 资金/流动性 | industry_amount_delta、industry_turnover、relative_volume | 资金流向 |
| 估值/均衡 | industry_pe_ttm、industry_pb | 估值因子 |
| 结构/龙头/惯性 | top5_pct_chg、top5_limit_up_ratio、history_limit_up_ratio、history_new_high_ratio | 龙头因子 / 行业基因库 |

### 2.5 互斥边界说明（允许的“复用”仅限分母/派生）

- **强制互斥**：同一类 raw 观测不能被拆成多个因子重复加权。
- **允许复用**：仅限作为分母/派生变量（例如 limit_up_count 仅用于构造比例/连续性）。
- **验收标准**：新增/调整 raw 观测必须更新 §2.4 并说明归属理由。

## 3. 因子计算公式

### 3.1 相对强度因子（Relative Strength）

```text
公式：
relative_strength = industry_pct_chg - benchmark_pct_chg
relative_strength_score = normalize_zscore(relative_strength)

参数：
- industry_pct_chg: 行业当日涨跌幅
- benchmark_pct_chg: 基准指数涨跌幅（沪深300或中证全指）

数据来源：raw_daily + raw_index_daily
权重：25%
```

### 3.2 连续性因子（Continuity / Breadth）

> **铁律对齐**：不使用基于价格序列的回归斜率类指标，改用行业“广度/扩散”的连续性刻画。

```text
定义（ratio）：
- rise_ratio = rise_count / stock_count
- fall_ratio = fall_count / stock_count
- net_breadth = rise_ratio - fall_ratio
- new_high_ratio = new_100d_high_count / stock_count
- new_low_ratio  = new_100d_low_count / stock_count
- net_new_high_ratio = new_high_ratio - new_low_ratio

公式：
continuity_raw = 0.6 × Σ(net_breadth, window=5)
               + 0.4 × Σ(net_new_high_ratio, window=5)
continuity_score = normalize_zscore(continuity_raw)

参数：
- window: 连续性窗口（默认5日）

数据来源：industry_snapshot（L2）
权重：20%
```

### 3.3 资金流向因子（Capital Flow）

```text
定义：
industry_amount_delta = industry_amount - industry_amount_prev
relative_volume = industry_amount / max(industry_amount_avg_20d, ε)   # 可选，用于流动性刻画

公式：
net_inflow_10d = Σ(industry_amount_delta, window=10)
capital_flow_score = normalize_zscore(net_inflow_10d)

参数：
- industry_amount_delta: 行业成交额增量
- window: 累计窗口（默认10日）

数据来源：raw_daily_basic 聚合
权重：20%
```

### 3.4 估值因子（Valuation）

```text
公式：
valuation_raw = -industry_pe_ttm
valuation_score = normalize_zscore(valuation_raw)

参数：
- industry_pe_ttm: 行业市盈率（TTM）
- valuation_raw: 估值方向标准化输入（PE 越低越优，先取负号）
- history_window: 估值归一化统计窗口（默认3年）

数据来源：raw_daily_basic
权重：15%
```

聚合口径（个股 `pe_ttm` → 行业 `industry_pe_ttm`）：

```text
1) 样本过滤
   - 仅保留 pe_ttm > 0 的成分股（亏损股负 PE 不参与均值/中位数）
   - 成分股集合使用 trade_date 当日有效的 raw_index_member

2) 异常值处理
   - 对 pe_ttm 进行双侧 winsorize（1%, 99%）
   - pe_ttm > 1000 的值截断到 1000（防止极端值主导）

3) 行业聚合
   - industry_pe_ttm = median(pe_ttm_winsorized)
   - industry_pb = median(pb_winsorized)

4) 冷启动与缺失
   - 若当日有效样本数 < min_constituents（默认 8），沿用前一交易日有效值，并标记 quality_flag="stale"
   - 若历史窗口不足 60 交易日，则估值因子分数回退为 50（中性），并标记 quality_flag="cold_start"
   - 正常场景标记 quality_flag="normal"
   - 输出 sample_days（有效样本天数）用于下游区分“真实中性”与“冷启动中性”
```

```python
irs_output = {
    "industry_score": industry_score,
    "quality_flag": quality_flag,  # normal/cold_start/stale
    "sample_days": sample_days
}
```

### 3.5 龙头因子（Leader Factor）

```text
公式：
leader_avg_pct = Mean(top5_pct_chg)
leader_limit_up_ratio = top5_limit_up / 5
leader_score = 0.6 × normalize_zscore(leader_avg_pct)
             + 0.4 × normalize_zscore(leader_limit_up_ratio)

参数：
- top5: 行业成交额或市值 Top5 股票（MVP 固定）
- top5_pct_chg: Top5 股票涨跌幅
- top5_limit_up: Top5 中涨停数量
- leader_top_n: 固定常量 5（与 `top5_*` 字段耦合；MVP 阶段不开放可调）

数据来源：raw_daily + raw_limit_list
权重：12%
```

### 3.6 行业基因库（Industry Gene）

```text
公式：
history_limit_up_ratio = history_limit_up_count / stock_count
history_new_high_ratio = history_new_high_count / stock_count
gene_raw = 0.6 × time_decay(history_limit_up_ratio, decay=0.9)
         + 0.4 × time_decay(history_new_high_ratio, decay=0.9)
gene_score = normalize_zscore(gene_raw)

参数：
- history_limit_up_count: 历史涨停股数量（3年滚动）
- history_new_high_count: 历史新高股数量（3年滚动）
- decay: 指数衰减系数（默认0.9）

数据来源：raw_daily + raw_limit_list
权重：8%
```

---

## 4. 综合评分计算

### 4.1 加权求和公式

```text
industry_score = relative_strength_score × 0.25
               + continuity_score × 0.20
               + capital_flow_score × 0.20
               + valuation_score × 0.15
               + leader_score × 0.12
               + gene_score × 0.08
```

### 4.2 归一化方法

统一使用 Z-Score 归一化（与 MSS/PAS 保持一致）：

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
- ${DATA_PATH}/config/irs_zscore_baseline.parquet

冷启动策略：
1. 首次部署：加载离线 baseline（建议覆盖完整牛熊周期）
2. 日常更新：按交易日滚动更新 mean/std（窗口默认 120 日）
3. 缺失兜底：任一因子缺 mean/std 时，因子得分返回 50（中性）

说明：
- valuation 因子先做方向标准化（valuation_raw = -industry_pe_ttm）后再做 Z-Score
- baseline 版本变更需写入数据版本日志（Data Layer）
```

---

## 5. 轮动状态识别

### 5.1 轮动状态（rotation_status）

| 状态 | 判定条件 | 说明 |
|------|----------|------|
| IN | `industry_score` 连续3日上升 | 行业进入轮动 |
| OUT | `industry_score` 连续3日下降 | 行业退出轮动 |
| HOLD | 其他情况 | 维持观望 |

```python
def detect_rotation_status(industry_score_t2: float, industry_score_t1: float, industry_score_t: float) -> str:
    if industry_score_t2 < industry_score_t1 < industry_score_t:
        return "IN"
    if industry_score_t2 > industry_score_t1 > industry_score_t:
        return "OUT"
    return "HOLD"
```

### 5.2 轮动详情（rotation_detail）

| 详情 | 特征 | 操作建议 |
|------|------|----------|
| 强势领涨 | 前3名评分持续上升 | 顺势超配 |
| 轮动加速 | 前3名频繁更替（5日内≥3次） | 分散配置 |
| 风格转换 | 领涨行业类型改变（成长↔价值） | 调整方向 |
| 热点扩散 | 上涨行业范围扩大 | 提高仓位 |
| 高位整固 | 前5名评分稳定 | 持有待涨 |
| 趋势反转 | 原领涨行业排名下滑 | 减仓换防 |

---

## 6. 配置建议规则

### 6.1 排名映射

| 配置建议 | 排名区间 | 仓位建议 |
|----------|----------|----------|
| 超配 | 前3名 | 30%-40% |
| 标配 | 4-10名 | 10%-20% |
| 减配 | 11-26名 | 5%-10% |
| 回避 | 后5名（27-31名） | 0%-5% |

> 覆盖性要求：31 个行业必须全部映射到 `allocation_advice`，不允许出现空档排名。

```python
def get_allocation_advice(rank: int) -> str:
    if 1 <= rank <= 3:
        return "超配"
    if 4 <= rank <= 10:
        return "标配"
    if 11 <= rank <= 26:
        return "减配"
    if 27 <= rank <= 31:
        return "回避"
    raise ValueError(f"invalid rank: {rank}")
```

### 6.2 信号触发条件

| 信号类型 | 触发条件 |
|----------|----------|
| 行业强势确认 | 从5名外进入前3 且 评分提升>15分 |
| 行业强势预警 | 评分连续3日下降 且 降幅>20分 |
| 配置调整信号 | 评分单日变化>25分 |

---

## 7. 中性度计算

```text
公式：
neutrality = 1 - |industry_score - 50| / 50
```

**语义说明**：
- 此公式计算的是**中性程度**（非信号强度）
- industry_score = 50 时，neutrality = 1（最中性）
- industry_score = 0 或 100 时，neutrality = 0（最极端）
- 用于表示"评分接近中性的程度"，越极端信号越明确但也越需谨慎

---

## 8. 参数配置

### 8.1 因子参数

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| continuity_window | 5 | 3-10 | 连续性窗口（基于行业广度） |
| breadth_net_weight | 0.6 | 0.4-0.8 | 连续性中净广度权重 |
| breadth_high_low_weight | 0.4 | 0.2-0.6 | 连续性中净新高权重 |
| zscore_window | 120 | 60-240 | Z-Score 统计窗口 |
| leader_top_n | 5（锁定） | 固定5 | 与 `top5_codes/top5_pct_chg/top5_limit_up` 字段强耦合，MVP 不开放可调 |
| gene_decay | 0.9 | 0.7-0.98 | 基因库衰减系数 |

### 8.2 权重参数

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| base_weight | 0.80 | 0.70-0.90 | 基础因子合计占比 |
| enhanced_weight | 0.20 | 0.10-0.30 | 增强因子合计占比 |

---

## 9. 验收与验证（可执行口径）

### 9.1 数据就绪（industry_snapshot + BenchmarkData 必须提供）

- 必备字段：
  - industry_snapshot 计数类：stock_count、rise_count、fall_count、limit_up_count、limit_down_count、new_100d_high_count、new_100d_low_count、top5_limit_up
  - industry_snapshot 连续类：industry_pct_chg、industry_amount、industry_turnover、industry_pe_ttm、industry_pb
  - industry_snapshot 质量类：data_quality（normal/stale/cold_start）、stale_days、source_trade_date
  - BenchmarkData：benchmark_pct_chg（来源 `raw_index_daily.pct_chg`）
- 约束（零容忍）：
  - stock_count > 0
  - rise_count + fall_count ≤ stock_count
  - 所有 ratio 必须落在 [0, 1]；使用 max(分母, 1) 防止除零
  - stale_days ≤ 3（>3 视为陈旧数据，阻断 IRS 主流程）

### 9.2 尺度一致性（count→ratio→zscore）

- 任一因子的输入如果是“家数/数量”，必须先转为 ratio 或 per-stock 比率。
- 归一化只能通过 `normalize_zscore`（或等价实现）完成。

### 9.3 宏观方向稽核（不得重复覆盖）

- 每个 raw 观测必须且只能归属到 §2.4 的一个宏观方向。
- 不允许“同一 raw 观测”以分子语义重复进入不同因子。

### 9.4 输出合法性

- industry_score 与各因子得分必须位于 [0, 100]
- neutrality 必须位于 [0, 1]
- rotation_status 必须落在 IN/OUT/HOLD
- quality_flag 必须落在 normal/cold_start/stale
- sample_days 必须为非负整数

---

## 10. 与其他模块协同

### 10.1 与 MSS 协同

- MSS 输出可作为市场整体风险上限参考，但不直接进入 IRS 因子计算
- IRS 算法仅基于 IrsIndustrySnapshot 与 BenchmarkData 字段完成行业评分
- MSS 驱动的风险敞口与仓位调整由 Integration 协同约束层执行

### 10.2 与 PAS 协同

- IRS 确定超配行业后，PAS 在该行业内进行个股精选
- PAS S级（评分 ≥ 85）的个股优先从超配行业中选择
- 协同为权重影响，不对 PAS 形成单点否决

### 10.3 与 Integration 协同

- IRS 输出 `industry_score` 和 `rotation_status`
- IRS 需同步输出 `quality_flag` 与 `sample_days`，供 Integration 在冷启动/陈旧场景回退 baseline 权重
- Integration 汇总 MSS + IRS + PAS 生成最终三三制信号，IRS 作为行业层权重与方向参考

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.2.9 | 2026-02-09 | 修复 R26：§3.4 冷启动输出新增 `quality_flag/sample_days`；§9.1 增加 snapshot 质量字段与 `stale_days ≤ 3` 门禁；§9.4 增加质量字段合法性校验；§10.3 明确 Integration 读取质量标记进行回退 |
| v3.2.8 | 2026-02-08 | 修复 R19：§10.1 明确 MSS 不直接进入 IRS 因子计算，MSS 驱动调整由 Integration 层执行 |
| v3.2.7 | 2026-02-08 | 修复 R13：`leader_top_n` 锁定为 5（与 `top5_*` 字段耦合）；`rotation_status` 明确基于 `industry_score`；§6.1 补充 rank→allocation_advice 伪代码 |
| v3.2.6 | 2026-02-07 | 修复 R9：§9.1 明确 benchmark_pct_chg 来源于 BenchmarkData/`raw_index_daily`，不再误标为 industry_snapshot 字段 |
| v3.2.5 | 2026-02-07 | 修复 R8 P2：IRS-PAS 协同阈值由“≥80”对齐为 PAS S级边界“≥85” |
| v3.2.4 | 2026-02-07 | 修复 R5：补充 IRS Z-Score 冷启动与 baseline 规范 |
| v3.2.3 | 2026-02-07 | 修复 P1：估值因子从 percentile_rank 统一为 normalize_zscore（PE 先取负再归一化） |
| v3.2.2 | 2026-02-07 | 修复 P0：配置建议排名映射改为 3/7/16/5（覆盖 31 行业，无空档） |
| v3.2.1 | 2026-02-06 | 数据来源表命名统一为 Data Layer raw_* 口径 |
| v3.2.0 | 2026-02-04 | 补齐验收口径：宏观方向归属与稽核条款；连续性因子纳入新高/新低扩散；统一 count→ratio→zscore；补充 GitHub 外部实践参考 |
| v3.1.0 | 2026-02-04 | 口径修订：移除基于价格序列的 slope，改用行业广度连续性因子 |
| v3.0.0 | 2026-01-31 | 重构版：统一公式表述、明确因子权重、与MSS归一化方法对齐 |

---

**关联文档**：
- 数据模型：[irs-data-models.md](./irs-data-models.md)
- API接口：[irs-api.md](./irs-api.md)
- 信息流：[irs-information-flow.md](./irs-information-flow.md)

