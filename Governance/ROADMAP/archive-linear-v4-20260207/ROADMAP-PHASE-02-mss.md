# ROADMAP Phase 02｜市场情绪全景（MSS）

**版本**: v4.0.2
**创建日期**: 2026-01-31
**最后更新**: 2026-02-06
**时间范围**: Phase 02
**核心交付**: MSS算法实现、温度计算、周期判断、仓位建议
**前置依赖**: Phase 01 (Data Layer)
**实现状态**: 未实现（截至 2026-02-06：`src/` 仅有 Skeleton/占位与少量基础骨架，详见 `Governance/ROADMAP/ROADMAP-OVERVIEW.md`）

---
## 文档对齐声明

> **权威设计文档**: `docs/design/core-algorithms/mss/`
> - 算法：`mss-algorithm.md`
> - 数据模型：`mss-data-models.md`
> - API：`mss-api.md`
> - 信息流：`mss-information-flow.md`

---

## 1. Phase 目标与量化验收标准

> **一句话**: 实现市场情绪温度测量，判断周期阶段，输出仓位建议

### 1.1 量化验收指标

| 指标项 | 验收标准 | 测量方法 | 优先级 |
|--------|----------|----------|--------|
| 温度计算精度 | 温度值∈[0,100]，精度4位小数 | 单元测试边界检查 | P0 |
| 周期判断准确率 | 7阶段状态机正确率≥99% | 历史回测对照验证 | P0 |
| 趋势识别正确率 | up/down/sideways判断≥95% | 滑动窗口验证 | P0 |
| 因子得分范围 | 所有因子∈[0,100] | 范围断言测试 | P0 |
| 数据完整性 | 每交易日1条mss_panorama记录 | COUNT检查 | P0 |
| 代码覆盖率 | ≥80%（含分支覆盖） | pytest-cov | P1 |
| 计算延迟 | 单日计算≤5秒 | 性能测试 | P1 |
| 历史回填 | 2015-01-01至今无缺失 | 日期连续性校验 | P1 |

### 1.2 里程碑检查点

| 里程碑 | 交付物 | 验收条件 | 预期时间 |
|--------|--------|----------|----------|
| M2.1 | 基础因子计算 | 大盘系数/赚钱效应/亏钱效应测试通过 | Task 1 |
| M2.2 | 增强因子计算 | 连续性/极端/波动因子测试通过 | Task 2 |
| M2.3 | 温度与周期 | 温度公式+周期状态机验证通过 | Task 3 |
| M2.4 | 落库与API | mss_panorama全量落库+API可用 | Task 4 |

---

## 2. 输入规范

### 2.1 数据依赖矩阵

| 输入表/接口 | 来源 | 关键字段 | 更新频率 | 必需 |
|-------------|------|----------|----------|------|
| market_snapshot | Phase 01 L2 | rise_count, fall_count, total_stocks | 每交易日 | ✅ |
| market_snapshot | Phase 01 L2 | limit_up_count, limit_down_count, touched_limit_up | 每交易日 | ✅ |
| market_snapshot | Phase 01 L2 | new_100d_high_count, new_100d_low_count | 每交易日 | ✅ |
| market_snapshot | Phase 01 L2 | strong_up_count, strong_down_count | 每交易日 | ✅ |
| raw_daily | Phase 01 L1 | pct_chg（计算派生字段） | 每交易日 | ✅ |
| raw_trade_cal | Phase 01 L1 | is_open（交易日判断） | 年度 | ✅ |

### 2.2 MssMarketSnapshot 输入字段规范

