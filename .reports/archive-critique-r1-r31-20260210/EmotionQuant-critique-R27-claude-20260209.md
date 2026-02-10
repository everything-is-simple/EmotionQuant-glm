# EmotionQuant 设计文档批判性审查报告 — R27

**审查轮次**: R27（API 跨模块一致性 & 信息流对齐）
**审查日期**: 2026-02-09
**审查范围**: 全部 API 文档与对应 data-models / algorithm / information-flow 的交叉一致性
**累计进度**: R1-R26 共 249 项已修复，R27 新增 10 项

---

## 审查方法

本轮聚焦于：
1. **API 接口 ↔ data-models 类型/字段一致性**：API 方法签名中的类型名、参数、返回值是否与 data-models 中的 dataclass 定义一致
2. **API 文档 ↔ algorithm 文档 R26 更新同步**：R26 新增的 quality_flag / unknown cycle / Gate FAIL 等变更是否已传播到 API 文档
3. **跨模块参数与类型名统一性**：同一类型在不同模块 API 中是否使用一致的名称和语义
4. **API 版本日期与关联文档的同步性**：API 文档更新是否滞后于 data-models 和 algorithm 文档

---

## P1 问题（5 项）

### P1-R27-01: BacktestConfig 费率结构 API vs data-models 不一致

**文件**:
- `docs/design/backtest/backtest-api.md` §2.1（第 154-187 行）
- `docs/design/backtest/backtest-data-models.md` §1.1（第 20-60 行）

**问题**:
- `backtest-api.md` 中 BacktestConfig 使用**扁平字段**：
  ```
  commission_rate: float = 0.0003
  stamp_duty_rate: float = 0.001
  transfer_fee_rate: float = 0.00002
  min_commission: float = 5.0
  ```
- `backtest-data-models.md` 中 BacktestConfig 使用**嵌套 AShareFeeConfig**：
  ```
  fee_config: AShareFeeConfig = field(default_factory=AShareFeeConfig)
  ```
- 同一个 `BacktestConfig` 在两个文档中结构不同，实现时必然冲突。

**修复建议**: `backtest-api.md` §2.1 BacktestConfig 的交易与成本部分改为使用 `fee_config: AShareFeeConfig`，与 data-models 对齐。移除 `commission_rate` / `stamp_duty_rate` / `transfer_fee_rate` / `min_commission` 四个扁平字段。

---

### P1-R27-02: `StockPAS` 类型名与规范 `StockPasDaily` 不匹配

**文件**:
- `docs/design/trading/trading-api.md` §8.2（第 646 行）`pas: StockPAS`
- `docs/design/analysis/analysis-api.md` §6.3（第 451 行）`pas_data: List[StockPAS]`
- `docs/design/core-algorithms/pas/pas-data-models.md` §3.1（第 102 行）`class StockPasDaily`
- `docs/design/core-algorithms/pas/pas-api.md` 全文使用 `StockPasDaily`

**问题**:
- PAS 数据模型中的规范类名为 `StockPasDaily`
- 但 trading-api.md 和 analysis-api.md 中使用了 `StockPAS`（不存在的类名）
- PAS API 自身（pas-api.md）使用的是正确的 `StockPasDaily`

**修复建议**:
- `trading-api.md` §8.2 `validate_signal` 参数 `pas: StockPAS` → `pas: StockPasDaily`
- `analysis-api.md` §6.3 `build_score_distribution` 参数 `pas_data: List[StockPAS]` → `pas_data: List[StockPasDaily]`

---

### P1-R27-03: IRS API 未文档化 quality_flag / sample_days 处理

**文件**:
- `docs/design/core-algorithms/irs/irs-api.md` v3.2.1（最后更新 2026-02-05）
- `docs/design/core-algorithms/irs/irs-data-models.md` §3.1（第 115-116 行）已有 `quality_flag` / `sample_days`

**问题**:
- R26 为 IrsIndustryDaily 新增了 `quality_flag: str` 和 `sample_days: int` 字段
- 但 irs-api.md 未做任何更新：
  - `calculate()` 返回值文档未说明 quality_flag 含义
  - 错误处理 §3 未提及 cold_start 场景
  - 无按 quality_flag 查询的 Repository 方法
- 下游 Integration 依赖 quality_flag 做 Gate 检查，但 IRS API 合约缺失该信息

