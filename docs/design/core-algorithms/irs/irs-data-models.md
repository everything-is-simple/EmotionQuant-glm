# IRS 数据模型

**版本**: v3.3.0（重构版）
**最后更新**: 2026-02-09
**状态**: 设计完成（验收口径补齐；代码未落地）

---

## 1. 数据依赖

### 1.1 Data Layer 输入依赖

| 输入表 | 更新频率 | 用途 |
|----------|----------|------|
| `raw_daily` | 每交易日 | 行业成分股日线行情 |
| `raw_daily_basic` | 每交易日 | 换手率、估值、流通市值 |
| `raw_limit_list` | 每交易日 | 涨跌停统计（龙头因子、基因库） |
| `raw_index_daily` | 每交易日 | 基准指数涨跌幅 |
| `raw_index_classify` | 半年 | 申万一级行业分类 |
| `raw_index_member` | 月度 | 行业成分股列表 |
| `raw_stock_basic` | 月度 | 股票基础信息 |
| `raw_trade_cal` | 年度 | 交易日历 |

### 1.2 数据字段依赖

| 因子 | 依赖字段 | 来源 |
|------|----------|------|
| 相对强度 | industry_pct_chg, benchmark_pct_chg | `raw_daily` + `raw_index_daily` |
| 连续性因子 | rise_count, fall_count, stock_count, new_100d_high_count, new_100d_low_count | `raw_daily` 聚合 |
| 资金流向 | industry_amount, industry_amount_prev, industry_amount_avg_20d | `raw_daily` + `raw_daily_basic` 聚合 |
| 估值因子 | industry_pe_ttm, industry_pb | `raw_daily_basic` |
| 龙头因子 | top5_pct_chg, top5_limit_up | `raw_daily` + `raw_limit_list` |
| 行业基因库 | history_limit_up, history_new_high | `raw_daily` + `raw_limit_list` |
| 辅助观测（非评分） | flat_count, yesterday_limit_up_today_avg_pct | `industry_snapshot` 聚合 |
| 归一化基线 | mean/std 参数（按因子） | `${DATA_PATH}/config/irs_zscore_baseline.parquet` |

> 说明：`industry_turnover` 保留在 `IrsIndustrySnapshot` 作为流动性辅助观测字段；当前资金流向评分公式不直接使用该字段。

---

## 2. 输入数据模型

### 2.1 行业日快照（IrsIndustrySnapshot）

```python
@dataclass
class IrsIndustrySnapshot:
    """IRS 行业日快照（输入）"""
    trade_date: str              # 交易日期 YYYYMMDD
    industry_code: str           # 行业代码（申万一级）
    industry_name: str           # 行业名称
    
    # 基础行情
    industry_pct_chg: float      # 行业当日涨跌幅
    industry_close: float        # 行业收盘指数
    industry_amount: float       # 行业成交额
    industry_turnover: float     # 行业平均换手率
    
    # 成分股统计
    stock_count: int             # 成分股数量
    rise_count: int              # 上涨股数
    fall_count: int              # 下跌股数
    flat_count: int              # 平盘股数（与 rise_count/fall_count 可交叉覆盖）
    limit_up_count: int          # 涨停股数
    limit_down_count: int        # 跌停股数
    new_100d_high_count: int     # 100日新高股数
    new_100d_low_count: int      # 100日新低股数
    
    # 估值数据
    industry_pe_ttm: float       # 行业市盈率（TTM）
    industry_pb: float           # 行业市净率
    
    # 龙头股数据
    top5_codes: List[str]        # Top5 股票代码
    top5_pct_chg: List[float]    # Top5 涨跌幅
    top5_limit_up: int           # Top5 中涨停数量
    yesterday_limit_up_today_avg_pct: float  # 昨涨停今平均涨幅（兼容观测字段，当前不直接参与IRS评分）
```

> 字段口径说明：`flat_count` 与 `yesterday_limit_up_today_avg_pct` 作为跨模块兼容观测字段保留；
> 当前 IRS 因子计算不直接使用这两个字段，但允许在协同层/诊断层透传。

### 2.2 基准指数数据

