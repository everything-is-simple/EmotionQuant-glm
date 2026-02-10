# EmotionQuant 第八轮批判性审查报告

**审查人**: Claude (claude 4.6 opus)
**日期**: 2026-02-07
**基线**: `develop` @ `5b8d931`（R7 修复已全部提交）
**审查角度**: 公式数学验证 · Backtest/PAS 端到端走查 · 跨轮修复后残留不一致

---

## 本轮方法论

R7 聚焦跨层参数冲突和多文档矛盾。本轮（R8）方法：

1. **公式数学验证**：对 PAS 风险收益比、Backtest Sortino 等公式做纯数学推演，检查是否为恒等式或错误公式。
2. **Backtest 端到端走查**：从 BacktestConfig → Signal → Trade → Position → Metrics 全链路比对 dataclass 与 DB schema。
3. **工作区修复后残留检查**：R6/R7 报告后文档出现大量未提交修改（v3.x.x changelog），本轮检查修复是否完整、是否引入新的不一致。

---

## 本次二次复查结论（Codex）

- 复查基线：`develop` @ `5b8d931`（2026-02-07）
- 复查结果：R8 列出的 10 项问题在当前基线均可复现（10/10 成立）
- 进展更新（2026-02-07）：R8 十项已修复并提交，剩余 0 项 OPEN

---

## R1-R7 修复状态（勘误更新）

> **勘误**（2026-02-07 14:56）：本报告初稿误以 `ad9ff99` 为基线，实际 HEAD 已推进至 `5b8d931`（10 个提交），R5/R6/R7 全部修复均已提交。以下为修正后的 R7 修复状态。

| R7 编号 | 修复状态 | 关闭提交 |
|---------|---------|----------|
| R7-01 (STRONG_BUY >=75 vs >=80) | OK 已提交 | `0641afc` |
| R7-02 (T+1 can_sell 逻辑) | OK 已提交 | `5b8d931`（harden can_sell pseudocode） |
| R7-03 (IRS 估值三方矛盾) | OK 已提交 | `0641afc` |
| R7-04 (双重冷市场缩减) | OK 已提交 | `0641afc`（Trading 层移除重复缩减；Integration 内部残留见 R8-05） |
| R7-05 (Trading 10% cap) | OK 已提交 | `0641afc`（Backtest 未同步见 R8-08） |
| R7-06 (IRS 配置缺口) | OK 已提交 | `0641afc` |
| R7-07 (recession sideways) | OK 已提交 | `0641afc` |
| R7-08 (TradeSignal 缺 signal_id) | OK 已提交 | `0641afc` |
| R7-09 (Order 缺 industry_code) | OK 已提交 | `0641afc` |
| R7-10 (Config 缺过户费) | OK 已提交 | `0641afc`（Config + `.env.example` 补齐） |
| R7-11 (MSS 信息流图漏因子) | OK 已提交 | `5b8d931`（补齐极端因子/波动因子） |

---

## 新发现（10 项，已全部修复并提交）

### P0 — 算法逻辑错误（3 项）

#### ~~P0-R8-01：PAS risk_reward_ratio 恒等于 2.0 — 公式为数学恒等式~~

**位置**: `pas-algorithm.md` §6

```text
entry = close
stop = min(low_20d, close × 0.92)
target = entry + (entry - stop) × 2
risk_reward_ratio = (target - entry) / (entry - stop)
```

**数学推演**：

```text
target - entry = [entry + 2(entry - stop)] - entry = 2(entry - stop)
risk_reward_ratio = 2(entry - stop) / (entry - stop) = 2
```

无论 entry 和 stop 取何值（只要 entry ≠ stop），risk_reward_ratio **恒等于 2.0**。

**连锁影响**：
- §6 判断 "risk_reward_ratio < 1 → 回避" **永远不触发**
- Integration/Backtest 存储并传递此字段 → 全链路携带一个常量
- BacktestSignal.risk_reward_ratio / IntegratedRecommendation.risk_reward_ratio 没有区分度
- pas-information-flow §2.5 的"过滤规则"为死逻辑

