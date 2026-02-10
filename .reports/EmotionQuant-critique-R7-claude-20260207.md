# EmotionQuant 第七轮批判性审查报告

**审查人**: Claude (claude 4.6 opus)
**日期**: 2026-02-07
**基线**: 原报告基线为 `develop@ad9ff99`；复查基线为 `develop@1672eb7`
**审查角度**: 跨层参数冲突 · Trading 算法逻辑验证 · 同一概念多文档不一致

---

## 本轮方法论

R6 聚焦单模块内部算法边界和跨模块字段契约。本轮（R7）方法：

1. **参数追踪**：同一参数（如仓位上限、冷市场系数、STRONG_BUY 阈值）在 Integration→Trading→Config 三层的取值是否一致或存在意外叠加。
2. **伪代码走查**：对 Trading 层 T+1、风控、信号生成等伪代码逐行推演，寻找运行时逻辑错误。
3. **同一概念多出处比对**：跟踪 IRS valuation 因子、IRS 配置建议、MSS recession 周期等概念在 algorithm / information-flow / data-layer-data-models / naming-conventions 中的全部出现，定位矛盾。

---

## ~~新发现（11 项）~~（复查后已全部关闭）

### ~~P0 — 规格冲突 / 算法逻辑错误（3 项）~~ ✅

#### ~~P0-R7-01：STRONG_BUY 阈值 — data-layer 说 ≥75，其余三处说 ≥80~~ ✅

**位置**:
- `data-layer-data-models.md` §4.4 (L422-L423)
- `integration-algorithm.md` §5.1
- `naming-conventions.md` §5.1
- `integration-data-models.md` §3.2

| 文档 | STRONG_BUY 条件 |
|------|----------------|
| **data-layer-data-models.md** | **≥ 75分** + MSS周期∈{emergence,fermentation} |
| integration-algorithm.md | ≥ 80分 + MSS周期∈{emergence,fermentation} |
| naming-conventions.md | ≥ 80分 + MSS周期∈{emergence,fermentation} |
| integration-data-models.md | ≥ 80分 |

data-layer 的阈值比其他文档低 5 分。实现者参考不同文档会得到不同行为。结合 R6-01（STRONG_BUY 在 ≥80 时几乎不可达），如果采用 ≥75 则可达性大幅提升，说明可能有人已尝试修复 R6-01 但只改了一个文件。

---

#### ~~P0-R7-02：Trading T+1 `can_sell` 逻辑错误 — 有今日新买入时昨日持仓无法卖出~~ ✅

**位置**: `trading-algorithm.md` §6.2

```python
def can_sell(stock_code, shares, trade_date):
    if stock_code not in frozen:
        return True
    frozen_today = frozen[stock_code].get(trade_date, 0)
    total_frozen = sum(frozen[stock_code].values())
    available = total_frozen - frozen_today
    return shares <= available
```

**场景推演**：
- T-1 日买入 100 股 → frozen = {T-1: 100}
- T 日 `clear_expired` 清理 T-1 记录 → frozen = {}
- T 日又买入 50 股 → frozen = {T: 50}
- T 日尝试卖出昨日的 100 股：

```
frozen_today = 50
total_frozen = 50  # 只剩今日记录
available = 50 - 50 = 0
return 100 <= 0  → False  ← 错误！昨日100股应该可卖
```

**根因**: `total_frozen` 取自 frozen tracker（仅含未清理记录），不是实际总持仓。`clear_expired` 删除了 T-1 记录后，T 日的 `total_frozen` 不包含昨日已可卖的份额。

**正确逻辑应为**:
```python
total_shares = positions[stock_code].shares  # 从持仓表取
frozen_today = frozen[stock_code].get(trade_date, 0)
available = total_shares - frozen_today
return shares <= available
```

---

#### ~~P0-R7-03：IRS 估值因子存在三个互相矛盾的规格~~ ✅

**位置**:
- `irs-algorithm.md` §3.4
- `irs-information-flow.md` §2.3
- `irs-algorithm.md` §9.2（统一规范声明）

| 来源 | 估值因子公式 | 方法 |
|------|-------------|------|
| irs-algorithm.md §3.4 | `percentile_rank(pe_ttm, 3y)` | 百分位排名 |
| irs-information-flow.md §2.3 | `normalize_zscore(-pe_ttm)` | Z-Score（取反） |
| irs-algorithm.md §9.2 | "归一化只能通过 normalize_zscore 完成" | Z-Score |

三份规格三种做法。R6 P1-R6-07 发现了 algorithm 内部的 percentile_rank vs zscore 矛盾，但未发现 information-flow 提供了第三种方案（取反后 zscore）。三方逻辑语义差异：

- `percentile_rank(pe_ttm)`：PE 高 → 高百分位 → 高分（估值越贵分越高 — 不合理？）
- `normalize_zscore(-pe_ttm)`：PE 高 → 负值更大 → 低分（估值越贵分越低 ✓）
- `normalize_zscore(pe_ttm)`：PE 高 → 高分（同 percentile 的问题）

