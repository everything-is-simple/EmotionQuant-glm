# EmotionQuant 第六轮批判性审查报告

**审查人**: Claude (claude 4.6 opus)
**日期**: 2026-02-07
**基线**: `develop` @ `ad9ff99`（与 R5 相同 — 无新提交）
**审查角度**: 跨模块契约一致性 · 算法边界/不可达逻辑 · 设计文档内部矛盾

---

## 本轮方法论

R1-R5 已覆盖：代码/文档比例失衡、质量扫描误报、导入路径、铁律合规、快照字段、PAS 归一化顺序、冷启动缺口、测试隔离等。

本轮（R6）方法：将三大算法（MSS/IRS/PAS）的四位一体文档（algorithm + data-models + api + information-flow）逐字段交叉比对，追踪字段从输入模型→算法公式→输出模型→集成输入模型→集成公式→交易信号的完整链路，挖掘契约断裂和边界不可达。

---

## 新发现（原 14 项，复查后 13 项）

### P0 — 设计缺陷 / 算法逻辑错误（5 项）

#### P0-R6-01：STRONG_BUY 在设计上数学不可达

**位置**: `integration-algorithm.md` §5.1 + §8.2（周期-温度映射）

**问题**: STRONG_BUY 要求 `final_score ≥ 80` **且** `mss_cycle ∈ {emergence, fermentation}`。但 emergence 要求 temperature < 30，fermentation 要求 30-45。集成公式 `final_score = (mss + irs + pas) / 3`，其中 mss_score = temperature。

数学证明：

```
emergence（temp < 30）:
  max final = (29.9 + 100 + 100) / 3 = 76.6 < 80  ← 不可能

fermentation（temp 30-45）:
  max final = (44.9 + 100 + 100) / 3 = 81.6
  × strength_factor(partial=0.9) = 73.4 < 80  ← 仅 consistent 才勉强够
  × strength_factor(consistent=1.0) = 81.6  ← 需要 IRS=100 且 PAS=100
```

结论：emergence 阶段 STRONG_BUY 数学不可达；fermentation 阶段仅在 IRS 和 PAS 同时接近 100 且三方向完全一致时才勉强触及。STRONG_BUY 实质上是死代码。

**修复**: 要么降低 STRONG_BUY 阈值（如 ≥70），要么在 STRONG_BUY 判定中使用 pre-constraint final_score，要么扩大适用周期。

---

#### P0-R6-02：IRS 配置建议覆盖缺口 — 6 个行业无分类

**位置**: `irs-algorithm.md` §6.1 + `irs-data-models.md` §3.3

**问题**: 31 个申万一级行业，配置建议映射为：

```
超配: 前 3 名     → 3 个
标配: 4-10 名     → 7 个
减配: 11-20 名    → 10 个
回避: 后 5 名     → 5 个
合计                25 ≠ 31
```

排名 21-26 的 6 个行业**没有对应的 allocation_advice**。枚举只有 4 个值（超配/标配/减配/回避），无法表达这些行业的状态。

**影响**: Integration 的 IRS 配置约束依赖 `allocation_advice` 字段做仓位调整（超配 ×1.05，回避 ×0.85），排名 21-26 行业的股票会因为 null 或未定义值导致运行时异常。

**修复**: 将"减配"扩展至 11-26 名，或新增"低配"类别覆盖 21-26。

---

#### P0-R6-03：MSS 周期检测 — sideways 在低温时被错误分类为"分歧期"

**位置**: `mss-algorithm.md` §5.2 伪代码 vs `naming-conventions.md` §1.1

**问题**: 周期定义表明确 divergence（分歧期）= 60-75°C + up/sideways。但伪代码：

```python
if trend == "sideways":
    return "divergence"  # 不检查温度！
```

当 temperature = 20°C + sideways 时，代码返回 "divergence"，但按定义应为未覆盖状态。以下 sideways 场景均被错误归类：

| 温度范围 | 趋势 | 代码输出 | 定义表应为 |
|----------|------|----------|-----------|
| < 30°C | sideways | divergence | 未定义 |
| 30-60°C | sideways | divergence | 未定义 |
| 60-75°C | sideways | divergence | divergence ✓ |

**修复**: 为 sideways + 低温场景补充周期定义（如 sideways + < 30°C → "recession"？），并在伪代码中加温度区间判断。

---

#### P0-R6-04：PAS 方向判定和风险收益比引用了数据模型中不存在的字段

**位置**: `pas-algorithm.md` §5.2 + §6 vs `pas-data-models.md` §2.1 (PasStockSnapshot)