**修复建议**:
1. `irs-api.md` §2.1 `calculate()` 返回值说明中补充：quality_flag 字段含义（normal/cold_start/stale）及 sample_days 取值规则
2. §3 错误处理增加：当 `sample_days < 最低阈值` 时输出 `quality_flag="cold_start"`
3. §2.2 IrsRepository 可选增加 `get_cold_start_industries(trade_date)` 方法

---

### P1-R27-04: MSS API get_cycle() 缺少 "unknown" 返回值文档

**文件**:
- `docs/design/core-algorithms/mss/mss-api.md` v3.1.1（最后更新 2026-02-05）
- `docs/design/core-algorithms/mss/mss-data-models.md` §3.2（第 144 行）`UNKNOWN = "unknown"`

**问题**:
- R26 将 `UNKNOWN = "unknown"` 加入 MssCycle 枚举（当历史数据不足以识别周期时返回）
- mss-api.md §2.1 `get_cycle()` 文档未说明可能返回 `"unknown"`
- §3 错误处理未描述 unknown cycle 与 DataNotReadyError 的区别
- GUI format_cycle 已正确处理 unknown（gui-api.md §4.2），但 MSS API 合约本身缺失

**修复建议**:
1. `mss-api.md` §2.1 `get_cycle()` docstring 添加返回值说明：`"unknown" 表示历史数据不足以识别周期`
2. §3 错误处理增加：与 `DataNotReadyError` 区分 — unknown 不是错误，而是合法的降级输出

---

### P1-R27-05: Integration API 未文档化 IRS quality_flag 对集成流程的影响

**文件**:
- `docs/design/core-algorithms/integration/integration-api.md` v3.4.2（最后更新 2026-02-08）
- `docs/design/core-algorithms/integration/integration-data-models.md` §2.2（第 57-58 行）IrsInput 含 quality_flag / sample_days
- `docs/design/core-algorithms/integration/integration-algorithm.md`（R26 已补充 cold_start Gate 逻辑）

**问题**:
- integration-algorithm.md 已在 R26 增加：当 IRS quality_flag="cold_start" 且 sample_days < 阈值时触发 Gate 警告
- 但 integration-api.md §2.1 `calculate()` 文档：
  - 参数说明未提及 quality_flag 对融合的影响
  - 错误处理 §3 未说明 cold_start IRS 输入的行为
  - `ValidationGateError` 的触发条件未含 quality_flag

**修复建议**:
1. `integration-api.md` §2.1 `calculate()` 参数说明：`irs_inputs` 描述中增加"当行业 quality_flag=cold_start 时，该行业评分可信度降低，Gate 可触发 WARN"
2. §3 错误处理增加场景：`所有行业均为 cold_start → Gate WARN 并回退 baseline 权重`

---

## P2 问题（5 项）

### P2-R27-06: Data Layer standardize_ts_code 去后缀与系统其他模块使用含后缀代码冲突

**文件**:
- `docs/design/data-layer/data-layer-api.md` §4.1（第 212 行）`standardize_ts_code(df) # 000001.SZ → 000001`
- `docs/design/trading/trading-api.md` §11（第 774 行）示例 `stock_code="000001.SZ"`
- 各 data-models 中 `stock_code` 字段无统一格式约定

**问题**:
- Data Layer 的标准化函数显式将 `.SZ` 后缀去除（`000001.SZ → 000001`）
- 但 Trading API 示例中使用含后缀的代码 `"000001.SZ"`
- PAS/Integration data-models 中 stock_code 注释为"股票代码（L2+）"，未明确是否含交易所后缀
- 如果 L1 到 L2 环节去除了后缀，但 L3 到 Trading 又使用含后缀的代码，则存在格式断层

**修复建议**: 在 `docs/design/naming-conventions.md` 或 `data-layer-api.md` 中统一声明 `stock_code` 格式约定：要么全局使用 `000001.SZ`（保留后缀），要么全局使用 `000001`（去除后缀）。如果选择去除后缀，则 `trading-api.md` §11 示例需修正。

---

### P2-R27-07: Trading API SignalBuilder 未文档化 Gate FAIL 前置检查

**文件**:
- `docs/design/trading/trading-api.md` §10.1（第 714-743 行）`build_trade_signals()`
- `docs/design/trading/trading-algorithm.md`（R26 新增 Gate FAIL 检查，第 36-39 行）

