# ROADMAP Phase 05｜三三制集成（Integration）

**版本**: v4.0.3
**创建日期**: 2026-01-31
**最后更新**: 2026-02-06
**时间范围**: Phase 05
**核心交付**: MSS+IRS+PAS集成、三分之一原则、推荐等级
**前置依赖**: Phase 02 (MSS), Phase 03 (IRS), Phase 04 (PAS)
**实现状态**: 未实现（截至 2026-02-06：`src/` 仅有 Skeleton/占位与少量基础骨架，详见 `Governance/ROADMAP/ROADMAP-OVERVIEW.md`）

---
## 文档对齐声明

> **权威设计文档**: `docs/design/core-algorithms/integration/`
> - 算法：`integration-algorithm.md`
> - 数据模型：`integration-data-models.md`
> - API：`integration-api.md`
> - 信息流：`integration-information-flow.md`

---

## 1. Phase 目标与量化验收标准

> **一句话**: 集成三个维度，生成最终投资推荐

### 1.1 量化验收指标

| 指标项 | 验收标准 | 测量方法 | 优先级 |
|--------|----------|----------|--------|
| 三分之一权重验证 | MSS:IRS:PAS = 1:1:1 绝对精确 | 单元测试权重断言 | P0 |
| 综合评分范围 | final_score ∈ [0,100] | 边界测试 | P0 |
| 推荐等级覆盖 | 5级分布合理 | 统计分布检查 | P0 |
| 方向一致性检查 | 一致性处理正确 | 多场景测试 | P0 |
| 每日推荐数量 | ≤ 20 只/日 | COUNT检查 | P1 |
| 行业分散度 | 每行业 ≤ 5 只 | 分组统计 | P1 |
| 计算延迟 | 单日集成 ≤ 10秒 | 性能测试 | P1 |
| 代码覆盖率 | ≥ 80% | pytest-cov | P1 |

### 1.2 里程碑检查点

| 里程碑 | 交付物 | 验收条件 | 预期时间 |
|--------|--------|----------|----------|
| M5.1 | 数据流对接 | MSS/IRS/PAS输入读取正常 | Task 1 |
| M5.2 | 三分之一计算 | 权重验证测试通过 | Task 2 |
| M5.3 | 推荐等级与仓位 | 信号生成+仓位计算测试通过 | Task 3 |
| M5.4 | 落库与API | integrated_recommendation全量落库 | Task 4 |

### 1.3 铁律约束（零容忍）

| 铁律 | 要求 | 检查方式 | 违反后果 |
|------|------|----------|----------|
| **三分之一原则** | MSS:IRS:PAS = 1/3:1/3:1/3，不得调整 | 单元测试+代码审查 | 立即回滚 |
| **自上而下** | TD 为默认主流程；BU 仅作补充信号，且 BU 总仓位/风险不得突破 TD 上限 | 集成测试 | 立即回滚 |
| **情绪优先** | 禁止使用技术指标作为集成因子 | 代码扫描 | 立即回滚 |

---

## 2. 输入规范

### 2.1 数据依赖矩阵

| 输入表 | 来源 | 关键字段 | 更新频率 | 必需 |
|--------|------|----------|----------|------|
| mss_panorama | Phase 02 | temperature, cycle, trend, neutrality | 每交易日 | ✅ |
| irs_industry_daily | Phase 03 | industry_score, rotation_status, allocation_advice | 每交易日 | ✅ |
| stock_pas_daily | Phase 04 | opportunity_score, opportunity_grade, direction, entry, stop, target | 每交易日 | ✅ |
| raw_stock_basic | Phase 01 | ts_code, name, industry | 月度 | ✅ |

### 2.2 MssInput 输入规范

```python
@dataclass
class MssInput:
    """MSS输入数据"""
    trade_date: str              # 交易日期 YYYYMMDD，非空
    temperature: float           # 市场温度 [0,100]
    cycle: str                   # 周期（英文）∈ 7个有效值
    trend: str                   # 趋势 up/down/sideways
    position_advice: str         # 仓位建议
    neutrality: float            # 中性度 [0,1]
```

### 2.3 IrsInput 输入规范

