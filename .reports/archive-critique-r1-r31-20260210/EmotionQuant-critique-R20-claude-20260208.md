# EmotionQuant 第 20 轮深度审查报告

**审查人**: Claude (Opus)
**日期**: 2026-02-08
**审查角度**: Backtest + Trading 模块四位一体内部一致性 & 与上游 Integration 层契约对齐
**覆盖文件**:
- `docs/design/backtest/backtest-algorithm.md` (v3.4.5)
- `docs/design/backtest/backtest-data-models.md` (v3.4.7)
- `docs/design/backtest/backtest-api.md` (v3.4.1)
- `docs/design/backtest/backtest-information-flow.md` (v3.4.0)
- `docs/design/trading/trading-algorithm.md` (v3.2.3)
- `docs/design/trading/trading-data-models.md` (v3.2.4)
- `docs/design/trading/trading-api.md` (v3.1.3)
- `docs/design/trading/trading-information-flow.md` (v3.2.2)
- 交叉参考: `integration-algorithm.md`, `integration-data-models.md`

**累计**: R1-R19 共发现 179 个问题（全部已修复验证），本轮 R20 新增 10 个

---

## 问题清单

### [x] ~~P1-R20-01：Trading §2.1 对 IRS/PAS 做二次硬截断过滤，违反"无单点否决"原则~~（已修复）

| 属性 | 值 |
|------|-----|
| 严重等级 | P1 |
| 文件 | `trading-algorithm.md` §2.1 |
| 交叉参考 | `integration-algorithm.md` §5.3, `backtest-algorithm.md` §3.1 |

**问题**：
Trading 信号构建流程中存在三层硬截断：

```text
if row.industry_code not in allowed_industries: continue   # IRS 行业硬过滤
if row.irs_score < config.min_irs_score: continue          # IRS 评分硬过滤 (50)
if row.pas_score < config.min_pas_score: continue          # PAS 评分硬过滤 (60)
```

Integration 层设计的核心原则是"协同约束、无单点否决"——IRS 回避行业仅做 `pas_score ×0.85` 软折扣，PAS 评分通过加权融合而非硬截断。Trading 二次引入行业/评分硬过滤，等效于 IRS 单点否决——行业排名 >5 且非 IN 的所有个股将被完全排除，即使其 `final_score` 很高。

**建议**：
- Trading 信号过滤应以 `final_score` + `recommendation` 为主门槛（与 Backtest 对齐）
- 行业/评分筛选如需保留，应作为软排序（降低优先级/仓位），而非硬截断
- 或明确文档声明 Trading 层有意加严风控（此时需标注"与 Integration 无单点否决偏离"）

---

### [x] ~~P1-R20-02：Trading vs Backtest 信号过滤逻辑不一致——回测无法复刻实盘行为~~（已修复）

| 属性 | 值 |
|------|-----|
| 严重等级 | P1 |
| 文件 | `trading-algorithm.md` §2.1, `backtest-algorithm.md` §3.1 |

**问题**：

对比两个模块消费同一 `integrated_recommendation` 的过滤逻辑：

| 过滤维度 | Backtest §3.1 | Trading §2.1 |
|----------|---------------|--------------|
| final_score | `< min_final_score` → 跳过 | 未直接过滤 final_score |
| recommendation | AVOID/SELL → 跳过 | 未直接过滤 recommendation |
| IRS 行业 | 无 | rotation_status≠IN 且 rank>5 → 跳过 |
| IRS 评分 | 无 | `< 50` → 跳过 |
| PAS 评分 | 无 | `< 60` → 跳过 |
| direction | 无过滤 | neutral → 不生成 |

这意味着：
1. Backtest 中通过 `final_score≥55 + recommendation=BUY` 留下的信号，可能在 Trading 中被 IRS/PAS 硬过滤剔除
2. 回测验证的策略表现无法反映真实交易行为——**回测等于白做**

**建议**：
- 统一 Backtest 与 Trading 的信号筛选逻辑（建议统一为 `final_score` + `recommendation` 主门槛）
- 或在 Backtest 中增加与 Trading 相同的行业/评分过滤（使回测能复刻实盘）

---

### [x] ~~P1-R20-03：Backtest 缺少 stop_loss / take_profit 退出算法段~~（已修复）

| 属性 | 值 |
|------|-----|
| 严重等级 | P1 |
| 文件 | `backtest-algorithm.md` §4 |
| 交叉参考 | `backtest-data-models.md` §1.1 BacktestConfig |

