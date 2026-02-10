# EmotionQuant 第十四轮审查报告

**审查者**: Claude (Warp Agent Mode)
**日期**: 2026-02-08
**审查范围**: 跨文档数据契约一致性、调度管线完整性、信息流准确性
**HEAD**: `a628f30` (develop)
**状态**: 🟢 已闭环（Codex 复核）

---

## 审查角度

本轮以 **数据契约（DDL/DataModel/Algorithm 三方对照）** 为主线，辅以 **调度管线完整性** 和 **信息流文档准确性**：
- Data Layer DDL（algorithm.md）vs Data Layer DataModel（data-models.md）vs 上游算法规范的三方对照
- 日级调度流程是否覆盖全部必需步骤（含 Validation Gate）
- Information-flow 文档描述的跨模块交互是否在对应 algorithm.md 中有对等实现
- Analysis 层归因公式的语义准确性

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

- 复核基线：`develop` @ `a628f30`。
- 复核结论：R14 列出的 10 项问题已全部完成修复（10/10）。
- 关键闭环：
  - Data Layer 三方契约：行业估值聚合统一为过滤 + Winsorize + median；`integrated_recommendation` DDL 已补 `weight_plan_id/validation_gate`；
  - Data Layer 调度：日级管线补齐 `stock_gene_cache` 与 Validation Gate 步骤（Integration 前置）；
  - 跨模块职责：IRS/PAS 信息流中 MSS 温度交互改为 Integration 层消费，移除误导性“IRS/PAS直接使用”表述；
  - 字段一致性：`trade_records.order_type` 统一 `auction/market/limit/stop`；`integrated_recommendation.stock_code` 统一 `VARCHAR(20)`；
  - Analysis 归因语义：`pnl_pct` 更名为 `execution_deviation`，明确为执行偏差而非交易盈亏。

---

## P1 — 重要

### ~~P1-R14-01 · Data Layer §3.2 行业估值聚合使用 mean() 而非 median()~~

| 项目 | 内容 |
|------|------|
| 文件 | `data-layer-algorithm.md` §3.2 (L230) vs `data-layer-data-models.md` §3.2 (L252, L266) vs `irs-algorithm.md` §3.4 (L175-192) |
| 现状 | 算法伪代码：`industry_pe_ttm=industry_daily_basic['pe_ttm'].mean()`。数据模型注释："先过滤 pe_ttm <= 0，再做 1%-99% Winsorize，最后取行业中位数"。IRS 算法 §3.4："industry_pe_ttm = median(pe_ttm_winsorized)"。 |
| 问题 | 伪代码使用 `mean()` 且无 Winsorize/过滤步骤，与数据模型注释和 IRS 算法口径三方矛盾。`mean` 受极端值影响大（A 股常有 PE>1000 的个股），实现者若按伪代码编写将产出错误估值。 |
| 建议 | §3.2 伪代码替换为：`valid = pe_ttm[(pe_ttm > 0) & (pe_ttm <= 1000)]`；`winsorized = valid.clip(lower=q01, upper=q99)`；`industry_pe_ttm = winsorized.median()`。同理 `industry_pb`。 |

### ~~P1-R14-02 · Data Layer trade_records DDL 枚举未随 R12 统一：`auction_open` → `auction`~~

| 项目 | 内容 |
|------|------|
| 文件 | `data-layer-data-models.md` §7.1 (L537) vs `trading-data-models.md` §1.2 (L78) |
| 现状 | Data Layer: `order_type VARCHAR(20) — auction_open/market/limit/stop`。Trading: `order_type: 枚举值 auction | market | limit | stop`。 |
| 问题 | R12（P2-R12-07）已将 Trading 和 Backtest 的 OrderType 统一为 `auction`，但 Data Layer 的 trade_records 表注释仍写 `auction_open`。若数据写入与查询用不同枚举值，将导致 JOIN/WHERE 不匹配。 |
| 建议 | `data-layer-data-models.md` §7.1 `order_type` 注释改为 `auction/market/limit/stop`，与 Trading/Backtest 统一。 |

### ~~P1-R14-03 · Data Layer 日级调度缺少 Validation Gate 步骤~~