```python
@dataclass
class MssMarketSnapshot:
    """MSS 每日市场快照（输入）"""
    trade_date: str              # 交易日期 YYYYMMDD，非空
    
    # 基础统计（必需）
    total_stocks: int            # 可交易股票总数，>0
    rise_count: int              # 上涨家数（pct_chg > 0），≥0
    fall_count: int              # 下跌家数（pct_chg < 0），≥0
    flat_count: int              # 平盘家数，≥0
    
    # 涨跌停统计（必需）
    limit_up_count: int          # 涨停家数，≥0
    limit_down_count: int        # 跌停家数，≥0
    touched_limit_up: int        # 触及涨停家数（含炸板），≥limit_up_count
    
    # 新高新低统计（必需）
    new_100d_high_count: int     # 100日新高家数，≥0
    new_100d_low_count: int      # 100日新低家数，≥0
    
    # 大涨大跌统计（必需）
    strong_up_count: int         # 涨幅>5%家数，≥0
    strong_down_count: int       # 跌幅<-5%家数，≥0
    
    # 连续性统计（增强因子，可选）
    continuous_limit_up_2d: int  # 连续2日涨停家数，≥0
    continuous_limit_up_3d_plus: int  # 连续3日+涨停家数，≥0
    continuous_new_high_2d_plus: int  # 连续2日+新高家数，≥0
    
    # 极端行为统计（增强因子，可选）
    high_open_low_close_count: int  # 高开低走且跌幅<-6%，≥0
    low_open_high_close_count: int  # 低开高走且涨幅>6%，≥0
    
    # 波动统计（增强因子，可选）
    pct_chg_std: float           # 全市场涨跌幅标准差，≥0
    amount_volatility: float     # 成交额波动率（相对20日均值）
```

### 2.3 输入验证规则

| 验证项 | 规则 | 错误处理 |
|--------|------|----------|
| total_stocks | > 0 | 抛出 ValueError |
| rise_count + fall_count + flat_count | ≤ total_stocks | 记录警告日志 |
| limit_up_count | ≤ touched_limit_up | 自动修正为 touched_limit_up |
| pct_chg_std | ≥ 0 | 设为 0 并记录警告 |
| trade_date | 必须是交易日 | 跳过计算 |

---

## 3. 核心算法（权威口径）

### 3.1 六因子体系

| 类别 | 因子名称 | 权重 | 取值范围 | 说明 |
|------|----------|------|----------|------|
| **基础因子** | 大盘系数 | 20% | [0,100] | 市场多空力量对比 |
| | 赚钱效应 | 40% | [0,100] | 多头力量强度 |
| | 亏钱效应 | 40% | [0,100] | 空头压力（反向使用） |
| **增强因子** | 连续性因子 | 5% | [0,100] | 趋势持续性 |
| | 极端因子 | 5% | [0,100] | 极端情绪状态 |
| | 波动因子 | 5% | [0,100] | 市场波动程度 |

> **权重分配原则**: 基础因子 85%，增强因子 15%
> **增强因子可选**: 不启用时直接使用基础温度

### 3.2 基础因子公式

> **统一规则**：所有 count 必须先转为 ratio（0-1），再做 Z-Score 归一化；禁止使用 ×100/×1000 等硬编码放大系数。

```python
# 大盘系数（20%权重）
market_coefficient_raw = rise_count / total_stocks
market_coefficient = zscore_normalize(market_coefficient_raw, mean, std)

# 赚钱效应（40%权重）
limit_up_ratio = limit_up_count / total_stocks
new_high_ratio = new_100d_high_count / total_stocks
strong_up_ratio = strong_up_count / total_stocks
profit_effect_raw = 0.4 * limit_up_ratio + 0.3 * new_high_ratio + 0.3 * strong_up_ratio
profit_effect = zscore_normalize(profit_effect_raw, mean, std)

# 亏钱效应（40%权重，反向使用）
broken_rate = (touched_limit_up - limit_up_count) / max(touched_limit_up, 1)
limit_down_ratio = limit_down_count / total_stocks
strong_down_ratio = strong_down_count / total_stocks
new_low_ratio = new_100d_low_count / total_stocks
loss_effect_raw = (
    0.3 * broken_rate
    + 0.2 * limit_down_ratio
    + 0.3 * strong_down_ratio
    + 0.2 * new_low_ratio
)
loss_effect = zscore_normalize(loss_effect_raw, mean, std)
```

### 3.3 增强因子公式

