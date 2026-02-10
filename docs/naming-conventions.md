# EmotionQuant 命名规范

**版本**: v3.0.7
**最后更新**: 2026-02-09
**状态**: 规范文档

---

> **重要**：本文档为 EmotionQuant 系统的**唯一权威命名规范**。
> 所有模块文档应引用本文档，不应重复定义。

---

## 1. 情绪周期命名（七阶段 + 异常兜底）

### 1.1 周期定义表

| 英文代码 | 中文名称 | 温度条件 | 趋势条件 | 特征描述 | 仓位建议 |
|----------|----------|----------|----------|----------|----------|
| emergence | 萌芽期 | <30°C | up | 情绪开始回暖，低位复苏 | 80%-100% |
| fermentation | 发酵期 | 30-45°C | up | 情绪持续上升，资金入场 | 60%-80% |
| acceleration | 加速期 | 45-60°C | up | 情绪快速上升，趋势明确 | 50%-70% |
| divergence | 分歧期 | 60-75°C | up/sideways | 多空分歧加大，高位震荡 | 40%-60% |
| climax | 高潮期 | ≥75°C | any | 情绪达到顶峰，风险积累 | 20%-40% |
| diffusion | 扩散期 | 60-75°C | down | 情绪开始扩散，价格滞涨 | 30%-50% |
| recession | 退潮期 | <60°C | down/sideways | 情绪回落，弱势整理或下跌确认 | 0%-20% |
| unknown | 异常兜底 | - | - | 输入异常或不可判定，仅用于降级保护 | 0%-20% |

### 1.2 周期判定优先级

```text
优先级1: climax（≥75°C，最高优先）
优先级2: emergence（<30°C + up）
优先级3: fermentation（30-45°C + up）
优先级4: acceleration（45-60°C + up）
优先级5: divergence（60-75°C + up/sideways）
优先级6: diffusion（60-75°C + down）
优先级7: recession（<60°C + down/sideways）
优先级8: unknown（输入异常兜底）
```

### 1.3 周期枚举定义

```python
class MssCycle(Enum):
    """情绪周期枚举（权威定义）"""
    EMERGENCE = "emergence"         # 萌芽期
    FERMENTATION = "fermentation"   # 发酵期
    ACCELERATION = "acceleration"   # 加速期
    DIVERGENCE = "divergence"       # 分歧期
    CLIMAX = "climax"               # 高潮期
    DIFFUSION = "diffusion"         # 扩散期
    RECESSION = "recession"         # 退潮期
    UNKNOWN = "unknown"             # 未知
```

---

## 2. 趋势方向命名

### 2.1 趋势定义表

| 英文代码 | 中文名称 | 判定条件 | 适用场景 |
|----------|----------|----------|----------|
| up | 上升/上行 | 连续3日温度上升 | MSS趋势 |
| down | 下降/下行 | 连续3日温度下降 | MSS趋势 |
| sideways | 横盘/震荡 | 其他情况 | MSS趋势 |

### 2.2 趋势枚举定义

```python
class Trend(Enum):
    """趋势方向枚举（权威定义）"""
    UP = "up"             # 上升
    DOWN = "down"         # 下降
    SIDEWAYS = "sideways" # 横盘
```

> **注意**：统一使用 `sideways`，不使用 `flat`。PAS 方向请使用 `bullish/bearish/neutral`（见 §4）。

---

## 3. 行业轮动状态命名

### 3.1 轮动状态定义表

| 英文代码 | 中文名称 | 判定条件 | 操作建议 |
|----------|----------|----------|----------|
| IN | 进入轮动 | 评分连续3日上升 | 超配 |
| OUT | 退出轮动 | 评分连续3日下降 | 减配 |
| HOLD | 维持观望 | 其他情况 | 标配 |

### 3.2 轮动状态枚举定义

```python
class RotationStatus(Enum):
    """轮动状态枚举（权威定义）"""
    IN = "IN"       # 进入轮动
    OUT = "OUT"     # 退出轮动
    HOLD = "HOLD"   # 维持观望
```

