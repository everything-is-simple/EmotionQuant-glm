# EmotionQuant 第十三轮审查报告

**审查者**: Claude (Warp Agent Mode)
**日期**: 2026-02-08
**审查范围**: MSS/IRS/PAS 因子算法内在逻辑、Integration Gate 流程、参数-数据耦合
**HEAD**: `b43c7d1` (develop)
**状态**: 🟢 已闭环（Codex 复核）

---

## 审查角度

本轮深入 **三大核心算法与集成层的内部逻辑**，重点审查：
- 因子公式中可配参数与数据字段名的耦合关系
- 验证约束在算法文档与数据模型文档之间的一致性
- 算法伪代码的完整性（是否有定义了的参数未被消费、定义了的字段未被引用）
- Validation Gate 在 Integration 算法中的落地路径

---

## 汇总

| 等级 | 数量 |
|------|------|
| P0（致命） | 0 |
| P1（重要） | 5 |
| P2（次要） | 5 |
| **合计** | **10** |

---

## 复查纠偏记录（Codex，2026-02-08）

- 复核基线：`develop` @ `b43c7d1`。
- 复核结论：R13 列出的 10 项问题已全部完成修复（10/10）。
- 关键闭环：
  - MSS：趋势判定改为严格递增/递减，数据约束与 `flat_count` 交叉覆盖口径对齐；
  - IRS/PAS：字段耦合窗口参数按 MVP 锁定，并补齐 `rotation_status` 与 `allocation_advice` 伪代码；
  - PAS：方向判定显式消费 `consecutive_down_days`，突破场景目标价加入 `RR≥1` 下限；
  - Backtest/Integration：补齐 `max_holding_days` 时限平仓规则、Validation Gate 前置检查与权重选择流程；
  - Config：补齐 `backtest_top_n` 与 `BACKTEST_TOP_N` 环境变量映射。

---

## P1 — 重要

### ~~P1-R13-01 · MSS §10.1 验证约束与数据模型矛盾：rise+fall+flat 是否允许 > total_stocks~~

| 项目 | 内容 |
|------|------|
| 文件 | `mss-algorithm.md` §10.1 (L398) vs `mss-data-models.md` §5.1 |
| 现状 | 算法：`rise_count + fall_count + flat_count ≤ total_stocks`。数据模型："允许 > total_stocks（flat_count 与 rise/fall 可交叉覆盖）"。 |
| 问题 | 两者互斥。如果实现按算法文档断言 `sum ≤ total_stocks`，合法数据会被拒绝；如果按数据模型允许重叠，则算法验收条款失效。 |
| 建议 | 统一为数据模型口径（允许重叠），将算法 §10.1 改为：`rise_count + fall_count ≤ total_stocks`（不含 flat_count），并注释 flat 可交叉覆盖。 |

### ~~P1-R13-02 · IRS/PAS 可配参数与数据字段名硬编码耦合~~

| 项目 | 内容 |
|------|------|
| 文件 | `irs-algorithm.md` §3.5 + §8.1；`pas-algorithm.md` §3.1 + §8.1 |
| 现状 | IRS `leader_top_n` 可配（默认 5，范围 3-10），但数据字段固定为 `top5_codes`/`top5_pct_chg`/`top5_limit_up`。PAS `limit_up_window`（默认 120）可配，但字段为 `limit_up_count_120d`。 |
| 问题 | 若用户将 `leader_top_n` 改为 10，分母变 10 但分子仍为 top5 数据 → 比例系统性偏低。同理 PAS `limit_up_window` 改为 60 但字段仍读 120d 数据 → ratio 可能超过 1。参数可调但数据管道不跟随。 |
| 建议 | 方案 A：将字段名改为泛化命名（`top_n_codes`、`limit_up_count_Nd`）并由 config 驱动数据管道窗口。方案 B：锁定参数为 const 不可调，并在注释中标明字段-参数耦合。推荐方案 B（MVP 阶段锁定）。 |

### ~~P1-R13-03 · PAS §5.2 bearish 方向判定条件未与 `consecutive_down_days` 字段显式关联~~

| 项目 | 内容 |
|------|------|
| 文件 | `pas-algorithm.md` §5.2 (L235) vs `pas-data-models.md` §2.1 (L67) |
| 现状 | 方向判定：`bearish: close < low_20d_prev 且 连续下跌≥3日`。数据模型有 `consecutive_down_days: int`，但算法中 **从未引用该字段**。 |
| 问题 | 实现者无法确定 "连续下跌≥3日" 应读取哪个字段。`consecutive_down_days` 在整个 PAS 因子计算中完全未消费——只在 direction 判定的自然语言描述中隐式对应。 |
| 建议 | §5.2 改为显式伪代码：`if close < low_20d_prev and consecutive_down_days >= 3: direction = "bearish"`。 |

### ~~P1-R13-04 · BacktestConfig.max_holding_days 定义但算法无时限平仓规则~~

| 项目 | 内容 |
|------|------|
| 文件 | `backtest-data-models.md` §1.1 (L52)；`backtest-algorithm.md` 全文 |
| 现状 | BacktestConfig 含 `max_holding_days: int = 10`，`config.py` 也有 `backtest_max_holding_days = 10`。 |
| 问题 | backtest-algorithm.md 没有任何步骤描述 "持仓超过 max_holding_days 则强制平仓"。该参数被采集、配置，但从未执行。如果不强制平仓，则参数名误导用户。 |
| 建议 | 在 backtest-algorithm.md §4（交易执行模型）中新增 "时限平仓" 步骤：每日检查持仓天数，超过 `config.max_holding_days` 则触发卖出。或将参数标注为 `reserved`。 |