**问题**: PAS 算法引用以下字段，但 PasStockSnapshot **均未定义**：

| 引用位置 | 字段 | PasStockSnapshot 中 |
|----------|------|---------------------|
| §5.2 方向判定 | `high_20d_prev` | ❌ 不存在（只有 `high_60d_prev`） |
| §5.2 方向判定 | `low_20d_prev` | ❌ 不存在 |
| §6 止损计算 | `low_20d` | ❌ 不存在（只有 `low_60d`） |

方向判定公式 `close > high_20d_prev` 和止损公式 `stop = min(low_20d, ...)` 所需的 20 日窗口数据在输入模型中根本不存在，实现时必然报错。

**修复**: 在 PasStockSnapshot 补充 `high_20d_prev`、`low_20d_prev`、`low_20d`；或将方向判定和止损改用已有的 60 日字段。

---

#### P0-R6-05：Integration 方向一致性检查 — 三方全部中性被错误判定为"divergent"

**位置**: `integration-information-flow.md` §2.4 + `integration-algorithm.md` §4.2

**问题**: 方向一致性公式：

```python
direction_sum = mss_dir + irs_dir + pas_dir  # 各取 -1/0/+1

if direction_sum == 3 or direction_sum == -3:
    consistency = "consistent"
elif abs(direction_sum) >= 1:
    consistency = "partial"
else:
    consistency = "divergent"  # abs(sum) < 1 → sum == 0
```

当 MSS=sideways(0)、IRS=HOLD(0)、PAS=neutral(0) 时，sum=0，被判定为 **divergent**。但三个系统明明**一致同意中性**。divergent 触发最严厉的惩罚（strength_factor=0.8，中性度系数=0.7）。

还有 (1,0,-1) 和 (-1,0,1) 等组合也落入 sum=0，但这些确实是方向不一致。问题在于 (0,0,0) 不应该和它们混为一谈。

**修复**: 特判 (0,0,0) 为 "consistent"（或新增 "neutral_consistent" 类别）。建议改为：

```python
if abs(direction_sum) == 3:
    consistency = "consistent"
elif mss_dir == 0 and irs_dir == 0 and pas_dir == 0:
    consistency = "consistent"  # 三方一致中性
elif abs(direction_sum) >= 1:
    consistency = "partial"
else:
    consistency = "divergent"
```

---

### P1 — 契约不一致 / 潜在风险（5 项）

#### P1-R6-06：代码 Snapshot 存在无规范支撑的幽灵字段

**位置**: `src/data/models/snapshots.py` vs `mss-data-models.md` / `irs-data-models.md`

| 代码字段 | MarketSnapshot | IndustrySnapshot | 设计规范 |
|----------|:-:|:-:|----------|
| `yesterday_limit_up_today_avg_pct` | L27 ✓ | L52 ✓ | ❌ 两份 data-models 均无 |
| `flat_count` | L12 ✓ | L38 ✓ | MSS 有 ✓ / IRS 无 ❌ |

`yesterday_limit_up_today_avg_pct` 是"昨日涨停股今日平均涨跌幅"——有价值但未纳入任何算法因子。代码有实现但设计无定义。

---

#### P1-R6-07：IRS 估值因子用 `percentile_rank` 而非声称的统一 `normalize_zscore`

**位置**: `irs-algorithm.md` §3.4 vs §4.2 + §9.2

§4.2 声明"统一使用 Z-Score 归一化"，§9.2 说"归一化只能通过 normalize_zscore 完成"。但 §3.4：

```
valuation_score = percentile_rank(industry_pe_ttm, history_window=3y)
```

`percentile_rank` 基于排序位置映射到 0-100，`normalize_zscore` 基于标准差映射。两者对尾部值和分布偏斜的处理完全不同。这违反了文档自身的统一规范要求。

---

#### P1-R6-08：Integration 中性度计算存在歧义 — Step 5 与 Step 6.5 冲突

**位置**: `integration-information-flow.md` §2.5 (Step 5) vs §2.7 (Step 6.5)

Step 5（协同约束）说：

```
MSS 温度 < 30 or > 80 → neutrality *= 1.1
```

Step 6.5（中性度计算）说：

```
neutrality = (mss_neut + irs_neut + pas_neut) / 3 × consistency_factor
```

问题：Step 5 修改了 neutrality（×1.1），但 Step 6.5 又从头计算 neutrality（三系统均值 × 一致性系数）。哪个结果是最终值？如果 Step 6.5 覆盖了 Step 5 的调整，那 Step 5 的 `neutrality *= 1.1` 就是死代码。

