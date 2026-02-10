# EmotionQuant 第十一轮批判性审查报告

**审查人**: Claude (claude 4.6 opus)
**日期**: 2026-02-08
**基线**: `develop` @ `313fe5d`（R10 修复已全部提交并验证，工作区 clean）
**审查角度**: 信息流 vs 算法伪代码交叉对齐 · 跨层字段传递链完整性 · 风控参数执行覆盖率 · 配置参数缺口（源码 vs 规格） · 公式符号一致性

---

## 本轮方法论

R10 聚焦公式常数、枚举交叉一致性、行业代码完整性与源码-规格字段对齐。本轮（R11）方法：

1. **信息流 vs 算法伪代码逐步交叉比对**：Integration/Trading/Backtest 三层的 information-flow 与 algorithm 文档逐步骤核对执行顺序、公式引用、字段传递。
2. **风控参数执行覆盖率**：RiskConfig 中定义的参数是否在算法伪代码中全部被引用和执行。
3. **配置参数源码 vs 规格缺口扫描**：`src/config/config.py` 与 `BacktestConfig` / `TradeConfig` / `CommissionConfig` 的字段覆盖率。
4. **公式符号与数学口径一致性**：跨文档同一公式使用的数学符号是否语义一致（特别是 Sortino 下行偏差）。
5. **数据模型 dataclass vs DDL 字段对齐**：Backtest/Trading 的 Python dataclass 与对应 SQL DDL 逐字段比对。

---

## 复查纠偏记录（Codex，2026-02-08）

- 纠偏基线：`develop` @ `31cab99`（含 R11 修复后补充的 config 命名兼容修正）。
- 复核结论：R11 报告列出的 10 项问题已全部闭环（10/10）。
- 处理说明：
  - P0/P1 所有执行冲突与参数缺口均已按建议修复；
  - P2-R11-09 采用报告建议方案 C：在 `integration-algorithm.md` 明确标注 STRONG_BUY 为早周期高置信稀缺信号，避免实现误判；
  - 其余项均完成字段/公式/信息流同步，跨文档口径一致。

---

## 新发现（10 项）

### P0 — 逻辑冲突 / 执行顺序错误（2 项）

#### P0-R11-01：Integration 算法 §5.2→§5.3 执行顺序导致 strength_factor 被覆盖

**位置**:
- `integration-algorithm.md` §5.2 (L166-173): `final_score *= strength_factor`
- `integration-algorithm.md` §5.3 (L178-185): IRS 协同约束后"重新计算 final_score（使用调整后的 pas_score）"
- `integration-information-flow.md` §2.5 Step 5 (L218-244): IRS 调整 → 重算 final_score → **然后** `final_score *= strength_factor`

**问题**：

算法文档的节序暗示执行顺序为：
1. §5.2: `final_score *= strength_factor`（先乘）
2. §5.3: 调整 pas_score → `final_score = mss×w + irs×w + adjusted_pas×w`（重算覆盖）

Step 2 的加权重算会**完全覆盖** Step 1 的 strength_factor 效果，导致方向一致性惩罚无效。

而信息流文档 §2.5 的顺序正好相反：先做 IRS 调整并重算 final_score，**最后**才乘 strength_factor，strength_factor 效果得以保留。

**影响**：若实现者按算法文档 §5.2→§5.3 的节序编码，方向一致性惩罚（divergent 时 ×0.8）完全失效；所有个股的 strength_factor 等效为 1.0。

**修复建议**：在 `integration-algorithm.md` 中明确执行顺序，将 §5.2 和 §5.3 合并为一个"协同约束"节，伪代码顺序为：(1) IRS 调整 pas_score → (2) re-clip → (3) 重算 final_score → (4) `final_score *= strength_factor`。与信息流 Step 5 对齐。

---

#### P0-R11-02：Trading 信息流 §4.1 仍显示 "MSS温度门控 (≥30)"，但算法 §2.1 和数据模型均已明确不执行该门控

**位置**:
- `trading-information-flow.md` §4.1 (L400): `1. MSS温度门控 (≥30)`
- `trading-algorithm.md` §2.1 (L35-36): MSS 只读取温度透传至 `mss_score`，无任何温度阈值检查
- `trading-data-models.md` §2.1 TradeConfig (L147): `min_mss_temperature: float = 30.0  # 仅非 Integration 信号流程使用`

