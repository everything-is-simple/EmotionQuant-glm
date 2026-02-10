# EmotionQuant 第十二轮审查报告

**审查者**: Claude (Warp Agent Mode)
**日期**: 2026-02-08
**审查范围**: 跨模块接口一致性、Analysis/Backtest/Integration 数据模型对齐
**HEAD**: `67af2d0` (develop)
**状态**: 🟢 已闭环（Codex 复核）

---

## 审查角度

本轮聚焦 **跨模块边界处的字段/公式/枚举一致性**，重点审查：
- Analysis 算法引用的字段名是否在 Trading/Backtest 数据模型中真实存在
- Backtest 算法伪代码对 Integration 输出字段的假设是否成立
- Dataclass ↔ DDL 字段完整性
- 同一概念在不同模块中的命名/枚举值一致性

---

## 汇总

| 等级 | 数量 |
|------|------|
| P0（致命） | 0 |
| P1（重要） | 6 |
| P2（次要） | 4 |
| **合计** | **10** |

---

## 复查纠偏记录（Codex，2026-02-08）

- 复核基线：`develop` @ `67af2d0` 起步，修复并回归至当前工作区版本。
- 复核结论：R12 列出的 10 项问题已全部完成修复（10/10）。
- 闭环说明：
  - P1-R12-01~06：年化口径、字段链路、DDL 缺口、配置/接口一致性均已修正；
  - P2-R12-07~10：枚举统一、字段命名对齐、残留参数清理、Position 对称性已补齐；
  - 本报告保留为“审查 + 纠偏闭环”单一事实源。

---

## P1 — 重要

### ~~P1-R12-01 · Analysis §2.1 annual_return 年化公式分母 off-by-one~~

| 项目 | 内容 |
|------|------|
| 文件 | `docs/design/analysis/analysis-algorithm.md` §2.1 (L46-47) |
| 现状 | `N = len(equity_curve)` → `annual_return = (equity[-1]/equity[0])^(252/N) - 1` |
| 问题 | N 个净值点对应 N-1 个交易日。用 N 做分母导致年化指数偏低。100 天净值序列 → 252/100=2.52 vs 正确 252/99=2.5454。短窗口差异更大。|
| 佐证 | 同文件 §7 (L378-379) 使用 `N = len(daily_returns)`（即 `len(equity_curve)-1`），与 `analysis-data-models.md` 公式表一致。§2.1 与 §7 自相矛盾。|
| 建议 | §2.1 改为 `N = len(equity_curve) - 1` 或改用 `len(daily_returns)`，与 §7 统一。 |

### ~~P1-R12-02 · Analysis §2.4 holding_days 引用不存在的字段~~

| 项目 | 内容 |
|------|------|
| 文件 | `docs/design/analysis/analysis-algorithm.md` §2.4 (L106) |
| 现状 | `holding_days = [(t.sell_date - t.buy_date).days for t in trades]` |
| 问题 | (1) `TradeRecord`（Trading）无 `sell_date` 和 `buy_date`；(2) `BacktestTrade`（Backtest）也无这两个字段；(3) `TradeRecord` 是单笔买卖记录，不是配对轮回——配对逻辑从未定义。|
| 佐证 | 同文件 §7 (L411) 改用 `t.holding_days`，但 BacktestTrade 字段名是 `hold_days`（见 P2-R12-08）。两种写法都与实际数据模型不符。 |
| 建议 | (1) 定义 "轮回交易" 配对规则（买卖配对 → holding_days）或 (2) 统一使用预计算字段 `hold_days`，§2.4 与 §7 保持一致。 |

### ~~P1-R12-03 · Backtest §3.1 引用 IntegratedRecommendation 不存在的 signal_id~~

| 项目 | 内容 |
|------|------|
| 文件 | `docs/design/backtest/backtest-algorithm.md` §3.1 (L95) |
| 现状 | `signal_id=(row.signal_id or f"SIG_{signal_date}_{row.stock_code}")` |
| 问题 | `row` 来自 `integrated_recommendation`，但 `IntegratedRecommendation` dataclass（integration-data-models.md §3.1）和 DDL（§4.1）均无 `signal_id` 字段。运行时会触发 `AttributeError`（dataclass）或 `KeyError`（Row）。 |
| 佐证 | Trading §2.1 (trading-algorithm.md L74) 从不尝试读取 `row.signal_id`，而是直接生成 `f"SIG_{trade_date}_{row.stock_code}"`。两侧策略不一致。|
| 建议 | 方案 A：IntegratedRecommendation 增加 `signal_id` 字段（dataclass + DDL）。方案 B：Backtest 改为与 Trading 一致，始终生成 signal_id，不依赖上游。 |

### ~~P1-R12-04 · Backtest Position dataclass 与 DDL 缺少 industry_code~~

| 项目 | 内容 |
|------|------|
| 文件 | `docs/design/backtest/backtest-data-models.md` §1.4 (L140-159) + §2.2 (L280-307) |
| 现状 | Backtest `Position` 无 `industry_code` 字段。|
| 问题 | Analysis §5.2（analysis-algorithm.md L264）按 `position.industry_code` 计算行业 HHI。回测持仓无该字段 → 分析引擎对回测结果执行行业集中度计算时 crash。|
| 佐证 | Trading `Position`（trading-data-models.md §1.3 L100）有 `industry_code`，DDL（§4.2 L282）也有。两侧不对称。|
| 建议 | Backtest Position dataclass 与 DDL 补齐 `industry_code: str`，与 Trading 对齐。 |

