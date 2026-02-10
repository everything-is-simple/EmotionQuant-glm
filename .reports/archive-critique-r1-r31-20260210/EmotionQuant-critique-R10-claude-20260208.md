# EmotionQuant 第十轮批判性审查报告

**审查人**: Claude (claude 4.6 opus)
**日期**: 2026-02-08
**基线**: `develop` @ `e0d7e67`（R9 修复已全部提交，工作区 clean）
**审查角度**: 公式细节验证 · 枚举/阈值边界交叉一致性 · 行业代码数据完整性 · 配置参数缺口 · 源码-规格对齐

---

## 本轮方法论

R9 聚焦 GUI 层全面审查与跨层数据契约端到端比对。本轮（R10）方法：

1. **核心算法公式逐行验证**：MSS/IRS/PAS/Integration 所有公式的常数值、边界条件、权重和做交叉核验。
2. **枚举合法值集合交叉一致性**：所有 `cycle`/`recommendation`/`direction` 枚举在算法层、数据模型层、验证规则层三处比对。
3. **行业代码与名称完整性**：IRS 行业代码表与 2021 版申万一级分类比对。
4. **配置参数完备性**：回测/分析公式引用的参数是否全部在 Config 中定义。
5. **源码 vs 设计规格字段对齐**：`src/data/models/*.py` 与 `data-layer-data-models.md` 逐字段比对。

---

## 新发现（10 项）

### P0 — 逻辑冲突 / 数据完整性（2 项）

#### P0-R10-01：IRS 行业代码表含已退役代码 801020（采掘），缺少 801980（美容护理）

**位置**: `irs-data-models.md` §5.1 (L241-272)

**现状**：列表中包含 31 个行业，其中：
- `801020 采掘` — 2021 年申万一级修订时已拆分为 `煤炭`(801950) + `石油石化`(801960)
- `801950 煤炭` 和 `801960 石油石化` 已在列表中（重复覆盖了旧 801020 的业务范围）
- `801980 美容护理` — 2021 修订新增行业，列表中缺失

**影响**：
- 查询 `raw_index_classify` 或 `raw_index_member` 时，`801020` 在 2021 版（SW2021 `src` 字段）中不存在 → 返回空集 → 该行业的 IRS 评分为 NaN
- 美容护理行业（约 40+ 成分股）无法被 IRS 覆盖 → 其个股永远无法进入超配行业推荐
- 净效果：31 个代码中有效 30 个、无效 1 个、漏失 1 个
**修复建议**：删除 `801020 采掘`，新增 `801980 美容护理`；同时核对 TuShare `index_classify(level='L1', src='SW2021')` 实际返回的代码集合。

**✅ 已修复** (`313fe5d`): `801020 采掘` 已删除，`801980 美容护理` 已新增；5 个旧版名称已同步更新为 2021 版（基础化工/纺织服饰/商贸零售/社会服务/电力设备）。版本升至 v3.2.5。

---

#### P0-R10-02
#### P0-R10-02：Backtest/Sharpe/Sortino 公式引用的 `rf`（无风险利率）未定义为配置参数

**位置**:
- `backtest-algorithm.md` §5.3 (L247): `sharpe = sqrt(252) × (mean(r_t) - rf/252) / std(r_t)`
- `backtest-algorithm.md` §5.3 (L250): `mar_daily = rf / 252`
- `backtest-data-models.md` §1.1 BacktestConfig (L20-54): **无 `risk_free_rate` 字段**

**影响**：
- 公式中 `rf` 无定义源，实现者必须自行决定值 → 不同实现可能使用 0% / 1.5% / 3% 等不同假设
- Sharpe 和 Sortino 结果不可复现
- `src/config/config.py` 中也无对应参数
**修复建议**：在 `BacktestConfig` 中添加 `risk_free_rate: float = 0.015`（年化 1.5%，当前中国十年期国债收益率近似值），并在 `config.py` 中同步定义 `backtest_risk_free_rate`。

**✅ 已修复** (`313fe5d`): `BacktestConfig` 新增 `risk_free_rate: float = 0.015`；`config.py` 两处 Config 分支均已添加 `backtest_risk_free_rate`。

---

### P1
### P1 — 规格冲突 / 数据契约缺口（5 项）

#### P1-R10-03：Analysis Sharpe 公式缺少无风险利率，与 Backtest Sharpe 公式不一致

**位置**:
- `analysis-data-models.md` §1.1 (L43): `sharpe_ratio = sqrt(252) × mean(r) / std(r)` — 无 rf
- `backtest-algorithm.md` §5.3 (L247): `sharpe = sqrt(252) × (mean(r_t) - rf/252) / std(r_t)` — 含 rf