```python
@dataclass
class IrsInput:
    """IRS输入数据"""
    trade_date: str              # 交易日期
    industry_code: str           # 行业代码，非空
    industry_name: str           # 行业名称
    industry_score: float        # 行业评分 [0,100]
    rotation_status: str         # 轮动状态 IN/OUT/HOLD
    allocation_advice: str       # 配置建议 超配/标配/减配/回避
    neutrality: float            # 中性度 [0,1]
```

### 2.4 PasInput 输入规范

```python
@dataclass
class PasInput:
    """PAS输入数据"""
    trade_date: str              # 交易日期
    stock_code: str              # 股票代码（L2+），非空
    stock_name: str              # 股票名称
    industry_code: str           # 所属行业
    opportunity_score: float     # 机会评分 [0,100]
    opportunity_grade: str       # 机会等级 S/A/B/C/D
    direction: str               # 方向 bullish/bearish/neutral
    risk_reward_ratio: float     # 风险收益比 ≥0
    entry: float                 # 入场价 >0
    stop: float                  # 止损价 >0
    target: float                # 目标价 >0
    neutrality: float            # 中性度 [0,1]
```

### 2.5 输入验证规则

| 验证项 | 规则 | 错误处理 |
|--------|------|----------|
| mss_temperature | ∈ [0, 100] | 抛出 ValueError |
| mss_cycle | ∈ 7个有效周期 | 抛出 ValueError |
| irs_score | ∈ [0, 100] | 抛出 ValueError |
| pas_score | ∈ [0, 100] | 抛出 ValueError |
| pas_grade | ∈ {S, A, B, C, D} | 抛出 ValueError |
| pas_direction | ∈ {bullish, bearish, neutral} | 抛出 ValueError |
| 行业匹配 | PAS.industry_code 必须存在于 IRS | 跳过该股票，记录警告 |

---

## 3. 核心算法（权威口径）

### 3.1 三分之一原则（⚠️ 铁律，不可违反）

```python
# 权重定义（固定不可改）
SYSTEM_WEIGHTS = {
    "mss": 1/3,  # 精确值，禁止近似
    "irs": 1/3,
    "pas": 1/3
}

# 综合评分计算
final_score = mss_score * (1/3) + irs_score * (1/3) + pas_score * (1/3)

# 其中：
# - mss_score = MssPanorama.temperature
# - irs_score = IrsIndustryDaily.industry_score（股票所属行业）
# - pas_score = StockPasDaily.opportunity_score
```

**禁止行为（零容忍）**：
```python
# ❌ 严禁 - 任何权重调整
final_score = mss * 0.4 + irs * 0.3 + pas * 0.3  # 违规
final_score = mss * 0.35 + irs * 0.35 + pas * 0.30  # 违规

# ❌ 严禁 - 动态权重
if market_hot:
    mss_weight = 0.5  # 违规
```

### 3.2 方向一致性检查

```python
# 方向映射
DIRECTION_MAP = {
    "mss": {"up": +1, "down": -1, "sideways": 0},
    "irs": {"IN": +1, "OUT": -1, "HOLD": 0},
    "pas": {"bullish": +1, "bearish": -1, "neutral": 0}
}

def calculate_direction_consistency(mss_trend: str, irs_status: str, pas_direction: str) -> tuple:
    """计算方向一致性"""
    mss_dir = DIRECTION_MAP["mss"][mss_trend]
    irs_dir = DIRECTION_MAP["irs"][irs_status]
    pas_dir = DIRECTION_MAP["pas"][pas_direction]
    
    direction_score = (mss_dir + irs_dir + pas_dir) / 3
    
    # 综合方向判定
    if direction_score > 0.3:
        final_direction = "bullish"
    elif direction_score < -0.3:
        final_direction = "bearish"
    else:
        final_direction = "neutral"
    
    # 一致性惩罚因子（用于中性度）
    directions = [mss_dir, irs_dir, pas_dir]
    if len(set(directions)) == 1:
        consistency_factor = 1.0  # 三者一致
    elif len(set(directions)) == 2:
        consistency_factor = 0.9  # 两者一致
    else:
        consistency_factor = 0.7  # 各不相同

    # 评分一致性惩罚因子（用于 final_score）
    if len(set(directions)) == 1:
        strength_factor = 1.0
    elif len(set(directions)) == 2:
        strength_factor = 0.9
    else:
        strength_factor = 0.8
    
    return final_direction, consistency_factor, strength_factor
```