### ~~P1-R13-05 · Integration 算法缺少 Validation Gate 检查步骤与权重选择伪代码~~

| 项目 | 内容 |
|------|------|
| 文件 | `integration-algorithm.md` 全文 |
| 现状 | §3.1："(w_mss, w_irs, w_pas) 来自已通过 validation_gate_decision 的权重方案"。但 (1) §2 输入规范未列出 `ValidationGateDecision`；(2) 算法无 "gate=FAIL → 拒绝进入集成" 步骤；(3) 无权重选择伪代码（baseline vs candidate）。 |
| 佐证 | integration-api.md 的 `calculate()` 签名含 `validation_gate_decision` 参数；data-models.md §2.6 定义了完整结构。API 与数据模型就绪但算法层空白。 |
| 建议 | §2 补增 §2.X 列出 ValidationGateDecision 输入；§3 前插入 "Gate 前置检查" 步骤（FAIL→拒绝、WARN→标记、PASS→继续），并给出权重选择伪代码：`weights = gate.selected_weight_plan == "baseline" ? BASELINE_WEIGHTS : candidate_plan`。 |

---

## P2 — 次要

### ~~P2-R13-06 · PAS 目标价计算对突破新高股票系统性不利~~

| 项目 | 内容 |
|------|------|
| 文件 | `pas-algorithm.md` §6 (L247-252) |
| 现状 | `target_ref = max(high_20d_prev, high_60d_prev)`；若股票在突破新高，两者均 < close → `target = entry × 1.03`。`stop = close × 0.92`（8% 止损）。`risk_reward = 0.03/0.08 = 0.375 < 1`。 |
| 问题 | 突破新高是结构位置因子的核心信号（breakout_strength > 0），但 risk_reward 却系统性 < 1。§6 判定 `< 1 → 回避`，与结构因子方向矛盾。 |
| 建议 | 为突破新高场景增加目标价扩展规则，例如 `target = max(target_ref, entry × (1 + stop_loss_pct))`，确保 risk_reward ≥ 1 作为底线。 |

### ~~P2-R13-07 · IRS §5.1 rotation_status 判定条件 "评分" 未指明字段~~

| 项目 | 内容 |
|------|------|
| 文件 | `irs-algorithm.md` §5.1 (L286-288) |
| 现状 | `IN: 评分连续3日上升`。"评分"指 `industry_score` 还是某个因子分？ |
| 建议 | 改为 `industry_score 连续3日上升`，消除歧义。 |

### ~~P2-R13-08 · IRS §6.1 rank→allocation_advice 映射无伪代码~~

| 项目 | 内容 |
|------|------|
| 文件 | `irs-algorithm.md` §6.1 (L307-312) |
| 现状 | 仅以表格给出排名区间与配置建议对应关系，无伪代码。其他判定逻辑（cycle、trend、rotation_status）均有伪代码。 |
| 建议 | 补充 `def get_allocation_advice(rank: int) -> str` 伪代码，与其他判定逻辑风格统一。 |

### ~~P2-R13-09 · config.py 缺少 `backtest_top_n` 参数~~

| 项目 | 内容 |
|------|------|
| 文件 | `src/config/config.py` vs `backtest-data-models.md` §1.1 |
| 现状 | BacktestConfig 含 `top_n: int = 20`（每日信号最大读取数），但 config.py 两个 Config 分支均未定义 `backtest_top_n`。R11 已补齐其余 7 个参数但遗漏此项。 |
| 建议 | Config 两分支补充 `backtest_top_n: int = 20`，并在 fallback 分支 `from_env` 中读取 `BACKTEST_TOP_N`。 |

### ~~P2-R13-10 · MSS §5.4 趋势判定 "连续3日上升/下降" 未明确严格递增语义~~

| 项目 | 内容 |
|------|------|
| 文件 | `mss-algorithm.md` §5.4 (L298-300) |
| 现状 | `上升: 连续3日温度上升`；`下降: 连续3日温度下降`。 |
| 问题 | "上升"是否要求严格递增（T-2 < T-1 < T）还是允许非递减（T-2 ≤ T-1 ≤ T）？若温度连续3日保持 50°C，是 sideways 还是 up？ |
| 建议 | 明确为严格递增：`temperature[t] > temperature[t-1] > temperature[t-2]`，并标注 "相等视为 sideways"。 |

---

## 审查方法

1. 逐算法对照 §因子公式 → §参数配置 → §数据模型，检查变量名/窗口/分母是否一一对应
2. 追踪 data model 字段在 algorithm 中的消费路径，识别"采集未消费"字段
3. 比较 algorithm.md 验收口径与 data-models.md 验证规则，找出矛盾断言
4. 检查 config.py 参数集与 BacktestConfig/TradeConfig 的覆盖完整性
5. 沿 Validation Gate → Integration → Trading/Backtest 信号链验证每一步的前置检查

---

*R13 完成（已闭环）。累计 R1-R13 共发现 119 个问题，当前 OPEN = 0。*
