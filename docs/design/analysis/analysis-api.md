# Analysis API 接口

**版本**: v3.1.4（重构版）
**最后更新**: 2026-02-09
**状态**: 设计完成（代码未落地）

---

## 1. 模块结构

Analysis 层产出 L4 分析指标与报告，不替代 L3 算法；仅消费 L3 算法输出与回测/实盘结果。

**外部库边界**：不得以 quantstats/empyrical 等第三方库替代 Analysis 模块，可作为内部计算工具使用（不改变输出口径）。

**输入依赖**：`mss_panorama`、`irs_industry_daily`、`stock_pas_daily`、`integrated_recommendation`；`trade_records` / `backtest_trade_records`、`backtest_results`（含 equity_curve）、`positions`。

```
analysis/
├── performance_analyzer.py   # 绩效指标计算
├── signal_attribution.py     # MSS/IRS/PAS贡献拆解
├── risk_reporter.py          # 风险与回撤分析
├── report_writer.py          # 报告输出（Markdown/CSV）
└── visualizer.py             # 可视化输出接口
```

---

## 2. PerformanceAnalyzer（绩效分析器）

### 2.1 类定义

```python
class PerformanceAnalyzer:
    """绩效分析器"""

    def __init__(self, repository: DataRepository) -> None:
        """初始化分析器"""
```

### 2.2 compute_metrics

```python
def compute_metrics(
    self,
    start_date: str,
    end_date: str,
    equity_curve: List[float] = None,
    trades: List[Trade] = None,
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

### 2.3 calculate_daily_returns

```python
def calculate_daily_returns(
    self,
    equity_curve: List[float]
) -> List[float]:
    """
    计算日收益率序列

    Args:
        equity_curve: 净值曲线

    Returns:
        List[float]: 日收益率列表
    """
```

### 2.4 calculate_max_drawdown

```python
def calculate_max_drawdown(
    self,
    equity_curve: List[float]
) -> Tuple[float, str, str]:
    """
    计算最大回撤

    Args:
        equity_curve: 净值曲线

    Returns:
        Tuple[float, str, str]: (最大回撤, 开始日期, 结束日期)
    """
```

### 2.5 calculate_risk_metrics

```python
def calculate_risk_metrics(
    self,
    daily_returns: List[float],
    annual_return: float,
    max_drawdown: float,
    risk_free_rate: float = 0.015
) -> dict:
    """
    计算风险调整收益指标

    Args:
        daily_returns: 日收益率
        annual_return: 年化收益率
        max_drawdown: 最大回撤
        risk_free_rate: 无风险利率

    Returns:
        dict: {sharpe_ratio, sortino_ratio, calmar_ratio}
    """
```

### 2.6 calculate_trade_stats

```python
def calculate_trade_stats(
    self,
    trades: List[Trade]
) -> dict:
    """
    计算交易统计

    Args:
        trades: 交易列表

    Returns:
        dict: {win_rate, profit_factor, avg_holding_days, total_trades}
    """
```

---

## 3. SignalAttributor（信号归因器）

### 3.1 类定义

```python
class SignalAttributor:
    """信号归因分析器"""

    def __init__(self, repository: DataRepository) -> None:
        """初始化归因器"""
```

### 3.2 attribute_signals

```python
def attribute_signals(
    self,
    trade_date: str
) -> SignalAttribution:
    """
    计算单日信号归因

    Args:
        trade_date: 交易日期

    Returns:
        SignalAttribution: 归因结果
    """
```

### 3.3 attribute_period

```python
def attribute_period(
    self,
    start_date: str,
    end_date: str
) -> List[SignalAttribution]:
    """
    计算时间段信号归因

    Args:
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        List[SignalAttribution]: 每日归因结果
    """
```

### 3.4 calculate_hit_rate

```python
def calculate_hit_rate(
    self,
    signals: List[Signal],
    trades: List[Trade],
    forward_days: int = 5
) -> dict:
    """
    计算信号命中率

    Args:
        signals: 信号列表
        trades: 交易列表
        forward_days: 前向窗口（天）

    Returns:
        dict: {hit_rate, avg_forward_return, sample_count}
    """