> `strength_factor` 用于评分惩罚：在 IRS 行业调整后执行 `final_score *= strength_factor`（不改变三分之一权重，仅削弱一致性差的信号）。

### 3.3 推荐等级判定

| 等级 | 英文代码 | 评分条件 | MSS周期条件 | 操作建议 |
|------|----------|----------|-------------|----------|
| 强烈买入 | STRONG_BUY | ≥ 80 | ∈ {emergence, fermentation} | 立即买入 |
| 买入 | BUY | 70-79 或 (≥80 + 其他周期) | - | 适时买入 |
| 持有 | HOLD | 50-69 | - | 继续持有 |
| 卖出 | SELL | 30-49 | - | 逐步卖出 |
| 回避 | AVOID | < 30 | - | 不参与 |

```python
def determine_recommendation(final_score: float, mss_cycle: str) -> str:
    """STRONG_BUY需同时满足评分和周期条件"""
    favorable_cycles = {"emergence", "fermentation"}
    
    if final_score >= 80 and mss_cycle in favorable_cycles:
        return "STRONG_BUY"
    elif final_score >= 70:
        return "BUY"
    elif final_score >= 50:
        return "HOLD"
    elif final_score >= 30:
        return "SELL"
    else:
        return "AVOID"
```

### 3.4 MSS温度约束（自上而下软约束）

```python
def apply_mss_constraints(
    mss_temperature: float,
    position_size: float,
    neutrality: float
) -> tuple:
    """
    MSS温度约束：不做单点否决，仅影响仓位与中性度
    - 冰点期（<30）：下调仓位，提高中性度
    - 过热期（>80）：下调仓位，提高中性度
    """
    if mss_temperature < 30:
        position_size *= 0.6
        neutrality = min(1.0, neutrality * 1.1)
    elif mss_temperature > 80:
        position_size *= 0.7
        neutrality = min(1.0, neutrality * 1.1)
    
    return position_size, neutrality
```

### 3.5 IRS行业配置门控

```python
def apply_irs_adjustment(pas_score: float, irs_allocation: str) -> float:
    """
    IRS行业配置调整
    - 回避行业：PAS评分轻度折扣
    - 超配行业：PAS评分轻度上浮（不超100）
    """
    IRS_ADJUSTMENT = {
        "超配": 1.05,
        "标配": 1.0,
        "回避": 0.85
    }
    adjusted_score = pas_score * IRS_ADJUSTMENT.get(irs_allocation, 1.0)
    return min(100.0, adjusted_score)
```

### 3.6 仓位计算公式

```python
def calculate_position_size(
    final_score: float,
    mss_temperature: float,
    irs_allocation: str,
    pas_grade: str
) -> float:
    """计算建议仓位"""
    # 基础仓位
    base_position = final_score / 100
    
    # MSS温度调整（越接近50越中性，越极端越保守）
    mss_factor = 1 - abs(mss_temperature - 50) / 100
    
    # IRS配置调整
    IRS_POSITION_FACTOR = {
        "超配": 1.2,
        "标配": 1.0,
        "减配": 0.7,
        "回避": 0.3
    }
    irs_factor = IRS_POSITION_FACTOR.get(irs_allocation, 1.0)
    
    # PAS等级调整
    PAS_POSITION_FACTOR = {
        "S": 1.2,
        "A": 1.0,
        "B": 0.7,
        "C": 0.3,
        "D": 0.3
    }
    pas_factor = PAS_POSITION_FACTOR.get(pas_grade, 0.3)
    
    # 最终仓位
    position_size = base_position * mss_factor * irs_factor * pas_factor
    
    # 边界约束
    return max(0.0, min(1.0, position_size))

# 单股仓位上限
SINGLE_STOCK_POSITION_CAP = {
    "S": 0.20,  # S级：最多20%
    "A": 0.15,  # A级：最多15%
    "B": 0.10,  # B级：最多10%
    "C": 0.05,  # C级：最多5%
    "D": 0.05   # D级：最多5%
}
```