**冲突链**：
1. 数据模型注释：`min_mss_temperature` 仅用于非 Integration 流程
2. 算法伪代码：主流程（Integration 信号）不使用温度门控
3. 信息流图：**仍然标注** "MSS温度门控 (≥30)" 作为 Signal Builder 的第一步

**影响**：
- 实现者看信息流图会添加温度门控（≥30°C），但 MSS 温度在退潮期可低至 0-60，温度 < 30 时所有信号被拦截
- 算法文档说不拦截 → 信息流图说拦截 → 实现行为不确定
- 在退潮期 BU 模式下此门控会阻断所有强股信号，与"BU 保留强股小仓"的设计意图冲突

**修复建议**：移除信息流 §4.1 中的 "MSS温度门控 (≥30)" 步骤，或改为注释"仅非集成信号流使用"。

---

### P1 — 规格冲突 / 数据契约缺口（5 项）

#### P1-R11-03：Backtest Position dataclass 缺少 `direction` 字段，与自身 DDL 和 Trading Position 不一致

**位置**:
- `backtest-data-models.md` §1.4 Position dataclass (L141-158): **无 direction 字段**
- `backtest-data-models.md` §2.2 positions 表 (L286): `direction VARCHAR(10)` — DDL 中有
- `trading-data-models.md` §1.3 Position dataclass (L89): `direction: str = "long"` — R10 已修复

**影响**：
- R10 修复了 Trading Position 添加 direction 字段对齐 Backtest DDL，但未同步修复 Backtest 的 **dataclass** 定义
- dataclass ↔ DDL 同一文档内字段不匹配：代码写入/读取 positions 表时 direction 列无法映射到 dataclass
- 若回测与实盘共享 Position 序列化逻辑，dataclass 缺字段将导致反序列化 KeyError

**修复建议**：在 `backtest-data-models.md` §1.4 Position dataclass 中添加 `direction: str = "long"`。

---

#### P1-R11-04：Trading RiskConfig.max_industry_ratio (30%) 已定义但风控算法 §3.1 未执行行业集中度检查

**位置**:
- `trading-data-models.md` §2.2 RiskConfig (L166): `max_industry_ratio: float = 0.30  # 行业最大仓位30%`
- `trading-algorithm.md` §3.1 (L131-167): 检查项为：资金检查 → 单股仓位 → 总仓位 → T+1 → 涨跌停。**无行业集中度检查**

**对比**：

| 风控参数 | 定义位置 | 是否在 §3.1 执行 |
|---------|---------|-----------------|
| max_position_ratio (20%) | RiskConfig L165 | ✅ §3.1 第 2 点 |
| max_total_position (80%) | RiskConfig L167 | ✅ §3.1 第 3 点 |
| stop_loss_ratio (8%) | RiskConfig L168 | ✅ §3.3 止损检查 |
| max_drawdown_limit (15%) | RiskConfig L169 | ✅ §3.4 回撤检查 |
| **max_industry_ratio (30%)** | RiskConfig L166 | ❌ 未执行 |

**影响**：单一行业可占据 100% 持仓（只受单股 20% 和总仓位 80% 约束）。若 IRS 某行业评分极高（超配），5 只同行业个股各 16% → 行业占比 80%，远超 30% 上限但不会触发任何风控。

**修复建议**：在 §3.1 增加第 2.5 步"行业集中度检查"：
```
if order.direction == "buy":
    industry_value = sum(p.market_value for p in positions.values() if p.industry_code == order.industry_code)
    new_industry_ratio = (industry_value + order.amount) / total_equity
    if new_industry_ratio > config.max_industry_ratio:
        return (False, f"行业仓位超限 ({new_industry_ratio:.1%})")
```

---

#### P1-R11-05：config.py 缺少 BacktestConfig 中 7 个参数，回测配置无法通过中央配置注入

**位置**:
- `backtest-data-models.md` §1.1 BacktestConfig (L20-55): 定义 17 个参数
- `src/config/config.py` (L54-101): 仅包含 6 个 backtest_* 参数

**缺失映射**：

