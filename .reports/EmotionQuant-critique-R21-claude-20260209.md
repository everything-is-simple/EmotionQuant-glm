# EmotionQuant R21 深度审查报告

**审查时间**: 2026-02-09  
**审查轮次**: R21  
**审查范围**: Analysis 模块四位一体（algorithm, data-models, api, information-flow）  
**审查角度**: 内部一致性 + 上游契约对齐 + 报告落盘规范  

---

## 审查概要

| 类型 | 数量 |
|------|------|
| P1（必须修复） | 5 |
| P2（建议修复） | 4 |
| 已修复 | 1 |
| **总计** | **10** |

---

## P1 级问题（5 项）

### [x] ~~**P1-R21-01: Analysis 归因算法 §4.1 execution_deviation 语义与 Data-Models §4.1 依赖表不一致**~~（已修复）

**位置**：
- `analysis-algorithm.md` line 184-192
- `analysis-data-models.md` line 287-295

**问题描述**：
- **Algorithm §4.1 line 184-192** 计算归因时使用 `execution_deviation = (exec_price - rec.entry) / rec.entry`（成交价相对建议入场价的偏差）
- **Data-Models §4.1 line 287-295** 输入依赖列出 `backtest_trade_records` 与 `trade_records`，但**未说明归因算法需要读取 `integrated_recommendation.entry` 字段进行比对**
- **隐含缺口**：`integrated_recommendation` 在 Data-Models §4.1 中列为依赖，但未说明归因计算的关键字段 `entry`（建议入场价）

**影响**：实现时可能遗漏 `integrated_recommendation.entry` 字段的依赖，导致归因计算失败。

**建议修正**：
```markdown
# analysis-data-models.md §4.1

| 数据表 | 用途 |
|--------|------|
| integrated_recommendation | 集成推荐（需读取 `entry` 字段参与归因计算） |
| trade_records | 交易记录（实盘分析场景，需读取 `filled_price` 或 `price` 字段） |
| backtest_trade_records | 回测成交记录（回测分析场景，需读取 `filled_price` 或 `price` 字段） |
```

**修复状态**：✅ 已修复

---

### [x] ~~**P1-R21-02: Analysis API §2.2 compute_metrics 缺少 `trades` 参数但算法 §7 需要读取交易列表**~~（已修复）

**位置**：
- `analysis-api.md` line 43-61
- `analysis-algorithm.md` line 375-426

**问题描述**：
- **API §2.2** `compute_metrics` 签名仅包含 `start_date, end_date, equity_curve, risk_free_rate`
- **Algorithm §7** 完整绩效计算流程 line 375-426 需要 `trades` 参数计算交易统计（`win_rate, profit_factor, avg_holding_days`）
- **断裂**：API 签名无法透传 `trades`，实现时必须在 `compute_metrics` 内部从 Repository 读取，但 API 文档未说明

**影响**：API 签名与算法流程不匹配，实现者可能困惑。

**建议修正**：
```python
# analysis-api.md §2.2

def compute_metrics(
    self,
    start_date: str,
    end_date: str,
    equity_curve: List[float] = None,
    trades: List[Trade] = None,  # 新增：交易列表（可选，不提供则从数据库读取）
    risk_free_rate: float = 0.015
) -> PerformanceMetrics:
    """
    计算绩效指标

    Args:
        start_date: 开始日期
        end_date: 结束日期
        equity_curve: 净值曲线（可选，不提供则从数据库读取）
        trades: 交易列表（可选，不提供则从数据库读取）
        risk_free_rate: 年化无风险利率（默认 0.015）

    Returns:
        PerformanceMetrics: 绩效指标
    """
```

**修复状态**：✅ 已修复

---

### [x] ~~**P1-R21-03: Information-Flow §2.1 日报生成流程 Step 3 缺少 `backtest_trade_records` 分支说明**~~（已修复）

**位置**：
- `analysis-information-flow.md` line 110-115
- `analysis-algorithm.md` line 26-27

**问题描述**：
- **Info-Flow §2.1 Step 3** line 110-115 仅说明 `trades = repo.get_trade_records()`（实盘场景）
- **Algorithm §1** line 26-27 明确指出回测分析场景使用 `backtest_trade_records`
- **缺口**：Info-Flow 未说明回测场景的分支逻辑

**影响**：实现时可能遗漏回测分析场景的数据源切换。

**建议修正**：
```markdown
# analysis-information-flow.md §2.1 Step 3

│  │  3. 获取信号与交易                       │
│  │     signals = repo.get_integrated_rec() │
│  │     # 实盘场景使用 trade_records
│  │     # 回测场景使用 backtest_trade_records
│  │     trades = repo.get_trade_records() if is_live else repo.get_backtest_trade_records()
│  │     → signal_count, filled, rejected    │
```

**修复状态**：✅ 已修复

---

### [x] ~~**P1-R21-04: Data-Models §3.1 daily_report DDL 缺少 `total_return` 字段但算法 §6.1 需要输出**~~（已修复）

**位置**：
- `analysis-data-models.md` line 214-236
- `analysis-algorithm.md` line 320-326