只有 info-flow 的"取反"版本在语义上正确（低 PE 应得高分）。但 algorithm 没有取反。

**修复**: 统一为 `normalize_zscore(-pe_ttm)` 或 `100 - percentile_rank(pe_ttm)`，并同步到两份文档。

---

### ~~P1 — 跨层参数冲突 / 链路断裂（5 项）~~ ✅

#### ~~P1-R7-04：冷市场仓位缩减在 Integration 和 Trading 双重叠加 — 0.6 × 0.6 = 0.36~~ ✅

**位置**:
- `integration-algorithm.md` §5.3 → `position_size *= 0.6` (MSS temp < 30)
- `trading-algorithm.md` §2.1 → `position_size *= cold_market_position_factor` (默认 0.6, MSS temp < 30)

当 MSS 温度 < 30 时：
1. Integration 先把 position_size 乘 0.6
2. Trading 收到已缩减的 position_size，再乘 0.6
3. 最终仓位 = 原始 × 0.36

任何一层单独的 0.6 系数都是合理的。但叠加后实际缩减至 36%，远超任何一方的设计意图。

---

#### ~~P1-R7-05：Trading max_position_pct(10%) 使 Integration 等级仓位上限(S=20%/A=15%)成为死逻辑~~ ✅

**位置**:
- `integration-algorithm.md` §6.2 → 单股上限 S=20%, A=15%, B=10%, C/D=5%
- `trading-algorithm.md` §2.1 → `min(row.position_size, config.max_position_pct)`, max_position_pct=0.10
- `trading-data-models.md` §2.1 → TradeConfig.max_position_pct = 0.10

Trading 层在信号生成时取 `min(position_size, 0.10)`，无条件将任何超过 10% 的仓位截断。Integration 为 S 级机会精心设计的 20% 仓位上限永远不会被执行。

此外，Trading 还有 RiskConfig.max_position_ratio = 0.20（20%）做风控检查，但由于信号已被截断到 10%，这个 20% 检查也永远不会触发。

---

#### ~~P1-R7-06：IRS 配置建议 — algorithm 与 information-flow 给出矛盾映射~~ ✅

**位置**:
- `irs-algorithm.md` §6.1
- `irs-information-flow.md` §2.6

| 排名区间 | algorithm 说 | info-flow 说 |
|----------|-------------|-------------|
| 1-3 | 超配 | 超配 |
| 4-10 | 标配 | 标配 |
| 11-20 | 减配 | 减配 |
| **21-26** | **（无定义）** | **减配** |
| 27-31 | 回避 | 回避 |

R6 P0-R6-02 报告的"6 行业缺口"在 info-flow 中其实已被修复（11-26 名全为减配）。但 algorithm 文档和 data-models 枚举（§3.3 注释"排名 11-20"）没有同步。同一模块两份文档给出冲突答案。

---

#### ~~P1-R7-07：data-layer recession 周期包含 sideways，但 MSS 算法和命名规范不含~~ ✅

**位置**:
- `data-layer-data-models.md` §4.1 (L340): `recession（退潮期）：<60°C + down/sideways`
- `mss-algorithm.md` §5.1: recession = `<60°C + down`（不含 sideways）
- `naming-conventions.md` §1.1: recession = `<60°C + down`

data-layer 对 recession 的定义多了一个 `sideways` 条件，与另外两个权威来源矛盾。这与 R6 P0-R6-03（MSS 伪代码对 sideways 不检查温度直接返回 divergence）形成三方冲突：

| 场景: temp=20, trend=sideways | 结果 |
|------|------|
| MSS 伪代码 | divergence |
| naming-conventions | 未定义 |
| data-layer | recession |

三份文档给出三个不同答案。

---

#### ~~P1-R7-08：TradeSignal 缺少 `signal_id` — Position/TradeRecord 引用断链~~ ✅

**位置**:
- `trading-data-models.md` §1.1 TradeSignal（无 signal_id 字段）
- `trading-data-models.md` §1.3 Position.signal_id
- `trading-data-models.md` §1.4 TradeRecord.signal_id

Position 和 TradeRecord 都有 `signal_id` 字段用于追溯交易来源，但 TradeSignal 没有定义此字段。信号→订单→成交→持仓的追溯链在起点就断裂了。signal_id 的生成规则也未在任何文档中定义。

---

### ~~P2 — 次要不一致（3 项）~~ ✅

#### ~~P2-R7-09：Order 缺少 `industry_code` 但 Position 有~~ ✅

Position.industry_code 的数据源不明。Order 不含 industry_code，从买入订单成交到创建 Position 的过程中，industry_code 需要额外查询，但此逻辑在 trading-algorithm.md 中未描述。

#### ~~P2-R7-10：Config backtest 费用参数 vs CommissionConfig 不对齐~~ ✅

