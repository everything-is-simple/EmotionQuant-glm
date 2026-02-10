# GUI 数据模型

**版本**: v3.1.7（重构版）
**最后更新**: 2026-02-09
**状态**: 设计完成（代码未落地）

---

## 1. 页面数据结构

### 1.1 Dashboard数据

```python
@dataclass
class DashboardData:
    """总览仪表盘数据"""
    # MSS卡片
    temperature: float            # 温度 [0-100]
    temperature_color: str        # 颜色 (red/orange/cyan/blue)
    cycle: str                    # 周期 (emergence/fermentation/acceleration/divergence/climax/diffusion/recession/unknown)
    trend: str                    # 趋势 (up/down/sideways)
    position_advice: str          # 仓位建议
    # 时间
    trade_date: str               # 交易日期
    # 推荐列表
    top_recommendations: List[RecommendationItem]  # Top N 推荐
    integration_mode_badge: str    # 主模式徽标（传统模式/实验模式/双重验证/互补模式）
    # 行业热点
    top_industries: List[IndustryRankItem]         # Top 5 行业
```

### 1.2 RecommendationItem（推荐项）

```python
@dataclass
class RecommendationItem:
    """集成推荐展示项"""
    rank: int                     # 排名
    stock_code: str               # 股票代码
    stock_name: str               # 股票名称
    industry_name: str            # 行业名称
    final_score: float            # 综合评分 [0-100]
    recommendation: str           # 推荐等级 (STRONG_BUY/BUY/HOLD/SELL/AVOID)
    recommendation_color: str     # 推荐颜色
    integration_mode: str         # top_down/bottom_up/dual_verify/complementary
    integration_mode_badge: str   # 传统模式/实验模式/双重验证/互补模式
    position_size: float          # 建议仓位 [0-1]
    direction: str                # 方向 (bullish/bearish/neutral)
    entry: float                  # 入场价
    stop: float                   # 止损价
    target: float                 # 目标价
    irs_score: float              # IRS评分
    pas_score: float              # PAS评分
```

### 1.3 IndustryRankItem（行业排名项）

```python
@dataclass
class IndustryRankItem:
    """行业排名展示项"""
    rank: int                     # 排名 [1-N]
    industry_code: str            # 行业代码
    industry_name: str            # 行业名称
    industry_score: float         # 行业评分 [0-100]
    rotation_status: str          # 轮动状态 (IN/OUT/HOLD)
    status_color: str             # 状态颜色
    allocation_advice: str        # 配置建议
```

### 1.4 MssPageData（MSS页面）

```python
@dataclass
class MssPageData:
    """MSS页面数据"""
    # 当日数据
    current: MssPanoramaDisplay
    # 历史数据（图表用）
    history: List[MssPanoramaDisplay]
    # 图表数据
    chart_data: TemperatureChartData
```

```python
@dataclass
class MssPanoramaDisplay:
    """MSS展示数据"""
    trade_date: str
    temperature: float
    temperature_color: str        # red/orange/cyan/blue
    cycle: str
    cycle_label: str              # 中文标签：萌芽期/发酵期/加速期/分歧期/高潮期/扩散期/退潮期/未知
    trend: str                    # up/down/sideways
    trend_icon: str               # ↑/↓/→
    position_advice: str
```

### 1.5 IrsPageData（IRS页面）

```python
@dataclass
class IrsPageData:
    """IRS页面数据"""
    trade_date: str
    industries: List[IndustryRankItem]
    chart_data: IndustryChartData
```

### 1.6 PasPageData（PAS页面）

```python
@dataclass
class PasPageData:
    """PAS页面数据"""
    trade_date: str
    stocks: List[StockPasDisplay]
    pagination: PaginationInfo
```

```python
@dataclass
class StockPasDisplay:
    """个股PAS展示数据"""
    stock_code: str
    stock_name: str
    industry_name: str
    opportunity_score: float      # [0-100]
    opportunity_grade: str        # S/A/B/C/D
    level_color: str              # gold/green/blue/gray/red
    direction: str                # bullish/bearish/neutral
    direction_icon: str           # ↑/↓/→
    neutrality: float             # [0-1]（越接近1越中性，越接近0信号越极端）
    neutrality_percent: int       # [0-100] 中性度百分比（越大越中性，越小信号越强），计算：int(neutrality * 100)
    risk_reward_ratio: float
    suggested_entry: float
    suggested_stop: float
    suggested_target: float
```

### 1.7 TradingPageData（交易页面）

```python
@dataclass
class TradingPageData:
    """交易页面数据"""
    trade_date: str
    # 持仓
    positions: List[PositionDisplay]
    total_market_value: float
    total_unrealized_pnl: float
    total_unrealized_pnl_pct: float
    # 交易记录
    trades: List[TradeRecordDisplay]
    pagination: PaginationInfo
```

```python
@dataclass
class PositionDisplay:
    """持仓展示数据"""
    stock_code: str
    stock_name: str
    shares: int
    cost_price: float
    market_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    pnl_color: str                # red (盈利 > 0) / green (亏损 < 0) / gray (持平 = 0)
    is_frozen: bool
    frozen_label: str             # "T+1冻结" / ""
    stop_price: float
    target_price: float
```

