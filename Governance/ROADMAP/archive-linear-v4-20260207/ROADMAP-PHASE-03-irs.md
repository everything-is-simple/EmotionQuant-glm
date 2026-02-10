# ROADMAP Phase 03｜行业轮动追踪（IRS）

**版本**: v4.0.3
**创建日期**: 2026-01-31
**最后更新**: 2026-02-06
**时间范围**: Phase 03
**核心交付**: IRS算法实现、六因子评分、轮动状态判断
**前置依赖**: Phase 01 (Data Layer)
**实现状态**: 未实现（截至 2026-02-06：`src/` 仅有 Skeleton/占位与少量基础骨架，详见 `Governance/ROADMAP/ROADMAP-OVERVIEW.md`）

---
## 文档对齐声明

> **权威设计文档**: `docs/design/core-algorithms/irs/`
> - 算法：`irs-algorithm.md`
> - 数据模型：`irs-data-models.md`
> - API：`irs-api.md`
> - 信息流：`irs-information-flow.md`

---

## 1. Phase 目标与量化验收标准

> **一句话**: 识别强势行业，追踪轮动节奏

### 1.1 量化验收指标

| 指标项 | 验收标准 | 测量方法 | 优先级 |
|--------|----------|----------|--------|
| 行业评分范围 | industry_score ∈ [0,100] | 边界测试 | P0 |
| 六因子权重验证 | 25%+20%+20%+15%+12%+8% = 100% | 单元测试权重断言 | P0 |
| 行业覆盖率 | 31个申万一级行业全覆盖 | COUNT检查 | P0 |
| 轮动状态准确率 | IN/OUT/HOLD判断≥95% | 历史回测验证 | P0 |
| 排名唯一性 | 同日无重复排名 | 唯一性约束检查 | P0 |
| 代码覆盖率 | ≥ 80% | pytest-cov | P1 |
| 计算延迟 | 31行业计算 ≤ 30秒 | 性能测试 | P1 |
| 历史回填 | 2015-01-01至今无缺失 | 日期连续性校验 | P1 |

### 1.2 里程碑检查点

| 里程碑 | 交付物 | 验收条件 | 预期时间 |
|--------|--------|----------|----------|
| M3.1 | 基础因子计算 | 相对强度/连续性因子/资金流向/估值因子测试通过 | Task 1 |
| M3.2 | 增强因子计算 | 龙头因子/行业基因库测试通过 | Task 2 |
| M3.3 | 综合评分与排名 | 加权求和+排名逻辑验证通过 | Task 3 |
| M3.4 | 轮动状态与配置 | irs_industry_daily全量落库 | Task 4 |

---

## 2. 输入规范

### 2.1 数据依赖矩阵

| 输入表/接口 | 来源 | 关键字段 | 更新频率 | 必需 |
|-------------|------|----------|----------|------|
| raw_daily | Phase 01 L1 | pct_chg, amount, close | 每交易日 | ✅ |
| raw_daily_basic | Phase 01 L1 | pe_ttm, turnover_rate | 每交易日 | ✅ |
| raw_index_daily | Phase 01 L1 | 基准指数pct_chg | 每交易日 | ✅ |
| raw_limit_list | Phase 01 L1 | 行业涨停统计 | 每交易日 | ✅ |
| industry_snapshot | Phase 01 L2 | rise_count, fall_count, stock_count, new_100d_high_count, new_100d_low_count | 每交易日 | ✅ |
| raw_stock_basic | Phase 01 L1 | 股票-行业映射 | 月度 | ✅ |
| raw_index_classify | Phase 01 L1 | 申万行业分类 | 年度 | ✅ |
| raw_trade_cal | Phase 01 L1 | is_open | 年度 | ✅ |

### 2.2 行业范围

**申万一级31个行业**（使用 `raw_index_classify` 表获取）