**对比**：

| 模块 | 公式 | rf |
|------|------|----|
| Backtest | `sqrt(252) × (mean(r) - rf/252) / std(r)` | 有 |
| Analysis | `sqrt(252) × mean(r) / std(r)` | 无 |

**影响**：同一条净值曲线，Backtest 与 Analysis 计算出的 Sharpe 不一致。当 rf > 0 时 Analysis 的 Sharpe 系统性偏高。Sortino 同理。
**修复建议**：Analysis 公式统一为 `sqrt(252) × (mean(r) - rf/252) / std(r)`，与 Backtest 一致。

**✅ 已修复** (`313fe5d`): Sharpe 与 Sortino 公式均已补入 rf 项，与 Backtest 一致。版本升至 v3.1.2。

---

#### P1-R10-04
#### P1-R10-04：MSS 输出验证规则 §5.2 cycle 合法值不含 'unknown'，但枚举和伪代码均包含 UNKNOWN

**位置**:
- `mss-data-models.md` §5.2 (L271): `cycle IN ('emergence', 'fermentation', ... , 'recession')` — 7 值，不含 unknown
- `mss-data-models.md` §3.2 (L144): `UNKNOWN = "unknown"` — 枚举定义包含 unknown
- `mss-algorithm.md` §5.2 (L279): `return "unknown"` — 伪代码有 fallback 分支

**冲突链**：
1. 枚举定义：8 种值（含 UNKNOWN）
2. 算法伪代码：可返回 "unknown"
3. 输出验证：只允许 7 种值（不含 unknown）

**影响**：
- 冷启动/边界条件下 MSS 返回 `unknown` → 输出验证失败 → 数据库写入被拒或报错
- 下游（Integration/GUI）即使已支持 UNKNOWN 映射，也收不到该值

**修复建议**：
- 方案 A（推荐）：将 §5.2 验证规则改为 8 种值（含 'unknown'），允许冷启动输出
- 方案 B：在 detect_cycle 最终 fallback 前增加兜底逻辑（如 temperature < 60 → recession），使 unknown 永远不可达 → 但仍需保留枚举用于防御

**✅ 已修复** (`313fe5d`): §5.2 验证规则已扩展为 8 种值（含 'unknown'）。版本升至 v3.1.3。

---

#### P1-R10-05

**位置**: `integration-algorithm.md` §5.3 (L181)

```text
IRS allocation_advice = "超配" → pas_score 轻度上浮（例如 ×1.05）
```

**问题**：若 `pas_score = 98`，调整后 `= 102.9`，超出 [0, 100] 边界。

- `calibrate_score`（§3.2）在协同约束 **之前** 执行，不会 re-clip
- `final_score = w × mss + w × irs + w × 102.9` 可导致 `final_score > 100`
- 输出验证要求 `final_score ∈ [0, 100]`，触发校验失败
**修复建议**：在 §5.3 协同约束后添加 `pas_score = clip(pas_score, 0, 100)` 再计算 final_score。

**✅ 已修复** (`313fe5d`): §5.3 已添加显式 `pas_score = clip(pas_score, 0, 100)` 边界裁剪。

---

#### P1-R10-06
#### P1-R10-06：PAS 行为因子 pct_chg_norm 映射区间 [-10%, 10%] 对创业板/科创板 20% 涨跌幅失去区分度

**位置**: `pas-algorithm.md` §3.3 (L161)

```text
pct_chg_norm = clip((pct_chg + 10) / 20, 0, 1)
```

**问题**：
- 此映射将 [-10%, 10%] 线性映射到 [0, 1]，超出 10% 的值统一 clip 到 1.0
- 创业板/科创板个股涨跌幅限制为 ±20%，北交所为 ±30%
- pct_chg = 10% 与 pct_chg = 20%（涨停）在该公式下得分相同（均为 1.0）
- 约 2000+ 创业板/科创板个股的行为因子在强势突破时丧失区分能力

**影响**：PAS 无法区分"创业板 10% 涨幅"与"创业板 20% 涨停"，后者的行为确认信号本应更强。

**修复建议**：
- 方案 A：扩大映射区间为 `clip((pct_chg + 20) / 40, 0, 1)` 以覆盖 ±20%
- 方案 B：按板块动态调整区间（主板 ±10%，创业板/科创板 ±20%，北交所 ±30%）
- 方案 C：在 §8 参数配置中增加 `pct_chg_map_range` 参数，允许运行时配置