```

### 3.5 calculate_rotation_hit_rate

```python
def calculate_rotation_hit_rate(
    self,
    start_date: str,
    end_date: str
) -> float:
    """
    计算IRS行业轮动命中率

    Args:
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        float: 轮动命中率
    """
```

---

## 4. RiskReporter（风险报告器）

### 4.1 类定义

```python
class RiskReporter:
    """风险分析与报告"""

    def __init__(self, repository: DataRepository) -> None:
        """初始化报告器"""
```

### 4.2 analyze_risk_distribution

```python
def analyze_risk_distribution(
    self,
    recommendations: List[Recommendation]
) -> RiskSummary:
    """
    分析风险等级分布

    Args:
        recommendations: 推荐列表

    Returns:
        RiskSummary: 风险摘要
    """
```

### 4.3 analyze_concentration

```python
def analyze_concentration(
    self,
    positions: List[Position]
) -> dict:
    """
    分析持仓集中度

    Args:
        positions: 持仓列表

    Returns:
        dict: {hhi, max_concentration, industry_count, top_industry}
    """
```

### 4.4 analyze_drawdown_periods

```python
def analyze_drawdown_periods(
    self,
    equity_curve: List[float],
    threshold: float = -0.05
) -> List[dict]:
    """
    分析回撤期间

    Args:
        equity_curve: 净值曲线
        threshold: 回撤阈值

    Returns:
        List[dict]: [{start_date, end_date, max_drawdown, duration}]
    """
```

---

## 5. ReportWriter（报告生成器）

### 5.1 类定义

```python
class ReportWriter:
    """报告生成与导出"""

    def __init__(self, repository: DataRepository) -> None:
        """初始化生成器"""
```

### 5.2 generate_daily_report

```python
def generate_daily_report(
    self,
    report_date: str
) -> DailyReportData:
    """
    生成日报数据

    Args:
        report_date: 报告日期

    Returns:
        DailyReportData: 日报数据
    """
```

### 5.3 render_markdown

```python
def render_markdown(
    self,
    report_data: DailyReportData,
    template: str = "daily_report"
) -> str:
    """
    渲染Markdown报告

    Args:
        report_data: 报告数据
        template: 模板名称

    Returns:
        str: Markdown内容
    """