**问题**:
- R26 为 trading-algorithm.md 新增了 Gate FAIL 前置检查（`validation_gate.final_gate == FAIL` 时阻断信号生成）
- 但 trading-api.md §10.1 `build_trade_signals()` 的 Processing 步骤中只有：
  1. MSS温度门控
  2. IRS行业筛选
  3. 获取集成推荐
  4. 评分过滤
  5. 构建TradeSignal
- 缺少 Gate FAIL 检查步骤

**修复建议**: `trading-api.md` §10.1 Processing 步骤中在"获取集成推荐"之前增加 `Gate FAIL 检查：读取 validation_gate_decision，若 final_gate=FAIL 则返回空列表`。

---

### P2-R27-08: backtest-api.md min_recommendation 缺少枚举引用与语义说明

**文件**:
- `docs/design/backtest/backtest-api.md` §2.1（第 167 行）`min_recommendation: str = "BUY"`
- `docs/design/core-algorithms/integration/integration-data-models.md` §3.2（第 186-192 行）Recommendation 枚举

**问题**:
- `min_recommendation: str = "BUY"` 注释 `# STRONG_BUY/BUY/HOLD`，但语义不明确：
  - 是"最低推荐等级"（即 BUY 及以上才纳入）？
  - 还是"只取该等级"？
- 未引用 `Recommendation` 枚举（定义在 integration-data-models.md），也未说明等级排序方向
- 注释只列了 3 个值（STRONG_BUY/BUY/HOLD），但枚举有 5 个值

**修复建议**: `min_recommendation` 注释改为：`# 最低推荐等级（仅纳入该等级及以上信号），引用 Recommendation 枚举（STRONG_BUY > BUY > HOLD > SELL > AVOID）`。

---

### P2-R27-09: Analysis API Visualizer 引用了 3 个未在 data-models 中定义的返回类型

**文件**:
- `docs/design/analysis/analysis-api.md` §6.1-6.3（第 411-461 行）
- `docs/design/analysis/analysis-data-models.md`（无对应类型定义）

**问题**:
- §6.1 `build_temperature_trend()` → `TemperatureTrendData`（未定义）
- §6.2 `build_industry_radar()` → `IndustryRadarData`（未定义）
- §6.3 `build_score_distribution()` → `ScoreDistributionData`（未定义）
- analysis-data-models.md 中不包含这三个可视化数据类型的定义

**修复建议**: 在 `analysis-data-models.md` 或 `gui-data-models.md` 中补充 `TemperatureTrendData` / `IndustryRadarData` / `ScoreDistributionData` 的 dataclass 定义（至少包含字段名和类型）。

---

### P2-R27-10: MSS/IRS API 版本日期显著滞后于对应 data-models / algorithm

**文件**:

| 文档 | 版本 | 最后更新 | 对应 data-models 版本 | data-models 最后更新 |
|------|------|----------|-----------------------|----------------------|
| mss-api.md | v3.1.1 | 2026-02-05 | v3.1.5 | 2026-02-08 |
| irs-api.md | v3.2.1 | 2026-02-05 | irs-data-models 含 quality_flag | 2026-02-09 |
| integration-api.md | v3.4.2 | 2026-02-08 | v3.4.8 | 2026-02-09 |

**问题**:
- MSS API 自 02-05 以来未更新，但 data-models 在 02-08 增加了 UNKNOWN cycle 枚举
- IRS API 自 02-05 以来未更新，但 data-models 在 R26 增加了 quality_flag / sample_days
- 这正是 P1-R27-03 / P1-R27-04 / P1-R27-05 问题的根本原因

**修复建议**: 每次修改 algorithm / data-models 时同步检查并更新对应 API 文档的版本号和内容。可在 A6 检查清单中增加"API 文档同步更新确认"项。

---

## 统计摘要

| 等级 | 数量 | 说明 |
|------|------|------|
| P1 | 5 | 类型不匹配、字段缺失、API 合约遗漏 |
| P2 | 5 | 格式约定、文档同步、枚举引用缺失 |
| **合计** | **10** | |

**累计**: R1-R27 共 259 项

---

## 下一轮建议

- R28 可聚焦于 **data-models 数据库 DDL 与 dataclass 一致性**（DDL 表结构是否覆盖 dataclass 全部字段、类型映射是否正确、索引是否充分）。
