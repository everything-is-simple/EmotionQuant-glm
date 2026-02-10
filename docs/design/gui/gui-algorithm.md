# GUI 核心算法

**版本**: v3.1.6（重构版）
**最后更新**: 2026-02-09
**状态**: 设计完成（代码未落地）

---

## 1. 算法定位

GUI层是系统的展示与交互层，核心职责：

1. **数据可视化**：将算法输出转化为可读的图表和指标
2. **信号展示**：MSS/IRS/PAS/集成推荐的直观呈现
3. **风控概览**：持仓、盈亏、风险指标一览
4. **只读展示**：遵循系统铁律，不引入技术指标计算

**运行形态**：Streamlit 为正式 GUI；Jupyter 仅用于内部原型/探索（不作为生产界面）。

**重要约束**：GUI层不执行任何算法计算，所有数据来自L3/L4层预计算结果。
**色彩约定**：遵循 A 股红涨绿跌（盈利/上涨用红色，亏损/下跌用绿色）。

---

## 2. 指标分级算法

### 2.1 温度颜色分级

```
输入: temperature (0-100)
输出: color_class, severity

if temperature > 80:
    return ("red", "high")      # 过热警示（与 MSS/Integration 阈值一致）
elif temperature >= 45:
    return ("orange", "medium") # 常温偏热
elif temperature >= 30:
    return ("cyan", "cool")     # 冷却区（介于冰点与发酵下界）
else:
    return ("blue", "low")      # 冰点区（<30）
```

显示规则：
| 温度范围 | 颜色 | 标签 | 建议 |
|----------|------|------|------|
| > 80 | 红色 | 过热 | 注意风险 |
| 45-80 | 橙色 | 中性 | 正常关注 |
| 30-44 | 青色 | 冷却 | 谨慎观察 |
| < 30 | 蓝色 | 冰点 | 观望为主 |

### 2.2 推荐等级分级

```
输入: final_score (0-100), mss_cycle
输出: recommendation_level, priority

if final_score >= 75 and mss_cycle in ("emergence", "fermentation"):
    return ("STRONG_BUY", "high")    # 强推荐
elif final_score >= 70:
    return ("BUY", "medium")         # 买入
elif final_score >= 50:
    return ("HOLD", "medium")        # 持有
elif final_score >= 30:
    return ("SELL", "low")           # 卖出
else:
    return ("AVOID", "low")          # 回避

# 说明：当 cycle="unknown" 时，不满足 STRONG_BUY 的周期附加条件，
# 会按 final_score 落入 BUY/HOLD/SELL/AVOID 分支。
```

显示规则：
| 评分范围 | 等级 | 优先级 | 显示 |
|----------|------|--------|------|
| ≥ 75（且mss_cycle∈{emergence,fermentation}） | STRONG_BUY | high | 红色强调 |
| 70-74（或不满足STRONG_BUY附加条件） | BUY | medium | 默认显示 |
| 50-69 | HOLD | medium | 默认显示 |
| 30-49 | SELL | low | 灰色淡化 |
| < 30 | AVOID | low | 灰色淡化 |

### 2.3 轮动状态分级

```
输入: rotation_status
输出: display_class, visibility

if rotation_status == "IN":
    return ("highlight", True)   # 高亮显示
elif rotation_status == "HOLD":
    return ("normal", True)      # 正常显示
else:  # OUT
    return ("muted", False)      # 灰色淡显
```

### 2.4 机会等级分级

```
输入: opportunity_grade (S/A/B/C/D)
输出: badge_class, color

mapping = {
    "S": ("premium", "gold"),
    "A": ("high", "green"),
    "B": ("medium", "blue"),
    "C": ("low", "gray"),
    "D": ("avoid", "red")
}
return mapping.get(opportunity_grade, ("unknown", "gray"))
```

---

## 3. 列表排序算法

### 3.1 默认排序规则

| 页面 | 主排序字段 | 方向 | 次排序 |
|------|------------|------|--------|
| Dashboard推荐 | final_score | DESC | stock_code ASC |
| MSS历史 | trade_date | DESC | - |
| IRS行业 | rank | ASC | industry_score DESC |
| PAS个股 | opportunity_score | DESC | neutrality ASC |
| 集成推荐 | final_score | DESC | position_size DESC |
| 交易记录 | trade_date | DESC | trade_id DESC |
| 持仓列表 | market_value | DESC | unrealized_pnl DESC |

### 3.2 排序算法

```
输入: items, sort_fields, directions
输出: sorted_items

def multi_sort(items, sort_fields, directions):
    """
    多字段排序

    Args:
        items: 待排序列表
        sort_fields: 排序字段列表
        directions: 排序方向列表 (ASC/DESC)
    """
    for i in range(len(sort_fields) - 1, -1, -1):
        field = sort_fields[i]
        reverse = directions[i] == "DESC"
        items = sorted(items, key=lambda x: x[field], reverse=reverse)
    return items
```