### 3.7 置信度计算

```python
def calculate_neutrality(
    mss_neut: float,
    irs_neut: float,
    pas_neut: float,
    consistency_factor: float
) -> float:
    """
    综合中性度 = 三系统中性度均值 × 一致性因子
    
    语义说明：中性度反映"中性程度"而非信号强度
    - 高中性度 = 评分接近50，信号中性，建议观望
    - 低中性度 = 评分极端，信号明确，适合交易触发
    """
    avg_neutrality = (mss_neut + irs_neut + pas_neut) / 3
    return avg_neutrality * consistency_factor
```

---

## 4. 输出规范

### 4.1 IntegratedRecommendation 输出规范

```python
@dataclass
class IntegratedRecommendation:
    """integrated_recommendation"""
    trade_date: str              # 交易日期 YYYYMMDD
    stock_code: str              # 股票代码（L2+）
    stock_name: str              # 股票名称
    industry_code: str           # 所属行业代码
    industry_name: str           # 行业名称
    
    # 追溯信息
    integration_mode: str        # top_down/bottom_up/dual_verify/complementary
    
    # 三系统输入评分
    mss_score: float             # MSS评分（温度）[0,100]
    irs_score: float             # IRS行业评分 [0,100]
    pas_score: float             # PAS机会评分 [0,100]
    
    # 集成输出
    final_score: float           # 综合评分 [0,100]
    direction: str               # 综合方向 bullish/bearish/neutral
    recommendation: str          # 推荐等级 STRONG_BUY/BUY/HOLD/SELL/AVOID
    position_size: float         # 仓位建议 [0,1]
    
    # 交易参考（沿用PAS输出）
    entry: float                 # 入场价
    stop: float                  # 止损价
    target: float                # 目标价
    risk_reward_ratio: float     # 风险收益比
    
    # 辅助信息
    neutrality: float            # 综合中性度 [0,1]
```

### 4.2 数据库表结构（DuckDB DDL）

```sql
CREATE TABLE integrated_recommendation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date VARCHAR(8) NOT NULL,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(20),
    industry_code VARCHAR(10),
    industry_name VARCHAR(20),
    
    -- 追溯信息
    integration_mode VARCHAR(20),
    
    -- 三系统输入
    mss_score DECIMAL(8,4) CHECK(mss_score >= 0 AND mss_score <= 100),
    irs_score DECIMAL(8,4) CHECK(irs_score >= 0 AND irs_score <= 100),
    pas_score DECIMAL(8,4) CHECK(pas_score >= 0 AND pas_score <= 100),
    
    -- 集成输出
    final_score DECIMAL(8,4) NOT NULL CHECK(final_score >= 0 AND final_score <= 100),
    direction VARCHAR(20) CHECK(direction IN ('bullish','bearish','neutral')),
    recommendation VARCHAR(20) NOT NULL CHECK(recommendation IN ('STRONG_BUY','BUY','HOLD','SELL','AVOID')),
    position_size DECIMAL(8,4) CHECK(position_size >= 0 AND position_size <= 1),
    
    -- 交易参考
    entry DECIMAL(12,4),
    stop DECIMAL(12,4),
    target DECIMAL(12,4),
    risk_reward_ratio DECIMAL(8,4),
    
    -- 辅助信息
    neutrality DECIMAL(8,4) CHECK(neutrality >= 0 AND neutrality <= 1),
    
    -- 元数据
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME,
    
    UNIQUE(trade_date, stock_code)
);

CREATE INDEX idx_integrated_trade_date ON integrated_recommendation(trade_date);
CREATE INDEX idx_integrated_final_score ON integrated_recommendation(final_score);
CREATE INDEX idx_integrated_recommendation ON integrated_recommendation(recommendation);
CREATE INDEX idx_integrated_industry ON integrated_recommendation(industry_code);
```

### 4.3 推荐列表筛选规则