**问题描述**：
- **Algorithm §6.1 line 320-326** 日报生成需要 `total_return` 字段
- **Data-Models §3.1 DDL** line 214-236 未包含 `total_return` 字段
- **断裂**：算法输出与 DDL 定义不匹配

**影响**：落库时 `total_return` 字段无处存储。

**建议修正**：
```sql
# analysis-data-models.md §3.1

CREATE TABLE daily_report (
    report_date VARCHAR(8) PRIMARY KEY,
    market_temperature DECIMAL(8,4),
    cycle VARCHAR(20),
    trend VARCHAR(20),
    position_advice VARCHAR(50),
    signal_count INT,
    filled_count INT,
    reject_count INT,
    hit_rate DECIMAL(8,4),
    avg_return_5d DECIMAL(8,4),
    avg_holding_days DECIMAL(8,2),
    total_return DECIMAL(10,4),      -- 新增
    max_drawdown DECIMAL(8,4),
    sharpe_ratio DECIMAL(8,4),
    win_rate DECIMAL(8,4),
    top_recommendations JSON,
    risk_summary JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**修复状态**：✅ 已修复

---

### [x] ~~**P1-R21-05: API §5.4 export_to_file 默认路径与治理规范 `.reports/analysis/` 未在文档中显式说明**~~（已修复）

**位置**：
- `analysis-api.md` line 358-378
- `analysis-algorithm.md` line 21

**问题描述**：
- **Algorithm §1 line 21** 明确规定 "输出规范：报告与导出统一落盘 `.reports/analysis/`"
- **API §5.4 line 358-378** `export_to_file` 文档字符串仅说明 "文件路径（默认落盘于 `.reports/analysis/`）"，但未在参数说明中显式标注
- **缺口**：调用者可能误以为需要显式传入路径

**影响**：文档不够清晰，可能导致实现时路径硬编码或遗漏默认路径配置。

**建议修正**：
```python
# analysis-api.md §5.4

def export_to_file(
    self,
    content: str,
    filename: str,
    format: str = "md",
    output_dir: str = None  # 新增：输出目录（可选，默认 `.reports/analysis/`）
) -> str:
    """
    导出报告文件

    Args:
        content: 内容
        filename: 文件基名（不含路径/时间戳）
        format: 格式 (md/csv)
        output_dir: 输出目录（可选，默认 `.reports/analysis/`，遵循治理规范）

    Returns:
        str: 完整文件路径（含时间戳，如 `.reports/analysis/daily_report_20260131_153000.md`）
    """
```

**修复状态**：✅ 已修复

---

## P2 级问题（4 项）

### [x] ~~**P2-R21-06: Algorithm §2.3 Sortino 分母符号 `downside_deviation` 与公式注释 "sqrt(mean([x**2 for x in downside_returns]))" 不一致**~~（已修复）

**位置**：
- `analysis-algorithm.md` line 75-78

**问题描述**：
- **Line 76** 定义 `downside_returns = [min(r - daily_rf, 0) for r in daily_returns]`（负值）
- **Line 77** 计算 `downside_deviation = sqrt(mean([x**2 for x in downside_returns]))`
- **语义断裂**：`downside_returns` 已经是负值，平方后求 RMS 是正确的，但变量名 `downside_returns` 容易与"收益"混淆，建议改名

**影响**：代码可读性差，可能被误解为"下行收益的标准差"。

**建议修正**：
```python
# analysis-algorithm.md §2.3

# 索提诺比率 (仅考虑下行波动)
downside_deviations = [min(r - daily_rf, 0) for r in daily_returns]  # 改名
downside_std = sqrt(mean([x**2 for x in downside_deviations])) if downside_deviations else 0
sortino_ratio = sqrt(252) × (mean(r) - daily_rf) / downside_std if downside_std > 0 else 0
```

**修复状态**：✅ 已修复

---

### [x] ~~**P2-R21-07: Data-Models §1.1 PerformanceMetrics 数据类缺少 `volatility` 字段但算法 §2.2 计算年化波动率**~~（已修复）

**位置**：
- `analysis-data-models.md` line 16-36
- `analysis-algorithm.md` line 51-63

**问题描述**：
- **Algorithm §2.2** line 62 计算 `volatility = std(daily_returns) × sqrt(252)`
- **Data-Models §1.1** line 16-36 `PerformanceMetrics` 数据类**已包含 `volatility` 字段**（line 25）
- **DDL §3.2** line 242-259 `performance_metrics` 表**已包含 `volatility` 字段**（line 249）
- **修正记录 v3.1.4** 已修复此问题

**修复状态**：✅ 已修复（v3.1.4）

---

### [x] ~~**P2-R21-08: Information-Flow §4.1 归因计算流程 line 265-270 `pnl_pct` 注释与算法 §4.1 `execution_deviation` 语义不一致**~~（已修复）

**位置**：
- `analysis-information-flow.md` line 265-270
- `analysis-algorithm.md` line 186-187

**问题描述**：
- **Info-Flow §4.1 line 265** 注释 `pnl_pct = (trade.price - rec.entry) / rec.entry`
- **Algorithm §4.1 line 186-187** 使用 `execution_deviation = (exec_price - rec.entry) / rec.entry if rec.entry and rec.entry > 0 else 0` 并注释 "计算执行偏差（成交价相对建议入场价）；非真实交易盈亏"
- **断裂**：Info-Flow 沿用了旧命名 `pnl_pct`，但算法已改为 `execution_deviation`

**影响**：文档术语不统一，可能引起误解。

**建议修正**：
```markdown
# analysis-information-flow.md §4.1