---

## 4. 过滤算法

### 4.1 默认过滤条件

| 页面 | 过滤条件 |
|------|----------|
| Dashboard | final_score >= 60, top_n = 10 |
| MSS曲线 | 近60交易日 |
| IRS行业 | rank <= 10, rotation_status IN ("IN") |
| PAS个股 | opportunity_score >= 60, opportunity_grade >= "B"（即 S/A/B） |
| 集成推荐 | final_score >= 70, position_size >= 0.05 |
| 交易执行 | trade_date = 最新交易日 |
| 分析报告 | report_date = 最新交易日 |

### 4.2 过滤链算法

```
输入: items, filters
输出: filtered_items

def apply_filters(items, filters):
    """
    链式过滤

    Args:
        items: 待过滤列表
        filters: 过滤条件列表
            [
                {"field": "final_score", "op": ">=", "value": 60},
                {"field": "rotation_status", "op": "in", "value": ["IN"]}
            ]
    """
    result = items
    for f in filters:
        field, op, value = f["field"], f["op"], f["value"]
        if op == ">=":
            result = [x for x in result if x[field] >= value]
        elif op == "<=":
            result = [x for x in result if x[field] <= value]
        elif op == "==":
            result = [x for x in result if x[field] == value]
        elif op == "in":
            result = [x for x in result if x[field] in value]
        elif op == "range":
            result = [x for x in result if value[0] <= x[field] <= value[1]]
    return result
```

---

## 5. 分页算法

### 5.1 分页参数

```python
@dataclass
class PaginationConfig:
    """分页配置"""
    default_page_size: int = 50
    page_size_options: List[int] = field(default_factory=lambda: [20, 50, 100])
    max_page_size: int = 100
```

### 5.2 分页计算

```
输入: items, page, page_size
输出: paged_items, pagination_info

def paginate(items, page, page_size):
    """
    分页计算

    Args:
        items: 全部数据
        page: 当前页码（从1开始）
        page_size: 每页条数

    Returns:
        paged_items: 当前页数据
        pagination_info: 分页信息
    """
    total = len(items)
    total_pages = (total + page_size - 1) // page_size
    start = (page - 1) * page_size
    end = min(start + page_size, total)

    return {
        "items": items[start:end],
        "pagination": {
            "current_page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages
        }
    }
```

---

## 6. 缓存策略

### 6.1 缓存时间规则

| 数据类型 | 缓存时间 | 说明 |
|----------|----------|------|
| L3日度数据 | 24小时 | mss_panorama, irs_industry_daily等 |
| 交易执行数据 | 1分钟 | trade_records, positions |
| 分析报告 | 24小时 | daily_report, performance_metrics |
| 配置数据 | 会话级 | 用户设置、筛选条件 |

### 6.2 缓存键生成

```
cache_key = f"{data_type}:{trade_date}:{hash(filters) if filters else 'none'}"

示例:
- "mss_panorama:20260131:none"
- "integrated_recommendation:20260131:abc123def"

说明:
- 当 filters 为 None/空时，固定使用 `"none"` 作为占位符。
- 当 filters 非空时，使用 `hash(filters)` 结果作为摘要段。
```

### 6.3 缓存失效

```
def should_refresh(cache_entry, data_type):
    """判断是否需要刷新缓存"""
    ttl = CACHE_TTL[data_type]
    age = now() - cache_entry.created_at
    return age > ttl
```

---

## 7. 图表数据转换

zone 边界约定：默认采用左闭右开 `[min, max)`；最高温区使用 `(80, 100]`，与 §2.1 的 `>80` 阈值一致。

### 7.1 温度曲线数据

```
输入: mss_history (List[MssPanorama])
输出: chart_data

def transform_temperature_chart(mss_history):
    """
    温度曲线数据转换

    Returns:
        {
            "x_axis": ["20260101", "20260102", ...],
            "y_axis": [45.5, 48.2, ...],
            "zones": [
            {"min_value": 0, "max_value": 30, "include_min": True, "include_max": False, "color": "blue", "label": "冰点"},      # [0, 30)
            {"min_value": 30, "max_value": 45, "include_min": True, "include_max": False, "color": "cyan", "label": "冷却"},     # [30, 45)
            {"min_value": 45, "max_value": 80, "include_min": True, "include_max": True, "color": "orange", "label": "中性"},    # [45, 80]
            {"min_value": 80, "max_value": 100, "include_min": False, "include_max": True, "color": "red", "label": "过热"}      # (80, 100]
        ]
    }
    """
    return {
        "x_axis": [m.trade_date for m in mss_history],
        "y_axis": [m.temperature for m in mss_history],
        "zones": [
            {"min_value": 0, "max_value": 30, "include_min": True, "include_max": False, "color": "blue", "label": "冰点"},
            {"min_value": 30, "max_value": 45, "include_min": True, "include_max": False, "color": "cyan", "label": "冷却"},
            {"min_value": 45, "max_value": 80, "include_min": True, "include_max": True, "color": "orange", "label": "中性"},
            {"min_value": 80, "max_value": 100, "include_min": False, "include_max": True, "color": "red", "label": "过热"}
        ]
    }
```

