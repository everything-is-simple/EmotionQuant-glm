# ROADMAP Phase 08｜图形界面（GUI）

**版本**: v4.0.1
**创建日期**: 2026-01-31
**最后更新**: 2026-02-06
**时间范围**: Phase 08
**核心交付**: 数据可视化、筛选功能、导出功能
**前置依赖**: Phase 01-07
**实现状态**: 未实现（截至 2026-02-06：`src/` 仅有 Skeleton/占位与少量基础骨架，详见 `Governance/ROADMAP/ROADMAP-OVERVIEW.md`）

---
## 文档对齐声明

> **权威设计文档**: `docs/design/gui/`

---

## 1. Phase 目标与量化验收标准

> **一句话**: 提供直观的数据可视化与交互界面

### 1.1 量化验收指标

| 指标项 | 验收标准 | 测量方法 | 优先级 |
|--------|----------|----------|--------|
| 页面加载时间 | ≤ 3秒 | 性能测试 | P0 |
| 图表渲染时间 | ≤ 1秒 | 性能测试 | P0 |
| 分页数据加载 | ≤ 500ms | 性能测试 | P1 |
| 筛选响应时间 | ≤ 500ms | 性能测试 | P1 |
| 导出成功率 | 100% | 功能测试 | P0 |
| 跨浏览器兼容 | Chrome/Firefox/Edge | 兼容性测试 | P1 |
| 测试覆盖率 | ≥ 70% | pytest-cov | P2 |

### 1.2 里程碑检查点

| 里程碑 | 交付物 | 验收条件 | 预期时间 |
|--------|--------|----------|----------|
| M8.1 | MSS市场全景视图 | 温度趋势图+周期指示 | Task 1 |
| M8.2 | IRS行业轮动视图 | 行业排名表+状态标识 | Task 2 |
| M8.3 | PAS个股推荐视图 | 推荐列表+评分分布 | Task 3 |
| M8.4 | 筛选与导出 | 多维筛选+CSV/Excel导出 | Task 4 |

---

## 2. 输入规范

### 2.1 数据依赖矩阵

| 输入表/接口 | 来源 | 关键字段 | 更新频率 | 必需 |
|-------------|------|----------|----------|------|
| mss_panorama | Phase 02 | temperature, cycle, trend | 每交易日 | ✅ |
| irs_industry_daily | Phase 03 | industry_score, rotation_status, rank | 每交易日 | ✅ |
| stock_pas_daily | Phase 04 | opportunity_score, opportunity_grade | 每交易日 | ✅ |
| integrated_recommendation | Phase 05 | final_score, recommendation | 每交易日 | ✅ |
| backtest_results | Phase 06 | 绩效指标 | 按需 | ⚠️可选 |
| positions | Phase 07 | 持仓信息 | 实时 | ⚠️可选 |

### 2.2 筛选条件输入

```python
@dataclass
class FilterCriteria:
    """筛选条件"""
    start_date: str = None       # 开始日期 YYYYMMDD
    end_date: str = None         # 结束日期 YYYYMMDD
    industry_codes: List[str] = None  # 行业代码列表
    min_score: float = None      # 最低评分
    max_score: float = None      # 最高评分
    grades: List[str] = None     # 等级列表 S/A/B/C/D
    recommendations: List[str] = None  # 推荐等级列表
    page: int = 1                # 页码
    page_size: int = 50          # 每页数量
```

### 2.3 输入验证规则

| 验证项 | 规则 | 错误处理 |
|--------|------|----------|
| start_date | ≤ end_date | 使用默认范围 |
| page | ≥ 1 | 设为1 |
| page_size | ∈ [10, 100] | 截断到边界 |
| min_score | ∈ [0, 100] | 截断到边界 |

---

## 3. 核心功能

### 3.1 MSS 市场全景视图