```python
# 入选条件
SELECTION_CRITERIA = {
    "pas_grade": ["S", "A", "B"],     # 等级限制
    "irs_allocation": ["超配", "标配", "减配"],  # 排除"回避"
    "mss_temperature_required": "not null",  # 温度必须存在
    "final_score_min": 55              # 评分下限
}

# 输出限制
OUTPUT_LIMITS = {
    "max_daily_recommendations": 20,   # 每日最多推荐20只
    "max_per_industry": 5               # 每行业最多5只
}

# 排序规则
SORT_RULES = [
    ("opportunity_grade", "DESC"),     # 首先按等级（S > A > B）
    ("final_score", "DESC")            # 然后按评分
]
```

### 4.4 输出验证规则

| 字段 | 验证规则 | 错误处理 |
|------|----------|----------|
| final_score | ∈ [0, 100] | 截断到边界 |
| recommendation | ∈ 5个有效值 | 抛出异常 |
| position_size | ∈ [0, 1] | 截断到边界 |
| integration_mode | ∈ {top_down, bottom_up, dual_verify, complementary} | 设为 top_down |
| neutrality | ∈ [0, 1] | 截断到边界 |
| 每日推荐数 | ≤ 20 | 截断并记录警告 |
| 每行业推荐数 | ≤ 5 | 截断并记录警告 |

---

## 5. API 接口规范

### 5.1 核心接口定义

```python
class IntegrationEngine:
    """Integration"""
    
    def calculate(
        self,
        mss_input: MssInput,
        irs_inputs: List[IrsInput],
        pas_inputs: List[PasInput]
    ) -> List[IntegratedRecommendation]:
        """
        计算集成推荐
        
        Args:
            mss_input: 当日MSS数据（全市场唯一）
            irs_inputs: 当日各行业IRS数据
            pas_inputs: 当日各股票PAS数据
        Returns:
            集成推荐列表（按final_score降序）
        Raises:
            ValueError: 输入数据无效
            WeightViolationError: 权重违规（不应发生）
        """
        pass
    
    def generate_recommendations(
        self,
        signals: List[IntegratedRecommendation],
        top_n: int = 20
    ) -> List[IntegratedRecommendation]:
        """
        筛选并生成最终推荐列表
        
        Args:
            signals: 全部集成信号
            top_n: 最大推荐数量
        Returns:
            筛选后的推荐列表（按等级+评分排序）
        """
        pass
    
    def get_latest_recommendations(self, trade_date: str = None) -> List[IntegratedRecommendation]:
        """获取最新推荐列表"""
        pass
    
    def verify_weights(self) -> bool:
        """验证三分之一权重（内部检查）"""
        return (
            self.MSS_WEIGHT == 1/3 and
            self.IRS_WEIGHT == 1/3 and
            self.PAS_WEIGHT == 1/3
        )


class IntegrationRepository:
    """Integration 数据仓库"""
    
    def save(self, recommendation: IntegratedRecommendation) -> None:
        """保存单条记录（幂等）"""
        pass
    
    def save_batch(self, recommendations: List[IntegratedRecommendation]) -> int:
        """批量保存"""
        pass
    
    def get_by_date(self, trade_date: str) -> List[IntegratedRecommendation]:
        """按日期查询"""
        pass
    
    def get_by_stock(self, stock_code: str, limit: int = 30) -> List[IntegratedRecommendation]:
        """按股票查询历史"""
        pass
```

---

## 6. 错误处理策略

### 6.1 错误分类与处理

| 错误场景 | 错误码 | 严重等级 | 处理策略 | 重试 |
|----------|--------|----------|----------|------|
| MSS数据缺失 | INT_E001 | P0 | 抛出异常，阻断流程 | 否 |
| IRS行业数据不完整 | INT_E002 | P1 | 跳过该行业股票，记录警告 | 否 |
| PAS股票数据缺失 | INT_E003 | P2 | 跳过该股票，记录信息 | 否 |
| 权重违规 | INT_E004 | P0 | 抛出 WeightViolationError，立即终止 | 否 |
| 评分越界 | INT_E005 | P1 | 截断到边界，记录警告 | 否 |
| 行业不匹配 | INT_E006 | P2 | 跳过该股票，记录警告 | 否 |
| 数据库写入失败 | INT_E007 | P0 | 重试3次后抛出异常 | ✅(3次) |
| 推荐数量超限 | INT_E008 | P2 | 截断并记录警告 | 否 |

