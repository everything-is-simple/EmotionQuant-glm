# GUI API 接口

**版本**: v3.1.3（重构版）
**最后更新**: 2026-02-09
**状态**: 设计完成（代码未落地）

---

## 1. 模块结构

**运行形态**：Streamlit 为正式 GUI；Jupyter 仅用于内部原型/探索（不作为生产界面）。

```
gui/
├── pages/
│   ├── dashboard.py       # 总览仪表盘
│   ├── mss.py             # MSS页面
│   ├── irs.py             # IRS页面
│   ├── pas.py             # PAS页面
│   ├── integrated.py      # 集成推荐页面
│   ├── trading.py         # 交易执行页面
│   └── analysis.py        # 分析报告页面
├── components/
│   ├── temperature_card.py
│   ├── cycle_badge.py
│   ├── industry_rank_table.py
│   ├── stock_signal_table.py
│   ├── recommendation_table.py
│   └── risk_overview.py
├── services/
│   └── data_service.py    # 数据服务层
└── utils/
    ├── formatters.py      # 格式化工具
    ├── filters.py         # 过滤工具
    └── exporters.py       # 导出工具
```

---

## 2. DataService（数据服务）

### 2.1 类定义

```python
class DataService:
    """GUI数据服务层（封装DataRepository）"""

    def __init__(self, repository: DataRepository) -> None:
        """
        初始化数据服务

        Args:
            repository: 数据仓库实例
        """
```

### 2.2 get_dashboard_data

```python
def get_dashboard_data(
    self,
    trade_date: str,
    top_n: int = 10
) -> DashboardData:
    """
    获取Dashboard数据

    Args:
        trade_date: 交易日期 (YYYYMMDD)
        top_n: 推荐列表数量

    Returns:
        DashboardData: 仪表盘数据

    Note:
        - 整合MSS/IRS/集成推荐数据
        - 自动进行颜色/等级转换
    """
```

### 2.3 get_mss_page_data

```python
def get_mss_page_data(
    self,
    trade_date: str,
    history_days: int = 60
) -> MssPageData:
    """
    获取MSS页面数据

    Args:
        trade_date: 交易日期
        history_days: 历史天数

    Returns:
        MssPageData: MSS页面数据
            - current: 当日MSS数据
            - history: 历史数据列表
            - chart_data: 图表数据
    """
```

### 2.4 get_irs_page_data

```python
def get_irs_page_data(
    self,
    trade_date: str,
    filters: FilterConfig = None
) -> IrsPageData:
    """
    获取IRS页面数据

    Args:
        trade_date: 交易日期
        filters: 过滤配置

    Returns:
        IrsPageData: IRS页面数据
    """
```

### 2.5 get_pas_page_data

```python
def get_pas_page_data(
    self,
    trade_date: str,
    filters: FilterConfig = None,
    page: int = 1,
    page_size: int = 50
) -> PasPageData:
    """
    获取PAS页面数据

    Args:
        trade_date: 交易日期
        filters: 过滤配置
        page: 页码
        page_size: 每页条数

    Returns:
        PasPageData: PAS页面数据（含分页）
    """
```

### 2.6 get_integrated_page_data

```python
def get_integrated_page_data(
    self,
    trade_date: str,
    filters: FilterConfig = None,
    page: int = 1,
    page_size: int = 50
) -> IntegratedPageData:
    """
    获取集成推荐页面数据

    Args:
        trade_date: 交易日期
        filters: 过滤配置
        page: 页码
        page_size: 每页条数

    Returns:
        IntegratedPageData: 集成推荐页面数据
    """
```

### 2.7 get_trading_page_data

```python
def get_trading_page_data(
    self,
    trade_date: str,
    page: int = 1,
    page_size: int = 50
) -> TradingPageData:
    """
    获取交易页面数据

    Args:
        trade_date: 交易日期
        page: 页码
        page_size: 每页条数

    Returns:
        TradingPageData: 交易页面数据
            - positions: 持仓列表
            - trades: 交易记录
            - pagination: 分页信息
    """
```

### 2.8 get_analysis_page_data

```python
def get_analysis_page_data(
    self,
    report_date: str
) -> AnalysisPageData:
    """
    获取分析页面数据

    Args:
        report_date: 报告日期

    Returns:
        AnalysisPageData: 分析页面数据
            - metrics: 绩效指标
            - daily_report: 日报内容
            - backtest_summary: 回测摘要
    """
```

---

## 3. FilterService（过滤服务）

### 3.1 apply_filters

```python
def apply_filters(
    items: List[dict],
    filters: List[FilterCondition]
) -> List[dict]:
    """
    应用过滤条件

    Args:
        items: 待过滤数据
        filters: 过滤条件列表
            [
                FilterCondition(field="final_score", op=">=", value=60),
                FilterCondition(field="rotation_status", op="==", value="IN")
            ]

    Returns:
        List[dict]: 过滤后数据
    """
```