**问题**：
`BacktestConfig` 定义了 `stop_loss_pct = 0.08` 和 `take_profit_pct = 0.15`，且 §4.8 明确提到"时限平仓与止损/止盈**并行**，谁先触发谁先执行"——但整个 §4 中不存在止损/止盈的执行算法描述。

缺失内容：
- 每日何时检查止损/止盈（收盘后？盘中？）
- 触发条件的精确定义（相对成本价还是相对最高点？）
- 触发后的信号生成（卖出信号？下一交易日执行？）
- 跌停/停牌无法卖出时的顺延策略

**建议**：
在 §4 新增 `§4.9 止损止盈退出规则`，格式参照 §4.8 时限平仓，包含触发条件、执行时点、顺延策略。

---

### [x] ~~P1-R20-04：Backtest info-flow §3 每日流程缺失持仓风控步骤~~（已修复）

| 属性 | 值 |
|------|-----|
| 严重等级 | P1 |
| 文件 | `backtest-information-flow.md` §3 |
| 交叉参考 | `backtest-algorithm.md` §4.8 |

**问题**：
info-flow §3 列出 9 个每日步骤：

```text
1. 数据就绪检查
2. 读取集成信号
3. 过滤与仓位约束
4. 生成订单并执行
5. 执行顺序：先卖后买
6. 交易执行
7. 费用与滑点
8. 记录交易与净值曲线
9. 计算绩效并落库
```

缺失步骤（应在 Step 4 之前或并行）：
- **止损/止盈检查**：扫描全部持仓，触发者生成卖出信号
- **时限平仓检查**：扫描 `holding_days ≥ max_holding_days` 的持仓
- 卖出信号应先于买入信号生成，以释放现金

**建议**：
在 Step 2 和 Step 3 之间插入持仓风控步骤，或重编步骤为：
```
2a. 检查止损/止盈/时限平仓（生成卖出信号）
2b. 读取集成信号（生成买入信号）
3. 合并卖出+买入信号，先卖后买
```

---

### [x] ~~P1-R20-05：Trading API §5.2 check_order 文档遗漏行业集中度检查项~~（已修复）

| 属性 | 值 |
|------|-----|
| 严重等级 | P1 |
| 文件 | `trading-api.md` §5.2 check_order |
| 交叉参考 | `trading-algorithm.md` §3.1 Step 2.5 |

**问题**：
`trading-algorithm.md` §3.1 在 R11 修复中新增了 Step 2.5 行业集中度检查（`max_industry_ratio = 0.30`）。但 `trading-api.md` §5.2 `check_order` 的文档注释（line 429-434）仍只列出 5 项检查：

```text
1. 资金充足性（买单）
2. 单股仓位上限（买单）
3. 总仓位上限（买单）
4. T+1限制（卖单）
5. 涨跌停限制
```

遗漏：`6. 行业集中度上限（买单）`

**建议**：
在 check_order docstring 补充第 6 项：`6. 行业集中度上限（买单，默认30%）`

---

### [x] ~~P2-R20-06：Trading TradeSignal.source 枚举含 dead value~~（已修复）

| 属性 | 值 |
|------|-----|
| 严重等级 | P2 |
| 文件 | `trading-data-models.md` §1.1 TradeSignal |

**问题**：
`TradeSignal.source` 注释为 `integrated/PAS/IRS/MSS`（line 31），但 `trading-algorithm.md` §2.1 始终设置 `source="integrated"`。PAS/IRS/MSS 值在当前设计中永远不会被赋值，属于 dead value。

**建议**：
- 如果未来有降级到单模块信号的计划，保留但标注为"预留"
- 否则收窄为 `source: str  # integrated`，与 Backtest 的 `integrated/pas_fallback` 枚举分别声明

---

### [x] ~~P2-R20-07：Backtest BacktestSignal.direction 与 BacktestTrade.direction 语义断裂未说明~~（已修复）

| 属性 | 值 |
|------|-----|
| 严重等级 | P2 |
| 文件 | `backtest-data-models.md` §1.2, §1.3 |

**问题**：
- `BacktestSignal.direction` = `bullish/bearish/neutral`（来自 Integration 方向）
- `BacktestTrade.direction` = `buy/sell`（交易执行方向）

两个 `direction` 字段语义不同但同名，且 Backtest 算法中未说明映射规则：
- 信号 bullish → 交易 buy？（隐含的，因为 SELL/AVOID 已被过滤）
- 信号 neutral 如何处理？（当前 Backtest §3.1 不做 direction 过滤，neutral 信号会通过）