```python
@dataclass
class BenchmarkData:
    """基准指数数据"""
    trade_date: str              # 交易日期
    index_code: str              # 指数代码（000300.SH / 000985.CSI）
    pct_chg: float               # 涨跌幅
    close: float                 # 收盘点位
```

---

## 3. 输出数据模型

### 3.1 IRS 计算结果（IrsIndustryDaily）

```python
@dataclass
class IrsIndustryDaily:
    """IRS 行业每日计算结果（输出）"""
    trade_date: str              # 交易日期 YYYYMMDD
    industry_code: str           # 行业代码
    industry_name: str           # 行业名称
    
    # 核心输出
    industry_score: float        # 行业综合评分 0-100
    rank: int                    # 行业排名
    rotation_status: str         # 轮动状态 IN/OUT/HOLD
    rotation_detail: str         # 轮动详情
    allocation_advice: str       # 配置建议
    quality_flag: str            # 质量标记 normal/cold_start/stale
    sample_days: int             # 有效样本天数
    
    # 因子得分
    relative_strength: float     # 相对强度得分
    continuity_factor: float     # 连续性因子得分
    capital_flow: float          # 资金流向得分
    valuation: float             # 估值得分
    leader_score: float          # 龙头因子得分
    gene_score: float            # 行业基因库得分
    
    # 辅助信息
    neutrality: float            # 中性度 0-1（越接近1越中性，越接近0信号越极端）
```

### 3.2 轮动状态枚举

```python
class IrsRotationStatus(Enum):
    """轮动状态枚举"""
    IN = "IN"           # 进入轮动
    OUT = "OUT"         # 退出轮动
    HOLD = "HOLD"       # 维持观望
```

### 3.3 轮动详情枚举

```python
class IrsRotationDetail(Enum):
    """轮动详情枚举"""
    LEADER_RALLY = "强势领涨"
    ROTATION_ACCEL = "轮动加速"
    STYLE_SWITCH = "风格转换"
    HOTSPOT_DIFFUSION = "热点扩散"
    HIGH_LEVEL_CONSOLIDATION = "高位整固"
    TREND_REVERSAL = "趋势反转"
```

### 3.4 配置建议枚举

```python
class IrsAllocationAdvice(Enum):
    """配置建议枚举"""
    OVERWEIGHT = "超配"      # 排名前3
    STANDARD = "标配"        # 排名4-10
    UNDERWEIGHT = "减配"     # 排名11-26
    AVOID = "回避"           # 排名27-31（后5）
```

---

## 4. 数据库表结构

> 以下为 **MySQL 风格逻辑DDL（伪代码）**，用于表达字段与约束语义，**不可直接在 DuckDB 执行**。  
> DuckDB 落地时请改写为 `CREATE TABLE ...` + `CREATE INDEX ...`，字段注释改为独立文档或 `COMMENT ON` 形式。

### 4.1 主表：irs_industry_daily

```sql
CREATE TABLE irs_industry_daily (
    id INTEGER PRIMARY KEY,
    trade_date VARCHAR(8) NOT NULL COMMENT '交易日期 YYYYMMDD',
    industry_code VARCHAR(10) NOT NULL COMMENT '行业代码',
    industry_name VARCHAR(50) COMMENT '行业名称',
    
    -- 核心输出
    industry_score DECIMAL(8,4) COMMENT '行业综合评分 0-100',
    rank INT COMMENT '行业排名',
    rotation_status VARCHAR(20) COMMENT '轮动状态',
    rotation_detail VARCHAR(50) COMMENT '轮动详情',
    allocation_advice VARCHAR(20) COMMENT '配置建议',
    quality_flag VARCHAR(20) COMMENT '质量标记 normal/cold_start/stale',
    sample_days INT COMMENT '有效样本天数',
    
    -- 因子得分
    relative_strength DECIMAL(8,4) COMMENT '相对强度得分',
    continuity_factor DECIMAL(8,4) COMMENT '连续性因子得分',
    capital_flow DECIMAL(8,4) COMMENT '资金流向得分',
    valuation DECIMAL(8,4) COMMENT '估值得分',
    leader_score DECIMAL(8,4) COMMENT '龙头因子得分',
    gene_score DECIMAL(8,4) COMMENT '行业基因库得分',
    
    -- 辅助信息
    neutrality DECIMAL(8,4) COMMENT '中性度 0-1（越接近1越中性，越接近0信号越极端）',

    -- 元数据
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_trade_date_industry (trade_date, industry_code),
    KEY idx_industry_score (industry_score),
    KEY idx_rank (rank)
);
```