```python
INDUSTRY_LIST = [
    "农林牧渔", "采掘", "化工", "钢铁", "有色金属",
    "电子", "汽车", "家用电器", "食品饮料", "纺织服装",
    "轻工制造", "医药生物", "公用事业", "交通运输", "房地产",
    "商贸零售", "社会服务", "综合", "建筑材料", "建筑装饰",
    "电力设备", "机械设备", "国防军工", "计算机", "传媒",
    "通信", "银行", "非银金融", "煤炭", "石油石化", "美容护理"
]  # 共计31个
```

### 2.3 输入验证规则

| 验证项 | 规则 | 错误处理 |
|--------|------|----------|
| 行业数量 | = 31 | 抛出 ValueError |
| pct_chg | ∈ [-20, 20] | 截断并记录警告 |
| 基准指数数据 | 非空 | 使用中证全指作为备用 |
| pe_ttm | > 0 或 NULL | NULL设为中位数 |
| trade_date | 必须是交易日 | 跳过计算 |

---

## 3. 核心算法（权威口径）

### 3.1 六因子架构

| 因子类别 | 因子名称 | 权重 | 取值范围 | 说明 |
|----------|----------|------|----------|------|
| **基础因子** | 相对强度 | 25% | [0,100] | 行业相对市场的强弱 |
| | 连续性因子 | 20% | [0,100] | 行业情绪/广度的持续性 |
| | 资金流向 | 20% | [0,100] | 资金进出情况 |
| | 估值因子 | 15% | [0,100] | 行业估值水平 |
| **增强因子** | 龙头因子 | 12% | [0,100] | 行业龙头股表现 |
| | 行业基因库 | 8% | [0,100] | 行业历史强势惯性 |

> **权重分配原则**: 基础因子 80%，增强因子 20%

### 3.2 相对强度因子（25%）

```python
# 计算公式
relative_strength = industry_pct_chg - benchmark_pct_chg
relative_strength_score = zscore_normalize(relative_strength)

# 参数
# - industry_pct_chg: 行业当日涨跌幅（行业内股票成交额加权平均）
# - benchmark_pct_chg: 基准指数涨跌幅（沪深300或中证全指）
# 数据来源: raw_daily + raw_index_daily
```

### 3.3 连续性因子（20%）

> **铁律对齐**：不使用基于价格序列的回归斜率类指标，改用行业“情绪/广度”的连续性刻画。

```python
# 定义
rise_ratio = rise_count / stock_count
fall_ratio = fall_count / stock_count
net_breadth = rise_ratio - fall_ratio
new_high_ratio = new_100d_high_count / stock_count
new_low_ratio = new_100d_low_count / stock_count
net_new_high = new_high_ratio - new_low_ratio

# 计算公式
continuity_raw = 0.6 * sum(net_breadth, window=5) \
               + 0.4 * sum(net_new_high, window=5)
continuity_factor = zscore_normalize(continuity_raw)

# 参数
# - window: 连续性窗口（默认5日）
# 数据来源: industry_snapshot（L2）
```

### 3.4 资金流向因子（20%）

```python
# 计算公式
net_inflow_10d = sum(industry_amount_delta, window=10)
capital_flow_score = zscore_normalize(net_inflow_10d)

# 参数
# - industry_amount_delta: 行业成交额增量（当日-前一日）
# - window: 累计窗口（默认10日）
# 数据来源: raw_daily_basic 聚合
```

### 3.5 估值因子（15%）

```python
# 计算公式
valuation_score = percentile_rank(industry_pe_ttm, history_window=3y)

# 参数
# - industry_pe_ttm: 行业市盈率（TTM，市值加权）
# - history_window: 历史分位窗口（3年）
# 数据来源: raw_daily_basic
# 说明: 低估值得分高，使用 100-percentile
```

### 3.6 龙头因子（12%）

```python
# 计算公式
leader_avg_pct = Mean(top5_pct_chg)
leader_limit_up_ratio = top5_limit_up_count / 5
leader_score = zscore_normalize(leader_avg_pct) * 0.6 + zscore_normalize(leader_limit_up_ratio) * 0.4

# 参数
# - top5: 行业成交额或市值 Top5 股票
# - top5_pct_chg: Top5 股票涨跌幅
# - top5_limit_up_count: Top5 中涨停数量
# 数据来源: raw_daily + raw_limit_list
```