### 7.2 行业排名图表

```
输入: irs_industries (List[IrsIndustryDaily])
输出: chart_data

def transform_industry_rank_chart(irs_industries):
    """
    行业排名柱状图数据

    Returns:
        {
            "x_axis": ["银行", "电子", ...],
            "y_axis": [85.2, 78.5, ...],
            "colors": ["green", "green", ...]
        }
    """
    # 按评分排序取Top N
    sorted_industries = sorted(irs_industries, key=lambda x: x.industry_score, reverse=True)[:10]

    return {
        "x_axis": [i.industry_name for i in sorted_industries],
        "y_axis": [i.industry_score for i in sorted_industries],
        "colors": [
            "green" if i.rotation_status == "IN" else "gray"
            for i in sorted_industries
        ]
    }
```

### 7.3 推荐散点图

```
输入: recommendations (List[IntegratedRecommendation])
输出: chart_data

def transform_recommendation_scatter(recommendations):
    """
    推荐分布散点图

    X轴: final_score
    Y轴: position_size
    """
    return {
        "points": [
            {
                "x": r.final_score,
                "y": r.position_size,
                "label": r.stock_code,
                "color": get_score_color(r.final_score)
            }
            for r in recommendations
        ],
        "x_label": "综合评分",
        "y_label": "建议仓位"
    }
```

---

## 8. 导出算法

### 8.1 CSV导出

```
输入: data, columns, filename
输出: csv_content

def export_csv(data, columns, filename):
    """
    导出CSV文件

    Args:
        data: 数据列表
        columns: 导出列配置
            [{"field": "stock_code", "header": "股票代码"}, ...]
        filename: 文件名模板

    Returns:
        path: 导出文件路径
    """
    report_ts = now().strftime("%Y%m%d_%H%M%S")
    path = f".reports/gui/{filename}_{report_ts}.csv"

    headers = [c["header"] for c in columns]
    rows = [[item[c["field"]] for c in columns] for item in data]

    write_csv(path, headers, rows)
    return path
```

### 8.2 Markdown导出

```
输入: report_data, template
输出: md_content

def export_markdown(report_data, template="daily_report"):
    """
    导出Markdown报告

    Returns:
        path: 导出文件路径
    """
    report_ts = now().strftime("%Y%m%d_%H%M%S")
    path = f".reports/gui/{template}_{report_ts}.md"
    content = render_template(template, report_data)
    write_file(path, content)
    return path
```

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.1.6 | 2026-02-09 | 修复 R22：统一 `ChartZone` 字段为 `min_value/max_value` 并补充 `label`；明确 `unknown` 周期降级逻辑；统一 PAS 默认过滤表述与缓存键占位符规则 |
| v3.1.5 | 2026-02-08 | 修复 R16：`STRONG_BUY` 显示语义由“绿色强调”改为“红色强调”，对齐 A 股红涨绿跌约定 |
| v3.1.4 | 2026-02-08 | 修复 R15：补充 A 股红涨绿跌色彩约定；温度 `zones` 增加 `include_min/include_max` 并明确边界契约 |
| v3.1.3 | 2026-02-07 | 修复 R9：温度颜色阈值对齐 MSS/Integration（30/80）并新增 30-45 冷却区（cyan/cool） |
| v3.1.2 | 2026-02-07 | 同步 Integration 推荐等级口径：STRONG_BUY 阈值 75，并明确 BUY 覆盖区间 |
| v3.1.1 | 2026-02-05 | 更新系统铁律表述 |
| v3.1.0 | 2026-02-04 | 明确 Streamlit 正式 GUI、Jupyter 原型定位 |
| v3.0.0 | 2026-01-31 | 重构版：统一算法描述 |
| v2.1.0 | 2026-01-23 | 增加图表数据转换算法 |
| v2.0.0 | 2026-01-20 | 初始版本 |

---

**关联文档**：
- 数据模型：[gui-data-models.md](./gui-data-models.md)
- API接口：[gui-api.md](./gui-api.md)
- 信息流：[gui-information-flow.md](./gui-information-flow.md)