### 6.2 权重违规检测（零容忍）

```python
class WeightViolationError(Exception):
    """三分之一原则违规异常"""
    pass

def validate_weights_at_runtime(mss_weight: float, irs_weight: float, pas_weight: float):
    """运行时权重验证（必须在计算前调用）"""
    EXPECTED = 1/3
    TOLERANCE = 1e-10  # 浮点数容差
    
    if not (abs(mss_weight - EXPECTED) < TOLERANCE and
            abs(irs_weight - EXPECTED) < TOLERANCE and
            abs(pas_weight - EXPECTED) < TOLERANCE):
        raise WeightViolationError(
            f"三分之一原则违规！"
            f"实际权重: MSS={mss_weight}, IRS={irs_weight}, PAS={pas_weight}, "
            f"期望权重: 1/3:1/3:1/3"
        )
```

### 6.3 重试策略

```python
INTEGRATION_RETRY_CONFIG = {
    "db_write": {
        "max_retries": 3,
        "base_delay": 1.0,
        "exponential": True,
        "max_delay": 10.0
    }
}
```

---

## 7. 质量监控

### 7.1 每日质量检查项

| 检查项 | 检查方法 | 预期结果 | 告警阈值 |
|--------|----------|----------|----------|
| 权重验证 | 运行时检查 | MSS:IRS:PAS = 1/3:1/3:1/3 | 任何偏差 |
| 推荐数量 | COUNT(*) | ≤ 20 | > 20 |
| 评分范围 | final_score | ∈ [0, 100] | 越界 |
| 行业分布 | 每行业COUNT | ≤ 5 | > 5 |
| 等级分布 | 各等级比例 | 合理分布 | 单一等级>80% |
| 数据连续性 | 与前一交易日间隔 | ≤ 1个交易日 | 缺失 |

### 7.2 质量监控表

```sql
CREATE TABLE integration_quality_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date VARCHAR(8) NOT NULL,
    check_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- 权重检查
    weight_valid BOOLEAN NOT NULL,
    mss_weight_actual DECIMAL(10,8),
    irs_weight_actual DECIMAL(10,8),
    pas_weight_actual DECIMAL(10,8),
    
    -- 输出检查
    recommendation_count INTEGER,
    max_per_industry INTEGER,
    score_range_valid BOOLEAN,
    
    -- 异常信息
    error_code VARCHAR(20),
    error_message TEXT,
    
    -- 状态
    status VARCHAR(20) DEFAULT 'PASS',
    
    UNIQUE(trade_date)
);
```

---

## 8. 执行计划

### 8.1 Task 级别详细计划

---

#### Task 1: 数据流对接

**目标**: 实现 MSS/IRS/PAS 三系统数据加载器

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| mss_panorama表 | Phase 02 | 数据存在 | 阻断 |
| irs_industry_daily表 | Phase 03 | 31行业数据 | 阻断 |
| stock_pas_daily表 | Phase 04 | ~5000股票数据 | 阻断 |
| raw_stock_basic表 | Phase 01 | 行业映射 | 阻断 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| MssInputLoader | 代码 | 读取MSS数据 | `src/integration/` |
| IrsInputLoader | 代码 | 读取31行业 | `src/integration/` |
| PasInputLoader | 代码 | 读取全市场 | `src/integration/` |
| InputValidator | 代码 | 验证数据完整性 | `src/integration/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| MSS数据 | temperature∈[0,100] | 边界测试 |
| IRS数据 | 31行业完整 | COUNT检查 |
| PAS数据 | ~5000股票 | COUNT检查 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| MSS数据缺失 | 抛出异常 | 立即阻断 |
| IRS行业不全 | 跳过该行业股票 | 记录警告 |
| PAS股票缺失 | 跳过该股票 | 记录信息 |

**验收检查**

- [ ] MSS数据加载正确
- [ ] IRS 31行业数据加载正确
- [ ] PAS全市场数据加载正确
- [ ] 行业匹配验证通过

---

#### Task 2: 三分之一计算（⚠️铁律）

**目标**: 实现三分之一权重的综合评分计算

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| MssInput | Task 1 | 测试通过 | 阻断 |
| IrsInput | Task 1 | 测试通过 | 阻断 |
| PasInput | Task 1 | 测试通过 | 阻断 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| ScoreCalculator | 代码 | 1/3+1/3+1/3=1 | `src/integration/` |
| WeightValidator | 代码 | 运行时校验 | `src/integration/` |
| DirectionChecker | 代码 | 一致性检查 | `src/integration/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 权重精确 | MSS:IRS:PAS=1/3:1/3:1/3 | 单元测试 |
| 评分范围 | [0,100] | 边界测试 |
| 方向一致性 | 一致因子计算正确 | 单元测试 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 权重违规 | 抛出 WeightViolationError | 立即终止 |
| 评分越界 | 截断到[0,100] | 记录警告 |