```python
# 连续性因子（5%权重）
continuous_limit_up_ratio = (
    continuous_limit_up_2d + 2 * continuous_limit_up_3d_plus
) / max(limit_up_count, 1)
continuous_new_high_ratio = continuous_new_high_2d_plus / max(new_100d_high_count, 1)
continuity_factor_raw = (
    0.5 * continuous_limit_up_ratio + 0.5 * continuous_new_high_ratio
)
continuity_factor = zscore_normalize(continuity_factor_raw, mean, std)

# 极端因子（5%权重）
high_open_low_close_ratio = high_open_low_close_count / total_stocks
low_open_high_close_ratio = low_open_high_close_count / total_stocks
extreme_factor_raw = high_open_low_close_ratio + low_open_high_close_ratio
extreme_factor = zscore_normalize(extreme_factor_raw, mean, std)

# 波动因子（5%权重）
volatility_factor_raw = 0.5 * pct_chg_std + 0.5 * amount_volatility
volatility_factor = zscore_normalize(volatility_factor_raw, mean, std)

# Z-Score 归一化方法
def zscore_normalize(value: float, mean: float, std: float) -> float:
    """Z-Score归一化并映射到0-100"""
    if std == 0:
        return 50.0
    z = (value - mean) / std
    return max(0.0, min(100.0, (z + 3) / 6 * 100))
```

### 3.4 温度计算公式

```python
# 基础温度（必选）
base_temperature = market_coefficient × 0.2 + profit_effect × 0.4 + (100 - loss_effect) × 0.4

# 完整温度（含增强因子）
temperature = base_temperature × 0.85 + continuity_factor × 0.05 + extreme_factor × 0.05 + volatility_factor × 0.05

# 边界约束
temperature = max(0.0, min(100.0, temperature))
```

### 3.5 周期状态机（优先级判定）

| 优先级 | 周期 | 英文代码 | 温度条件 | 趋势条件 | 仓位建议 |
|--------|------|----------|----------|----------|----------|
| 1（最高） | 高潮期 | climax | ≥75 | any | 20%-40% |
| 2 | 萌芽期 | emergence | <30 | up | 80%-100% |
| 3 | 发酵期 | fermentation | 30-45 | up | 60%-80% |
| 4 | 加速期 | acceleration | 45-60 | up | 50%-70% |
| 5 | 分歧期 | divergence | 60-75 | up/sideways | 40%-60% |
| 6 | 扩散期 | diffusion | 60-75 | down | 30%-50% |
| 7（最低） | 退潮期 | recession | <60 | down | 0%-20% |

```python
def detect_cycle(temperature: float, trend: str) -> str:
    """周期判定逻辑（按优先级顺序）"""
    # 优先级1：高潮期
    if temperature >= 75:
        return "climax"
    
    # 优先级2-5：上升趋势
    if trend == "up":
        if temperature < 30:
            return "emergence"
        if temperature < 45:
            return "fermentation"
        if temperature < 60:
            return "acceleration"
        return "divergence"  # 60-75，上升
    
    # 优先级5：横盘
    if trend == "sideways":
        return "divergence"
    
    # 优先级6-7：下降趋势
    if trend == "down":
        if temperature >= 60:
            return "diffusion"
        return "recession"
    
    return "unknown"
```

### 3.6 趋势判定规则

| 趋势 | 英文代码 | 判定条件 | 窗口 |
|------|----------|----------|------|
| 上升 | up | 连续N日温度上升 | N=3 |
| 下降 | down | 连续N日温度下降 | N=3 |
| 横盘 | sideways | 其他情况 | - |

### 3.7 中性度计算

```python
neutrality = 1 - abs(temperature - 50) / 50
# 语义：越接近50越中性（中性度高），越极端越低
# 取值范围: [0, 1]
```

---

## 4. 输出规范

### 4.1 MssPanorama 输出字段规范

```python
@dataclass
class MssPanorama:
    """MSS 每日计算结果（输出）"""
    trade_date: str              # 交易日期 YYYYMMDD
    
    # 核心输出（必需）
    temperature: float           # 市场温度 [0,100]
    cycle: str                   # 情绪周期（英文代码）
    trend: str                   # 趋势方向 up/down/sideways
    position_advice: str         # 仓位建议 "80%-100%" 等
    
    # 因子得分（调试用）
    market_coefficient: float    # 大盘系数得分 [0,100]
    profit_effect: float         # 赚钱效应得分 [0,100]
    loss_effect: float           # 亏钱效应得分 [0,100]
    continuity_factor: float     # 连续性因子得分 [0,100]
    extreme_factor: float        # 极端因子得分 [0,100]
    volatility_factor: float     # 波动因子得分 [0,100]
    
    # 辅助信息
    neutrality: float            # 中性度 [0,1]
    rank: int                    # 历史排名
    percentile: float            # 百分位排名 [0,100]
```