### 3.2 apply_sort

```python
def apply_sort(
    items: List[dict],
    sort_fields: List[str],
    directions: List[str]
) -> List[dict]:
    """
    应用排序

    Args:
        items: 待排序数据
        sort_fields: 排序字段列表
        directions: 排序方向列表 ("ASC"/"DESC")

    Returns:
        List[dict]: 排序后数据
    """
```

### 3.3 paginate

```python
def paginate(
    items: List[dict],
    page: int,
    page_size: int
) -> Tuple[List[dict], PaginationInfo]:
    """
    分页

    Args:
        items: 全部数据
        page: 页码（从1开始）
        page_size: 每页条数

    Returns:
        Tuple[List[dict], PaginationInfo]: (当前页数据, 分页信息)
    """
```

---

## 4. FormatterService（格式化服务）

### 4.1 format_temperature

```python
def format_temperature(
    temperature: float
) -> TemperatureCardData:
    """
    格式化温度显示

    Args:
        temperature: 温度值 [0-100]

    Returns:
        TemperatureCardData: 温度卡片数据
            - value: 温度值
            - color: 颜色 (red/orange/cyan/blue)
            - label: 标签 (过热/中性/冷却/冰点)
    """
```

### 4.2 format_cycle

```python
def format_cycle(
    cycle: str
) -> CycleBadgeData:
    """
    格式化周期显示

    Args:
        cycle: 周期英文 (emergence/fermentation/acceleration/divergence/climax/diffusion/recession/unknown)

    Returns:
        CycleBadgeData: 周期标签数据
            - cycle: 英文
            - label: 中文
            - color: 颜色
    """
```

### 4.3 format_trend

```python
def format_trend(
    trend: str
) -> Tuple[str, str]:
    """
    格式化趋势显示

    Args:
        trend: 趋势 (up/down/sideways)

    Returns:
        Tuple[str, str]: (图标, 颜色)
            - up: ("↑", "red")
            - down: ("↓", "green")
            - sideways: ("→", "gray")
    """
```

### 4.4 format_percent

```python
def format_percent(
    value: float,
    with_sign: bool = False
) -> str:
    """
    格式化百分比

    Args:
        value: 小数值 (0.152 → "15.2%")
        with_sign: 是否带正负号

    Returns:
        str: 格式化字符串
            - with_sign=True: "+15.2%" / "-8.5%"
            - with_sign=False: "15.2%"
    """
```

### 4.5 format_pnl

```python
def format_pnl(
    value: float
) -> Tuple[str, str]:
    """
    格式化盈亏

    Args:
        value: 盈亏金额

    Returns:
        Tuple[str, str]: (格式化金额, 颜色)
            - 盈利: ("+1,234.56", "red")
            - 亏损: ("-1,234.56", "green")
    """
```

---

## 5. ExportService（导出服务）

### 5.1 export_to_csv

```python
    def export_to_csv(
    data: List[dict],
    columns: List[ColumnConfig],
    filename: str
) -> str:
    """
    导出CSV

    Args:
        data: 数据列表
        columns: 列配置
            [
                ColumnConfig(field="stock_code", header="股票代码"),
                ColumnConfig(field="final_score", header="综合评分")
            ]
        filename: 文件名（不含日期后缀）

    Returns:
        str: 导出文件路径（.reports/gui/{filename}_{timestamp}.csv）
             timestamp 格式：YYYYMMDD_HHMMSS，如 20260209_012345

    Note:
        文件保存至 .reports/gui/{filename}_{timestamp}.csv
    """
```

### 5.2 export_to_markdown

```python
def export_to_markdown(
    content: str,
    filename: str
) -> str:
    """
    导出Markdown

    Args:
        content: Markdown内容
        filename: 文件名

    Returns:
        str: 导出文件路径
    """
```

### 5.3 export_recommendations

```python
def export_recommendations(
    trade_date: str,
    filters: FilterConfig = None
) -> str:
    """
    导出推荐列表

    Args:
        trade_date: 交易日期
        filters: 过滤配置

    Returns:
        str: 导出文件路径
    """
```

### 5.4 export_performance_report

```python
def export_performance_report(
    report_date: str
) -> Tuple[str, str]:
    """
    导出绩效报告

    Args:
        report_date: 报告日期

    Returns:
        Tuple[str, str]: (CSV路径, Markdown路径)
    """
```

---

## 6. ChartService（图表服务）

### 6.1 build_temperature_chart

```python
def build_temperature_chart(
    mss_history: List[MssPanorama]
) -> TemperatureChartData:
    """
    构建温度曲线图表数据

    Args:
        mss_history: MSS历史数据

    Returns:
        TemperatureChartData: 图表数据
            - x_axis: 日期列表
            - y_axis: 温度列表
            - zones: 颜色区域
    """
```

### 6.2 build_industry_chart