**验收检查**

- [ ] **三分之一权重精确**（1/3:1/3:1/3）
- [ ] 综合评分范围[0,100]
- [ ] 方向一致性检查正确
- [ ] **权重违规抛出异常**

---

#### Task 3: 推荐等级与仓位

**目标**: 实现推荐等级判定、MSS门控、仓位计算

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| ScoreCalculator | Task 2 | 测试通过 | 阻断 |
| WeightValidator | Task 2 | 测试通过 | 阻断 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| RecommendationGenerator | 代码 | 5级推荐 | `src/integration/` |
| MssGatekeeper | 代码 | 温度门控 | `src/integration/` |
| PositionCalculator | 代码 | 仓位计算 | `src/integration/` |
| ConfidenceCalculator | 代码 | 置信度计算 | `src/integration/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 推荐等级 | 5级分布合理 | 统计检查 |
| MSS门控 | <30或>80下调仓位/提高中性度（无单点否决） | 场景测试 |
| 仓位范围 | [0,1] | 边界测试 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 推荐等级无效 | 抛出异常 | 立即阻断 |
| 仓位越界 | 截断到[0,1] | 记录警告 |

**验收检查**

- [ ] 推荐等级判定正确（5级）
- [ ] MSS温度门控正确
- [ ] IRS行业调整正确
- [ ] 仓位计算正确

---

#### Task 4: 集成与落库

**目标**: 实现完整集成引擎、筛选逻辑、数据落库

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| ScoreCalculator | Task 2 | 测试通过 | 阻断 |
| RecommendationGenerator | Task 3 | 测试通过 | 阻断 |
| PositionCalculator | Task 3 | 测试通过 | 阻断 |
| DuckDB连接 | Phase 01 | 可连接 | 阻断 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| IntegrationEngine | 代码 | 完整集成流程 | `src/integration/` |
| RecommendationFilter | 代码 | ≤20只/日 | `src/integration/` |
| IntegrationRepository | 代码 | 幂等写入 | `src/integration/` |
| integrated_recommendation表 | 数据 | 推荐列表 | L3 DuckDB（按年分库） |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 覆盖率 | ≥80% | `pytest --cov` |
| 推荐数 | ≤20只/日 | COUNT检查 |
| 行业分散 | 每行业≤5只 | 分组统计 |
| 幂等性 | 重复写入不报错 | 单元测试 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 推荐超限1 | 截断并警告 | 记录警告 |
| DB写入失败 | 重试3次 | 失败后抛异常 |

**验收检查**

- [ ] 集成引擎完整可用
- [ ] 推荐列表≤20只/日
- [ ] 每行业≤5只
- [ ] 测试覆盖率≥80%
- [ ] **M5里程碑完成**

### 8.2 每日执行时序

```text
17:15  MSS/IRS/PAS 计算完成（Phase 02/03/04）
  ↓
17:16  触发 Integration 计算
  ↓
17:16  加载 MSS 输入（全市场1条）
  ↓
17:16  加载 IRS 输入（31行业）
  ↓
17:17  加载 PAS 输入（~5000股票）
  ↓
17:17  权重验证（铁律检查）
  ↓
17:18  计算 final_score（三分之一加权）
  ↓
17:19  应用 MSS 门控
  ↓
17:19  应用 IRS 调整
  ↓
17:20  生成推荐等级
  ↓