### 4.2 数据库表结构（DuckDB DDL）

```sql
CREATE TABLE mss_panorama (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date VARCHAR(8) NOT NULL,
    
    -- 核心输出
    temperature DECIMAL(8,4) NOT NULL CHECK(temperature >= 0 AND temperature <= 100),
    cycle VARCHAR(20) NOT NULL CHECK(cycle IN ('emergence','fermentation','acceleration','divergence','climax','diffusion','recession','unknown')),
    trend VARCHAR(20) NOT NULL CHECK(trend IN ('up','down','sideways')),
    position_advice VARCHAR(20),
    
    -- 因子得分
    market_coefficient DECIMAL(8,4) CHECK(market_coefficient >= 0 AND market_coefficient <= 100),
    profit_effect DECIMAL(8,4) CHECK(profit_effect >= 0 AND profit_effect <= 100),
    loss_effect DECIMAL(8,4) CHECK(loss_effect >= 0 AND loss_effect <= 100),
    continuity_factor DECIMAL(8,4),
    extreme_factor DECIMAL(8,4),
    volatility_factor DECIMAL(8,4),
    
    -- 辅助信息
    neutrality DECIMAL(8,4) CHECK(neutrality >= 0 AND neutrality <= 1),
    rank INTEGER,
    percentile DECIMAL(8,4) CHECK(percentile >= 0 AND percentile <= 100),
    
    -- 元数据
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME,
    
    UNIQUE(trade_date)
);

CREATE INDEX idx_mss_temperature ON mss_panorama(temperature);
CREATE INDEX idx_mss_cycle ON mss_panorama(cycle);
CREATE INDEX idx_mss_trade_date ON mss_panorama(trade_date);
```

### 4.3 输出验证规则

| 字段 | 验证规则 | 错误处理 |
|------|----------|----------|
| temperature | 0 ≤ x ≤ 100 | 截断到边界 |
| cycle | IN ('emergence', 'fermentation', 'acceleration', 'divergence', 'climax', 'diffusion', 'recession') | 设为 'unknown' |
| trend | IN ('up', 'down', 'sideways') | 设为 'sideways' |
| neutrality | 0 ≤ x ≤ 1 | 截断到边界 |
| 每日记录数 | = 1 | 幂等插入 |

---

## 5. API 接口规范

### 5.1 核心接口定义

```python
class MssCalculator:
    """MSS 计算器接口"""
    
    def calculate(self, trade_date: str) -> MssPanorama:
        """
        计算指定日期的 MSS 全景数据
        
        Args:
            trade_date: 交易日期 YYYYMMDD
        Returns:
            MssPanorama 对象
        Raises:
            ValueError: 非交易日或输入数据缺失
            DataNotReadyError: 依赖数据未就绪
        """
        pass
    
    def batch_calculate(self, start_date: str, end_date: str) -> List[MssPanorama]:
        """
        批量计算日期范围内的 MSS 数据
        
        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
        Returns:
            MssPanorama 列表（按日期升序）
        """
        pass
    
    def get_latest(self) -> MssPanorama:
        """获取最新一日的 MSS 数据"""
        pass
    
    def get_temperature(self, trade_date: str) -> float:
        """获取指定日期的温度值"""
        pass
    
    def get_cycle(self, trade_date: str) -> str:
        """获取指定日期的周期阶段"""
        pass
    
    def get_position_advice(self, trade_date: str) -> str:
        """获取指定日期的仓位建议"""
        pass


class MssRepository:
    """MSS 数据仓库接口"""
    
    def save(self, panorama: MssPanorama) -> None:
        """保存单条记录（幂等）"""
        pass
    
    def save_batch(self, panoramas: List[MssPanorama]) -> int:
        """批量保存，返回实际插入/更新条数"""
        pass
    
    def get_by_date(self, trade_date: str) -> Optional[MssPanorama]:
        """按日期查询"""
        pass
    
    def get_by_date_range(self, start_date: str, end_date: str) -> List[MssPanorama]:
        """按日期范围查询"""
        pass
    
    def get_latest_n(self, n: int = 30) -> List[MssPanorama]:
        """获取最近N条记录"""
        pass
```