| 参数 | Config (config.py) | CommissionConfig (trading) |
|------|-------------------|---------------------------|
| 佣金率 | `backtest_commission_rate` = 0.0003 | `COMMISSION_RATE` = 0.0003 |
| 印花税 | `backtest_stamp_duty_rate` = 0.001 | `STAMP_DUTY_RATE` = 0.001 |
| 过户费 | ~~❌ 缺失~~ ✅ 已补齐 | `TRANSFER_FEE_RATE` = 0.00002 |
| 最低佣金 | ~~❌ 缺失~~ ✅ 已补齐 | `MIN_COMMISSION` = 5.0 |

Config 缺少过户费和最低佣金参数。如果回测使用 Config 参数，费用计算将与 CommissionConfig 不一致。

#### ~~P2-R7-11：MSS 信息流架构图只画了 4 个因子~~ ✅

`mss-information-flow.md` §1 架构图的"因子计算层"方框中只列出大盘系数、赚钱效应、亏钱效应、连续因子，遗漏了极端因子和波动因子。文字描述（§2.3-§2.5）正确列出全部 6 个因子，仅图示遗漏。

---

## R5/R6 遗留汇总（已关闭）

| 轮次 | OPEN 项数 | 说明 |
|------|----------|------|
| R5 | 0 | 已全部关闭 |
| R6 | 0 | 已全部关闭（含 R6-02 与 R7-06 口径同步） |

---

## 累计统计（已收口）

| 轮次 | 新增 | 已修复 | 当前 OPEN |
|------|------|--------|-----------|
| R1-R4 | 27 | 27 | 0 |
| R5 | 9 | 9 | 0 |
| R6 | 13 | 13 | 0 |
| **R7** | **11** | **11** | **0** |
| **总计** | **60** | **60** | **0** |

---

## 本轮修复优先级建议（已完成）

**立即处理（实现前必须统一）**:
1. ~~P0-R7-01: STRONG_BUY 阈值统一~~ ✅
2. ~~P0-R7-02: T+1 can_sell 用持仓表替代 frozen tracker~~ ✅
3. ~~P0-R7-03: IRS 估值因子统一为 zscore(-pe_ttm)~~ ✅

**架构级修复**:
4. ~~P1-R7-04: 冷市场缩减去重~~ ✅
5. ~~P1-R7-05: Trading max_position_pct 改为尊重 Integration 等级仓位上限~~ ✅
6. ~~P1-R7-06: IRS allocation_advice 同步~~ ✅
7. ~~P1-R7-07: recession 周期定义统一~~ ✅

---

## 复查勘误与执行回写（Codex，2026-02-07）

基于当前仓库实查（`develop@98b6cc6`）复查 R7，结论如下：

| ID | 复查结论 | 处理状态 |
|----|----------|----------|
| ~~P0-R7-01~~ | STRONG_BUY 阈值在 Integration / Data Layer / Naming / Integration Data Models 已统一为 `>=75` | ✅ 勘误关闭 |
| ~~P0-R7-02~~ | Trading `can_sell` 伪代码确有缺陷（误用 `total_frozen`） | ✅ 已修复（改为 `total_shares - frozen_today`） |
| ~~P0-R7-03~~ | IRS 估值因子已统一为 `valuation_raw=-industry_pe_ttm` + `normalize_zscore` | ✅ 勘误关闭 |
| ~~P1-R7-04~~ | Integration 与 Trading 冷市场仓位缩减双重叠加 | ✅ 已修复（Trading 不再重复缩放） |
| ~~P1-R7-05~~ | Trading `max_position_pct=0.10` 压死 Integration S/A 仓位上限 | ✅ 已修复（上调为 0.20 全局硬上限） |
| ~~P1-R7-06~~ | IRS 配置建议映射（11-26 减配）在 algorithm/info-flow 已一致 | ✅ 勘误关闭 |
| ~~P1-R7-07~~ | recession 条件在 MSS / Naming / Data Layer 已一致为 `<60 + down/sideways` | ✅ 勘误关闭 |
| ~~P1-R7-08~~ | TradeSignal 缺 `signal_id` 导致链路断裂 | ✅ 已修复（TradeSignal 补 `signal_id/industry_code`） |
| ~~P2-R7-09~~ | Order 缺 `industry_code` 且链路未定义 | ✅ 已修复（Order/TradeRecord 补 `industry_code`，Order 补 `signal_id`） |
| ~~P2-R7-10~~ | Config 缺过户费/最低佣金参数 | ✅ 已修复（Config + `.env.example` 补齐） |
| ~~P2-R7-11~~ | MSS 信息流架构图仅 4 因子 | ✅ 已修复（补齐极端因子/波动因子） |

本次落地文件（关键）：
- `docs/design/trading/trading-algorithm.md`
- `docs/design/trading/trading-data-models.md`
- `src/config/config.py`
- `.env.example`
- `docs/design/core-algorithms/mss/mss-information-flow.md`

验证：
- `pytest tests/unit/config/test_config_defaults.py tests/unit/config/test_env_docs_alignment.py tests/unit/config/test_dependency_manifest.py -q` 通过
- `C:\\miniconda3\\python.exe scripts/quality/local_quality_check.py --scan` 通过

当前 OPEN：**0**

---

*报告结束*