**修复**：若 R/R 需有区分度，target 应独立于 stop 计算（如基于阻力位或历史波动），而非机械地设为 `entry + 2×risk`。

**状态更新（2026-02-07）**：
- 已修复（工作区）：`docs/design/core-algorithms/pas/pas-algorithm.md`、`docs/design/core-algorithms/pas/pas-information-flow.md`
- 当前状态：已提交（本次 R8 全量修复）

---

#### ~~P0-R8-02：Backtest Sortino ratio 公式错误 — `std(min(r_t, 0))` 不等于下行偏差~~

**位置**: `backtest-algorithm.md` §5.3

```text
sortino = sqrt(252) × (mean(r_t) - rf/252) / std(min(r_t, 0))
```

**问题**：`min(r_t, 0)` 将正收益替换为 0，然后对包含大量 0 的数组求 `std`。这与标准 Sortino 下行偏差（Downside Deviation）不同。

**标准公式**：
```text
DD = sqrt(mean(min(r_t - MAR, 0)^2))
Sortino = sqrt(252) × (mean(r_t) - MAR) / DD
```

其中 MAR 通常为无风险收益率或 0。

**差异**：
- 标准：只对下行部分求均方根（零值不参与计算或视为非下行）
- 当前：`std` 函数将 0 视为有效数据点，拉低均值、膨胀 N，导致下行偏差被低估，Sortino 被高估

**影响**：回测的风险调整收益指标失真，策略比较结论可能错误。

**状态更新（2026-02-07）**：
- 已修复（工作区）：`docs/design/backtest/backtest-algorithm.md`
- 当前状态：已提交（本次 R8 全量修复）

---

#### ~~P0-R8-03：Integration 信息流仍使用等权 `(mss+irs+pas)/3`，但算法已升级为可配置权重~~

**位置**:
- `integration-information-flow.md` §1.1 架构图 (L48): `final = (mss+irs+pas) / 3`
- `integration-information-flow.md` §2.3 Step 3 (L160): `final_score = (mss_score + irs_score + pas_score) / 3`
- `integration-algorithm.md` §3.1: `final_score = mss_score × w_mss + irs_score × w_irs + pas_score × w_pas`

algorithm v3.4.0 引入了 Validation Gate + WeightPlan，允许候选权重通过验证后替代 baseline（1/3）。但 information-flow 的架构图和 Step 3 公式仍硬编码为简单平均。

如果实现者以 info-flow 为准，Validation Gate 的权重优化将永远不生效。

**状态更新（2026-02-07）**：
- 已修复（工作区）：`docs/design/core-algorithms/integration/integration-information-flow.md`
- 当前状态：已提交（本次 R8 全量修复）

---

### P1 — 规格冲突 / 歧义（4 项）

#### ~~P1-R8-04：PAS 冷市场行为 — 算法说"下调"，信息流说"暂停"~~

**位置**:
- `pas-algorithm.md` §10.1 (L336): "MSS 温度 < 30（冰点），PAS 信号强度与仓位建议**下调**"
- `pas-information-flow.md` §5.1 (L346): "temperature < 30（冰点）：**暂停** S/A 级买入信号"

"下调"（scale down）保留弱化后的信号；"暂停"（suspend）完全停止 S/A 信号输出。两者行为截然不同：
- 下调：冰点期仍有 S/A 信号进入 Integration，只是分数较低
- 暂停：冰点期 S/A 信号直接消失，Integration 只收到 B/C/D

**状态更新（2026-02-07）**：
- 已修复（工作区）：`docs/design/core-algorithms/pas/pas-information-flow.md`
- 当前状态：已提交（本次 R8 全量修复）

---

#### ~~P1-R8-05：Integration 仓位计算存在内部双重冷市场缩减 — 显式 ×0.6 与 mss_factor 冲突~~

