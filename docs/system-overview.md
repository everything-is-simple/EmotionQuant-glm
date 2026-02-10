# EmotionQuant 系统总览（Spiral 实现版）

**版本**: v4.1.2
**最后更新**: 2026-02-09
**状态**: 实现前最终架构基线（文档）

---

## 1. 系统定位

EmotionQuant 是面向中国 A 股的情绪驱动量化系统。自 2026-02-07 起，执行模型从线性 Phase 切换为 Spiral 闭环：

- 每 7 天一圈（默认）
- 每圈必须有命令、测试、产物、复盘、同步
- 文档服务实现，不再作为线性阻塞关卡

---

## 2. 核心原则（实现口径）

1. 情绪优先：情绪因子是主信号来源。
2. 单指标不得独立决策：技术指标可用于对照实验或辅助特征工程，但必须与情绪因子联合验证，且不得单独触发交易。
3. 本地数据优先：主流程以本地数据为准，远端只用于补采。
4. 禁止路径/密钥硬编码。
5. A 股规则刚性执行（T+1、涨跌停、交易时段）。
6. Spiral 闭环强制：缺任一闭环证据不得收口。

---

## 3. 架构分层（八层）

| 层 | 职责 | 关键输出 |
|---|---|---|
| Data Layer | 原始数据采集与清洗 | L1/L2 数据集 |
| Signal Layer | MSS/IRS/PAS 计算 | 单系统分数 |
| Validation Layer | 因子验证 + 权重验证（新） | 验证报告 + Gate 决策 |
| Integration Layer | 信号集成与推荐生成 | `integrated_recommendation` |
| Backtest Layer | 可复现回测与敏感性分析 | 回测结果 |
| Trading Layer | 纸上交易/风控执行 | 订单与持仓日志 |
| Analysis Layer | 绩效归因与日报 | 归因与报告 |
| GUI Layer | 可视化展示与导出 | Dashboard + 导出文件 |

> 关键新增：Validation Layer 是独立模块，不再散落在算法/回测说明中。

---

## 4. 数据架构（简化口径）

- 存储策略：`Parquet + DuckDB 单库优先`
- 默认数据库：`DUCKDB_DIR/emotionquant.duckdb`
- 分库策略：仅在明确性能阈值触发后启用（需 ADR + 基准测试）

### 4.1 分层

- L1：原始数据（raw_*）
- L2：特征与快照（market_snapshot / industry_snapshot / stock_gene_cache）
- L3：算法输出与集成推荐
  - 含 Validation 输出：`validation_gate_decision`、`validation_weight_plan`
- L4：分析产物（报告/指标）

---

## 5. 回测引擎选型策略（更新）

采用“平台主选 + 接口可替换”：

- 主选研究平台：`Qlib`（社区活跃、近年持续更新、因子研究能力完整）
- 执行口径基线：本地向量化回测器（对齐 A 股规则与快速迭代）
- 兼容适配：`backtrader` 保留为兼容选项，不作为主选
- 切换条件：因子研究与快速验证阶段优先 `Qlib`；生产决策与口径对齐阶段使用本地向量化回测器；`backtrader` 仅用于兼容回放

详见：`docs/design/backtest/backtest-engine-selection.md`

---

## 6. GUI 技术口径（更新）

- 主线组合：`Streamlit + Plotly`
- `Altair` 已转为可选依赖，待现有 Altair 图表完成 Plotly 迁移后移除

---

## 7. Spiral 周期可行性说明

“7 天一圈”可行，但前提是圈目标足够小：

- 每圈只允许 1 个主目标
- 每圈只切 1-3 个能力包切片
- 无法闭环时必须拆分为更小圈，不得硬收口

补充口径：

- 路线术语统一使用 `Capability Pack (CP)`。
- `ROADMAP-PHASE-*.md` 仅为兼容文件名，不代表线性阶段闸门。

---

## 8. 文档导航

- 模块索引：`docs/module-index.md`
- 路线总览：`Governance/ROADMAP/ROADMAP-OVERVIEW.md`
- 能力包（CP）：`Governance/ROADMAP/ROADMAP-PHASE-*.md`
- 因子/权重验证设计：`docs/design/validation/`
- 回测选型：`docs/design/backtest/backtest-engine-selection.md`

---

## 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v4.1.2 | 2026-02-09 | 修复 R29：明确技术指标边界与铁律一致（可对照/辅助特征但不得独立决策）；L3 分层补充 Validation 运行时输出 |
| v4.1.1 | 2026-02-09 | 修复 R25：L2 分层补充 `stock_gene_cache`；明确回测引擎切换条件；补充 Altair 移除前置条件 |
| v4.1.0 | 2026-02-07 | 明确回测平台主选 Qlib；补充本地执行基线与兼容口径 |
| v4.0.0 | 2026-02-07 | 切换到 Spiral 实现口径；新增 Validation Layer；更新回测与存储策略 |
| v3.3.0 | 2026-02-05 | 线性重构版 |