### 3.7 行业基因库（8%）

```python
# 计算公式
history_limit_up_ratio = history_limit_up_count / stock_count
history_new_high_ratio = history_new_high_count / stock_count
gene_raw = time_decay(history_limit_up_ratio, decay=0.9) * 0.6 \
         + time_decay(history_new_high_ratio, decay=0.9) * 0.4
gene_score = zscore_normalize(gene_raw)

# 参数
# - history_limit_up_count: 历史涨停股数量（3年滚动）
# - history_new_high_count: 历史新高股数量（3年滚动）
# - stock_count: 行业成分股数量
# - decay: 指数衰减系数（默认0.9）
# 数据来源: raw_daily + raw_limit_list
```

### 3.8 综合评分计算

```python
# 加权求和公式
industry_score = relative_strength_score * 0.25 \
               + continuity_factor * 0.20 \
               + capital_flow_score * 0.20 \
               + valuation_score * 0.15 \
               + leader_score * 0.12 \
               + gene_score * 0.08

# 边界约束
industry_score = max(0.0, min(100.0, industry_score))
```

### 3.9 Z-Score归一化方法

```python
def zscore_normalize(value: float, mean: float, std: float) -> float:
    """Z-Score归一化并映射到0-100"""
    if std == 0:
        return 50.0
    z = (value - mean) / std
    # 映射规则：[-3σ, +3σ] → [0, 100]
    score = (z + 3) / 6 * 100
    return max(0.0, min(100.0, score))
```

---

## 4. 轮动状态与配置建议

### 4.1 轮动状态判定（rotation_status）

| 状态 | 英文代码 | 判定条件 | 说明 |
|------|----------|----------|------|
| 进入轮动 | IN | 评分连续3日上升 | 行业进入轮动 |
| 退出轮动 | OUT | 评分连续3日下降 | 行业退出轮动 |
| 维持观望 | HOLD | 其他情况 | 维持观望 |

### 4.2 轮动详情（rotation_detail）

| 详情 | 特征 | 操作建议 |
|------|------|----------|
| 强势领涨 | 前3名评分持续上升 | 顺势超配 |
| 轮动加速 | 前3名频繁更替（5日内≥3次） | 分散配置 |
| 风格转换 | 领涨行业类型改变（成长↔价值） | 调整方向 |
| 热点扩散 | 上涨行业范围扩大 | 提高仓位 |
| 高位整固 | 前5名评分稳定 | 持有待涨 |
| 趋势反转 | 原领涨行业排名下滑 | 减仓换防 |

### 4.3 配置建议规则（allocation_advice）

| 配置建议 | 中文 | 排名区间 | 仓位建议 |
|----------|------|----------|----------|
| 超配 | 超配 | 前3名 | 30%-40% |
| 标配 | 标配 | 4-10名 | 10%-20% |
| 减配 | 减配 | 11-20名 | 5%-10% |
| 回避 | 回避 | 后5名 | 0%-5% |

### 4.4 中性度计算

```python
neutrality = 1 - abs(industry_score - 50) / 50
# 语义：越接近50越中性（中性度高），越极端越低
# 取值范围: [0, 1]
```

---

## 5. 输出规范

### 5.1 IrsIndustryDaily 输出字段规范

