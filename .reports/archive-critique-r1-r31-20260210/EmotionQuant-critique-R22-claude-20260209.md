# EmotionQuant R22 深度审查报告

**审查时间**: 2026-02-09  
**审查轮次**: R22  
**审查范围**: GUI 模块四位一体（algorithm, data-models, api, information-flow）  
**审查角度**: 内部一致性 + 上游契约对齐 + 导出路径规范  

---

## 审查概要

| 类型 | 数量 |
|------|------|
| P1（必须修复） | 5 |
| P2（建议修复） | 5 |
| **总计** | **10** |

---

## P1 级问题（5 项）

### **P1-R22-01: GUI Algorithm §7.1 温度曲线 zones 边界约定与 Data-Models §2.1 ChartZone 字段定义不一致**

**位置**：
- `gui-algorithm.md` line 302-318
- `gui-data-models.md` line 256-266

**问题描述**：
- **Algorithm §7.1** line 302-318 温度曲线数据转换返回 `zones` 列表，每个 zone 包含 `{min, max, include_min, include_max, color}`
- **Data-Models §2.1** line 256-266 定义 `ChartZone` 数据类使用字段名 `min_value, max_value, include_min, include_max, color, label`
- **断裂 1**：算法返回 `min/max`，但数据类定义 `min_value/max_value`
- **断裂 2**：算法未返回 `label` 字段，但数据类包含该字段

**影响**：实现时字段名不匹配，导致数据类实例化失败或 `label` 字段未填充。

**建议修正**：
```python
# gui-algorithm.md §7.1 统一字段名

def transform_temperature_chart(mss_history):
    """
    温度曲线数据转换

    Returns:
        {
            "x_axis": ["20260101", "20260102", ...],
            "y_axis": [45.5, 48.2, ...],
            "zones": [
                {"min_value": 0, "max_value": 30, "include_min": True, "include_max": False, "color": "blue", "label": "冰点"},
                {"min_value": 30, "max_value": 45, "include_min": True, "include_max": False, "color": "cyan", "label": "冷却"},
                {"min_value": 45, "max_value": 80, "include_min": True, "include_max": True, "color": "orange", "label": "中性"},
                {"min_value": 80, "max_value": 100, "include_min": False, "include_max": True, "color": "red", "label": "过热"}
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

**修复状态**：❌ 待修复

---

### **P1-R22-02: GUI API §2.6 get_integrated_page_data 返回类型 `IntegratedPageData` 但 Data-Models 未定义该数据类**

**位置**：
- `gui-api.md` line 148-170
- `gui-data-models.md` 全文

**问题描述**：
- **API §2.6** line 157 声明返回 `IntegratedPageData: 集成推荐页面数据`
- **Data-Models** 全文搜索未发现 `IntegratedPageData` 数据类定义
- **缺口**：API 承诺的返回类型在数据模型中不存在

**影响**：实现时无法实例化返回类型，导致编译或运行时错误。

**建议修正**：
```python
# gui-data-models.md 补充定义

### 1.9 IntegratedPageData（集成推荐页面）

```python
@dataclass
class IntegratedPageData:
    """集成推荐页面数据"""
    trade_date: str
    recommendations: List[RecommendationItem]
    pagination: PaginationInfo
```
```

**修复状态**：❌ 待修复

---

### **P1-R22-03: GUI Algorithm §2.1 温度颜色分级逻辑与 §2.2 推荐等级分级中 mss_cycle 使用的周期枚举不一致**

**位置**：
- `gui-algorithm.md` line 57
- `gui-data-models.md` line 20

**问题描述**：
- **Algorithm §2.2** line 57 推荐等级分级使用 `mss_cycle in ("emergence", "fermentation")`
- **Data-Models §1.1 DashboardData** line 20 `cycle` 字段注释包含 `unknown` 枚举值
- **断裂**：算法未处理 `cycle = "unknown"` 的情况

**影响**：当 `mss_cycle = "unknown"` 时，推荐等级分级逻辑可能产生意外结果（`STRONG_BUY` 条件永远不满足）。

**建议修正**：
```python
# gui-algorithm.md §2.2 增加 unknown 处理说明

if final_score >= 75 and mss_cycle in ("emergence", "fermentation"):
    return ("STRONG_BUY", "high")    # 强推荐
# 注：cycle = "unknown" 时不满足 STRONG_BUY 条件，按 final_score 降级
elif final_score >= 70:
    return ("BUY", "medium")         # 买入