---

## 6. 错误处理策略

### 6.1 错误分类与处理

| 错误场景 | 错误码 | 严重等级 | 处理策略 | 重试 |
|----------|--------|----------|----------|------|
| market_snapshot 缺失 | MSS_E001 | P0 | 抛出异常，阻断流程 | 否 |
| total_stocks = 0 | MSS_E002 | P0 | 抛出异常，记录错误日志 | 否 |
| 温度计算溢出 | MSS_E003 | P1 | 截断到[0,100]，记录警告 | 否 |
| 周期判定失败 | MSS_E004 | P1 | 设为'unknown'，记录警告 | 否 |
| 趋势判定数据不足 | MSS_E005 | P2 | 设为'sideways'，记录信息 | 否 |
| 数据库写入失败 | MSS_E006 | P0 | 重试3次后抛出异常 | ✅(3次) |
| Z-Score统计参数缺失 | MSS_E007 | P2 | 使用默认值(mean=0,std=1)，记录警告 | 否 |
| 历史数据不足(<120日) | MSS_E008 | P2 | 降级为基础因子模式，记录警告 | 否 |

### 6.2 重试策略

```python
MSS_RETRY_CONFIG = {
    "db_write": {
        "max_retries": 3,
        "base_delay": 1.0,  # 秒
        "exponential": True,
        "max_delay": 10.0
    }
}

def retry_db_operation(func):
    """数据库操作重试装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        config = MSS_RETRY_CONFIG["db_write"]
        for attempt in range(config["max_retries"]):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt < config["max_retries"] - 1:
                    delay = min(
                        config["base_delay"] * (2 ** attempt),
                        config["max_delay"]
                    )
                    logger.warning(f"DB操作失败，{delay}秒后重试: {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"DB操作失败，已达最大重试次数: {e}")
                    raise
    return wrapper
```

### 6.3 预警规则

| 预警类型 | 触发条件 | 预警等级 | 处理建议 |
|----------|----------|----------|----------|
| 过热预警 | temperature ≥ 80 | WARN | 建议降低风险暴露 |
| 过冷预警 | temperature ≤ 20 | INFO | 关注反转机会 |
| 趋势背离 | trend 与 cycle 不一致 | WARN | 需人工复核 |
| 极端涨停 | limit_up_count > 200 | INFO | 市场过热信号 |

---

## 7. 质量监控

### 7.1 每日质量检查项

| 检查项 | 检查方法 | 预期结果 | 告警阈值 |
|--------|----------|----------|----------|
| 记录完整性 | COUNT(*) WHERE trade_date = ? | = 1 | ≠ 1 |
| 温度范围 | temperature | ∈ [0, 100] | 越界 |
| 周期有效性 | cycle | ∈ 7个有效值 | 无效值 |
| 因子得分范围 | 各因子得分 | ∈ [0, 100] | 越界 |
| 连续性 | 与前一交易日间隔 | ≤ 1个交易日 | 缺失 |

### 7.2 质量监控表

```sql
CREATE TABLE mss_quality_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date VARCHAR(8) NOT NULL,
    check_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- 检查结果
    record_count INTEGER,
    temperature_valid BOOLEAN,
    cycle_valid BOOLEAN,
    factors_valid BOOLEAN,
    continuity_valid BOOLEAN,
    
    -- 异常信息
    error_code VARCHAR(20),
    error_message TEXT,
    
    -- 状态
    status VARCHAR(20) DEFAULT 'PASS',  -- PASS/WARN/FAIL
    
    UNIQUE(trade_date)
);
```

---

## 8. 执行计划

### 8.1 Task 级别详细计划

---

#### Task 1: 基础因子实现