```python
@dataclass
class IrsIndustryDaily:
    """IRS 行业每日评分（输出）"""
    trade_date: str              # 交易日期 YYYYMMDD
    industry_code: str           # 行业代码
    industry_name: str           # 行业名称
    
    # 核心输出
    industry_score: float        # 行业综合评分 [0,100]
    rank: int                    # 排名 [1,31]
    rotation_status: str         # 轮动状态 IN/OUT/HOLD
    rotation_detail: str         # 轮动详情
    allocation_advice: str       # 配置建议 超配/标配/减配/回避
    
    # 因子得分
    relative_strength: float     # 相对强度得分 [0,100]
    continuity_factor: float     # 连续性因子得分 [0,100]
    capital_flow: float          # 资金流向得分 [0,100]
    valuation: float             # 估值得分 [0,100]
    leader_score: float          # 龙头因子得分 [0,100]
    gene_score: float            # 行业基因库得分 [0,100]
    
    # 辅助信息
    neutrality: float            # 中性度 [0,1]
```

### 5.2 数据库表结构（DuckDB DDL）

```sql
CREATE TABLE irs_industry_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date VARCHAR(8) NOT NULL,
    industry_code VARCHAR(20) NOT NULL,
    industry_name VARCHAR(50),
    
    -- 核心输出
    industry_score DECIMAL(8,4) NOT NULL CHECK(industry_score >= 0 AND industry_score <= 100),
    rank INTEGER NOT NULL CHECK(rank >= 1 AND rank <= 31),
    rotation_status VARCHAR(10) NOT NULL CHECK(rotation_status IN ('IN','OUT','HOLD')),
    rotation_detail VARCHAR(50),
    allocation_advice VARCHAR(20) CHECK(allocation_advice IN ('超配','标配','减配','回避')),
    
    -- 因子得分
    relative_strength DECIMAL(8,4) CHECK(relative_strength >= 0 AND relative_strength <= 100),
    continuity_factor DECIMAL(8,4) CHECK(continuity_factor >= 0 AND continuity_factor <= 100),
    capital_flow DECIMAL(8,4) CHECK(capital_flow >= 0 AND capital_flow <= 100),
    valuation DECIMAL(8,4) CHECK(valuation >= 0 AND valuation <= 100),
    leader_score DECIMAL(8,4) CHECK(leader_score >= 0 AND leader_score <= 100),
    gene_score DECIMAL(8,4) CHECK(gene_score >= 0 AND gene_score <= 100),
    
    -- 辅助信息
    neutrality DECIMAL(8,4) CHECK(neutrality >= 0 AND neutrality <= 1),
    
    -- 元数据
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME,
    
    UNIQUE(trade_date, industry_code)
);

CREATE INDEX idx_irs_trade_date ON irs_industry_daily(trade_date);
CREATE INDEX idx_irs_industry_score ON irs_industry_daily(industry_score);
CREATE INDEX idx_irs_rank ON irs_industry_daily(rank);
CREATE INDEX idx_irs_rotation_status ON irs_industry_daily(rotation_status);
```

### 5.3 输出验证规则

| 字段 | 验证规则 | 错误处理 |
|------|----------|----------|
| industry_score | ∈ [0, 100] | 截断到边界 |
| rank | ∈ [1, 31]，无重复 | 抛出异常 |
| rotation_status | ∈ {IN, OUT, HOLD} | 设为 HOLD |
| allocation_advice | ∈ {超配, 标配, 减配, 回避} | 根据排名计算 |
| 每日行业数 | = 31 | 抛出异常 |
| neutrality | ∈ [0, 1] | 截断到边界 |

---

## 6. API 接口规范

### 6.1 核心接口定义