### 4.2 因子中间表：irs_factor_intermediate

```sql
CREATE TABLE irs_factor_intermediate (
    id INTEGER PRIMARY KEY,
    trade_date VARCHAR(8) NOT NULL COMMENT '交易日期 YYYYMMDD',
    industry_code VARCHAR(10) NOT NULL COMMENT '行业代码',
    
    -- 原始因子值（归一化前）
    relative_strength_raw DECIMAL(12,6) COMMENT '相对强度原始值',
    continuity_factor_raw DECIMAL(12,6) COMMENT '连续性因子原始值',
    capital_flow_raw DECIMAL(12,6) COMMENT '资金流向原始值',
    valuation_raw DECIMAL(12,6) COMMENT '估值原始值',
    leader_score_raw DECIMAL(12,6) COMMENT '龙头因子原始值',
    gene_score_raw DECIMAL(12,6) COMMENT '行业基因库原始值',

    -- 归一化统计参数快照（6 因子独立 mean/std）
    relative_strength_mean DECIMAL(12,6) COMMENT '相对强度滚动均值',
    relative_strength_std DECIMAL(12,6) COMMENT '相对强度滚动标准差',
    continuity_factor_mean DECIMAL(12,6) COMMENT '连续性因子滚动均值',
    continuity_factor_std DECIMAL(12,6) COMMENT '连续性因子滚动标准差',
    capital_flow_mean DECIMAL(12,6) COMMENT '资金流向滚动均值',
    capital_flow_std DECIMAL(12,6) COMMENT '资金流向滚动标准差',
    valuation_mean DECIMAL(12,6) COMMENT '估值因子滚动均值',
    valuation_std DECIMAL(12,6) COMMENT '估值因子滚动标准差',
    leader_score_mean DECIMAL(12,6) COMMENT '龙头因子滚动均值',
    leader_score_std DECIMAL(12,6) COMMENT '龙头因子滚动标准差',
    gene_score_mean DECIMAL(12,6) COMMENT '行业基因库滚动均值',
    gene_score_std DECIMAL(12,6) COMMENT '行业基因库滚动标准差',
    
    -- 元数据
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_trade_date_industry (trade_date, industry_code)
);
```

### 4.3 配置日志表：irs_allocation_log

```sql
CREATE TABLE irs_allocation_log (
    id INTEGER PRIMARY KEY,
    trade_date VARCHAR(8) NOT NULL COMMENT '交易日期 YYYYMMDD',
    industry_code VARCHAR(10) NOT NULL COMMENT '行业代码',
    
    -- 配置信息
    allocation_advice VARCHAR(20) COMMENT '配置建议',
    target_weight DECIMAL(8,4) COMMENT '目标权重',
    reason VARCHAR(200) COMMENT '调整原因',
    
    -- 元数据
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    KEY idx_trade_date (trade_date)
);
```

---

## 5. 行业代码映射

### 5.1 申万一级行业（31个）

| 行业代码 | 行业名称 | 类型 |
|----------|----------|------|
| 801010 | 农林牧渔 | 周期 |
| 801030 | 基础化工 | 周期 |
| 801040 | 钢铁 | 周期 |
| 801050 | 有色金属 | 周期 |
| 801080 | 电子 | 成长 |
| 801110 | 家用电器 | 消费 |
| 801120 | 食品饮料 | 消费 |
| 801130 | 纺织服饰 | 消费 |
| 801140 | 轻工制造 | 消费 |
| 801150 | 医药生物 | 成长 |
| 801160 | 公用事业 | 防御 |
| 801170 | 交通运输 | 防御 |
| 801180 | 房地产 | 周期 |
| 801200 | 商贸零售 | 消费 |
| 801210 | 社会服务 | 消费 |
| 801230 | 综合 | 其他 |
| 801710 | 建筑材料 | 周期 |
| 801720 | 建筑装饰 | 周期 |
| 801730 | 电力设备 | 成长 |
| 801740 | 国防军工 | 成长 |
| 801750 | 计算机 | 成长 |
| 801760 | 传媒 | 成长 |
| 801770 | 通信 | 成长 |
| 801780 | 银行 | 金融 |
| 801790 | 非银金融 | 金融 |
| 801880 | 汽车 | 周期 |
| 801890 | 机械设备 | 周期 |
| 801950 | 煤炭 | 周期 |
| 801960 | 石油石化 | 周期 |
| 801970 | 环保 | 成长 |
| 801980 | 美容护理 | 消费 |

