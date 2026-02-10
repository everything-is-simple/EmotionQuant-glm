# EmotionQuant 设计文档深度审查 — 第 16 轮 (R16)

**审查日期**: 2026-02-08
**审查范围**: API 层规范 ↔ 算法文档 ↔ 数据模型 ↔ 信息流 交叉一致性
**审查基线**: develop branch HEAD `354b10e`
**发现数量**: 10（P1 ×4, P2 ×6）→ ✅ 本轮已闭环 10/10
**累计**: R1-R16 共 149 个问题（本轮全部修复完成）
**复查结论**: ✅ R16 所有问题均已完成纠偏并同步到对应文档

---

## 审查角度

本轮聚焦 **API 接口文档**与其关联的**算法文档、数据模型、信息流**之间的交叉一致性，重点检查：
- A 股色彩约定在 API 返回值中的落地情况
- API 参数/返回值枚举与数据模型字段的对齐
- API 签名与数据结构字段的完整性匹配
- 信息流示例与算法分段规则的一致性

---

## P1 级（必须修复 — 数据/逻辑不一致）

### ~~P1-R16-01: gui-api.md `format_pnl` 颜色违反 A 股惯例~~ ✅ 已修复

**位置**: `docs/design/gui/gui-api.md` (lines 385-388)
**问题**: `format_pnl` 返回值注释使用西方惯例（green=盈利, red=亏损），与 A 股惯例（red=盈利, green=亏损）相反。

**现状** (gui-api.md line 386-387):
```
- 盈利: ("+1,234.56", "green")
- 亏损: ("-1,234.56", "red")
```

**矛盾源**:
- `gui-data-models.md` line 167: `pnl_color: str  # red (盈) / green (亏)` — A 股惯例 ✅
- `gui-algorithm.md` line 21: `色彩约定：遵循 A 股红涨绿跌` ✅

**修复**: 将 format_pnl 返回值注释改为:
```
- 盈利: ("+1,234.56", "red")
- 亏损: ("-1,234.56", "green")
```

---

### ~~P1-R16-02: gui-api.md `format_trend` 颜色违反 A 股惯例~~ ✅ 已修复

**位置**: `docs/design/gui/gui-api.md` (lines 345-347)
**问题**: `format_trend` 返回值使用西方惯例（green=up, red=down），与 A 股惯例相反。

**现状**:
```
- up: ("↑", "green")
- down: ("↓", "red")
- sideways: ("→", "gray")
```

**矛盾源**: 同 P1-R16-01，gui-algorithm.md 明确声明"A 股红涨绿跌"。

**修复**:
```
- up: ("↑", "red")
- down: ("↓", "green")
- sideways: ("→", "gray")
```

---

### ~~P1-R16-03: gui-api.md `format_temperature` 颜色枚举缺 cyan，与数据模型/算法 4 色不一致~~ ✅ 已修复

**位置**: `docs/design/gui/gui-api.md` (line 306)
**问题**: `format_temperature` 返回值注释只列出 3 种颜色 `(red/orange/blue)`，遗漏 `cyan`。

**现状** (gui-api.md line 306):
```
color: 颜色 (red/orange/blue)
```

**矛盾源**:
- `gui-data-models.md` line 19: `temperature_color: str  # 颜色 (red/orange/cyan/blue)` — 4 色 ✅
- `gui-algorithm.md` §2.1 (lines 33-40): 4 段分级 — red(>80)/orange(45-80)/cyan(30-44)/blue(<30) ✅

**修复**: 改为 `color: 颜色 (red/orange/cyan/blue)`

---

### ~~P1-R16-04: trading-api.md `add_position` 缺少 `industry_code` 参数~~ ✅ 已修复

**位置**: `docs/design/trading/trading-api.md` (lines 290-319)
**问题**: `PositionManager.add_position()` 的参数列表不包含 `industry_code`，但 `Position` 数据结构中 `industry_code` 是必填字段（无默认值）。