---

#### P1-R6-09：PAS bull_gene_raw 内部子因子量级差异 ~500:1

**位置**: `pas-algorithm.md` §3.1

```
bull_gene_raw = 0.4 × limit_up_120d_ratio + 0.3 × new_high_60d_ratio + 0.3 × max_pct_chg_history
```

典型值域：
- `limit_up_120d_ratio` ≈ 0.01-0.05（120日内涨停次数/窗口长度）
- `new_high_60d_ratio` ≈ 0.02-0.15（60日新高次数/窗口长度）
- `max_pct_chg_history` ≈ 5-20%（百分比值）

实际贡献：0.4×0.03 = 0.012 vs 0.3×15 = 4.5。`max_pct_chg_history` 的实际影响力是 `limit_up_120d_ratio` 的 **~375 倍**，使声称的权重（0.4/0.3/0.3）形同虚设。

这是 R5 P1-3 的深化：不仅 PAS 整体存在 combine-then-normalize 问题，内部子因子之间也存在同样的量级失衡。

---

#### P1-R6-10：`.env.example` 缺少 Config 类中 4 个字段

**位置**: `.env.example` vs `src/config/config.py`

Config 类定义了以下字段但 `.env.example` 中无对应条目：

| 字段 | Config 默认值 | .env.example |
|------|---------------|-------------|
| `STREAMLIT_PORT` | 8501 | ❌ 缺失 |
| `BACKTEST_INITIAL_CAPITAL` | 1,000,000 | ❌ 缺失 |
| `BACKTEST_COMMISSION_RATE` | 0.0003 | ❌ 缺失 |
| `BACKTEST_STAMP_DUTY_RATE` | 0.001 | ❌ 缺失 |

用户无法从 `.env.example` 得知这些可配参数的存在。

---

### P2 — 文档不一致 / 维护隐患（原 4 项，复查后 3 项）

#### P2-R6-11：ROADMAP 已切换 Spiral 模型，但 Warp rules 仍嵌入线性 Phase→Task→Step 工作流

ROADMAP-OVERVIEW.md 已于 2026-02-07 重构为 Spiral S0-S6 + CP 模型，development-status.md 也同步更新。但 `.warp/rules/` 中的 6A 工作流仍描述 `Phase→Task→Step` 线性模型（feature/phase-XX-task-Y 分支命名等）。会话开始时加载的规则与实际治理模型脱节。

#### P2-R6-12：Integration data-models 版本滞后于 API/algorithm/info-flow

| 文档 | 版本 | 日期 |
|------|------|------|
| integration-algorithm.md | v3.4.1 | 2026-02-07 |
| integration-api.md | v3.4.0 | 2026-02-07 |
| integration-information-flow.md | v3.4.1 | 2026-02-07 |
| **integration-data-models.md** | **v3.3.1** | **2026-02-07** |

data-models 未同步 Validation Gate 相关变更（`weight_plan`、`ValidationGateDecision` 等新类型未在数据模型中定义）。

#### P2-R6-13：所有 DuckDB DDL 使用 MySQL 语法

项目明确选用 DuckDB，但 6 个 data-models 文件中的 `CREATE TABLE` 语句全部使用 MySQL 特有语法：

- `COMMENT '...'`（DuckDB 不支持）
- `UNIQUE KEY uk_xxx`（DuckDB 用 `UNIQUE(col)`）
- `KEY idx_xxx`（DuckDB 用 `CREATE INDEX`）

直接在 DuckDB 中执行会全部报错。虽然标注了"逻辑DDL"，但既然已选定 DuckDB 作为目标引擎，DDL 应使用 DuckDB 语法（或标注为伪代码而非 SQL 代码块）。

#### P2-R6-14：MssMarketSnapshot `flat_count` 与 `rise_count`/`fall_count` 存在交叉覆盖

`flat_count` 定义为 `abs(pct_chg) <= 0.5%`，`rise_count` 定义为 `pct_chg > 0`。一只 pct_chg = 0.3% 的股票同时被计入 rise_count 和 flat_count。验证规则写 `rise_count + fall_count + flat_count ≤ total_stocks`（≤ 而非 =），表明设计者已意识到重叠，但这一语义在文档中未显式说明，实现者容易假设互斥而写出 `== total_stocks` 的断言。

---

## R5 遗留（已全部关闭）

按 R6 原始审查时点（`develop@ad9ff99`）口径，R5 曾有 9 项问题；当前基线均已关闭：