| BacktestConfig 参数 | config.py 参数 | 状态 |
|---------------------|---------------|------|
| initial_cash | backtest_initial_capital | ✅ 有（但命名不同: cash vs capital） |
| commission_rate | backtest_commission_rate | ✅ |
| stamp_duty_rate | backtest_stamp_duty_rate | ✅ |
| transfer_fee_rate | backtest_transfer_fee_rate | ✅ |
| min_commission | backtest_min_commission | ✅ |
| risk_free_rate | backtest_risk_free_rate | ✅ |
| slippage_value | — | ❌ 缺失 |
| max_positions | — | ❌ 缺失 |
| max_position_pct | — | ❌ 缺失 |
| stop_loss_pct | — | ❌ 缺失 |
| take_profit_pct | — | ❌ 缺失 |
| min_final_score | — | ❌ 缺失 |
| max_holding_days | — | ❌ 缺失 |

**影响**：回测的仓位、止损止盈、滑点、评分门限等关键参数无法通过 `.env` 注入，只能硬编码在 BacktestConfig 默认值中，违反"配置可外部化"原则。

**修复建议**：在 config.py 补充缺失的 7 个 `backtest_*` 参数，并统一命名（`initial_cash` → `backtest_initial_cash` 或保留 `backtest_initial_capital` 并在 BacktestConfig 中加别名）。

---

#### P1-R11-06：Integration API `MAX_MODULE_WEIGHT` 常量被引用但从未定义，实际值应为 0.60

**位置**:
- `integration-api.md` §2.1 (L82): `all(v <= self.MAX_MODULE_WEIGHT for v in weight_plan.values())`
- `integration-data-models.md` §5.1 (L264): `单模块权重 ≤ MAX_MODULE_WEIGHT`
- `factor-weight-validation-algorithm.md` §4.1 (L77): `max(w_i) <= 0.60`

**问题**：
- `MAX_MODULE_WEIGHT` 在 API 代码和数据模型验证规则中被引用，但未在任何位置定义其值
- 唯一的数值来源是 Validation 文档中的 `0.60`，但 Integration 文档自身没有这个值
- 实现者需跨三个文档拼凑才能确定：常量名在 API，约束语义在 data-models，数值在 validation

**修复建议**：在 `integration-algorithm.md` §11 参数配置中添加 `MAX_MODULE_WEIGHT = 0.60`；或在 IntegrationEngine 类定义中显式声明。

---

#### P1-R11-07：Analysis Sortino 公式使用 `std()` 符号，与 Backtest 的 RMS 口径不一致

**位置**:
- `analysis-data-models.md` §1.1 (L44): `sortino_ratio = sqrt(252) × (mean(r) - rf/252) / std(下行(r-rf/252))`
- `backtest-algorithm.md` §5.3 (L251-252): `downside_deviation = sqrt(mean(min(r_t - mar_daily, 0)^2))`

**对比**：

| 模块 | 下行偏差公式 | 数学含义 |
|------|------------|---------|
| Backtest | `sqrt(mean(min(r-mar,0)^2))` | RMS（所有点，非负返回贡献 0） |
| Analysis | `std(下行(r-rf/252))` | 标准差（可理解为仅取负值子集的 std，或全部数据的 std） |

标准 Sortino 使用 **下行偏差（Downside Deviation）** = `sqrt(mean(min(r-mar,0)^2))`，是 RMS 而非 std。
`std(x) = sqrt(mean(x^2) - mean(x)^2)` ≠ `sqrt(mean(x^2))`（当 mean(x) ≠ 0 时）。

**影响**：同一净值曲线，若 Analysis 按 `std()` 实现、Backtest 按 RMS 实现，两者 Sortino 值不同。

**修复建议**：将 Analysis 公式统一为 `sortino_ratio = sqrt(252) × (mean(r) - rf/252) / sqrt(mean(min(r - rf/252, 0)^2))`，与 Backtest 一致。

---

### P2 — 次要不一致（3 项）

#### P2-R11-08：src/data/models/entities.py TradeCalendar 字段名 `trade_date` 与规格 `cal_date` 不匹配

**位置**:
- `src/data/models/entities.py` (L13-16): `trade_date: str, is_open: bool`
- `data-layer-data-models.md` §2.8 (L192-196): `cal_date VARCHAR(8), is_open INTEGER (1/0)`

**差异**：

| 项 | entities.py | 规格 |
|----|------------|------|
| 日期字段名 | `trade_date` | `cal_date` |
| 开市类型 | `bool` | `INTEGER (1/0)` |

**影响**：从 Parquet 文件（列名为 `cal_date`）读入 TradeCalendar 时，字段名不匹配导致映射失败或需额外 rename。bool vs int 类型差异在 Python 中通常可自动转换，但字段名差异是硬错误。