```

**修复状态**：❌ 待修复

---

### **P1-R22-04: GUI API §5.1 export_to_csv 返回路径格式与 Algorithm §8.1 不一致**

**位置**：
- `gui-api.md` line 416
- `gui-algorithm.md` line 403

**问题描述**：
- **API §5.1** line 416 返回路径示例：`.reports/gui/{filename}_{YYYYMMDD_HHMMSS}.csv`
- **Algorithm §8.1** line 403 返回路径格式：`.reports/gui/{filename}_{report_ts}.csv`
- **不一致**：API 使用占位符 `{YYYYMMDD_HHMMSS}`，算法使用变量 `{report_ts}`，但算法 line 402 定义 `report_ts = now().strftime("%Y%m%d_%H%M%S")`
- **实际格式差异**：`%Y%m%d_%H%M%S` → `20260209_012345`，但 API 示例 `{YYYYMMDD_HHMMSS}` 容易被理解为 `20260209_HHMMSS`

**影响**：文档表述混淆，可能导致实现时时间戳格式错误。

**建议修正**：
```python
# gui-api.md §5.1 统一格式说明

Returns:
    str: 导出文件路径（.reports/gui/{filename}_{timestamp}.csv）
         timestamp 格式：YYYYMMDD_HHMMSS（如 20260209_012345）
```

**修复状态**：❌ 待修复

---

### **P1-R22-05: GUI Data-Models §1.6 StockPasDisplay 字段 `neutrality_percent` 计算逻辑与注释 "数值越小信号越强" 语义混淆**

**位置**：
- `gui-data-models.md` line 130-131

**问题描述**：
- **Line 130** 定义 `neutrality: float  # [0-1]（越接近1越中性，越接近0信号越极端）`
- **Line 131** 定义 `neutrality_percent: int  # [0-100] 数值越小信号越强`
- **语义断裂**：`neutrality_percent` 按字面意义是百分比形式的中性度（应该数值越大越中性），但注释说"数值越小信号越强"，暗示该字段实际是"极端度百分比"或"信号强度"，而非"中性度百分比"

**影响**：
1. 字段命名误导（`neutrality_percent` 实际表示极端度）
2. 实现时可能计算错误（`neutrality_percent = neutrality * 100` vs `neutrality_percent = (1 - neutrality) * 100`）

**建议修正**：
```python
# gui-data-models.md §1.6 改为一致语义

neutrality: float             # [0-1]（越接近1越中性，越接近0信号越极端）
neutrality_percent: int       # [0-100] 中性度百分比（数值越大越中性，越小信号越强）
                             # 计算方式：int(neutrality * 100)
```

或改名为 `extremity_percent`：
```python
neutrality: float             # [0-1]（越接近1越中性，越接近0信号越极端）
extremity_percent: int        # [0-100] 极端度百分比（数值越大信号越强）
                             # 计算方式：int((1 - neutrality) * 100)
```

**修复状态**：❌ 待修复

---

## P2 级问题（5 项）

### **P2-R22-06: GUI Algorithm §4.1 默认过滤条件 PAS 与 Data-Models §4.2 FilterConfig 默认值不一致**

**位置**：
- `gui-algorithm.md` line 158
- `gui-data-models.md` line 382

**问题描述**：
- **Algorithm §4.1** line 158 PAS 默认过滤：`opportunity_grade in ("S","A","B")`
- **Data-Models §4.2** line 382 FilterConfig 默认：`pas_min_level: str = "B"`
- **不一致**：算法说"SAB都显示"，配置说"B以上显示"（含B），两者等价但表述不同

**影响**：文档理解混淆，可能导致实现时逻辑不一致。

**建议修正**：
```python
# gui-algorithm.md §4.1 统一表述

| PAS个股 | opportunity_score >= 60, opportunity_grade >= "B" （即 S/A/B） |
```

**修复状态**：❌ 待修复

---

### **P2-R22-07: GUI Information-Flow §3.1 温度卡片示例注释遗漏 `< 30` 分支说明**

**位置**：
- `gui-information-flow.md` line 236-242

**问题描述**：
- **Line 236-242** 温度卡片数据流示例注释说明了 `> 80`, `>= 45`, `>= 30` 三个分支
- **缺少 `< 30` 分支**：注释未说明当温度 < 30 时返回 `blue/冰点`

**影响**：文档不完整，可能被误解为只有三段分级。

**建议修正**：
```markdown
# gui-information-flow.md §3.1

│  FormatterService              │
│  format_temperature(65.5)      │
│                                │
│  - 65.5 > 80? No              │
│  - 65.5 >= 45? Yes → orange   │
│  - (若未命中上支) >= 30? → cyan │
│  - (若仍未命中) < 30 → blue     │  -- 补充此行
```

**修复状态**：❌ 待修复

---

### **P2-R22-08: GUI API §4.2 format_cycle 参数列表遗漏 `unknown` 枚举值**

**位置**：
- `gui-api.md` line 321
- `gui-data-models.md` line 337