| ID | 优先级 | 摘要 | 状态 |
|----|--------|------|------|
| P0-R5-01 | P0 | ~~test_config_defaults 失败（pydantic 读 .env）~~ | ✅ |
| P0-R5-02 | P0 | ~~quality_check 测试文件自触发~~ | ✅ |
| P1-R5-03 | P1 | ~~PAS 因子量纲治理问题（原归一化顺序争议）~~ | ✅（含 R6-09 深化） |
| P1-R5-04 | P1 | ~~IRS/PAS 缺 Z-Score 冷启动规范~~ | ✅ |
| P1-R5-05 | P1 | ~~hooks 文件 bare except~~ | ✅ |
| P1-R5-06 | P1 | ~~Snapshot 缺 created_at~~ | ✅ |
| P2-R5-07 | P2 | ~~IndustrySnapshot top5_codes 需 json.dumps~~ | ✅ |
| P2-R5-08 | P2 | ~~_resolve_storage_paths 空白边界~~ | ✅ |
| P2-R5-09 | P2 | trading-algorithm.md 版本未更新 | ✅ 已更新至 v3.2.0 |

> R5-09 在 R6 检查中发现 trading-algorithm.md 已为 v3.2.0（2026-02-06），可关闭。

---

## 累计统计

| 轮次 | 发现 | 已修复 | 本轮新增 | 当前 OPEN |
|------|------|--------|----------|-----------|
| R1-R3 | 22 | 18 | — | 0 |
| R4 | 5 | 5 | — | 0 |
| R5 | 9 | 9 | — | 0 |
| **R6** | — | — | **13** | **0** |

*R5 全部问题已在 R6 收口完成。

---

## 执行回写（2026-02-07）

已按优先级落地 3 个 P0：

1. `P0-R6-01`（STRONG_BUY 可达域问题）  
   - 已修复：`STRONG_BUY_threshold` 调整为 75，并同步到 Integration/命名规范/Data Layer/GUI。  
   - 影响文件：`docs/design/core-algorithms/integration/integration-algorithm.md`、`docs/design/core-algorithms/integration/integration-information-flow.md`、`docs/design/core-algorithms/integration/integration-data-models.md`、`docs/naming-conventions.md`、`docs/design/data-layer/data-layer-data-models.md`、`docs/design/gui/gui-algorithm.md`

2. `P0-R6-02`（IRS allocation_advice 覆盖缺口）  
   - 已修复：排名映射改为 `前3/4-10/11-26/27-31`，覆盖全部 31 行业。  
   - 影响文件：`docs/design/core-algorithms/irs/irs-algorithm.md`、`docs/design/core-algorithms/irs/irs-data-models.md`、`docs/design/core-algorithms/irs/irs-information-flow.md`

3. `P0-R6-05`（方向一致性 0,0,0 误判）  
   - 已修复：`mss=0, irs=0, pas=0` 特判为 `consistent`。  
   - 影响文件：`docs/design/core-algorithms/integration/integration-information-flow.md`、`docs/design/core-algorithms/integration/integration-algorithm.md`

状态变更：
- R6 有效问题：13 → 10（关闭 3 项）
- 总 OPEN：21 → 18

---

## 执行回写（二）（2026-02-07）

继续按你确认的下一组落地 3 项：

4. `P0-R6-03`（MSS sideways 低温误判）  
   - 已修复：`sideways` 增加温度分支，`temperature < 60` 归入 `recession`，`temperature >= 60` 才归入 `divergence`。  
   - 影响文件：`docs/design/core-algorithms/mss/mss-algorithm.md`、`docs/naming-conventions.md`、`docs/design/data-layer/data-layer-data-models.md`、`docs/design/core-algorithms/integration/integration-algorithm.md`

5. `P0-R6-04`（PAS 20 日字段缺口）  
   - 已修复：`PasStockSnapshot` 补齐 `high_20d_prev`、`low_20d_prev`、`low_20d`，并同步到 PAS 算法数据就绪口径与信息流示例。  
   - 影响文件：`docs/design/core-algorithms/pas/pas-data-models.md`、`docs/design/core-algorithms/pas/pas-algorithm.md`、`docs/design/core-algorithms/pas/pas-information-flow.md`

6. `P1-R6-08`（Integration 中性度流程歧义）  
   - 已修复：Step 5 输出 `neutrality_risk_factor`，Step 7 一次性计算 `neutrality = mean × consistency_factor × neutrality_risk_factor`（并 clip 到 [0,1]）。  
   - 影响文件：`docs/design/core-algorithms/integration/integration-information-flow.md`、`docs/design/core-algorithms/integration/integration-algorithm.md`