```python
@dataclass
class TradeRecordDisplay:
    """交易记录展示数据"""
    trade_id: str
    trade_date: str
    stock_code: str
    stock_name: str
    direction: str                # buy/sell
    direction_label: str          # 买入/卖出
    direction_color: str          # red/green
    price: float
    shares: int
    amount: float
    total_fee: float
    status: str
    status_label: str             # 已成交/部分成交/已取消
```

### 1.8 AnalysisPageData（分析页面）

```python
@dataclass
class AnalysisPageData:
    """分析页面数据"""
    report_date: str
    # KPI卡片
    metrics: PerformanceMetricsDisplay
    # 日报预览
    daily_report: str             # Markdown内容
    # 回测结果
    backtest_summary: BacktestSummaryDisplay
```

```python
@dataclass
class PerformanceMetricsDisplay:
    """绩效指标展示数据"""
    total_return: float
    total_return_pct: str         # 格式化："+15.2%"
    annual_return: float
    annual_return_pct: str
    max_drawdown: float
    max_drawdown_pct: str         # 格式化："-8.5%"
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    win_rate: float
    win_rate_pct: str             # 格式化："65.3%"
    profit_factor: float
```

```python
@dataclass
class BacktestSummaryDisplay:
    """回测结果摘要展示"""
    backtest_name: str
    start_date: str
    end_date: str
    total_return_pct: str         # 格式化："+15.2%"
    annual_return_pct: str
    max_drawdown_pct: str         # 格式化："-8.5%"
    sharpe_ratio: float
    total_trades: int
    win_rate_pct: str             # 格式化："65.3%"
```

### 1.9 IntegratedPageData（集成推荐页面）

```python
@dataclass
class IntegratedPageData:
    """集成推荐页面数据"""
    trade_date: str
    recommendations: List[RecommendationItem]
    pagination: PaginationInfo
```

---

## 2. 图表数据结构

### 2.1 TemperatureChartData（温度曲线）

```python
@dataclass
class TemperatureChartData:
    """温度曲线图表数据"""
    x_axis: List[str]             # 日期序列
    y_axis: List[float]           # 温度序列
    zones: List[ChartZone]        # 颜色区域
```

```python
@dataclass
class ChartZone:
    """图表颜色区域"""
    min_value: float
    max_value: float
    include_min: bool             # 是否包含下边界（默认 True）
    include_max: bool             # 是否包含上边界（最高区间可为 True）
    color: str
    label: str
```

### 2.2 IndustryChartData（行业排名图）

```python
@dataclass
class IndustryChartData:
    """行业排名柱状图数据"""
    x_axis: List[str]             # 行业名称
    y_axis: List[float]           # 行业评分
    colors: List[str]             # 柱状图颜色
```

### 2.3 RecommendationScatterData（推荐散点图）

```python
@dataclass
class RecommendationScatterData:
    """推荐散点图数据"""
    points: List[ScatterPoint]
    x_label: str                  # X轴标签
    y_label: str                  # Y轴标签
```

```python
@dataclass
class ScatterPoint:
    """散点"""
    x: float
    y: float
    label: str
    color: str
```

---

## 3. 组件数据结构

### 3.1 TemperatureCard（温度卡片）

```python
@dataclass
class TemperatureCardData:
    """温度卡片数据"""
    value: float                  # 温度值
    color: str                    # 背景色
    label: str                    # 标签（高温/中性/低温）
    trend: str                    # 趋势图标
```

### 3.2 CycleBadge（周期标签）

```python
@dataclass
class CycleBadgeData:
    """周期标签数据"""
    cycle: str                    # emergence/fermentation/acceleration/divergence/climax/diffusion/recession/unknown
    label: str                    # 萌芽期/发酵期/...
    color: str                    # 标签颜色
```

周期中英文映射：
| 英文 | 中文 | 颜色 |
|------|------|------|
| emergence | 萌芽期 | blue |
| fermentation | 发酵期 | cyan |
| acceleration | 加速期 | green |
| divergence | 分歧期 | yellow |
| climax | 高潮期 | orange |
| diffusion | 扩散期 | purple |
| recession | 退潮期 | gray |
| unknown | 未知 | slate |

### 3.3 PaginationInfo（分页信息）

```python
@dataclass
class PaginationInfo:
    """分页信息"""
    current_page: int
    page_size: int
    total_items: int
    total_pages: int
    has_prev: bool
    has_next: bool
```

---

## 4. 配置数据结构

### 4.1 GuiConfig（GUI配置）

```python
@dataclass
class GuiConfig:
    """GUI配置"""
    refresh_interval: int = 60     # 刷新间隔（秒）
    default_page_size: int = 50    # 默认分页大小
    top_n_recommendations: int = 10  # Dashboard推荐数
    top_n_industries: int = 5      # Dashboard行业数
    mss_history_days: int = 60     # MSS历史天数
```

### 4.2 FilterConfig（过滤配置）

