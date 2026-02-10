# EmotionQuant 第十五轮深度审查报告

**审查人**: Claude  
**日期**: 2026-02-08  
**基线**: develop @ `2b987fb`  
**审查角度**: GUI ↔ Backtest ↔ Analysis ↔ DataLayer ↔ Config 跨模块 DDL/数据模型/枚举 三方对照  
**累计问题**: R1–R14 = 129 已修复；R15 共 10 项已闭环（10/10）
**复查结论**: ✅ 本轮 10 项问题均已完成修复与文档同步

---

## 严重度说明

| 级别 | 含义 |
|------|------|
| P1 | 跨层 DDL/主键/字段缺失——运行时写入/读取必崩或数据丢失 |
| P2 | 类型引用未定义、配置缺失、精度不一致——可编译但行为不符预期 |

---

## ~~P1-R15-01  Data Layer `trade_records` DDL 缺 `industry_code` 列~~ ✅ 已修复

| 项 | 值 |
|---|---|
| 文件 | `docs/design/data-layer/data-layer-data-models.md` §7.1 |
| 对比 | `docs/design/trading/trading-data-models.md` §1.4 TradeRecord + §4.1 DDL |
| 严重度 | P1 |

**现状**：

- Trading 侧 `TradeRecord` 数据类有 `industry_code: str`，Trading DDL §4.1 也有 `industry_code | TEXT`。
- Data Layer 权威 DDL §7.1 `trade_records` 表 **无 `industry_code` 列**。
- 写入时字段无对应列 → INSERT 失败或字段静默丢失。

**修复方案**：

在 `data-layer-data-models.md` §7.1 `trade_records` 表中，`stock_name` 之后加入：

```
| industry_code | VARCHAR(10) | 行业代码 |
```

---

## ~~P1-R15-02  Data Layer `backtest_trade_records` DDL 缺 `integration_mode` + `recommendation`~~ ✅ 已修复

| 项 | 值 |
|---|---|
| 文件 | `docs/design/data-layer/data-layer-data-models.md` §7.4 |
| 对比 | `docs/design/backtest/backtest-data-models.md` §2.1 |
| 严重度 | P1 |

**现状**：

- Backtest DDL §2.1 有 `integration_mode VARCHAR(20)` 和 `recommendation VARCHAR(20)`。
- Data Layer §7.4 `backtest_trade_records` 缺这两列。
- 回测模式与推荐等级无法持久化 → 溯源断链。

**修复方案**：

在 `data-layer-data-models.md` §7.4 `signal_source` 之后加入：

```
| integration_mode | VARCHAR(20) | 集成模式 top_down/bottom_up/dual_verify/complementary |
| recommendation | VARCHAR(20) | 推荐等级 STRONG_BUY/BUY/HOLD/SELL/AVOID |
```

---

## ~~P1-R15-03  Trading `positions` DDL 主键策略与 Data Layer 不一致~~ ✅ 已修复

| 项 | 值 |
|---|---|
| 文件 | `docs/design/trading/trading-data-models.md` §4.2 |
| 对比 | `docs/design/data-layer/data-layer-data-models.md` §7.2 |
| 严重度 | P1 |

**现状**：

- Data Layer §7.2（权威）：`id INTEGER PK`（自增） + `stock_code UNIQUE` + 有 `created_at`。
- Trading §4.2：`stock_code TEXT PK`（无 `id`，无 `created_at`）。
- 同一张业务表 `positions`，两套 DDL 的主键设计冲突；实现时如按 Trading DDL 建表，后续 Data Layer 侧查询 `WHERE id = ?` 即失败。

**修复方案**：

Trading §4.2 对齐 Data Layer：

1. 首行改为 `| id | INTEGER | 自增主键 |`。
2. `stock_code` 由 `TEXT PK` 改为 `TEXT UNIQUE`。
3. 末尾加 `| created_at | TEXT | 创建时间 |`。

---

## ~~P1-R15-04  Analysis `PerformanceMetrics` + DDL 缺 `volatility` 字段~~ ✅ 已修复

| 项 | 值 |
|---|---|
| 文件 | `docs/design/analysis/analysis-data-models.md` §1.1 + §3.2 |
| 对比 | `docs/design/analysis/analysis-algorithm.md` §2.2；`docs/design/backtest/backtest-data-models.md` §1.6 |
| 严重度 | P1 |

**现状**：

- Analysis 算法 §2.2 计算 `volatility = std(r_t) × sqrt(252)` 并使用。
- Backtest `BacktestMetrics` §1.6 有 `volatility: float` 字段。
- 但 Analysis 自己的 `PerformanceMetrics` 数据类和 DDL `performance_metrics` 表 **都没有 `volatility` 字段**。
- 指标算了却无处存储；GUI 的 `PerformanceMetricsDisplay` 也无法映射。