│  2. 计算盈亏贡献                         │
│                                          │
│  for rec, trade in matched:             │
│      execution_deviation = (trade.price - rec.entry)  -- 改名
│                          / rec.entry               
│      # 注：execution_deviation 为执行偏差，非交易盈亏
│                                          │
│      mss_contrib = rec.mss_score * execution_deviation  -- 更新
│      irs_contrib = rec.irs_score * execution_deviation
│      pas_contrib = rec.pas_score * execution_deviation
```

**修复状态**：✅ 已修复

---

### [x] ~~**P2-R21-09: API §4.3 analyze_concentration 返回字段 `top_industry` 但算法 §5.2 未计算该字段**~~（已修复）

**位置**：
- `analysis-api.md` line 269-284
- `analysis-algorithm.md` line 254-278

**问题描述**：
- **API §4.3** line 282 返回 `dict: {hhi, max_concentration, industry_count, top_industry}`
- **Algorithm §5.2** line 254-278 仅计算 `hhi, max_concentration, industry_count`，未输出 `top_industry`

**影响**：API 承诺的返回字段与算法不匹配。

**建议修正**：
```python
# analysis-algorithm.md §5.2 补充 top_industry 计算

# 最大行业占比
max_concentration = max(v / total_value for v in industry_values.values())
# 找出最大行业代码
top_industry = max(industry_values, key=lambda k: industry_values[k])

return {
    "hhi": hhi,
    "max_concentration": max_concentration,
    "industry_count": len(industry_values),
    "top_industry": top_industry  # 补充
}
```

**修复状态**：✅ 已修复

---

### [x] ~~**P2-R21-10: Data-Models §2.1 DailyReportData 数据类未包含 `created_at` 字段但 DDL §3.1 包含**~~（已修复）

**位置**：
- `analysis-data-models.md` line 100-118
- `analysis-data-models.md` line 214-236

**问题描述**：
- **DDL §3.1 line 234** `created_at DATETIME DEFAULT CURRENT_TIMESTAMP`
- **Data-Models §2.1** line 100-118 `DailyReportData` 数据类未包含 `created_at` 字段
- **断裂**：数据类与 DDL 定义不一致

**影响**：落库时需要手动补充 `created_at` 字段，数据类无法直接映射。

**建议修正**：
```python
# analysis-data-models.md §2.1

@dataclass
class DailyReportData:
    """日报生成数据"""
    report_date: str
    market_overview: MarketOverview
    industry_rotation: IndustryRotation
    signal_stats: SignalStats
    performance: PerformanceSummary
    top_recommendations: List[RecommendationSummary]
    risk_summary: RiskSummary
    created_at: datetime = None  # 新增：创建时间（可选，落库时自动生成）
```

**修复状态**：✅ 已修复

---

## 修复优先级建议

### 立即修复（P1）
1. **P1-R21-01**: 补充 `integrated_recommendation.entry` 依赖说明
2. **P1-R21-02**: API `compute_metrics` 增加 `trades` 参数
3. **P1-R21-03**: 日报生成流程补充回测场景分支
4. **P1-R21-04**: `daily_report` DDL 补充 `total_return` 字段
5. **P1-R21-05**: `export_to_file` 显式说明默认路径参数

### 建议修复（P2）
6. **P2-R21-06**: Sortino 变量名改为 `downside_deviations`
7. **P2-R21-08**: Info-Flow 归因术语改为 `execution_deviation`
8. **P2-R21-09**: 算法补充 `top_industry` 计算
9. **P2-R21-10**: `DailyReportData` 数据类补充 `created_at` 字段

---

## 审查结论

**Analysis 模块四位一体文档整体质量较高**，已完成多轮修正（v3.1.x），但仍存在以下典型问题：

1. **API ↔ Algorithm 接口不匹配**：`compute_metrics` 缺少 `trades` 参数
2. **Data-Models ↔ Algorithm 字段缺口**：DDL 缺少算法需要的输出字段（`total_return`）
3. **Info-Flow ↔ Algorithm 术语不统一**：`pnl_pct` vs `execution_deviation`
4. **回测 vs 实盘分支说明缺失**：Info-Flow 未说明数据源切换逻辑

建议优先修复 **P1 级 5 项**，确保 API 签名与算法流程匹配、DDL 与数据类一致。

---

**下一步**：
- 用户修复上述问题后提交，Agent 进入 R21 验证
- R22 继续审查 **GUI 模块四位一体**

---

**报告生成时间**: 2026-02-09  
**Agent**: Claude (Warp)  
**审查轮次**: R21 / 预计 26-27 轮总计