```python
def build_industry_chart(
    industries: List[IrsIndustryDaily],
    top_n: int = 10
) -> IndustryChartData:
    """
    构建行业排名图表数据

    Args:
        industries: 行业数据
        top_n: Top N数量

    Returns:
        IndustryChartData: 图表数据
    """
```

### 6.3 build_recommendation_scatter

```python
def build_recommendation_scatter(
    recommendations: List[IntegratedRecommendation]
) -> RecommendationScatterData:
    """
    构建推荐散点图数据

    Args:
        recommendations: 推荐数据

    Returns:
        RecommendationScatterData: 散点图数据
    """
```

---

## 7. CacheService（缓存服务）

### 7.1 get_cached

```python
def get_cached(
    cache_key: str
) -> Optional[Any]:
    """
    获取缓存

    Args:
        cache_key: 缓存键

    Returns:
        Any: 缓存数据，不存在返回None
    """
```

### 7.2 set_cached

```python
def set_cached(
    cache_key: str,
    data: Any,
    ttl: int = None
) -> None:
    """
    设置缓存

    Args:
        cache_key: 缓存键
        data: 缓存数据
        ttl: 过期时间（秒），None使用默认值
    """
```

### 7.3 build_cache_key

```python
def build_cache_key(
    data_type: str,
    trade_date: str,
    filters: FilterConfig = None
) -> str:
    """
    构建缓存键

    Args:
        data_type: 数据类型
        trade_date: 交易日期
        filters: 过滤配置

    Returns:
        str: 缓存键
            示例:
            - "mss_panorama:20260131:none"                  # filters 为 None/空
            - "integrated_recommendation:20260131:abc123def" # filters 非空时摘要段

    Note:
        - 占位符规则：当 filters 为 None/空时，固定使用字符串 "none"
        - 其余情况使用 filters 哈希摘要作为第三段
    """
```

---

## 8. GUI字段→接口参数映射

| 页面 | 组件字段 | API | 参数 |
|------|----------|-----|------|
| Dashboard | temperature | DataService.get_dashboard_data | trade_date |
| Dashboard | top_recommendations | DataService.get_dashboard_data | trade_date, top_n |
| MSS | temperature_history | DataService.get_mss_page_data | trade_date, history_days |
| IRS | industries | DataService.get_irs_page_data | trade_date, filters |
| PAS | stocks | DataService.get_pas_page_data | trade_date, filters, page |
| Integrated | recommendations | DataService.get_integrated_page_data | trade_date, filters, page |
| Trading | positions | DataService.get_trading_page_data | trade_date |
| Trading | trades | DataService.get_trading_page_data | trade_date, page |
| Analysis | metrics | DataService.get_analysis_page_data | report_date |
| Analysis | daily_report | DataService.get_analysis_page_data | report_date |

---

## 9. 完整调用示例

```python
from gui.services.data_service import DataService
from gui.services.filter_service import FilterService
from gui.services.export_service import ExportService
from gui.utils.formatters import FormatterService

# 初始化服务
data_service = DataService(repository)
filter_service = FilterService()
export_service = ExportService()
formatter = FormatterService()

# 获取Dashboard数据
dashboard = data_service.get_dashboard_data(
    trade_date="20260131",
    top_n=10
)

# 格式化温度显示
temp_card = formatter.format_temperature(dashboard.temperature)
print(f"温度: {temp_card.value} ({temp_card.label})")

# 获取PAS数据（带过滤和分页）
filters = FilterConfig(pas_min_score=70)
pas_data = data_service.get_pas_page_data(
    trade_date="20260131",
    filters=filters,
    page=1,
    page_size=50
)

# 导出推荐列表
csv_path = export_service.export_recommendations(
    trade_date="20260131",
    filters=FilterConfig(integrated_min_score=70)
)
print(f"已导出: {csv_path}")
```

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.1.3 | 2026-02-09 | 修复 R22：`build_cache_key` 明确 `filters=None/空 -> \"none\"` 占位符规则，并补充非空过滤器示例 |
| v3.1.1 | 2026-02-08 | 修复 R16：`format_temperature` 补齐 4 色/4 标签；`format_trend` 与 `format_pnl` 颜色改为 A 股红涨绿跌；`export_to_csv` 返回路径后缀修正为 `.csv` |
| v3.1.0 | 2026-02-04 | 明确 Streamlit 正式 GUI、Jupyter 原型定位 |
| v3.0.0 | 2026-01-31 | 重构版：统一API接口定义 |
| v2.1.0 | 2026-01-23 | 增加图表服务和缓存服务 |
| v2.0.0 | 2026-01-20 | 初始版本 |

---

**关联文档**：
- 核心算法：[gui-algorithm.md](./gui-algorithm.md)
- 数据模型：[gui-data-models.md](./gui-data-models.md)
- 信息流：[gui-information-flow.md](./gui-information-flow.md)