**现状** (trading-api.md lines 290-299):
```python
def add_position(
    self,
    stock_code: str,
    stock_name: str,
    shares: int,
    cost_price: float,
    buy_date: str,
    signal_id: str = None,
    stop_price: float = None,
    target_price: float = None
) -> Position:
```

**矛盾源**:
- `trading-data-models.md` line 101: `industry_code: str  # 行业代码` — 无默认值
- `trading-algorithm.md` line 78: 信号构建时 `industry_code` 从 Integration 透传

**修复**: 在 `add_position` 参数列表中补入 `industry_code: str`（放在 `buy_date` 之后）。

---

## P2 级（建议修复 — 表述/完整性问题）

### ~~P2-R16-05: gui-api.md `format_temperature` label 枚举仅 3 标签，算法实际 4 标签~~ ✅ 已修复

**位置**: `docs/design/gui/gui-api.md` (line 307)
**问题**: label 注释为 `(高温/中性/低温)` 仅 3 标签，但 gui-algorithm.md §2.1 定义了 4 标签。

**现状** (gui-api.md line 307):
```
label: 标签 (高温/中性/低温)
```

**参考** (gui-algorithm.md §2.1 lines 46-49):
| 温度范围 | 标签 |
|----------|------|
| > 80     | 过热 |
| 45-80    | 中性 |
| 30-44    | 冷却 |
| < 30     | 冰点 |

**修复**: 改为 `label: 标签 (过热/中性/冷却/冰点)`

---

### ~~P2-R16-06: gui-api.md `export_to_csv` 返回值注释误写 `.md`~~ ✅ 已修复

**位置**: `docs/design/gui/gui-api.md` (line 416)
**问题**: `export_to_csv` 的 Returns 注释中路径后缀误写为 `.md`。

**现状** (line 416):
```
str: 导出文件路径（.reports/gui/{filename}_{YYYYMMDD_HHMMSS}.md）
```

**对照** (line 419):
```
文件保存至 .reports/gui/{filename}_{YYYYMMDD_HHMMSS}.csv
```

**修复**: line 416 `.md` 改为 `.csv`。

---

### ~~P2-R16-07: gui-algorithm.md STRONG_BUY "绿色强调"与 A 股色彩约定矛盾~~ ✅ 已修复

**位置**: `docs/design/gui/gui-algorithm.md` (line 72)
**问题**: STRONG_BUY（最强看多信号）的显示规则标注为"绿色强调"，但同文档 line 21 明确声明"遵循 A 股红涨绿跌"。按 A 股惯例，最强看多信号应使用红色强调。

**现状** (line 72):
```
| ≥ 75（且mss_cycle∈{emergence,fermentation}） | STRONG_BUY | high | 绿色强调 |
```

**矛盾源** (line 21):
```
色彩约定：遵循 A 股红涨绿跌（盈利/上涨用红色，亏损/下跌用绿色）。
```

**修复**: "绿色强调" → "红色强调"

---

### ~~P2-R16-08: analysis-api.md `compute_metrics` 未暴露 `risk_free_rate` 参数~~ ✅ 已修复

**位置**: `docs/design/analysis/analysis-api.md` (lines 43-59)
**问题**: `compute_metrics(start_date, end_date, equity_curve)` 不接受 `risk_free_rate` 参数，内部调用 `calculate_risk_metrics` 时硬编码 `0.015`。而 `BacktestConfig.risk_free_rate` 可由用户配置。若回测使用非默认利率，Analysis 层仍用 0.015 计算，导致同一净值曲线产生不同 Sharpe/Sortino。

**修复**: `compute_metrics` 增加 `risk_free_rate: float = 0.015` 可选参数，透传至 `calculate_risk_metrics`。

---

### ~~P2-R16-09: backtest-data-models.md `BacktestTrade.status` 注释遗漏 `partially_filled`~~ ✅ 已修复