```python
class IrsCalculator:
    """IRS 计算器接口"""
    
    def calculate(self, trade_date: str) -> List[IrsIndustryDaily]:
        """
        计算指定日期的所有行业评分
        
        Args:
            trade_date: 交易日期 YYYYMMDD
        Returns:
            31个行业的评分列表（按排名升序）
        Raises:
            ValueError: 非交易日或数据缺失
        """
        pass
    
    def batch_calculate(self, start_date: str, end_date: str) -> Dict[str, List[IrsIndustryDaily]]:
        """批量计算日期范围内的行业评分"""
        pass
    
    def get_factor_scores(self, trade_date: str, industry_code: str) -> dict:
        """获取指定行业的六因子得分"""
        pass
    
    def get_top_industries(self, trade_date: str, top_n: int = 10) -> List[str]:
        """获取评分前N的行业代码"""
        pass
    
    def get_rotation_status(self, trade_date: str, industry_code: str) -> str:
        """获取指定行业的轮动状态"""
        pass


class IrsRepository:
    """IRS 数据仓库接口"""
    
    def save(self, industry_daily: IrsIndustryDaily) -> None:
        """保存单条记录（幂等）"""
        pass
    
    def save_batch(self, industry_dailies: List[IrsIndustryDaily]) -> int:
        """批量保存"""
        pass
    
    def get_by_date(self, trade_date: str) -> List[IrsIndustryDaily]:
        """按日期查询所有行业"""
        pass
    
    def get_by_industry(self, industry_code: str, limit: int = 30) -> List[IrsIndustryDaily]:
        """按行业查询历史"""
        pass
```

---

## 7. 错误处理策略

### 7.1 错误分类与处理

| 错误场景 | 错误码 | 严重等级 | 处理策略 | 重试 |
|----------|--------|----------|----------|------|
| 行业分类数据缺失 | IRS_E001 | P0 | 抛出异常，阻断流程 | 否 |
| 行业数量不足31 | IRS_E002 | P0 | 抛出异常 | 否 |
| 基准指数数据缺失 | IRS_E003 | P1 | 使用备用基准，记录警告 | 否 |
| 行业日线数据不足 | IRS_E004 | P1 | 该行业评分设为50，记录警告 | 否 |
| PE数据缺失 | IRS_E005 | P2 | 使用行业中位数，记录信息 | 否 |
| 评分越界 | IRS_E006 | P1 | 截断到[0,100]，记录警告 | 否 |
| 排名冲突 | IRS_E007 | P1 | 按评分重新排序，记录警告 | 否 |
| 数据库写入失败 | IRS_E008 | P0 | 重试3次后抛出异常 | ✅(3次) |

### 7.2 重试策略

```python
IRS_RETRY_CONFIG = {
    "db_write": {
        "max_retries": 3,
        "base_delay": 1.0,
        "exponential": True,
        "max_delay": 10.0
    }
}
```

---

## 8. 质量监控

### 8.1 每日质量检查项

| 检查项 | 检查方法 | 预期结果 | 告警阈值 |
|--------|----------|----------|----------|
| 行业数量 | COUNT(DISTINCT industry_code) | = 31 | ≠ 31 |
| 评分范围 | industry_score | ∈ [0, 100] | 越界 |
| 排名唯一性 | COUNT(DISTINCT rank) | = 31 | < 31 |
| 权重总和 | 25+20+20+15+12+8 | = 100 | ≠ 100 |
| 轮动状态有效性 | rotation_status | ∈ 3个有效值 | 无效值 |
| 连续性 | 与前一交易日间隔 | ≤ 1个交易日 | 缺失 |

### 8.2 质量监控表

```sql
CREATE TABLE irs_quality_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date VARCHAR(8) NOT NULL,
    check_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- 检查结果
    industry_count INTEGER,
    score_range_valid BOOLEAN,
    rank_unique BOOLEAN,
    weight_sum_valid BOOLEAN,
    rotation_status_valid BOOLEAN,
    continuity_valid BOOLEAN,
    
    -- 异常信息
    error_code VARCHAR(20),
    error_message TEXT,
    
    -- 状态
    status VARCHAR(20) DEFAULT 'PASS',
    
    UNIQUE(trade_date)
);
```

---

## 9. 执行计划

### 9.1 Task 级别详细计划

---

#### Task 1: 基础因子实现