**✅ 已修复** (`313fe5d`): 采用方案 A，映射区间扩展为 `clip((pct_chg + 20) / 40, 0, 1)` 覆盖 ±20%。

---

#### P1-R10-07

**位置**: `trading-algorithm.md` §6.2 (L334-345)

```text
can_sell(stock_code, shares, trade_date) -> bool:
    if stock_code not in positions:
        return True          ← 不持有的股票也返回"可卖"
```

**问题**：
- A 股不允许卖空，不持有 → 不可卖 → 应返回 False
- 该函数被 §3.1 风控检查（点 4）调用：`if not t1_tracker.can_sell(...): return (False, "T+1限制")`
- 若股票不在持仓中，can_sell 返回 True → 风控通过 → 生成无效卖单

**修复建议**：改为 `if stock_code not in positions: return False`。或将此分支改为 `return shares <= 0`（语义：不持有 = 可卖 0 股），明确 0 股卖单不下发。

**✅ 已修复** (`313fe5d`): `can_sell()` 已改为 `if stock_code not in positions: return False`。版本升至 v3.2.2。

---

### P2

#### P2-R10-08：Backtest Position 含 direction 字段，Trading Position 不含

**位置**:
- `backtest-data-models.md` §2.2 positions 表 (L285): `direction VARCHAR(10)`
- `trading-data-models.md` §1.3 Position dataclass (L85-103): 无 direction 字段

**影响**：A 股为纯多头市场，direction 始终为 "buy"/"long"，但两处 Position 结构不一致会导致：
- 代码复用困难（回测与实盘无法共享 Position 类）
- 序列化/反序列化时字段不匹配
**修复建议**：统一两处 Position 定义。建议 Trading Position 添加 `direction: str = "long"` 字段与 Backtest 对齐。

**✅ 已修复** (`313fe5d`): Trading Position 已新增 `direction: str = "long"` 字段（L89），与 Backtest 对齐。

---

#### P2-R10-09
#### P2-R10-09：IRS 行业名称使用旧版申万分类名称，与 2021 版 API 返回不一致

**位置**: `irs-data-models.md` §5.1 (L241-272)

| 代码 | 文档名称 | 2021 版名称 |
|------|----------|-------------|
| 801030 | 化工 | 基础化工 |
| 801130 | 纺织服装 | 纺织服饰 |
| 801200 | 商业贸易 | 商贸零售 |
| 801210 | 休闲服务 | 社会服务 |
| 801730 | 电气设备 | 电力设备 |

**影响**：TuShare `index_classify(src='SW2021')` 返回的 `index_name` 使用 2021 版名称。若代码中以行业名称做 join 或 lookup，将因名称不匹配而丢失数据。
**修复建议**：更新为 2021 版名称。若需保留旧名称用于兼容，增加 `legacy_name` 列。

**✅ 已修复** (`313fe5d`): 与 P0-R10-01 合并修复，5 个行业名称已更新为 2021 版。

---

#### P2-R10-10
#### P2-R10-10：monitoring-alerting-design.md 和 scheduler-orchestration-design.md 版本 v0.1 草案，仅含占位内容

**位置**:
- `monitoring-alerting-design.md`: v0.1, 2026-02-02, 22 行
- `scheduler-orchestration-design.md`: v0.1, 2026-02-02, 17 行

**影响**：
- 系统所有其他模块（MSS/IRS/PAS/Integration/Trading/Backtest/GUI/Data-Layer/Validation）均已有详尽设计（数千行）
- 监控告警与调度编排仍为 5-6 句话的占位草案，6 天未更新
- 进入实现阶段后，无法定义数据就绪检查、任务依赖、失败重试、告警升级等关键运维流程

**修复建议**：在下一个 Spiral 圈之前，补充至少包含以下内容的设计：
- 任务 DAG（Data → MSS → IRS → PAS → Integration → Trading）及依赖关系
- 数据就绪检查点与超时阈值
- 告警级别定义与升级路径
- 失败重试策略（指数退避 / 最大重试次数）

**✅ 已修复** (`313fe5d`): 两份文档均从 v0.1 占位升级至 v0.2 可执行草案。monitoring-alerting-design.md 补充监控范围、指标阈值、告警升级、重试策略；scheduler-orchestration-design.md 补充 DAG、就绪检查点、调度窗口、补偿策略。

---

## R1-R9 遗留更新

全部已关闭（89/89）。

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
|| **R10** | **10** | **10** | **0** |
|| **合计** | **99** | **99** | **0** |

---

## 优先修复建议

全部 10 项已修复并验证通过（`313fe5d`）。无待处理项。