```

### 5.4 export_to_file

```python
def export_to_file(
    self,
    content: str,
    filename: str,
    format: str = "md",
    output_dir: str = None
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

### 5.5 export_metrics_csv

```python
def export_metrics_csv(
    self,
    metrics: PerformanceMetrics,
    filename: str = None
) -> str:
    """
    导出绩效指标CSV

    Args:
        metrics: 绩效指标
        filename: 文件基名（可选，不含路径/时间戳）

    Returns:
        str: 文件路径
    """
```

---

## 6. Visualizer（可视化接口）

### 6.1 build_temperature_trend

```python
def build_temperature_trend(
    self,
    mss_history: List[MssPanorama]
) -> TemperatureTrendData:
    """
    构建温度趋势图数据

    Args:
        mss_history: MSS历史数据

    Returns:
        TemperatureTrendData: 图表数据
    """
```

### 6.2 build_industry_radar

```python
def build_industry_radar(
    self,
    irs_data: List[IrsIndustryDaily],
    top_n: int = 10
) -> IndustryRadarData:
    """
    构建行业雷达图数据

    Args:
        irs_data: IRS数据
        top_n: Top N数量

    Returns:
        IndustryRadarData: 雷达图数据
    """
```

### 6.3 build_score_distribution

```python
def build_score_distribution(
    self,
    pas_data: List[StockPasDaily]
) -> ScoreDistributionData:
    """
    构建PAS评分分布图数据

    Args:
        pas_data: PAS数据

    Returns:
        ScoreDistributionData: 分布图数据
    """
```

---

## 7. 完整调用示例

```python
from analysis.performance_analyzer import PerformanceAnalyzer
from analysis.signal_attribution import SignalAttributor
from analysis.risk_reporter import RiskReporter
from analysis.report_writer import ReportWriter

# 初始化
analyzer = PerformanceAnalyzer(repository)
attributor = SignalAttributor(repository)
risk_reporter = RiskReporter(repository)
report_writer = ReportWriter(repository)

# 计算绩效指标
metrics = analyzer.compute_metrics(
    start_date="20260101",
    end_date="20260131",
    trades=repository.get_trade_records("20260131"),  # 可选；不传则由实现自行读取
    risk_free_rate=0.015
)
print(f"总收益: {metrics.total_return:.2%}")
print(f"夏普比率: {metrics.sharpe_ratio:.2f}")

# 信号归因
attribution = attributor.attribute_signals("20260131")
print(f"MSS贡献: {attribution.mss_attribution:.4f}")
print(f"IRS贡献: {attribution.irs_attribution:.4f}")
print(f"PAS贡献: {attribution.pas_attribution:.4f}")

# 风险分析
positions = repository.get_positions()
concentration = risk_reporter.analyze_concentration(positions)
print(f"HHI: {concentration['hhi']:.4f}")
print(f"最大行业占比: {concentration['max_concentration']:.2%}")

# 生成日报
report_data = report_writer.generate_daily_report("20260131")
markdown = report_writer.render_markdown(report_data)
path = report_writer.export_to_file(markdown, "daily_report", "md")
print(f"报告已导出: {path}")  # .reports/analysis/daily_report_{YYYYMMDD_HHMMSS}.md

# 导出绩效CSV
csv_path = report_writer.export_metrics_csv(metrics)
print(f"指标已导出: {csv_path}")
```

---

## 8. 报告落盘路径

| 文件类型 | 路径模板 | 示例 |
|----------|----------|------|
| 日报 | .reports/analysis/daily_report_{YYYYMMDD_HHMMSS}.md | .reports/analysis/daily_report_20260131_153000.md |
| 周报 | .reports/analysis/weekly_report_{YYYYMMDD_HHMMSS}.md | .reports/analysis/weekly_report_20260131_153000.md |
| 月报 | .reports/analysis/monthly_report_{YYYYMMDD_HHMMSS}.md | .reports/analysis/monthly_report_20260131_153000.md |
| 绩效指标 | .reports/analysis/performance_metrics_{YYYYMMDD_HHMMSS}.csv | .reports/analysis/performance_metrics_20260131_153000.csv |
| 归因结果 | .reports/analysis/signal_attribution_{YYYYMMDD_HHMMSS}.csv | .reports/analysis/signal_attribution_20260131_153000.csv |
| 回测报告 | .reports/analysis/backtest_report_{YYYYMMDD_HHMMSS}.md | .reports/analysis/backtest_report_20260131_153000.md |
| 归档（可选） | .archive/analysis/{YYYYMM}/analysis_reports_{YYYYMMDD_HHMMSS}.zip | .archive/analysis/202601/analysis_reports_20260131_153000.zip |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.1.4 | 2026-02-09 | 修复 R27：`build_score_distribution` 参数类型更正为 `List[StockPasDaily]`，与 PAS data-model/API 一致 |
| v3.1.3 | 2026-02-09 | 修复 R21：`compute_metrics` 增加 `trades` 可选参数并明确默认回源；`export_to_file` 增加 `output_dir` 可选参数并显式默认 `.reports/analysis/` |
| v3.1.2 | 2026-02-08 | 修复 R16：`compute_metrics` 增加 `risk_free_rate` 参数并透传到风险指标计算口径 |
| v3.1.1 | 2026-02-08 | 修复 R10：`calculate_risk_metrics` 默认 `risk_free_rate` 调整为 0.015，与 Analysis/Backtest 公式统一 |
| v3.1.0 | 2026-02-04 | 对齐边界/依赖与报告落盘规范 |
| v3.0.0 | 2026-01-31 | 重构版：统一API接口定义 |
| v2.1.0 | 2026-01-23 | 增加信号归因接口 |
| v2.0.0 | 2026-01-20 | 初始版本 |

---

**关联文档**：
- 核心算法：[analysis-algorithm.md](./analysis-algorithm.md)
- 数据模型：[analysis-data-models.md](./analysis-data-models.md)
- 信息流：[analysis-information-flow.md](./analysis-information-flow.md)