**修复方案**：

1. `PerformanceMetrics` 数据类：`max_drawdown` 之后加 `volatility: float  # 年化波动率`。
2. DDL `performance_metrics`：`max_drawdown` 之后加 `| volatility | DECIMAL(10,4) | 年化波动率 |`。

---

## ~~P2-R15-05  GUI `BacktestSummaryDisplay` 类型引用未定义~~ ✅ 已修复

| 项 | 值 |
|---|---|
| 文件 | `docs/design/gui/gui-data-models.md` §1.8 |
| 严重度 | P2 |

**现状**：

```python
class AnalysisPageData:
    ...
    backtest_summary: BacktestSummaryDisplay
```

`BacktestSummaryDisplay` 在 GUI 文档全文无定义。实现时无法确定其字段。

**修复方案**：

在 §1.8 `PerformanceMetricsDisplay` 之后定义：

```python
@dataclass
class BacktestSummaryDisplay:
    """回测结果摘要展示"""
    backtest_name: str
    start_date: str
    end_date: str
    total_return_pct: str       # "+15.2%"
    annual_return_pct: str
    max_drawdown_pct: str       # "-8.5%"
    sharpe_ratio: float
    total_trades: int
    win_rate_pct: str           # "65.3%"
```

---

## ~~P2-R15-06  Config.py 缺少 Trading 侧所有可配置参数~~ ✅ 已修复

| 项 | 值 |
|---|---|
| 文件 | `src/config/config.py` |
| 对比 | `docs/design/trading/trading-data-models.md` §2.1 TradeConfig + §2.2 RiskConfig |
| 严重度 | P2 |

**现状**：

Config.py 仅有 `backtest_*` 前缀参数。Trading 算法依赖以下参数但均无集中配置入口：

- `max_industry_rank`（默认 5）
- `min_irs_score`（默认 50）
- `min_pas_score`（默认 60）
- `top_n`（默认 20）
- `stop_loss_pct`（默认 0.08）
- `take_profit_pct`（默认 0.15）
- `max_position_ratio`（默认 0.20）
- `max_industry_ratio`（默认 0.30）
- `max_total_position`（默认 0.80）

**修复方案**：

在 Config 类中增加 `trading_*` 前缀参数组，与 `backtest_*` 并列；同步 `from_env()` / dataclass fallback 分支读取对应环境变量。

---

## ~~P2-R15-07  Backtest DDL `transfer_fee` 精度 DECIMAL(12,2) 与 Data Layer DECIMAL(12,4) 不一致~~ ✅ 已修复

| 项 | 值 |
|---|---|
| 文件 | `docs/design/backtest/backtest-data-models.md` §2.1 |
| 对比 | `docs/design/data-layer/data-layer-data-models.md` §7.4 |
| 严重度 | P2 |

**现状**：

- Backtest DDL §2.1：`transfer_fee | DECIMAL(12,2)`。
- Data Layer §7.4 同名字段：`transfer_fee | DECIMAL(12,4)`。
- 过户费率 = 0.00002，小额交易（如 1 万元）过户费 = 0.2000 元；(12,2) 会截断为 0.20，丢失后两位有效数字。

**修复方案**：

Backtest §2.1 将 `transfer_fee DECIMAL(12,2)` 改为 `DECIMAL(12,4)`，与 Data Layer 保持一致。

---

## ~~P2-R15-08  Backtest `BacktestResult` 数据类主键 `backtest_id: str` 与 DDL `id: INTEGER` 类型/命名冲突~~ ✅ 已修复

| 项 | 值 |
|---|---|
| 文件 | `docs/design/backtest/backtest-data-models.md` §1.7 vs §2.3 |
| 严重度 | P2 |

**现状**：

- 数据类 §1.7：`backtest_id: str`（字符串标识）。
- DDL §2.3 `backtest_results`：`id | INTEGER | 自增主键`（整型自增，且无 `backtest_id` 列）。
- 字段名不同（`backtest_id` vs `id`）、类型不同（str vs INTEGER）。
- ORM 映射时要么找不到列，要么类型转换失败。

**修复方案**（二选一）：

- **方案 A**（推荐）：DDL 加列 `backtest_id VARCHAR(50) UNIQUE`，`id` 保留为自增代理键；数据类中增加 `id: int`（标注 DB 自动生成）。
- **方案 B**：数据类改为 `id: int`，放弃字符串业务 ID。

---

## ~~P2-R15-09  GUI `PositionDisplay.pnl_color` 使用西方色彩惯例，与 A 股用户预期相反~~ ✅ 已修复

| 项 | 值 |
|---|---|
| 文件 | `docs/design/gui/gui-data-models.md` §1.7 |
| 严重度 | P2 |

**现状**：

```python
class PositionDisplay:
    pnl_color: str  # green (盈) / red (亏)
```