---

## 6. 数据验证规则

### 6.1 输入验证

| 字段 | 验证规则 |
|------|----------|
| industry_code | 必须在31个申万一级行业内 |
| stock_count | > 0 |
| rise_count + fall_count | ≤ stock_count |
| flat_count | ≤ stock_count |
| irs_zscore_baseline | 文件可读且覆盖 6 个因子；缺失时回退 50 |

### 6.2 输出验证

| 字段 | 验证规则 |
|------|----------|
| industry_score | 0 ≤ x ≤ 100 |
| rank | 1 ≤ x ≤ 31 |
| rotation_status | IN/OUT/HOLD |
| rotation_detail | 强势领涨/轮动加速/风格转换/热点扩散/高位整固/趋势反转 |
| quality_flag | normal/cold_start/stale |
| sample_days | x ≥ 0 |
| neutrality | 0 ≤ x ≤ 1 |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.3.0 | 2026-02-09 | 修复 R28：DDL 中 `trade_date` 统一为 `VARCHAR(8)`；`industry_name` 宽度统一为 `VARCHAR(50)`；时间戳命名统一为 `created_at` 并移除 L3 主表 `update_time` |
| v3.2.9 | 2026-02-09 | 修复 R26：`IrsIndustryDaily` 与 `irs_industry_daily` DDL 增加 `quality_flag/sample_days`；§6.2 输出验证补充质量字段约束 |
| v3.2.8 | 2026-02-08 | 修复 R19：新增 `IrsRotationDetail` 枚举；§6.2 输出验证补齐 `rotation_detail` 合法值约束 |
| v3.2.7 | 2026-02-08 | 修复 R18：`irs_factor_intermediate` 补齐 6 因子独立 `mean/std` 快照，增强归一化参数追溯能力 |
| v3.2.6 | 2026-02-08 | 修复 R17：资金流向依赖字段改为 `industry_amount/industry_amount_prev/industry_amount_avg_20d`；补充 `industry_turnover` 为辅助观测说明 |
| v3.2.5 | 2026-02-08 | 修复 R10：行业映射对齐申万2021，移除退役代码 `801020`、新增 `801980`，并同步名称口径（基础化工/纺织服饰/商贸零售/社会服务/电力设备） |
| v3.2.4 | 2026-02-07 | 修复 R5：补充 IRS baseline 依赖与冷启动兜底校验口径；DDL 标注为 DuckDB 不可直接执行的伪代码 |
| v3.2.3 | 2026-02-07 | 修复 P1：补齐兼容观测字段 `flat_count`/`yesterday_limit_up_today_avg_pct`，与 Data Layer 与快照实现对齐 |
| v3.2.2 | 2026-02-07 | 修复 P0：allocation_advice 映射口径覆盖 31 行业（减配 11-26，回避 27-31） |
| v3.2.1 | 2026-02-06 | 输入依赖命名统一为 Data Layer raw_* 表口径 |
| v3.2.0 | 2026-02-04 | 同步 IRS v3.2.0：动量斜率替换为连续性因子；补齐新高/新低字段与口径 |
| v3.0.0 | 2026-01-31 | 重构版：统一数据模型、添加枚举定义、完善验证规则 |

---

**关联文档**：
- 算法设计：[irs-algorithm.md](./irs-algorithm.md)
- API接口：[irs-api.md](./irs-api.md)
- 信息流：[irs-information-flow.md](./irs-information-flow.md)