```python
class MSSView:
    """市场全景视图"""
    
    def render_temperature_chart(self, days: int = 30) -> Chart:
        """
        渲染温度趋势图
        
        图表要素：
        - X轴：日期
        - Y轴：温度 [0-100]
        - 色带：过冷(<30)/中性(30-70)/过热(>70)
        - 周期标注：7个周期阶段
        """
        pass
    
    def render_cycle_indicator(self, trade_date: str) -> Widget:
        """渲染周期指示器"""
        pass
    
    def render_trend_status(self, trade_date: str) -> Widget:
        """渲染趋势状态"""
        pass
```

### 3.2 IRS 行业轮动视图

```python
class IRSView:
    """行业轮动视图"""
    
    def render_industry_ranking(self, trade_date: str, top_n: int = 31) -> Table:
        """
        渲染行业排名表
        
        列：
        - 排名
        - 行业名称
        - 行业评分 [0-100]
        - 轮动状态 (IN/OUT/HOLD)
        - 评分变化
        """
        pass
    
    def render_industry_heatmap(self, trade_date: str) -> Chart:
        """渲染行业热力图"""
        pass
    
    def render_rotation_timeline(self, industry_code: str, days: int = 30) -> Chart:
        """渲染行业轮动时间线"""
        pass
```

### 3.3 PAS/Integration 个股推荐视图

```python
class StockView:
    """个股推荐视图"""
    
    def render_recommendation_list(
        self, 
        trade_date: str, 
        filter_criteria: FilterCriteria
    ) -> PaginatedTable:
        """
        渲染推荐列表
        
        列：
        - 股票代码
        - 股票名称
        - 行业
        - 综合评分 [0-100]
        - 推荐等级 (STRONG_BUY/BUY/HOLD/SELL/AVOID)
        - MSS/IRS/PAS分项评分
        - 建议操作
        """
        pass
    
    def render_score_distribution(self, trade_date: str) -> Chart:
        """渲染评分分布图"""
        pass
    
    def render_stock_detail(self, stock_code: str, trade_date: str) -> Panel:
        """渲染个股详情"""
        pass
```

### 3.4 筛选功能

```python
class FilterComponent:
    """筛选组件"""
    
    def render_date_range_picker(self) -> Widget:
        """日期范围选择器"""
        pass
    
    def render_industry_selector(self) -> Widget:
        """行业选择器（31行业多选）"""
        pass
    
    def render_score_slider(self) -> Widget:
        """评分区间滑块"""
        pass
    
    def render_grade_checkbox(self) -> Widget:
        """等级复选框 S/A/B/C/D"""
        pass
    
    def render_recommendation_checkbox(self) -> Widget:
        """推荐等级复选框"""
        pass
```

### 3.5 导出功能

```python
class ExportService:
    """导出服务"""
    
    def export_to_csv(self, data: List[Dict], filename: str) -> bytes:
        """导出为CSV"""
        pass
    
    def export_to_excel(self, data: List[Dict], filename: str) -> bytes:
        """导出为Excel"""
        pass
    
    def export_filtered_results(
        self, 
        filter_criteria: FilterCriteria, 
        format: str = 'csv'
    ) -> bytes:
        """导出筛选结果"""
        pass
```

---

## 4. 输出规范

### 4.1 API 响应格式

```python
@dataclass
class PaginatedResponse:
    """分页响应"""
    data: List[Dict]             # 数据列表
    total: int                   # 总记录数
    page: int                    # 当前页
    page_size: int               # 每页数量
    total_pages: int             # 总页数

@dataclass
class ChartData:
    """图表数据"""
    chart_type: str              # 图表类型 line/bar/heatmap/pie
    title: str                   # 标题
    x_axis: List[str]            # X轴数据
    y_axis: List[float]          # Y轴数据
    series: List[Dict]           # 数据系列
    options: Dict                # 图表选项
```

### 4.2 导出文件格式

| 格式 | 扩展名 | 编码 | 最大行数 |
|------|--------|------|----------|
| CSV | .csv | UTF-8 with BOM | 100000 |
| Excel | .xlsx | - | 100000 |

### 4.3 输出验证规则

| 字段 | 验证规则 | 错误处理 |
|------|----------|----------|
| total | ≥ 0 | 设为0 |
| page | ≤ total_pages | 设为最后一页 |
| 导出数据 | 不为空 | 提示无数据 |