状态变更：
- R6 有效问题：10 → 7（再关闭 3 项）
- 总 OPEN：18 → 15

---

## 执行回写（三）（2026-02-07）

继续按 OPEN 优先级落地 3 项（P1）：

7. `P1-R6-07`（IRS 估值归一化口径不一致）  
   - 已修复：估值因子从 `percentile_rank` 统一为 `normalize_zscore`，并明确 `valuation_raw = -industry_pe_ttm`（PE 越低越优）。  
   - 影响文件：`docs/design/core-algorithms/irs/irs-algorithm.md`、`docs/design/core-algorithms/irs/irs-information-flow.md`

8. `P1-R6-09`（PAS bull_gene 子因子量纲歧义）  
   - 已修复：明确 `max_pct_chg_history` 为百分数口径（15 表示 15%），在牛股基因计算前统一 `/100` 转为 ratio 后再加权。  
   - 影响文件：`docs/design/core-algorithms/pas/pas-algorithm.md`、`docs/design/core-algorithms/pas/pas-data-models.md`、`docs/design/core-algorithms/pas/pas-information-flow.md`

9. `P1-R6-10`（`.env.example` 配置缺口）  
   - 已修复：补齐 `STREAMLIT_PORT`、`BACKTEST_INITIAL_CAPITAL`、`BACKTEST_COMMISSION_RATE`、`BACKTEST_STAMP_DUTY_RATE`。  
   - 影响文件：`.env.example`

状态变更：
- R6 有效问题：7 → 4（再关闭 3 项）
- 总 OPEN：15 → 12

---

## 执行回写（四）（2026-02-07）

继续处理剩余优先项 3 个：

10. `P1-R6-06`（Core/Data Layer 字段分布不统一）  
   - 已修复：在 MSS/IRS core data-models 显式补齐兼容观测字段口径（`yesterday_limit_up_today_avg_pct`、`flat_count`），并标注“非当前打分因子”的使用边界。  
   - 影响文件：`docs/design/core-algorithms/mss/mss-data-models.md`、`docs/design/core-algorithms/irs/irs-data-models.md`

11. `P2-R6-12`（Integration data-models 版本滞后）  
   - 已修复：`integration-data-models` 升级到 `v3.4.3`，补齐 `WeightPlan` / `ValidationGateDecision` 输入模型、`validation_gate`/`weight_plan_id` 追溯字段及对应验证规则。  
   - 影响文件：`docs/design/core-algorithms/integration/integration-data-models.md`、`docs/design/data-layer/data-layer-data-models.md`

12. `P2-R6-14`（`flat_count` 与涨跌家数重叠语义不清）  
   - 已修复：在 MSS 与 Data Layer 文档显式声明 `flat_count` 可与 `rise_count`/`fall_count` 交叉覆盖，并将验证规则改为按“非互斥口径”描述。  
   - 影响文件：`docs/design/core-algorithms/mss/mss-data-models.md`、`docs/design/data-layer/data-layer-data-models.md`

状态变更：
- R6 有效问题：4 → 1（再关闭 3 项）
- 总 OPEN：12 → 9

---

## 执行回写（五）（2026-02-07）

继续完成剩余 OPEN 收口（9 项）：

13. `P2-R6-13`（DuckDB DDL 语法口径）  
   - 已修复：在 MSS/IRS/PAS/Integration/Analysis 的 data-models 文档中统一将 DDL 明确标注为“MySQL 风格逻辑伪DDL，不可直接在 DuckDB 执行”，并给出 DuckDB 落地改写约束。  
   - 影响文件：`docs/design/core-algorithms/mss/mss-data-models.md`、`docs/design/core-algorithms/irs/irs-data-models.md`、`docs/design/core-algorithms/pas/pas-data-models.md`、`docs/design/core-algorithms/integration/integration-data-models.md`、`docs/design/analysis/analysis-data-models.md`

14. `R5 遗留 8 项`（P0-R5-01/02、P1-R5-03/04/05/06、P2-R5-07/08）  
   - 已修复：完成 P0 测试隔离与扫描边界修正、PAS/IRS 冷启动与尺度治理补充、hooks 裸 except 收敛、Snapshot `created_at` 与 JSON 序列化契约落地。  
   - 影响文件：`src/config/config.py`、`scripts/quality/local_quality_check.py`、`.claude/hooks/*.py`、`src/data/models/snapshots.py`、`tests/unit/config/test_config_defaults.py`、`tests/unit/scripts/test_local_quality_check.py`、`tests/unit/data/models/test_snapshots.py`、以及 IRS/PAS/Data Layer 相关文档