| 项目 | 内容 |
|------|------|
| 文件 | `data-layer-algorithm.md` §7.1-7.2 (L494-533) vs `factor-weight-validation-algorithm.md` §2.1 |
| 现状 | 调度流程：fetch → snapshot → MSS/IRS/PAS → Integration。Validation 算法 §2.1："时点：T 日收盘后，Integration 前"。 |
| 问题 | 调度器 `DailyPipelineScheduler.run()` 在 `run_pas()` 与 `run_integration()` 之间没有 `run_validation_gate()` 步骤。Integration 的 `resolve_gate_and_weights()` 需要 `ValidationGateDecision` 作为输入（R13 修复），但调度流程未产出该输入。 |
| 建议 | 在 §7.1 时间表 17:00-17:20 算法输出后、17:20 集成前，插入 "17:15-17:20 Validation Gate" 步骤。`run()` 方法在 `run_pas()` 后补增 `self.executor.run_validation_gate(trade_date)`。 |

### ~~P1-R14-04 · MSS/IRS/PAS 信息流描述的跨模块交互在算法文档中不存在~~

| 项目 | 内容 |
|------|------|
| 文件 | `irs-information-flow.md` §5.1 (L346-348)；`pas-information-flow.md` §5.1 (L353-356) |
| 现状 | IRS 信息流 §5.1："当 temperature > 70（过热），IRS 偏向防御行业；当 temperature < 30（冰点），IRS 偏向进攻行业"。PAS 信息流 §5.1："temperature < 30：S/A 级信号强度与仓位建议下调；temperature > 80：下调"。 |
| 问题 | IRS 算法 §3-§6 **无任何 temperature 输入和防御/进攻偏向逻辑**。PAS 算法同样无 temperature 驱动的下调。这些调整仅在 Integration §5.3 协同约束中执行。信息流文档将 Integration 的职责错误归属给 IRS/PAS 自身，会误导实现者在 IRS/PAS 内部添加不必要的 MSS 依赖。 |
| 建议 | IRS 信息流 §5.1 改为："MSS → Integration（非 IRS 直接消费）：Integration 使用 temperature 做仓位缩放和 pas_score 折扣"。PAS 信息流 §5.1 同理，明确 temperature 调整发生在 Integration 层，非 PAS 层。 |

### ~~P1-R14-05 · Data Layer DDL `integrated_recommendation` 缺少 `weight_plan_id` / `validation_gate` 列~~

| 项目 | 内容 |
|------|------|
| 文件 | `data-layer-algorithm.md` §4.4 (L384-415) vs `data-layer-data-models.md` §4.4 (L409-411) |
| 现状 | Data Layer 数据模型表正确包含 `weight_plan_id VARCHAR(40)` 和 `validation_gate VARCHAR(10)`。但 Data Layer 算法文档的 DDL（§4.4 CREATE TABLE）缺少这两列。 |
| 问题 | DDL 是开发者建表的直接参考。缺失列将导致 Integration 写入 `weight_plan_id` 和 `validation_gate` 时报列不存在。R13 修复已在 Integration 算法中增加了 Gate 输入与权重选择，但 Data Layer DDL 未同步。 |
| 建议 | §4.4 DDL 补增 `weight_plan_id VARCHAR(40) COMMENT '权重方案ID'` 和 `validation_gate VARCHAR(10) COMMENT '验证门禁 PASS/WARN/FAIL'`，与数据模型表对齐。 |

---

## P2 — 次要

### ~~P2-R14-06 · Analysis §4.1 归因公式 `pnl_pct` 计算的是执行偏差而非交易盈亏~~

| 项目 | 内容 |
|------|------|
| 文件 | `analysis-algorithm.md` §4.1 (L185-192) |
| 现状 | `pnl_pct = (exec_price - rec.entry) / rec.entry`。注释："加权贡献度 = 信号评分 × 实际盈亏"。 |
| 问题 | `exec_price` 是 **成交价**，`rec.entry` 是 **建议入场价**。两者之差是"执行滑点/偏差"，而非"交易盈亏"。真正的 PnL 需要 exit_price（平仓价）。变量命名和注释均误导。 |
| 建议 | 若目的是"信号执行质量归因"，将变量改名为 `execution_deviation` 并修正注释。若目的是"交易盈亏归因"，需引入 exit_price 字段计算真实 PnL。 |