**目标**: 实现相对强度、连续性、资金流向、估值因子

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| raw_daily | Phase 01 | 记录≥4500 | 阻断 |
| raw_daily_basic | Phase 01 | PE数据存在 | 用中位数填充 |
| raw_index_daily | Phase 01 | 基准指数存在 | 用中证全指 |
| 行业映射 | Phase 01 | 31行业 | 阻断 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| RelativeStrengthCalculator | 代码 | 输出∈[0,100] | `src/algorithms/irs/` |
| ContinuityCalculator | 代码 | 连续性窗口统计 | `src/algorithms/irs/` |
| CapitalFlowCalculator | 代码 | 10日累计 | `src/algorithms/irs/` |
| ValuationCalculator | 代码 | 3年分位 | `src/algorithms/irs/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 因子范围 | [0,100] | 边界测试 |
| 权重分配 | 25%+20%+20%+15%=80% | 单元测试 |
| 行业覆盖 | 31个 | DISTINCT检查 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 基准数据缺失 | 用备用基准 | 记录警告 |
| PE数据缺失 | 用行业中位数 | 记录警告 |
| 行业数据不足 | 评分设为50 | 记录警告 |

**验收检查**

- [ ] 相对强度因子正确
- [ ] 连续性因子正确
- [ ] 资金流向因子正确
- [ ] 估值因子正确

---

#### Task 2: 增强因子实现

**目标**: 实现龙头因子、行业基因库

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| raw_daily | Phase 01 | 数据存在 | 阻断 |
| raw_limit_list | Phase 01 | 数据存在 | 阻断 |
| 历史数据3年 | Phase 01 | 用于基因库 | 缩短窗口 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| LeaderCalculator | 代码 | Top5龙头 | `src/algorithms/irs/` |
| GeneCalculator | 代码 | 时间衰减正确 | `src/algorithms/irs/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 因子范围 | [0,100] | 边界测试 |
| 权重分配 | 12%+8%=20% | 单元测试 |
| 衰减系数 | 0.9默认 | 参数检查 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 龙头数据不足 | 用现有数据 | 记录警告 |
| 历史数据不足 | 缩短窗口 | 记录警告 |

**验收检查**

- [ ] 龙头因子计算正确
- [ ] 行业基因库衰减正确
- [ ] 所有因子∈[0,100]

---

#### Task 3: 综合评分与排名

**目标**: 实现六因子加权评分和排名生成

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| 基础因子 | Task 1 | 测试通过 | 阻断 |
| 增强因子 | Task 2 | 测试通过 | 阻断 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| IrsScoreCalculator | 代码 | 权重合=100% | `src/algorithms/irs/` |
| RankGenerator | 代码 | 排名1-31无重复 | `src/algorithms/irs/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 评分范围 | [0,100] | 边界测试 |
| 权重总和 | =100% | 单元测试 |
| 排名唯一 | 无重复 | DISTINCT检查 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 评分越界 | 截断到[0,100] | 记录警告 |
| 排名冲突 | 按评分重排 | 记录警告 |

**验收检查**

- [ ] 六因子权重合=100%
- [ ] 评分范围正确
- [ ] 排名1-31无重复

---

#### Task 4: 轮动状态与落库

**目标**: 实现轮动状态判断、数据落库、质量监控

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| 评分计算器 | Task 3 | 测试通过 | 阻断 |
| 历史评分3日 | 自身 | 用于轮动判断 | 设为HOLD |
| DuckDB连接 | Phase 01 | 可连接 | 阻断 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| RotationDetector | 代码 | IN/OUT/HOLD | `src/algorithms/irs/` |
| IrsRepository | 代码 | 幂等写入 | `src/algorithms/irs/` |
| irs_industry_daily表 | 数据 | 31行业/日 | L3 DuckDB（按年分库） |
| 质量监控 | 代码 | 6项检查 | `scripts/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 覆盖率 | ≥80% | `pytest --cov` |
| 行业覆盖 | =31 | COUNT检查 |
| 幂等性 | 重复写入不报错 | 单元测试 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 行业不足31 | 抛出异常 | 立即阻断 |
| DB写入失败 | 重试3次 | 失败后抛异常 |
| 历史数据不足 | 状态设为HOLD | 记录信息 |

**验收检查**

- [ ] 轮动状态连续3日规则
- [ ] 31行业全覆盖
- [ ] 测试覆盖率≥80%
- [ ] **M3里程碑完成**