状态变更：
- R6 有效问题：1 → 0（关闭最后 1 项）
- 总 OPEN：9 → 0

---

## 修复优先级建议

**已完成（本次落地）**:
1. P0-R6-01: STRONG_BUY 阈值/条件修订
2. P0-R6-02: IRS 配置建议覆盖 31 个行业
3. P0-R6-05: 方向一致性 (0,0,0) 特判
4. P0-R6-03: MSS sideways 周期补全
5. P0-R6-04: PAS 补充 20d 字段或改用 60d
6. P1-R6-08: 明确 Integration neutrality 计算顺序
7. P1-R6-07: IRS 估值因子统一为 normalize_zscore
8. P1-R6-09 + R5-03: PAS 子因子量纲治理与归一化口径统一
9. P1-R6-10: `.env.example` 补齐 Config 可配置项
10. P1-R6-06: Core/Data Layer 字段分布统一（`flat_count`/`yesterday_limit_up_today_avg_pct`）
11. P2-R6-12: Integration data-models 升级到 v3.4.x 并补齐 Validation Gate 类型
12. P2-R6-14: `flat_count` 交叉覆盖语义显式化

**待继续处理（OPEN）**:
- ~~13. P2-R6-13: DuckDB 逻辑DDL语法标注/改写统一~~ ✅
- ~~14. R5 遗留 8 项：见“R5 遗留（9 项未关闭）”表（除已关闭 R5-09 外）~~ ✅
- 当前 OPEN：**0**

---

## 复查勘误（Codex，2026-02-07）

基于当前仓库实查（代码 + 文档）对本报告做勘误，结论如下：

### 1) 基线说明（时间点差异）

- 本报告写作时基线为 `develop@ad9ff99`；
- 当前仓库基线已前进到 `develop@d1def0f`（2026-02-07，当日新增报告修订提交）。

因此“与 R5 相同 — 无新提交”仅对写作时成立，不适用于当前仓库状态。

### 2) P2-R6-11 撤回（未复现）

原条目称 `.warp/rules/` 与 Spiral 治理冲突。  
当前仓库中未发现 `.warp/` 目录（路径不存在），该问题在当前基线上无法复现，予以撤回。

### 3) P0-R6-01 结论收敛（非“死代码”）

`STRONG_BUY` 在 `emergence` 周期下数学上不可达，这一点成立；  
但在 `fermentation` 周期下仍可达（窗口很窄，需高分且一致性惩罚较低）。  
因此更准确表述应为“**可达域极窄**”，而非“实质死代码”。

### 4) P0-R6-02 影响收敛（实现相关推断）

“排名 21-26 会导致运行时异常”属于实现层推断。  
当前仓库尚无 Integration 落地代码，能确认的是**配置映射覆盖不完整**；是否抛异常取决于实现默认分支与兜底策略。

### 5) P1-R6-06 结论修正（跨文档口径差异，不是幽灵字段）

`yesterday_limit_up_today_avg_pct` 与 `flat_count` 在 `src/data/models/snapshots.py` 存在；  
它们在 `docs/design/data-layer/data-layer-data-models.md` 也有定义。  
问题实质是：**Core 算法 data-models 与 Data Layer data-models 的口径分布不统一**，不应表述为“无规范支撑的幽灵字段”。

### 6) P1-R6-09 量级结论加前提

`bull_gene_raw` 的量级失衡风险成立，但“~375 倍”取决于 `max_pct_chg_history` 的单位口径（5 vs 0.05）。  
更稳妥表达应为：**若使用百分数口径（如 15 表示 15%），将显著放大该子项影响**；需在文档中显式统一单位。

### 7) P2-R6-12 状态更新（已修复）

`integration-data-models.md` 已升级到 **v3.4.3（2026-02-07）**，并补齐  
`WeightPlan` / `ValidationGateDecision` 及 `validation_gate`/`weight_plan_id` 追溯字段；  
与 `integration-algorithm/integration-information-flow` 的 v3.4.x 口径已对齐。

### 8) 复查后有效问题计数（当前基线）

- R6 新发现：由 14 项修正为 **13 项有效问题**（撤回 P2-R6-11）。
- 其余条目保持有效，但以上 4 条已做表述收敛。

*报告结束*