**建议**：
- 在 `BacktestSignal.direction` 注释中明确：该字段为 Integration 原始方向（追溯用），不直接用于买卖决策
- 或在数据模型中将信号方向字段改名为 `signal_direction` 以区分

---

### [x] ~~P2-R20-08：Trading §4.1 quality_score 取 max 可能导致 PAS 权重膨胀~~（已修复）

| 属性 | 值 |
|------|-----|
| 严重等级 | P2 |
| 文件 | `trading-algorithm.md` §4.1 |

**问题**：
信号质量验证公式为：

```text
quality_score = max(signal.score, pas.opportunity_score)
```

`signal.score` = `final_score`（已包含 PAS 加权贡献）。取 `max` 等效于：当 `pas.opportunity_score > final_score` 时，PAS 单独覆盖了三三制加权结果。

示例：MSS=30, IRS=40, PAS=95 → final_score=55 → quality_score=max(55,95)=95
结果：一个三系统分歧极大的信号通过了质量检查（以 95 分通过 55 分门槛），而实际集成信号只有 55 分。

**建议**：
- 如果意图是"PAS 极强个股可以豁免弱市场/弱行业"，应显式标注此意图
- 否则建议 `quality_score = signal.score`（即 final_score），让三三制权重发挥作用

---

### [x] ~~P2-R20-09：Backtest data-models §4.1 L3 依赖列出 mss_panorama / irs_industry_daily 但算法未直接读取~~（已修复）

| 属性 | 值 |
|------|-----|
| 严重等级 | P2 |
| 文件 | `backtest-data-models.md` §4.1 |

**问题**：
§4.1 依赖表列出 4 个 L3 数据源：

| 数据源 | 用途 |
|--------|------|
| integrated_recommendation | 集成信号（算法直接读取 ✅） |
| pas_breadth_daily | BU 活跃度（算法直接读取 ✅） |
| mss_panorama | 风险上下文（❌ 算法未直接读取） |
| irs_industry_daily | 行业上下文（❌ 算法未直接读取） |

`backtest-algorithm.md` §3.1 仅从 `integrated_recommendation` 获取 `mss_score` / `irs_score`（透传字段），不直接查询 `mss_panorama` 或 `irs_industry_daily` 表。

**建议**：
- 在依赖表中区分"直接读取"与"间接获取（经 Integration 透传）"
- 或去掉 `mss_panorama` / `irs_industry_daily`，改为注释说明这些数据经 `integrated_recommendation` 透传获得

---

### [x] ~~P2-R20-10：Trading / Backtest 费率参数重复定义无统一来源~~（已修复）

| 属性 | 值 |
|------|-----|
| 严重等级 | P2 |
| 文件 | `trading-data-models.md` §2.4, `backtest-data-models.md` §1.1 |

**问题**：
相同的 A 股费率在两个模块独立定义：

| 费率 | Trading CommissionConfig | Backtest BacktestConfig |
|------|--------------------------|-------------------------|
| 佣金 | COMMISSION_RATE = 0.0003 | commission_rate = 0.0003 |
| 印花税 | STAMP_DUTY_RATE = 0.001 | stamp_duty_rate = 0.001 |
| 过户费 | TRANSFER_FEE_RATE = 0.00002 | transfer_fee_rate = 0.00002 |
| 最低佣金 | MIN_COMMISSION = 5.0 | min_commission = 5.0 |

两处命名风格不同（UPPER_CASE vs snake_case），且无交叉引用。若费率调整（如印花税减半），需手动同步两处。

**建议**：
- 在共享配置层（如 `utils/config` 或 `data-layer`）定义统一的 `AShareFeeConfig`
- Trading 和 Backtest 从该统一来源引用，而非各自定义

---

## 统计

| 等级 | 数量 | 占比 |
|------|------|------|
| P1 | 5 | 50% |
| P2 | 5 | 50% |
| **合计** | **10** | 100% |

---

## 本轮主要发现

1. **Trading 与 Integration 的架构矛盾**（P1-R20-01/02）：Trading 重新引入 IRS/PAS 硬截断过滤，与 Integration"无单点否决"设计原则冲突，且导致 Backtest 与 Trading 行为不一致
2. **Backtest 止损/止盈算法缺失**（P1-R20-03/04）：Config 定义了参数，时限平仓引用了"止损/止盈并行"，但缺少对应的算法段和 info-flow 步骤
3. **跨模块契约不完整**（P1-R20-05, P2-R20-06/07/09/10）：API 文档与算法不同步、信号枚举有 dead value、依赖边界模糊、费率参数重复