---

## 4. PAS 方向命名

### 4.1 方向定义表

| 英文代码 | 中文名称 | 判定条件 | 说明 |
|----------|----------|----------|------|
| bullish | 看涨 | close > high_20d_prev 且 连续上涨≥3日 | 价格位置判定，非均线 |
| bearish | 看跌 | close < low_20d_prev 且 连续下跌≥3日 | 价格位置判定，非均线 |
| neutral | 中性 | 其他情况 | 观望 |

### 4.2 方向枚举定义

```python
class PasDirection(Enum):
    """PAS方向枚举（权威定义）"""
    BULLISH = "bullish"   # 看涨
    BEARISH = "bearish"   # 看跌
    NEUTRAL = "neutral"   # 中性
```

> **铁律合规**：方向判定使用**价格位置**（相对N日高低点）；MA 等技术指标仅可用于对照实验或辅助特征，且必须与情绪因子联合验证，不得单独触发交易决策。

---

## 5. 推荐等级命名

### 5.1 集成推荐等级（大写存储）

| 英文代码 | 中文名称 | 评分条件 | 附加条件 |
|----------|----------|----------|----------|
| STRONG_BUY | 强烈买入 | final_score ≥ 75 | MSS周期 ∈ {emergence, fermentation} |
| BUY | 买入 | final_score ≥ 70 | 不满足 STRONG_BUY 附加条件 |
| HOLD | 持有 | final_score 50-69 | - |
| SELL | 卖出 | final_score 30-49 | - |
| AVOID | 回避 | final_score < 30 | - |

### 5.2 PAS 机会等级

| 等级 | 评分区间 | 操作建议 |
|------|----------|----------|
| S | [85, +∞) | 重仓买入 |
| A | [70, 85) | 标准仓位 |
| B | [55, 70) | 轻仓试探 |
| C | [40, 55) | 观望 |
| D | <40 | 回避 |

---

## 6. 中性度公式（统一规范）

### 6.1 公式定义

```text
neutrality = 1 - |score - 50| / 50
```

### 6.2 语义说明

| score 值 | neutrality 值 | 语义 |
|----------|---------------|------|
| 50 | 1.0 | 最高中性度（信号不明确） |
| 0 或 100 | 0.0 | 最低中性度（信号极端） |

**解释**：
- **中性度**反映的是信号的**中性程度**，而非信号强度
- neutrality 接近 0 → 信号极端（评分接近0或100）→ 适合交易
- neutrality 接近 1 → 信号中性（评分接近50）→ 建议观望

**实际使用**：
- 极端信号（低 neutrality）更适合作为交易触发
- 中性信号（高 neutrality）建议观望

### 6.3 代码实现

```python
def calculate_neutrality(score: float) -> float:
    """计算中性度（统一公式）
    
    返回值越接近1越中性，越接近0信号越极端
    """
    return max(0.0, min(1.0, 1 - abs(score - 50) / 50))
```

---

## 7. 归一化方法（统一规范）

### 7.1 Z-Score 归一化公式

```text
z = (value - mean) / std
score = (z + 3) / 6 × 100
```

### 7.2 映射规则

- 输入范围：[-3σ, +3σ]
- 输出范围：[0, 100]
- 超出范围：裁剪到边界

### 7.3 代码实现

```python
def zscore_normalize(value: float, mean: float, std: float) -> float:
    """Z-Score归一化并映射到0-100（统一公式）"""
    if std == 0:
        return 50.0
    z = (value - mean) / std
    score = (z + 3) / 6 * 100
    return max(0.0, min(100.0, score))
```

---

## 8. 数据表命名规范

### 8.1 命名规则

```text
{模块前缀}_{实体}_{粒度}
```

### 8.2 核心表命名