**位置**:
- `integration-information-flow.md` §2.5 Step 5: `if mss_temperature < 30: position_size *= 0.6`
- `integration-information-flow.md` §2.8 Step 7: `position_size = base_position × mss_factor × irs_factor × pas_factor`
  其中 `mss_factor = 1 - |mss_temperature - 50| / 100`

当 MSS 温度 = 20 时：
- Step 5: position_size × 0.6
- Step 7: mss_factor = 1 - 30/100 = 0.7

**歧义**：
1. 若 Step 7 **覆盖** Step 5（重新从 base_position 计算）→ Step 5 的 0.6 是死代码
2. 若 Step 7 **叠加** Step 5 → 仓位 = base × 0.6 × 0.7 = base × 0.42（过度缩减）
3. Step 5 的 0.6 与 Step 7 的 mss_factor 数值不一致（0.6 vs 0.7），说明两者可能来自不同设计意图

algorithm §5.3 仅说"下调"未给出具体系数，但 §6.1 给出了 mss_factor 公式。info-flow 额外添加了 0.6 但 algorithm 无对应。

> 注：R7-04 中 Trading 的重复缩减已在 v3.2.1 移除（"不重复下调"），但 Integration 内部的冲突仍在。

**状态更新（2026-02-07）**：
- 已修复（工作区）：`docs/design/core-algorithms/integration/integration-information-flow.md`
- 当前状态：已提交（本次 R8 全量修复）

---

#### ~~P1-R8-06：Backtest Position.signal_id 类型冲突 — Python `str` vs DB `BIGINT`~~

**位置**:
- `backtest-data-models.md` §1.4 Position 数据类 (L154): `signal_id: str`
- `backtest-data-models.md` §2.2 positions 表 (L296): `signal_id BIGINT`

Python 侧为字符串（如 "SIG_20260131_000001"），DB 侧为 BIGINT（整数）。写入时要么类型转换失败，要么截断/丢失数据。

> 注：Trading 侧 Position.signal_id: str 与 TradeSignal.signal_id: str 一致（均为字符串），Backtest 的 DB 表是唯一使用 BIGINT 的地方。

**状态更新（2026-02-07）**：
- 已修复（工作区）：`docs/design/backtest/backtest-data-models.md`
- 当前状态：已提交（本次 R8 全量修复）

---

#### ~~P1-R8-07：BacktestTrade 数据类缺少 signal_id，但 DB 表有此字段~~

**位置**:
- `backtest-data-models.md` §1.3 BacktestTrade (L92-L132): 无 signal_id 字段
- `backtest-data-models.md` §2.1 backtest_trade_records 表 (L266): `signal_id VARCHAR(50)`

BacktestTrade 用于写入 DB。数据类没有 signal_id，DB 的 signal_id 列存在高风险为空（除非实现方额外旁路赋值）。交易回溯（从成交找到对应信号）在回测中断裂风险升高。

**状态更新（2026-02-07）**：
- 已修复（工作区）：`docs/design/backtest/backtest-data-models.md`
- 当前状态：已提交（本次 R8 全量修复）

---

### P2 — 次要不一致（3 项）

#### ~~P2-R8-08：Backtest max_position_pct (0.10) 与 Trading 更新后的值 (0.20) 不一致~~

Trading v3.2.1 将 max_position_pct 从 0.10 提升至 0.20（"不低于 Integration S 级 20%"），但 BacktestConfig 未同步：

| 层 | max_position_pct | 说明 |
|----|-----------------|------|
| Integration | S=20%, A=15% | 等级仓位上限 |
| **Trading** | **0.20** | 已更新（v3.2.1） |
| **Backtest** | **0.10** | 未更新 |

回测结果会比实盘更保守（S 级仓位被回测截断到 10%），策略表现评估失真。

**状态更新（2026-02-07）**：
- 已修复（工作区）：`docs/design/backtest/backtest-data-models.md`
- 当前状态：已提交（本次 R8 全量修复）

#### ~~P2-R8-09：data-layer stock_gene_cache.max_pct_chg_history 单位未标注~~