### ~~P2-R14-07 · Data Layer DDL `stock_pas_daily` 缺少 `id` 自增主键列~~

| 项目 | 内容 |
|------|------|
| 文件 | `data-layer-algorithm.md` §4.3 (L361-378) vs `data-layer-data-models.md` §4.3 (L372) |
| 现状 | 数据模型表含 `id | INTEGER | 主键ID`，但算法 DDL 用 `PRIMARY KEY (trade_date, stock_code)` 且无 `id` 列。 |
| 问题 | 同表 mss_panorama、irs_industry_daily、integrated_recommendation 的 DDL 均有 `id INTEGER PRIMARY KEY`。stock_pas_daily 缺失 `id` 属于漏写。 |
| 建议 | 算法 DDL 补增 `id INTEGER PRIMARY KEY` 并将复合主键改为 `UNIQUE KEY`。 |

### ~~P2-R14-08 · Data Layer 日级调度缺少 `stock_gene_cache` 更新步骤~~

| 项目 | 内容 |
|------|------|
| 文件 | `data-layer-algorithm.md` §7.1-7.2 (L494-533) vs §3.3 (L249-282) |
| 现状 | §3.3 标注 stock_gene_cache "更新频率：每日增量更新"。但 §7.1 调度时间表和 §7.2 `run()` 方法均无 `process_stock_gene_cache()` 步骤。 |
| 问题 | PAS 因子计算依赖 stock_gene_cache 提供 `limit_up_count_120d`、`new_high_count_60d` 等字段。若缓存不更新，PAS 将使用陈旧数据。 |
| 建议 | §7.1 在 "16:30-17:00 快照聚合" 中增加 `stock_gene_cache` 增量更新；§7.2 `run()` 在 snapshot 聚合后补增 `self.processor.process_stock_gene_cache(trade_date)`。 |

### ~~P2-R14-09 · Data Layer DDL `integrated_recommendation.stock_code` 类型宽度不一致~~

| 项目 | 内容 |
|------|------|
| 文件 | `data-layer-algorithm.md` §4.4 (L388) vs `data-layer-data-models.md` §4.4 (L401) |
| 现状 | 算法 DDL: `stock_code VARCHAR(10)`。数据模型表: `stock_code VARCHAR(20)`。 |
| 问题 | TuShare 的 `ts_code` 格式为 `000001.SZ`（9 字符）。VARCHAR(10) 仅勉强容纳且无余量；其他表（raw_daily、stock_pas_daily 等）均使用 VARCHAR(20)。 |
| 建议 | 算法 DDL 统一为 `VARCHAR(20)`，与数据模型和其他表一致。 |

### ~~P2-R14-10 · Data Layer §3.1 `flat_count` 阈值 0.5% 硬编码无配置参数~~

| 项目 | 内容 |
|------|------|
| 文件 | `data-layer-algorithm.md` §3.1 (L180)；`data-layer-data-models.md` §3.1 (L212) |
| 现状 | `flat_count = len(daily[daily['pct_chg'].abs() <= 0.5])`。阈值 0.5% 直接写在伪代码中。 |
| 问题 | 其他类似阈值（如 strong_up 的 5%、MSS 的 `strong_move_threshold`）均有配置参数和可调范围。flat_count 的 0.5% 无对应参数定义，且 data-models 注释也未记录该阈值。 |
| 建议 | 在 Data Layer 配置参数中增加 `flat_threshold: float = 0.5`（单位 %），并在伪代码和数据模型注释中引用该参数。 |

---

## 审查方法

1. Data Layer DDL（algorithm.md）← 逐列对照 → Data Layer DataModel（data-models.md）← 逐字段对照 → 上游算法规范
2. 比较 algorithm.md 伪代码中的聚合函数/过滤逻辑与数据模型注释中的口径说明
3. 审查调度管线 `DailyPipelineScheduler` 是否覆盖 Validation Gate 与所有 L2 更新步骤
4. 追踪 information-flow.md §5 描述的跨模块交互，在目标 algorithm.md 中确认对等实现
5. 检查 R12/R13 修复是否已完整传播到 Data Layer 文档

---

*R14 完成（已闭环）。累计 R1-R14 共发现 129 个问题，当前 OPEN = 0。*