| 模块 | 表名 | 说明 |
|------|------|------|
| MSS | mss_panorama | MSS每日计算结果 |
| IRS | irs_industry_daily | IRS行业每日评分 |
| PAS | stock_pas_daily | PAS个股每日评分 |
| Integration | integrated_recommendation | 三三制集成推荐 |
| Validation | validation_gate_decision | Validation 日门禁决策 |
| Validation | validation_weight_plan | `selected_weight_plan` 到 `WeightPlan` 的数值桥接 |

> 说明：推荐输出统一为 `integrated_recommendation`，不再单列 `daily_recommendation` 表。

### 8.3 中间表命名

| 模块 | 表名 | 说明 |
|------|------|------|
| MSS | mss_factor_intermediate | MSS因子中间结果 |
| IRS | irs_factor_intermediate | IRS因子中间结果 |
| PAS | pas_factor_intermediate | PAS因子中间结果 |
| Validation | validation_factor_report | 因子验证明细（IC/RankIC/衰减/覆盖） |
| Validation | validation_weight_report | 权重候选 Walk-Forward 评估结果 |
| Validation | validation_run_manifest | Validation 运行闭环元数据 |

---

## 9. 字段命名规范

### 9.1 命名规则

- 统一使用 `snake_case`
- 统一使用名词+语义后缀

### 9.2 后缀语义

| 后缀 | 含义 | 示例 |
|------|------|------|
| _score | 评分 | mss_score, pas_score |
| _ratio | 比率 | risk_reward_ratio |
| _count | 数量 | limit_up_count |
| _flag | 标记 | is_limit_up |
| _trend | 趋势 | market_trend |
| _cycle | 周期 | market_cycle |
| _date | 日期 | trade_date |
| _code | 代码 | stock_code, industry_code |

### 9.3 关键字段统一命名

| 字段 | 标准名称 | 弃用名称 | 说明 |
|------|----------|----------|------|
| 风险收益比 | risk_reward_ratio | rr_ratio | 全系统统一使用完整名称 |
| 平盘家数 | flat_count | - | 口径: abs(pct_chg) <= 0.5% |
| 曾涨停家数 | touched_limit_up | - | 口径: limit ∈ {'U', 'Z'} |
| 股票代码（内部） | stock_code | ts_code | L2+ 内部统一 6 位代码（如 `000001`，不含交易所后缀） |
| 股票代码（外部） | ts_code | stock_code | L1/外部接口使用 TuShare 格式（如 `000001.SZ`、`600519.SH`） |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.0.7 | 2026-02-09 | 修复 R30：§8.2/§8.3 补齐 Validation 核心表与中间表命名清单（`validation_gate_decision/validation_weight_plan/validation_factor_report/validation_weight_report/validation_run_manifest`） |
| v3.0.6 | 2026-02-09 | 修复 R29：§4 合规说明与系统铁律统一为“可对照/辅助特征，但不得独立决策” |
| v3.0.5 | 2026-02-09 | 修复 R27：§9.3 增加 `stock_code/ts_code` 全局格式约定（内部 6 位无后缀，外部 TuShare 含后缀） |
| v3.0.4 | 2026-02-09 | 修复 R26：§1.1 周期定义表补齐 `unknown` 兜底项；§1.2 判定优先级补充 `unknown` 末级兜底 |
| v3.0.3 | 2026-02-08 | 修复 R18：PAS 等级区间改为半开区间表达（`[70,85)` 等），消除浮点边界歧义 |
| v3.0.2 | 2026-02-07 | 修复 MSS 周期边界：recession 趋势条件从 down 扩展为 down/sideways（消除低温横盘空档） |
| v3.0.1 | 2026-02-07 | 同步 Integration 口径：STRONG_BUY 阈值从 80 调整为 75（保持早周期可达性） |
| v3.0.0 | 2026-02-01 | 初始版本：从各模块文档抽取统一规范 |

---

**关联文档**：
- 系统总览：[system-overview.md](./system-overview.md)
- 模块索引：[module-index.md](./module-index.md)