- data-layer DDL 注释仅为 "历史单日最大涨幅（PAS使用）"
- PAS 规格明确要求 "百分数口径，15 表示 15%；进入 bull_gene 前需 /100 转为 ratio"
- data-layer 缺乏单位说明，实现者无法确定存储的是 15（百分数）还是 0.15（ratio）

建议在 DDL 注释中追加单位口径说明（如 "百分数口径，15 表示 15%"）。

**状态更新（2026-02-07）**：
- 已修复（工作区）：`docs/design/data-layer/data-layer-data-models.md`
- 当前状态：已提交（本次 R8 全量修复）

#### ~~P2-R8-10：IRS §10.2 "PAS 评分 ≥ 80" 不对应任何 PAS 等级边界~~

- IRS algorithm §10.2: "PAS 评分 ≥ 80 的个股优先从超配行业中选择"
- PAS 等级边界: S ≥ 85, A = 70-84, B = 55-69
- 80 不是任何等级分界线 — 它切在 A 级中间（70-84），将 A 级拆成了"上半部(80-84)优先"和"下半部(70-79)非优先"

应对齐为 ≥ 85（S 级）或 ≥ 70（A 级及以上），而非任意选取 80。

**状态更新（2026-02-07）**：
- 已修复（工作区）：`docs/design/core-algorithms/irs/irs-algorithm.md`
- 当前状态：已提交（本次 R8 全量修复）

---

## R5/R6/R7 遗留更新（勘误：全部已关闭）

> **勘误**：初稿误判 R5/R6/R7 有遗留 OPEN 项。实际经 `1619ce7`-`5b8d931` 共 10 个提交，R1-R7 的 60 项问题已全部关闭并提交。详见各轮报告的"复查勘误"章节。

| 轮次 | 新增 | 已关闭 | 当前 OPEN |
|------|------|--------|-----------|
| R5 | 9 | 9 | 0 |
| R6 | 13 | 13 | 0 |
| R7 | 11 | 11 | 0 |

---

## 累计统计（勘误后）

| 轮次 | 新增 | 已修复（committed） | 已修复（working tree） | 当前 OPEN |
|------|------|---------------------|----------------------------------|-----------|
| R1-R4 | 27 | 27 | 27 | 0 |
| R5 | 9 | 9 | 9 | 0 |
| R6 | 13 | 13 | 13 | 0 |
| R7 | 11 | 11 | 11 | 0 |
| **R8** | **10** | **10** | **10** | **0** |
| **总计** | **70** | **70** | **70** | **0** |

> committed 口径修复率：70/70 = **100.0%**。  
> working tree 口径修复率：70/70 = **100.0%**（与 committed 口径一致）。

---

## 本轮修复优先级建议

**已完成（已提交）**:
1. ~~P0-R8-01: PAS risk_reward_ratio 恒等式修复~~
2. ~~P0-R8-02: Backtest Sortino 公式修复~~
3. ~~P0-R8-03: Integration 信息流等权残留修复~~
4. ~~P1-R8-04: PAS 冷市场语义统一（“下调” vs “暂停”）~~
5. ~~P1-R8-05: Integration 冷市场缩减逻辑去重（0.6 与 mss_factor 二选一）~~
6. ~~P1-R8-06: Backtest Position.signal_id 类型统一（str vs BIGINT）~~
7. ~~P1-R8-07: BacktestTrade 补齐 signal_id（数据类与表结构对齐）~~
8. ~~P2-R8-08: Backtest max_position_pct 与 Trading 对齐（0.20）~~
9. ~~P2-R8-09: Data Layer 标注 max_pct_chg_history 单位口径~~
10. ~~P2-R8-10: IRS 与 PAS 等级边界阈值对齐（≥85）~~

**剩余未修复**:
1. 无（R8 OPEN = 0）

**提交建议**:
- 可一次性提交 R8 全量文档修复，或按 `P0` / `P1+P2` 分两批提交以便审阅。

---

*报告结束*