---

## 5. API 接口规范

```python
class GUIAPI:
    """GUI API 接口"""
    
    # MSS
    def get_mss_temperature_history(self, days: int = 30) -> ChartData:
        """获取市场温度历史"""
        pass
    
    def get_mss_current(self, trade_date: str = None) -> Dict:
        """获取当前市场状态"""
        pass
    
    # IRS
    def get_industry_ranking(self, trade_date: str = None) -> List[Dict]:
        """获取行业排名"""
        pass
    
    def get_industry_history(self, industry_code: str, days: int = 30) -> ChartData:
        """获取行业历史数据"""
        pass
    
    # 个股
    def get_recommendations(
        self, 
        trade_date: str = None,
        filter_criteria: FilterCriteria = None
    ) -> PaginatedResponse:
        """获取推荐列表"""
        pass
    
    def get_stock_detail(self, stock_code: str, trade_date: str = None) -> Dict:
        """获取个股详情"""
        pass
    
    # 导出
    def export_data(
        self, 
        data_type: str,
        filter_criteria: FilterCriteria = None,
        format: str = 'csv'
    ) -> bytes:
        """导出数据"""
        pass
```

---

## 6. 错误处理策略

### 6.1 错误分类与处理

| 错误场景 | 错误码 | 严重等级 | 处理策略 | 用户提示 |
|----------|--------|----------|----------|----------|
| 数据加载失败 | GUI_E001 | P1 | 重试3次 | "数据加载失败，请稍后重试" |
| 无数据 | GUI_E002 | P2 | 显示空状态 | "无符合条件的数据" |
| 筛选参数无效 | GUI_E003 | P2 | 使用默认值 | 记录警告 |
| 导出失败 | GUI_E004 | P1 | 重试3次 | "导出失败，请稍后重试" |
| 数据量过大 | GUI_E005 | P2 | 限制数据量 | "数据量过大，请缩小筛选范围" |

### 6.2 前端错误处理

```python
# 统一错误响应格式
@dataclass
class ErrorResponse:
    error_code: str
    message: str
    details: str = None
    retry_after: int = None  # 重试等待秒数
```

---

## 7. 质量监控

### 7.1 质量检查项

| 检查项 | 检查方法 | 预期结果 | 告警阈值 |
|--------|----------|----------|----------|
| 页面加载时间 | 性能监控 | ≤ 3秒 | > 3秒 |
| API响应时间 | 性能监控 | ≤ 500ms | > 1秒 |
| 错误率 | 日志统计 | < 1% | > 1% |
| 数据一致性 | 对账检查 | 与数据库一致 | 不一致 |

---

## 8. 执行计划

### 8.1 Task 级别详细计划

---

#### Task 1: MSS市场全景视图

**目标**: 实现市场温度趋势图和周期指示器

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| mss_panorama | Phase 02 | 数据存在 | 显示空状态 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| MSSView | 组件 | 温度图渲染 | `src/gui/` |
| TemperatureChart | 组件 | 趋势图+色带 | `src/gui/` |
| CycleIndicator | 组件 | 7周期指示 | `src/gui/` |
| TrendStatus | 组件 | 趋势状态 | `src/gui/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 渲染时间 | ≤1秒 | 性能测试 |
| 数据展示 | 温度/周期/趋势正确 | 功能测试 |
| 色带标注 | 过冷/中性/过热 | 视觉检查 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 数据加载失败 | 重试3次 | 显示错误提示 |
| 无数据 | 显示空状态 | 记录信息 |

**验收检查**

- [ ] 温度趋势图正确展示
- [ ] 周期指示器正确
- [ ] 趋势状态正确
- [ ] 色带标注正确

---

#### Task 2: IRS行业轮动视图

**目标**: 实现行业排名表和轮动状态展示

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| irs_industry_daily | Phase 03 | 31行业数据 | 显示空状态 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| IRSView | 组件 | 行业视图 | `src/gui/` |
| IndustryRankingTable | 组件 | 排名表 | `src/gui/` |
| RotationStatusBadge | 组件 | IN/OUT/HOLD标识 | `src/gui/` |
| IndustryHeatmap | 组件 | 热力图 | `src/gui/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 排名展示 | 31行业完整 | 功能测试 |
| 状态标识 | IN/OUT/HOLD正确 | 视觉检查 |
| 排序功能 | 按评分/排名排序 | 功能测试 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 数据加载失败 | 重试3次 | 显示错误提示 |
| 行业数据不全 | 显示现有数据 | 记录警告 |