### ~~P1-R12-05 · Analysis §4.1 归因字段 trade.price 在 BacktestTrade 中不存在~~

| 项目 | 内容 |
|------|------|
| 文件 | `docs/design/analysis/analysis-algorithm.md` §4.1 (L186) |
| 现状 | `pnl_pct = (trade.price - rec.entry) / rec.entry` |
| 问题 | `TradeRecord`（Trading）字段为 `price` ✓，但 `BacktestTrade`（Backtest）字段为 `filled_price` ✗。Analysis §4.1 注释明确说 "回测分析改用 `backtest_trade_records`"（L170），同一行代码无法兼容两种来源。 |
| 建议 | 方案 A：统一字段名（Trading `TradeRecord.price` → `filled_price`，与 Backtest 对齐）。方案 B：Analysis 归因代码对回测/实盘分别处理。推荐方案 A。 |

### ~~P1-R12-06 · backtest_results DDL 缺少 4 个 BacktestMetrics 字段~~

| 项目 | 内容 |
|------|------|
| 文件 | `docs/design/backtest/backtest-data-models.md` §1.6 vs §2.3 |
| 现状 | `BacktestMetrics` dataclass 含 `volatility`, `fill_rate`, `limit_up_rejected`, `auction_failed`；`backtest_results` DDL（§2.3 L309-343）均无对应列。 |
| 问题 | 回测绩效持久化后，波动率与成交统计指标丢失，无法在 Analysis 或 GUI 中还原。 |
| 建议 | DDL 补齐 4 列：`volatility DECIMAL(10,4)`, `fill_rate DECIMAL(8,4)`, `limit_up_rejected INTEGER`, `auction_failed INTEGER`。 |

---

## P2 — 次要

### ~~P2-R12-07 · OrderType 枚举值不一致：Trading `auction_open` vs Backtest `auction`~~

| 项目 | 内容 |
|------|------|
| 文件 | `trading-data-models.md` §6.2 vs `backtest-data-models.md` §3.1 |
| 现状 | Trading: `OrderType.AUCTION_OPEN = "auction_open"`；Backtest: `OrderType.AUCTION = "auction"`。 |
| 问题 | 同一语义（A 股集合竞价）的枚举值不同，交叉分析（如 Analysis 合并实盘/回测交易记录）时需额外映射。 |
| 建议 | 统一为 `auction`（更简洁），或保留 `auction_open` 并在 Backtest 对齐。 |

### ~~P2-R12-08 · Analysis §7 引用 `t.holding_days`，BacktestTrade 字段为 `hold_days`~~

| 项目 | 内容 |
|------|------|
| 文件 | `analysis-algorithm.md` §7 (L411) vs `backtest-data-models.md` §1.3 (L128) |
| 现状 | Analysis: `mean([t.holding_days for t in trades])`；BacktestTrade: `hold_days: int`。 |
| 问题 | 字段名差一个词缀 `ing`，运行时 AttributeError。 |
| 建议 | 统一命名为 `hold_days`（与 BacktestTrade 和 DDL 一致），Analysis 引用同步。 |

### ~~P2-R12-09 · TradeConfig.min_mss_temperature 无任何使用路径~~

| 项目 | 内容 |
|------|------|
| 文件 | `trading-data-models.md` §2.1 (L147) |
| 现状 | `min_mss_temperature: float = 30.0  # 仅非 Integration 信号流程使用` |
| 问题 | 系统中不存在 "非 Integration 信号流程"——Trading 仅消费 `integrated_recommendation`。该参数为 R11 修复 MSS 温度门控后的残留，注释虽标注但代码永远不会读取。 |
| 建议 | (1) 移除该参数，或 (2) 若未来计划增加非集成信号流程，则保留并在注释中标注 `reserved`。 |

### ~~P2-R12-10 · Trading Position 与 Backtest Position 字段集不对称~~

| 项目 | 内容 |
|------|------|
| 文件 | `trading-data-models.md` §1.3 vs `backtest-data-models.md` §1.4 |
| 现状 | Trading Position 有 `industry_code`，无 `cost_amount`；Backtest Position 有 `cost_amount`，无 `industry_code`。 |
| 问题 | 两侧 Position 定义应尽量对齐。`cost_amount` 在 Trading 中可由 `shares × cost_price` 推导但回测显式存储；`industry_code` 在 Backtest 中缺失影响 Analysis（见 P1-R12-04）。 |
| 建议 | 双侧互补：Trading Position 可补 `cost_amount`（可选），Backtest Position 必须补 `industry_code`（强需求）。 |

---

## 审查方法

1. 以 Analysis/Backtest/Trading/Integration 四模块为节点，逐对检查字段合约
2. 对比 dataclass 定义与 DDL 列名，验证完整性
3. 交叉验证同一公式在不同文件中的写法一致性
4. 跟踪枚举值从定义到使用的全链路

---

*R12 完成（已闭环）。累计 R1-R12 共发现 109 个问题，当前 OPEN = 0。*