中国 A 股惯例：红色 = 涨/盈利，绿色 = 跌/亏损。GUI 在同一文件中，`TradeRecordDisplay.direction_color` 已遵循中国惯例（`red` = 买入，`green` = 卖出），但 `pnl_color` 反用了西方惯例。同一产品两套色彩语义会造成认知混乱。

**修复方案**：

统一为 A 股惯例：

```python
pnl_color: str  # red (盈) / green (亏)
```

同时在 GUI 算法文档中补充"色彩惯例约定：遵循 A 股红涨绿跌"。

---

## ~~P2-R15-10  GUI 温度图表 zone 边界值重叠，缺乏 inclusive/exclusive 约定~~ ✅ 已修复

| 项 | 值 |
|---|---|
| 文件 | `docs/design/gui/gui-algorithm.md` §7.1 |
| 严重度 | P2 |

**现状**：

```python
"zones": [
    {"min": 0, "max": 30, "color": "blue"},
    {"min": 30, "max": 45, "color": "cyan"},
    {"min": 45, "max": 80, "color": "orange"},
    {"min": 80, "max": 100, "color": "red"}
]
```

边界值 30/45/80 同时出现在相邻两个 zone 的 min/max 中。图表库在渲染时行为未定义（同一点可能被两个 zone 着色）。虽然 §2.1 的 if/elif 逻辑无歧义，但图表 zone 数据结构本身是独立传给前端的，没有附带 inclusive/exclusive 规则。

**修复方案**：

采用左闭右开 `[min, max)` 约定，最高 zone 右闭：

```python
"zones": [
    {"min": 0, "max": 30, "color": "blue"},       # [0, 30)
    {"min": 30, "max": 45, "color": "cyan"},       # [30, 45)
    {"min": 45, "max": 80, "color": "orange"},     # [45, 80]
    {"min": 80, "max": 100, "color": "red"}        # (80, 100]
]
```

并在 §7 首段补充约定："zone 边界遵循左闭右开 `[min, max)` 原则，最高 zone 使用 `(80, 100]`；与 §2.1 的 `>80` 阈值一致。"

---

## 汇总

| ID | 严重度 | 模块 | 一句话 |
|---|---|---|---|
| P1-R15-01 | P1 | DataLayer ↔ Trading | `trade_records` DDL 缺 `industry_code` |
| P1-R15-02 | P1 | DataLayer ↔ Backtest | `backtest_trade_records` DDL 缺 `integration_mode` + `recommendation` |
| P1-R15-03 | P1 | Trading ↔ DataLayer | `positions` 表主键策略冲突（`stock_code PK` vs `id PK + stock_code UNIQUE`） |
| P1-R15-04 | P1 | Analysis | `PerformanceMetrics` + DDL 缺 `volatility` |
| P2-R15-05 | P2 | GUI | `BacktestSummaryDisplay` 引用未定义 |
| P2-R15-06 | P2 | Config | Config.py 缺全部 Trading 侧可配参数 |
| P2-R15-07 | P2 | Backtest ↔ DataLayer | `transfer_fee` 精度 (12,2) vs (12,4) |
| P2-R15-08 | P2 | Backtest | `BacktestResult.backtest_id: str` vs DDL `id: INTEGER` |
| P2-R15-09 | P2 | GUI | `pnl_color` 西方色彩惯例与 A 股红涨绿跌矛盾 |
| P2-R15-10 | P2 | GUI | 温度 zone 边界值重叠，缺 inclusive/exclusive 约定 |

---

## 复查纠偏记录（2026-02-08）

- ~~P1-R15-01~~：已在 `data-layer-data-models.md` 的 `trade_records` 补齐 `industry_code`。
- ~~P1-R15-02~~：已在 `data-layer-data-models.md` 的 `backtest_trade_records` 补齐 `integration_mode/recommendation`。
- ~~P1-R15-03~~：已将 Trading `positions` DDL 对齐为 `id` 主键 + `stock_code UNIQUE`。
- ~~P1-R15-04~~：已在 Analysis 数据类与 DDL 同步增加 `volatility`。
- ~~P2-R15-05~~：已新增 `BacktestSummaryDisplay` 数据结构定义。
- ~~P2-R15-06~~：已在 `src/config/config.py` 增加完整 `trading_*` 参数组及 env 读取。
- ~~P2-R15-07~~：已将 Backtest `transfer_fee` 精度统一为 `DECIMAL(12,4)`。
- ~~P2-R15-08~~：已统一为 `id` 代理主键 + `backtest_id` 业务唯一键双键模型。
- ~~P2-R15-09~~：已统一 GUI 盈亏颜色为 A 股约定（红盈绿亏）。
- ~~P2-R15-10~~：已补充 zone 边界契约并加入 `include_min/include_max` 消除边界重叠歧义。