**目标**: 实现大盘系数、赚钱效应、亏钱效应三个基础因子

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| market_snapshot | Phase 01 | 字段非空 | 阻断 |
| raw_limit_list | Phase 01 | 数据存在 | 阻断 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| MarketCoefficientCalculator | 代码 | 输出∈[0,100] | `src/algorithms/mss/` |
| ProfitEffectCalculator | 代码 | 测试覆盖≥80% | `src/algorithms/mss/` |
| LossEffectCalculator | 代码 | 测试覆盖≥80% | `src/algorithms/mss/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 因子范围 | [0,100] | 边界测试 |
| 权重分配 | 20%+40%+40% | 单元测试 |
| 公式正确 | 与设计文档一致 | 代码审查 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| total_stocks=0 | 抛出异常 | 立即阻断 |
| 分母为零 | 返回默认值50 | 记录警告 |

**验收检查**

- [ ] 大盘系数计算正确
- [ ] 赚钱效应计算正确
- [ ] 亏钱效应计算正确
- [ ] 所有因子∈[0,100]

---

#### Task 2: 增强因子实现

**目标**: 实现连续性、极端、波动三个增强因子

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| market_snapshot | Phase 01 | 字段非空 | 阻断 |
| 历史数据120日 | Phase 01 | 用于Z-Score | 使用默认均值 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| ContinuityCalculator | 代码 | Z-Score归一化正确 | `src/algorithms/mss/` |
| ExtremeCalculator | 代码 | 输出∈[0,100] | `src/algorithms/mss/` |
| VolatilityCalculator | 代码 | 测试覆盖≥80% | `src/algorithms/mss/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| Z-Score范围 | [-3,+3]→[0,100] | 边界测试 |
| 权重分配 | 5%+5%+5%=15% | 单元测试 |
| 历史窗口 | 120日默认 | 参数配置检查 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 历史数据<120日 | 降级为基础模式 | 记录警告 |
| 标准差=0 | 返回50 | 记录警告 |

**验收检查**

- [ ] Z-Score归一化正确
- [ ] 三个增强因子输出正确
- [ ] 数据不足时降级处理

---

#### Task 3: 温度与周期

**目标**: 实现温度计算、7阶段周期判断、趋势识别

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| 基础因子 | Task 1 | 计算完成 | 阻断 |
| 增强因子 | Task 2 | 计算完成 | 使用基础模式 |
| 历史温度3日 | 自身 | 用于趋势判断 | 设为sideways |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| TemperatureCalculator | 代码 | 输出∈[0,100] | `src/algorithms/mss/` |
| CycleDetector | 代码 | 7阶段状态机正确 | `src/algorithms/mss/` |
| TrendDetector | 代码 | up/down/sideways | `src/algorithms/mss/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 温度范围 | [0,100] | 边界测试 |
| 周期覆盖 | 7种 | DISTINCT检查 |
| 历史验证 | ≥95%准确 | 对比验证 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 温度越界 | 截断到[0,100] | 记录警告 |
| 周期判定失败 | 设为unknown | 记录错误 |
| 趋势数据不足 | 设为sideways | 记录信息 |

**验收检查**

- [ ] 温度公式正确（基础×0.85+增强×0.15）
- [ ] 周期状态机优先级正确
- [ ] 趋势判定连续3日规则
- [ ] 历史数据对比验证通过

---

#### Task 4: 集成与落库

**目标**: 集成MSS计算器、实现数据落库和质量监控

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| 所有因子计算器 | Task 1-3 | 测试通过 | 阻断 |
| DuckDB连接 | Phase 01 | 可连接 | 阻断 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| MssCalculator | 代码 | 全流程测试通过 | `src/algorithms/mss/` |
| MssRepository | 代码 | 幂等写入 | `src/algorithms/mss/` |
| mss_panorama表 | 数据 | 每交易日1条 | L3 DuckDB（按年分库） |
| 质量监控 | 代码 | 5项检查 | `scripts/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 覆盖率 | ≥80% | `pytest --cov` |
| 数据完整 | 每日1条 | COUNT检查 |
| 幂等性 | 重复写入不报错 | 单元测试 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| DB写入失败 | 重试3次 | 失败后抛异常 |
| 数据重复 | 覆盖写入 | 记录日志 |

**验收检查**

- [ ] MssCalculator全流程测试
- [ ] mss_panorama表数据完整
- [ ] 测试覆盖率≥80%
- [ ] **M2里程碑完成**

### 8.2 每日执行时序