17:20  计算仓位建议
  ↓
17:21  筛选 TOP 20 推荐
  ↓
17:22  写入 integrated_recommendation
  ↓
17:23  质量检查
  ↓
17:23  Integration 完成，通知 Phase 06 (Backtest)
```

---

## 9. 验收检查清单

### 9.1 铁律验收（零容忍）

- [ ] **三分之一权重**: MSS:IRS:PAS = 1/3:1/3:1/3，绝对精确
- [ ] **权重固定**: 代码中无动态权重调整
- [ ] **运行时验证**: 每次计算前验证权重
- [ ] **自上而下**: MSS门控正确实现

### 9.2 功能验收

- [ ] 综合评分计算正确（IRS调整后 `(mss + irs + pas_adj) / 3`，并应用 strength_factor）
- [ ] 方向一致性检查正确（含 strength_factor 规则）
- [ ] 推荐等级判定正确（5级）
- [ ] MSS温度门控正确（<30或>80下调仓位/提高中性度，不做单点否决）
- [ ] IRS行业调整正确
- [ ] 仓位计算正确
- [ ] 置信度计算正确
- [ ] 推荐列表筛选正确（≤20只，每行业≤5只）

### 9.3 质量验收

- [ ] 测试覆盖率 ≥ 80%
- [ ] final_score ∈ [0, 100]
- [ ] recommendation ∈ 5个有效值
- [ ] position_size ∈ [0, 1]
- [ ] 数据完整性检查通过

### 9.4 性能验收

- [ ] 单日集成计算 ≤ 10秒
- [ ] 历史回测（1年）≤ 10分钟
- [ ] 数据库写入幂等

---

## 10. 参数配置表

### 10.1 权重参数（固定不可改）

| 参数名称 | 代码 | 值 | 说明 |
|----------|------|------|------|
| MSS权重 | MSS_WEIGHT | 1/3 | 固定，铁律 |
| IRS权重 | IRS_WEIGHT | 1/3 | 固定，铁律 |
| PAS权重 | PAS_WEIGHT | 1/3 | 固定，铁律 |

### 10.2 阈值参数

| 参数名称 | 代码 | 默认值 | 说明 |
|----------|------|--------|------|
| STRONG_BUY阈值 | STRONG_BUY_THRESHOLD | 80 | 等级分界 |
| BUY阈值 | BUY_THRESHOLD | 70 | 等级分界 |
| HOLD阈值 | HOLD_THRESHOLD | 50 | 等级分界 |
| SELL阈值 | SELL_THRESHOLD | 30 | 等级分界 |
| MSS冰点阈值 | MSS_COLD_THRESHOLD | 30 | 门控下限 |
| MSS过热阈值 | MSS_HOT_THRESHOLD | 80 | 门控上限 |

### 10.3 输出限制参数

| 参数名称 | 代码 | 默认值 | 说明 |
|----------|------|--------|------|
| 每日最大推荐数 | MAX_DAILY_RECOMMENDATIONS | 20 | 硬限制 |
| 每行业最大推荐数 | MAX_PER_INDUSTRY | 5 | 分散化要求 |
| 最低评分阈值 | MIN_FINAL_SCORE | 55 | 入选条件 |

### 10.4 仓位调整因子

| 因子 | 条件 | 系数 |
|------|------|------|
| IRS配置 | 超配 | 1.2 |
| | 标配 | 1.0 |
| | 减配 | 0.7 |
| | 回避 | 0.3 |
| PAS等级 | S级 | 1.2 |
| | A级 | 1.0 |
| | B级 | 0.7 |
| | C/D级 | 0.3 |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v4.0.3 | 2026-02-06 | 依赖输入表命名统一为 Data Layer raw_* 口径 |
| v4.0.2 | 2026-02-05 | 一致性惩罚因子口径对齐、MSS门控表述修正、Integration实现路径修正 |
| v4.0.1 | 2026-02-04 | 存储层说明统一为 DuckDB 按年分库 |
| v4.0.0 | 2026-02-02 | 完整重构：添加量化验收标准、I/O规范、错误处理、铁律检查 |
| v3.0.0 | 2026-01-31 | 重构版：强化三分之一原则 |