**问题描述**：
- **API §4.2** line 321 `format_cycle` 参数 `cycle` 列出 7 个周期：`emergence/fermentation/acceleration/divergence/climax/diffusion/recession`
- **Data-Models §3.2** line 337 CycleBadge 映射表包含 8 个周期，增加 `unknown → 未知 → slate`
- **缺口**：API 文档未说明如何处理 `cycle = "unknown"`

**影响**：实现时可能遗漏 `unknown` 处理分支。

**建议修正**：
```python
# gui-api.md §4.2

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

**修复状态**：❌ 待修复

---

### **P2-R22-09: GUI Algorithm §6.2 缓存键生成示例与 API §7.3 build_cache_key 返回格式不一致**

**位置**：
- `gui-algorithm.md` line 264-268
- `gui-api.md` line 595

**问题描述**：
- **Algorithm §6.2** line 264 缓存键格式：`{data_type}:{trade_date}:{hash(filters)}`
- **Algorithm §6.2** line 267 示例 1：`mss_panorama:20260131:none`（无过滤器时使用字符串 `"none"`）
- **API §7.3** line 595 示例：`mss_panorama:20260131:none`（未说明 `none` 是占位符还是 `hash(None)` 结果）
- **不一致**：算法使用 `hash(filters)` 但示例使用 `none` 字符串，未说明映射规则

**影响**：实现时可能使用 `str(hash(None))` 而非 `"none"`，导致缓存键不一致。

**建议修正**：
```python
# gui-algorithm.md §6.2

cache_key = f"{data_type}:{trade_date}:{hash(filters) if filters else 'none'}"

示例:
- "mss_panorama:20260131:none"                     # filters 为 None 或空
- "integrated_recommendation:20260131:abc123def"  # filters 非空时使用 hash 值
```

**修复状态**：❌ 待修复

---

### **P2-R22-10: GUI Data-Models §1.7 PositionDisplay 字段 `pnl_color` 注释 "red (盈) / green (亏)" 与 A 股红涨绿跌约定一致但未说明逻辑**

**位置**：
- `gui-data-models.md` line 167

**问题描述**：
- **Line 167** `pnl_color: str  # red (盈) / green (亏)`
- **语义正确**：符合 A 股红涨绿跌约定
- **缺口**：未说明计算逻辑（`unrealized_pnl > 0 → red, unrealized_pnl < 0 → green, unrealized_pnl = 0 → ?`）

**影响**：实现时可能遗漏 `pnl = 0` 的情况。

**建议修正**：
```python
# gui-data-models.md §1.7

pnl_color: str                # red (盈利 > 0) / green (亏损 < 0) / gray (持平 = 0)
```

**修复状态**：❌ 待修复

---

## 修复优先级建议

### 立即修复（P1）
1. **P1-R22-01**: Algorithm 温度曲线 zones 字段名改为 `min_value/max_value` 并补充 `label`
2. **P1-R22-02**: Data-Models 补充 `IntegratedPageData` 数据类定义
3. **P1-R22-03**: Algorithm 推荐等级分级增加 `cycle = "unknown"` 处理说明
4. **P1-R22-04**: API `export_to_csv` 返回路径格式统一为 `YYYYMMDD_HHMMSS`
5. **P1-R22-05**: Data-Models `neutrality_percent` 改名或改注释消除语义混淆

### 建议修复（P2）
6. **P2-R22-06**: Algorithm PAS 默认过滤表述改为 `>= "B"` 统一配置
7. **P2-R22-07**: Info-Flow 温度卡片示例补充 `< 30 → blue` 分支
8. **P2-R22-08**: API `format_cycle` 参数列表补充 `unknown` 枚举值
9. **P2-R22-09**: Algorithm 缓存键生成明确 `hash(None) → "none"` 映射规则
10. **P2-R22-10**: Data-Models `pnl_color` 补充 `pnl = 0 → gray` 说明

---

## 审查结论

**GUI 模块四位一体文档整体质量良好**，已完成多轮修正（v3.1.x），但仍存在以下典型问题：

1. **Algorithm ↔ Data-Models 字段名不一致**：`ChartZone` 字段名 `min/max` vs `min_value/max_value`
2. **API 返回类型缺失**：`IntegratedPageData` 未定义
3. **枚举值处理缺口**：`cycle = "unknown"` 在多处算法中未说明处理逻辑
4. **文档表述不一致**：时间戳格式、过滤条件、缓存键生成规则多处表述混乱
5. **字段语义混淆**：`neutrality_percent` 命名与注释不匹配

建议优先修复 **P1 级 5 项**，确保数据类定义完整、字段名一致、枚举值处理逻辑清晰。

---

**下一步**：
- 用户修复上述问题后提交，Agent 进入 R22 验证
- R23 继续审查 **Validation 模块四位一体**

---

**报告生成时间**: 2026-02-09  
**Agent**: Claude (Warp)  
**审查轮次**: R22 / 预计 26-27 轮总计