```text
17:00  market_snapshot 数据就绪（Phase 01）
  ↓
17:05  触发 MSS 计算
  ↓
17:05  加载 MssMarketSnapshot
  ↓
17:06  计算基础因子（大盘系数、赚钱效应、亏钱效应）
  ↓
17:07  计算增强因子（如启用）
  ↓
17:08  计算温度
  ↓
17:08  判定趋势
  ↓
17:08  判定周期
  ↓
17:09  写入 mss_panorama
  ↓
17:10  质量检查
  ↓
17:10  MSS 计算完成，通知 Phase 03 (IRS)
```

---

## 9. 验收检查清单

### 9.1 功能验收

- [ ] 大盘系数计算正确（`rise_count / total_stocks` → `zscore_normalize`）
- [ ] 赚钱效应计算正确（涨停分×0.4 + 新高分×0.3 + 表现分×0.3）
- [ ] 亏钱效应计算正确（炸板分×0.3 + 跌停分×0.2 + 大跌分×0.3 + 新低分×0.2）
- [ ] 温度计算正确（基础×0.85 + 增强×0.15）
- [ ] 周期判断准确（7阶段状态机，优先级正确）
- [ ] 趋势识别正确（连续3日判定）
- [ ] 仓位建议正确（根据周期输出）
- [ ] 中性度计算正确（`1 - |temperature - 50| / 50`）

### 9.2 质量验收

- [ ] 测试覆盖率 ≥ 80%
- [ ] 所有因子得分 ∈ [0, 100]
- [ ] 温度值 ∈ [0, 100]
- [ ] 周期值 ∈ 7个有效英文代码
- [ ] 趋势值 ∈ {up, down, sideways}
- [ ] 每交易日1条mss_panorama记录
- [ ] 历史数据回填完整（2015-01-01至今）

### 9.3 性能验收

- [ ] 单日计算延迟 ≤ 5秒
- [ ] 批量计算（1年）≤ 5分钟
- [ ] 数据库写入幂等

### 9.4 文档验收

- [ ] API 文档完整
- [ ] 错误码文档完整
- [ ] 部署文档完整

---

## 10. 参数配置表

### 10.1 算法参数

| 参数名称 | 代码 | 默认值 | 可调范围 | 说明 |
|----------|------|--------|----------|------|
| 新高统计窗口 | new_high_window | 100 | 60-120 | 100日新高判定 |
| 大涨阈值 | strong_move_threshold | 5% | 3%-7% | 涨幅>5%为大涨 |
| 炸板率阈值 | broken_rate_threshold | 20% | 10%-30% | - |
| 趋势判定窗口 | trend_window | 3 | 2-5 | 连续N日判定趋势 |
| Z-Score窗口 | zscore_window | 120 | 60-240 | 滚动统计窗口 |

### 10.2 权重参数

| 参数名称 | 代码 | 默认值 | 可调范围 | 说明 |
|----------|------|--------|----------|------|
| 基础因子权重 | base_weight | 0.85 | 0.70-0.90 | - |
| 增强因子权重 | enhanced_weight | 0.15 | 0.10-0.30 | - |
| 大盘系数权重 | market_coef_weight | 0.20 | - | 固定 |
| 赚钱效应权重 | profit_weight | 0.40 | - | 固定 |
| 亏钱效应权重 | loss_weight | 0.40 | - | 固定 |

### 10.3 温度阈值

| 阈值名称 | 代码 | 默认值 | 说明 |
|----------|------|--------|------|
| 高潮阈值 | climax_threshold | 75 | ≥75为高潮期 |
| 萌芽上限 | emergence_upper | 30 | <30+up为萌芽期 |
| 发酵上限 | fermentation_upper | 45 | 30-45+up为发酵期 |
| 加速上限 | acceleration_upper | 60 | 45-60+up为加速期 |
| 过热预警 | overheat_threshold | 80 | ≥80触发过热预警 |
| 过冷预警 | overcool_threshold | 20 | ≤20触发过冷预警 |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v4.0.2 | 2026-02-06 | 对齐输入依赖命名为 raw_* 并统一数据库重试异常表述 |
| v4.0.1 | 2026-02-04 | 修正输入层级标注并统一为 DuckDB 存储口径 |
| v4.0.0 | 2026-02-02 | 完整重构：添加量化验收标准、I/O规范、错误处理、质量监控 |
| v3.0.0 | 2026-01-31 | 重构版：统一公式、命名 |