**验收检查**

- [ ] 行业排名表正确展示
- [ ] 轮动状态标识正确
- [ ] 排序功能正常
- [ ] 热力图渲染正确

---

#### Task 3: PAS个股推荐视图

**目标**: 实现个股推荐列表和分页加载

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| stock_pas_daily | Phase 04 | 数据存在 | 显示空状态 |
| integrated_recommendation | Phase 05 | 数据存在 | 可为空 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| StockView | 组件 | 个股视图 | `src/gui/` |
| RecommendationList | 组件 | 推荐列表 | `src/gui/` |
| PaginationControl | 组件 | 分页控件 | `src/gui/` |
| ScoreDistribution | 组件 | 评分分布图 | `src/gui/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 分页加载 | ≤500ms | 性能测试 |
| 列表展示 | 评分/等级/方向正确 | 功能测试 |
| 页面大小 | 默认50，最大100 | 功能测试 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 数据加载失败 | 重试3次 | 显示错误提示 |
| 无数据 | 显示空状态 | 记录信息 |

**验收检查**

- [ ] 推荐列表正确展示
- [ ] 分页加载正常
- [ ] 评分分布图正确
- [ ] 页面大小可配置

---

#### Task 4: 筛选与导出

**目标**: 实现多维筛选和数据导出功能

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| 所有视图组件 | Task 1-3 | 测试通过 | 阻断 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| FilterComponent | 组件 | 多维筛选 | `src/gui/` |
| DateRangePicker | 组件 | 日期选择 | `src/gui/` |
| IndustrySelector | 组件 | 行业多选 | `src/gui/` |
| ExportService | 服务 | CSV/Excel导出 | `src/services/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 筛选响应 | ≤500ms | 性能测试 |
| 导出成功 | 100% | 功能测试 |
| 跨浏览器 | Chrome/Firefox/Edge | 兼容性测试 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 导出失败 | 重试3次 | 显示错误提示 |
| 数据量过大 | 限制10万行 | 提示缩小范围 |

**验收检查**

- [ ] 多维筛选功能可用
- [ ] CSV导出正确
- [ ] Excel导出正确
- [ ] 跨浏览器兼容
- [ ] **M8里程碑完成**

---

## 9. 验收检查清单

### 9.1 功能验收

- [ ] MSS温度趋势图正确展示
- [ ] MSS周期/趋势指示器正常
- [ ] IRS行业排名表正确展示
- [ ] IRS轮动状态标识正确
- [ ] 个股推荐列表正确展示
- [ ] 分页加载正常
- [ ] 多维筛选功能可用
- [ ] CSV导出正确
- [ ] Excel导出正确

### 9.2 性能验收

- [ ] 页面加载 ≤ 3秒
- [ ] 图表渲染 ≤ 1秒
- [ ] 分页加载 ≤ 500ms
- [ ] 筛选响应 ≤ 500ms

### 9.3 质量验收

- [ ] 测试覆盖率 ≥ 70%
- [ ] 跨浏览器兼容
- [ ] 响应式布局

---

## 10. 参数配置表

### 10.1 默认配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 默认页大小 | 50 | 每页显示数量 |
| 最大页大小 | 100 | 最大每页数量 |
| 图表默认天数 | 30 | 图表默认时间范围 |
| 导出最大行数 | 100000 | 导出数据上限 |
| 缓存时间 | 5分钟 | 静态数据缓存 |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v4.0.1 | 2026-02-04 | 元数据日期更新 |
| v4.0.0 | 2026-02-02 | 完整重构：添加量化验收标准、I/O规范、视图设计、API规范 |
| v3.0.0 | 2026-01-31 | 重构版 |