**修复建议**：统一字段名为 `cal_date`（与 TuShare 返回一致），或在规格中明确 rename 映射。

---

#### P2-R11-09：Integration STRONG_BUY 在 emergence 周期几乎不可达 — 温度 <30 与 final_score ≥75 矛盾

**位置**:
- `integration-algorithm.md` §5.1 (L156): `≥75 + MSS周期∈{emergence,fermentation} → STRONG_BUY`
- `mss-algorithm.md` §5.1 (L236): `萌芽期 | <30°C | up`

**计算验证**（等权 baseline）：
- emergence 时 mss_score (temperature) < 30，假设 28
- 即使 irs_score = 100, pas_score = 100:
  `final_score = (28 + 100 + 100) / 3 = 76.0` → 刚过 75
- 但经 strength_factor（partial=0.9 时）：`76.0 × 0.9 = 68.4` → **低于 75，降为 BUY**
- 实际 IRS/PAS 不可能同时为 100 → emergence 下 STRONG_BUY 实质不可达

fermentation (30-45°C) 下：
- temp=40: `(40 + 95 + 95) / 3 = 76.7` → 勉强可达，但 strength_factor < 1.0 即跌破

**影响**：STRONG_BUY 的附加条件（emergence/fermentation）要求低温周期，但低温本身会拖低 final_score。设计意图是"在情绪早期阶段给出最强信号"，但公式使其几乎不可能触发。

**修复建议**：
- 方案 A：STRONG_BUY 评分阈值在 emergence/fermentation 周期下调（如 65）
- 方案 B：STRONG_BUY 判定不使用 final_score，改用 `(irs_score + pas_score) / 2 ≥ 85 + 周期条件`
- 方案 C：保持现状但在文档中标注"STRONG_BUY 为极端罕见信号"

---

#### P2-R11-10：Backtest 算法 §3.1 信号构建伪代码缺少 BacktestSignal 的 5+ 个字段

**位置**:
- `backtest-algorithm.md` §3.1 Step 3 (L93-104): 仅填充 signal_date/stock_code/entry/stop/target/position_size/recommendation/final_score/integration_mode
- `backtest-data-models.md` §1.2 BacktestSignal (L60-87): 额外定义 signal_id/stock_name/industry_code/mss_score/irs_score/pas_score/direction/neutrality/risk_reward_ratio/source

**缺失字段**：signal_id, stock_name, industry_code, mss_score, irs_score, pas_score, direction, neutrality, risk_reward_ratio, source — 共 10 个字段在伪代码中未赋值。

**影响**：
- `integrated_recommendation` 上游输出包含所有这些字段，可直接透传
- 伪代码缺失导致实现者不确定字段来源（是透传还是需要重新计算）
- `signal_id` 缺失意味着回测交易无法回溯到原始集成信号

**修复建议**：补全 §3.1 Step 3 的信号构建伪代码，显式列出所有字段赋值（透传自 `row.*`）。

---

## R1-R10 遗留更新

全部已关闭（99/99）。

---

## 累计统计

| 轮次 | 新发现 | 轮末修复 | 轮末OPEN |
|------|--------|----------|----------|
| R1 | 10 | 10 | 0 |
| R2 | 10 | 10 | 0 |
| R3 | 10 | 10 | 0 |
| R4 | 10 | 10 | 0 |
| R5 | 10 | 10 | 0 |
| R6 | 10 | 10 | 0 |
| R7 | 10 | 10 | 0 |
| R8 | 10 | 10 | 0 |
| R9 | 9 | 9 | 0 |
| R10 | 10 | 10 | 0 |
| **R11** | **10** | **10** | **0** |
| **合计** | **109** | **109** | **0** |

---

## 优先修复建议

1. **P0-R11-01**（strength_factor 覆盖）：影响所有信号的方向一致性惩罚，必须明确执行顺序
2. **P0-R11-02**（MSS 门控幽灵）：信息流图误导实现者，尤其影响 BU 模式在退潮期行为
3. **P1-R11-04**（行业集中度未执行）：风控缺口，可导致单一行业过度集中
4. **P1-R11-07**（Sortino std vs RMS）：公式口径不一致，回测与分析结果不可比
5. **P1-R11-03 + P1-R11-05 + P1-R11-06**：dataclass/config 补齐，一次性修复
6. 其余 P2 按优先级逐项处理