**位置**: `docs/design/backtest/backtest-data-models.md` (line 121)
**问题**: BacktestTrade 数据类的 `status` 注释写 `# pending/filled/rejected`，遗漏 `partially_filled`，与同文档 TradeStatus 枚举（line 369-374）的 4 值不一致。

**现状** (line 121):
```python
status: str              # pending/filled/rejected
```

**对照** (line 369-374):
```python
class TradeStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    REJECTED = "rejected"
```

**修复**: 注释改为 `# pending/filled/partially_filled/rejected`

---

### ~~P2-R16-10: gui-information-flow.md 温度格式化示例遗漏 cyan 分支~~ ✅ 已修复

**位置**: `docs/design/gui/gui-information-flow.md` (lines 238-239)
**问题**: 温度卡片数据流示例仅展示 2 级判断（`>80` → red / `>=45` → orange），遗漏 `>=30 → cyan` 分支。虽然对于示例值 65.5 正确命中 orange，但作为参考文档误导读者以为只有 3 级（red/orange/blue），与 gui-algorithm.md 的 4 级分段不一致。

**现状** (lines 238-239):
```
│  - 65.5 > 80? No              │
│  - 65.5 >= 45? Yes → orange   │
```

**修复**: 补全 4 级判断:
```
│  - 65.5 > 80? No              │
│  - 65.5 >= 45? Yes → orange   │
│  (- >= 30? → cyan)            │
│  (- else → blue)              │
```

---

## 修复索引

| ID | 严重性 | 文件 | 行号 | 摘要 |
|----|--------|------|------|------|
| P1-R16-01 | P1 | gui-api.md | 385-388 | format_pnl 颜色反 A 股惯例 |
| P1-R16-02 | P1 | gui-api.md | 345-347 | format_trend 颜色反 A 股惯例 |
| P1-R16-03 | P1 | gui-api.md | 306 | format_temperature 缺 cyan |
| P1-R16-04 | P1 | trading-api.md | 290-299 | add_position 缺 industry_code |
| P2-R16-05 | P2 | gui-api.md | 307 | format_temperature label 缺冷却/冰点 |
| P2-R16-06 | P2 | gui-api.md | 416 | export_to_csv 注释误写 .md |
| P2-R16-07 | P2 | gui-algorithm.md | 72 | STRONG_BUY 绿色强调违反 A 股约定 |
| P2-R16-08 | P2 | analysis-api.md | 43-59 | compute_metrics 缺 risk_free_rate 参数 |
| P2-R16-09 | P2 | backtest-data-models.md | 121 | BacktestTrade.status 注释漏 partially_filled |
| P2-R16-10 | P2 | gui-information-flow.md | 238-239 | 温度示例漏 cyan 分支 |

---

## 复查纠偏记录（2026-02-08）

- ~~P1-R16-01~~：`gui-api.md` 中 `format_pnl` 改为红盈绿亏（A 股口径）。
- ~~P1-R16-02~~：`gui-api.md` 中 `format_trend` 改为 `up→red`、`down→green`。
- ~~P1-R16-03~~：`gui-api.md` `format_temperature` 颜色枚举补齐 `cyan`。
- ~~P1-R16-04~~：`trading-api.md` `add_position()` 增加必填 `industry_code` 参数。
- ~~P2-R16-05~~：`gui-api.md` 温度标签补齐为“过热/中性/冷却/冰点”。
- ~~P2-R16-06~~：`gui-api.md` `export_to_csv` 返回路径后缀修正为 `.csv`。
- ~~P2-R16-07~~：`gui-algorithm.md` STRONG_BUY 显示改为“红色强调”。
- ~~P2-R16-08~~：`analysis-api.md` `compute_metrics` 增加 `risk_free_rate` 参数并在示例透传。
- ~~P2-R16-09~~：`backtest-data-models.md` `BacktestTrade.status` 注释补齐 `partially_filled`。
- ~~P2-R16-10~~：`gui-information-flow.md` 温度示例补全 `>=30→cyan` 与 `else→blue` 分支说明。