### 9.2 每日执行时序

```text
17:00  raw_daily/raw_daily_basic 数据就绪（Phase 01）
  ↓
17:10  触发 IRS 计算
  ↓
17:10  加载 31 行业的股票日线数据
  ↓
17:11  计算相对强度因子
  ↓
17:12  计算连续性因子
  ↓
17:12  计算资金流向因子
  ↓
17:13  计算估值因子
  ↓
17:13  计算龙头因子
  ↓
17:14  计算行业基因库
  ↓
17:14  加权求和得到综合评分
  ↓
17:14  生成排名
  ↓
17:15  判定轮动状态
  ↓
17:15  生成配置建议
  ↓
17:15  写入 irs_industry_daily
  ↓
17:16  质量检查
  ↓
17:16  IRS 计算完成，通知 Phase 04 (PAS)
```

---

## 10. 验收检查清单

### 10.1 功能验收

- [ ] 相对强度因子计算正确（行业-基准）
- [ ] 连续性因子计算正确（广度连续性）
- [ ] 资金流向因子计算正确（10日累计）
- [ ] 估值因子计算正确（3年分位）
- [ ] 龙头因子计算正确（Top5加权）
- [ ] 行业基因库计算正确（时间衰减）
- [ ] 综合评分计算正确（权重精确）
- [ ] 排名生成正确（无重复）
- [ ] 轮动状态判定正确（连续3日规则）
- [ ] 配置建议正确（排名映射）

### 10.2 质量验收

- [ ] 测试覆盖率 ≥ 80%
- [ ] 31个行业全覆盖
- [ ] 所有因子得分 ∈ [0, 100]
- [ ] industry_score ∈ [0, 100]
- [ ] 排名 ∈ [1, 31]，无重复
- [ ] rotation_status ∈ {IN, OUT, HOLD}
- [ ] 历史数据回填完整

### 10.3 性能验收

- [ ] 31行业计算延迟 ≤ 30秒
- [ ] 批量计算（1年）≤ 10分钟
- [ ] 数据库写入幂等

---

## 11. 参数配置表

### 11.1 因子权重（固定）

| 因子 | 权重 | 说明 |
|------|------|------|
| 相对强度 | 25% | 基础因子 |
| 连续性因子 | 20% | 基础因子 |
| 资金流向 | 20% | 基础因子 |
| 估值因子 | 15% | 基础因子 |
| 龙头因子 | 12% | 增强因子 |
| 行业基因库 | 8% | 增强因子 |

### 11.2 算法参数

| 参数名称 | 代码 | 默认值 | 可调范围 | 说明 |
|----------|------|--------|----------|------|
| 连续性窗口 | continuity_window | 5 | 3-10 | 连续性统计窗口 |
| 资金流窗口 | capital_flow_window | 10 | 5-20 | 资金流向累计窗口 |
| 估值历史窗口 | valuation_history_window | 3y | 1y-5y | PE分位历史窗口 |
| Z-Score窗口 | zscore_window | 120 | 60-240 | Z-Score统计窗口 |
| 龙头Top | leader_top_n | 5 | 3-10 | 龙头股样本数 |
| 基因衰减 | gene_decay | 0.9 | 0.7-0.98 | 基因库衰减系数 |
| 轮动窗口 | rotation_window | 3 | 2-5 | 连续N日判定轮动 |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v4.0.3 | 2026-02-06 | 输入依赖统一为 Data Layer raw_* 表命名，数据来源注释与执行时序同步修正 |
| v4.0.2 | 2026-02-05 | 龙头因子/行业基因库归一化口径与设计文档对齐（ratio→zscore） |
| v4.0.1 | 2026-02-04 | 连续性因子命名统一、DuckDB存储口径更新 |
| v4.0.0 | 2026-02-02 | 完整重构：添加量化验收标准、I/O规范、错误处理、质量监控 |
| v3.0.0 | 2026-01-31 | 重构版：统一六因子架构 |