```python
@dataclass
class FilterConfig:
    """默认过滤配置"""
    # Dashboard
    dashboard_min_score: float = 60.0
    # IRS
    irs_max_rank: int = 10
    irs_rotation_status: List[str] = field(default_factory=lambda: ["IN"])
    # PAS
    pas_min_score: float = 60.0
    pas_min_level: str = "B"
    # 集成推荐
    integrated_min_score: float = 70.0
    integrated_min_position: float = 0.05
```

### 4.3 PermissionConfig（权限配置）

```python
@dataclass
class PermissionConfig:
    """权限配置"""
    # Viewer: 只读查看
    # Analyst: 可导出
    # Admin: 可调整显示参数（非交易参数）
    level: str = "Analyst"
    can_export: bool = True
    can_adjust_display: bool = False
```

---

## 5. 输入数据依赖（L3/L4层）

### 5.1 核心数据表

| 数据表 | 用途 | 页面 |
|--------|------|------|
| mss_panorama | MSS温度/周期/趋势 | Dashboard, MSS |
| irs_industry_daily | 行业评分/轮动 | Dashboard, IRS |
| stock_pas_daily | 个股评分/方向 | PAS |
| integrated_recommendation | 集成推荐 | Dashboard, 集成推荐 |
| trade_records | 交易记录 | Trading |
| positions | 持仓 | Trading |
| backtest_results | 回测结果 | Analysis |
| daily_report | 日报 | Analysis |
| performance_metrics | 绩效指标 | Analysis |

### 5.2 字段映射

| GUI字段 | 数据源 | 转换 |
|---------|--------|------|
| temperature_color | mss_panorama.temperature | 分级算法 |
| cycle_label | mss_panorama.cycle | 中英文映射 |
| trend_icon | mss_panorama.trend | 图标映射 |
| status_color | irs_industry_daily.rotation_status | IN→绿色 |
| level_color | stock_pas_daily.opportunity_grade | S→金色 |
| integration_mode_badge | integrated_recommendation.integration_mode | 模式中文映射 |
| pnl_color | positions.unrealized_pnl | >0→红色，<0→绿色，=0→灰色（A股红涨绿跌） |

---

## 6. 枚举定义

### 6.1 TemperatureLevel（温度等级）

```python
class TemperatureLevel(Enum):
    HIGH = "high"       # > 80
    MEDIUM = "medium"   # 45-80
    COOL = "cool"       # 30-44
    LOW = "low"         # < 30
```

### 6.2 RecommendationLevel（推荐等级）

```python
class RecommendationLevel(Enum):
    STRONG_BUY = "STRONG_BUY"  # ≥ 75（且 mss_cycle ∈ {emergence, fermentation}）
    BUY = "BUY"                # 70-74（或不满足 STRONG_BUY 附加条件）
    HOLD = "HOLD"              # 50-69
    SELL = "SELL"              # 30-49
    AVOID = "AVOID"            # < 30
```

### 6.3 OpportunityLevel（机会等级）

```python
class OpportunityLevel(Enum):
    S = "S"  # 顶级机会
    A = "A"  # 优质机会
    B = "B"  # 普通机会
    C = "C"  # 低优先
    D = "D"  # 规避
```

### 6.4 RotationStatus（轮动状态）

```python
class RotationStatus(Enum):
    IN = "IN"         # 轮入
    OUT = "OUT"       # 轮出
    HOLD = "HOLD"     # 观望
```

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.1.7 | 2026-02-09 | 修复 R26：`DashboardData/RecommendationItem` 增加 `integration_mode` 与 `integration_mode_badge` 展示字段；§5.2 补充模式映射来源 |
| v3.1.6 | 2026-02-09 | 修复 R22：补充 `IntegratedPageData`；明确 `neutrality_percent` 为中性度百分比；`pnl_color` 补齐持平分支（gray） |
| v3.1.5 | 2026-02-08 | 修复 R15：新增 `BacktestSummaryDisplay`；`pnl_color` 改为 A 股红涨绿跌口径；`ChartZone` 增加边界包含约定字段 |
| v3.1.4 | 2026-02-08 | 复查修正：TemperatureLevel 阈值改为 30/45/80 并补充 `COOL`，与 `gui-algorithm.md` 保持一致 |
| v3.1.3 | 2026-02-07 | 修复 R9：RecommendationLevel 注释阈值对齐 75/70-74；温度颜色口径补充 cyan；CycleBadge 增加 UNKNOWN 映射 |
| v3.1.2 | 2026-02-07 | 同步 GUI 算法 v3.1.2 的推荐等级口径 |
| v3.1.0 | 2026-02-04 | 版本对齐：GUI 文档统一 v3.1.0 |
| v3.0.0 | 2026-01-31 | 重构版：统一数据模型定义 |
| v2.1.0 | 2026-01-23 | 增加图表数据结构 |
| v2.0.0 | 2026-01-20 | 初始版本 |

---

**关联文档**：
- 核心算法：[gui-algorithm.md](./gui-algorithm.md)
- API接口：[gui-api.md](./gui-api.md)
- 信息流：[gui-information-flow.md](./gui-information-flow.md)


