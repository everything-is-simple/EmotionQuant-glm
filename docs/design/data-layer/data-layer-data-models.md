# Data Layer 数据模型

**版本**: v3.2.5（重构版）
**最后更新**: 2026-02-09
**状态**: 设计完成（对齐 MSS/IRS/PAS/Integration；代码未落地）

---

## 实现状态（仓库现状）

- 当前 `src/data/models/*.py` 仅包含简化占位数据类，字段与本文档不一致。
- 本文档为权威数据模型口径，实际实现以本表为准。

---

## 1. 数据模型总览

### 1.1 分层结构

```
┌─────────────────────────────────────────────────────────────────┐
│                    数据模型分层架构                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  L1 Raw Tables（Parquet文件）                                    │
│  ├── raw_daily              个股日线行情                         │
│  ├── raw_daily_basic        日线基础数据                         │
│  ├── raw_limit_list         涨跌停列表                           │
│  ├── raw_index_daily        指数日线                             │
│  ├── raw_index_member       行业成分股                           │
│  ├── raw_index_classify     行业分类                             │
│  ├── raw_stock_basic        股票基础信息                         │
│  └── raw_trade_cal          交易日历                             │
│                                                                  │
│  L2 Processed Tables（DuckDB 单库优先，阈值触发分库）            │
│  ├── market_snapshot        市场快照                             │
│  ├── industry_snapshot      行业快照                             │
│  └── stock_gene_cache       牛股基因缓存                         │
│                                                                  │
│  L3 Runtime Tables（DuckDB 单库优先，阈值触发分库）              │
│  ├── mss_panorama           MSS全景输出                          │
│  ├── irs_industry_daily     IRS行业评分                          │
│  ├── stock_pas_daily        PAS每日评分                          │
│  ├── integrated_recommendation  三三制集成                       │
│  ├── pas_breadth_daily      PAS广度聚合（BU派生）                 │
│  └── validation_*           Validation运行时表（5张，详见§4.6）   │
│                                                                  │
│  L4 Analysis Tables（DuckDB 单库优先，阈值触发分库）             │
│  ├── daily_report           日度分析报告                         │
│  ├── performance_metrics    绩效指标                             │
│  └── signal_attribution     信号归因                             │
│                                                                  │
│  Ops/Metadata Tables（DuckDB ops.duckdb）                        │
│  ├── system_config          系统配置                             │
│  ├── data_version_log       数据版本日志                         │
│  ├── task_execution_log     任务执行日志                         │
│  └── data_quality_report    数据质量报告                         │
│                                                                  │
│  Business Tables（DuckDB 单库优先，阈值触发分库）                │
│  ├── trade_records          交易记录                             │
│  ├── positions              持仓记录                             │
│  ├── t1_frozen              T+1冻结记录                          │
│  ├── backtest_trade_records 回测交易记录                         │
│  └── backtest_results       回测结果                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. L1 原始数据表

### 2.1 raw_daily 日线行情

| 字段 | 类型 | 说明 | 来源 |
|------|------|------|------|
| ts_code | VARCHAR(20) | 股票代码（含交易所后缀） | TuShare |
| trade_date | VARCHAR(8) | 交易日期 YYYYMMDD | TuShare |
| open | DECIMAL(12,4) | 开盘价 | TuShare |
| high | DECIMAL(12,4) | 最高价 | TuShare |
| low | DECIMAL(12,4) | 最低价 | TuShare |
| close | DECIMAL(12,4) | 收盘价 | TuShare |
| pre_close | DECIMAL(12,4) | 前收盘价 | TuShare |
| change | DECIMAL(12,4) | 涨跌额 | TuShare |
| pct_chg | DECIMAL(10,4) | 涨跌幅(%) | TuShare |
| vol | DECIMAL(20,2) | 成交量(手) | TuShare |
| amount | DECIMAL(20,2) | 成交额(千元) | TuShare |

**存储**：`${DATA_PATH}/parquet/daily/{trade_date}.parquet`

### 2.2 raw_daily_basic 日线基础

| 字段 | 类型 | 说明 | 来源 |
|------|------|------|------|
| ts_code | VARCHAR(20) | 股票代码 | TuShare |
| trade_date | VARCHAR(8) | 交易日期 | TuShare |
| turnover_rate | DECIMAL(10,4) | 换手率(%) | TuShare |
| turnover_rate_f | DECIMAL(10,4) | 换手率(自由流通股) | TuShare |
| volume_ratio | DECIMAL(8,4) | 量比 | TuShare |
| pe_ttm | DECIMAL(12,4) | 市盈率(TTM) | TuShare |
| pe | DECIMAL(12,4) | 市盈率 | TuShare |
| pb | DECIMAL(12,4) | 市净率 | TuShare |
| total_mv | DECIMAL(20,2) | 总市值(万元) | TuShare |
| circ_mv | DECIMAL(20,2) | 流通市值(万元) | TuShare |

**存储**：`${DATA_PATH}/parquet/daily_basic/{trade_date}.parquet`

### 2.3 raw_limit_list 涨跌停列表

| 字段 | 类型 | 说明 | 来源 |
|------|------|------|------|
| ts_code | VARCHAR(20) | 股票代码 | TuShare |
| trade_date | VARCHAR(8) | 交易日期 | TuShare |
| name | VARCHAR(50) | 股票名称 | TuShare |
| close | DECIMAL(12,4) | 收盘价 | TuShare |
| pct_chg | DECIMAL(10,4) | 涨跌幅 | TuShare |
| amp | DECIMAL(10,4) | 振幅 | TuShare |
| limit | VARCHAR(10) | 涨跌停类型 U/D/Z | TuShare |
| fc_ratio | DECIMAL(10,4) | 封单金额/流通市值 | TuShare |
| fl_ratio | DECIMAL(10,4) | 封单手数/成交量 | TuShare |
| fd_amount | DECIMAL(20,2) | 封单金额 | TuShare |
| first_time | VARCHAR(8) | 首次涨停时间 | TuShare |
| last_time | VARCHAR(8) | 最后涨停时间 | TuShare |
| open_times | INTEGER | 打开次数 | TuShare |
| strth | DECIMAL(8,4) | 涨跌停强度 | TuShare |

**limit类型说明**：
- `U`: 涨停（封住）
- `D`: 跌停（封住）
- `Z`: 曾涨停（炸板）

**存储**：`${DATA_PATH}/parquet/limit_list/{trade_date}.parquet`

### 2.4 raw_index_daily 指数日线

| 字段 | 类型 | 说明 |
|------|------|------|
| ts_code | VARCHAR(20) | 指数代码 |
| trade_date | VARCHAR(8) | 交易日期 |
| close | DECIMAL(12,4) | 收盘点位 |
| open | DECIMAL(12,4) | 开盘点位 |
| high | DECIMAL(12,4) | 最高点位 |
| low | DECIMAL(12,4) | 最低点位 |
| pre_close | DECIMAL(12,4) | 前收盘点位 |
| change | DECIMAL(12,4) | 涨跌点 |
| pct_chg | DECIMAL(10,4) | 涨跌幅(%) |
| vol | DECIMAL(20,2) | 成交量(手) |
| amount | DECIMAL(20,2) | 成交额(千元) |

**存储**：`${DATA_PATH}/parquet/index_daily/{trade_date}.parquet`

### 2.5 raw_index_member 行业成分

| 字段 | 类型 | 说明 |
|------|------|------|
| index_code | VARCHAR(20) | 行业指数代码 |
| index_name | VARCHAR(50) | 行业名称 |
| con_code | VARCHAR(20) | 成分股代码 |
| con_name | VARCHAR(50) | 成分股名称 |
| in_date | VARCHAR(8) | 纳入日期 |
| out_date | VARCHAR(8) | 剔除日期 |
| is_new | VARCHAR(10) | 是否最新 |

**存储**：`${DATA_PATH}/parquet/index_member/index_member.parquet`

### 2.6 raw_index_classify 行业分类

| 字段 | 类型 | 说明 |
|------|------|------|
| index_code | VARCHAR(20) | 行业指数代码 |
| index_name | VARCHAR(50) | 行业名称 |
| level | VARCHAR(10) | 行业级别（L1/L2/L3） |
| parent_code | VARCHAR(20) | 上级行业代码（可空） |
| src | VARCHAR(20) | 分类来源（如 SW2021） |

> 说明：字段以 TuShare 官方返回为准，至少保留 `index_code/index_name/level/src` 以满足行业映射。

**存储**：`${DATA_PATH}/parquet/index_classify/index_classify.parquet`

### 2.7 raw_stock_basic 股票基础信息

| 字段 | 类型 | 说明 |
|------|------|------|
| ts_code | VARCHAR(20) | 股票代码（含交易所后缀） |
| name | VARCHAR(50) | 股票名称 |
| industry | VARCHAR(50) | 行业名称（TuShare 字段，可空） |
| list_date | VARCHAR(8) | 上市日期 YYYYMMDD |

**存储**：`${DATA_PATH}/parquet/stock_basic/stock_basic.parquet`

### 2.8 raw_trade_cal 交易日历

| 字段 | 类型 | 说明 |
|------|------|------|
| cal_date | VARCHAR(8) | 日期 YYYYMMDD |
| is_open | INTEGER | 是否交易日（1/0） |
| pretrade_date | VARCHAR(8) | 上一交易日（可空） |

**存储**：`${DATA_PATH}/parquet/trade_cal/trade_cal.parquet`

---

## 3. L2 处理数据表

### 3.1 market_snapshot 市场快照

| 字段 | 类型 | 说明 | 计算逻辑 |
|------|------|------|----------|
| trade_date | VARCHAR(8) | 交易日期 | PK |
| total_stocks | INTEGER | 有效股票总数 | COUNT(daily) |
| rise_count | INTEGER | 上涨家数 | pct_chg > 0 |
| fall_count | INTEGER | 下跌家数 | pct_chg < 0 |
| flat_count | INTEGER | 平盘家数 | abs(pct_chg) <= flat_threshold（单位：%，默认 0.5） |
| strong_up_count | INTEGER | 大涨家数 | pct_chg > 5% |
| strong_down_count | INTEGER | 大跌家数 | pct_chg < -5% |
| limit_up_count | INTEGER | 涨停家数 | limit == 'U' |
| limit_down_count | INTEGER | 跌停家数 | limit == 'D' |
| touched_limit_up | INTEGER | 曾涨停家数 | limit ∈ {'U', 'Z'}（当日触及涨停总数） |
| new_100d_high_count | INTEGER | 100日新高数 | close > max(close, 100d) |
| new_100d_low_count | INTEGER | 100日新低数 | close < min(close, 100d) |
| continuous_limit_up_2d | INTEGER | 连续2日涨停 | 派生计算 |
| continuous_limit_up_3d_plus | INTEGER | 连续3+日涨停 | 派生计算 |
| continuous_new_high_2d_plus | INTEGER | 连续2日+新高 | 派生计算 |
| high_open_low_close_count | INTEGER | 高开低走计数 | open>pre_close*1.02 且 close<open*0.94 |
| low_open_high_close_count | INTEGER | 低开高走计数 | open<pre_close*0.98 且 close>open*1.06 |
| pct_chg_std | DECIMAL | 全市场涨跌幅标准差 | std(pct_chg) |
| amount_volatility | DECIMAL | 成交额相对20日均值的波动率 | (amount - ma20(amount))/ma20(amount) |
| yesterday_limit_up_today_avg_pct | DECIMAL | 昨涨停今平均涨幅 | 聚合计算 |
| data_quality | VARCHAR(20) | 数据质量标记 normal/stale/cold_start | 缺口降级标记 |
| stale_days | INTEGER | 距离源数据最近有效交易日的天数 | stale 时 > 0 |
| source_trade_date | VARCHAR(8) | 本条快照实际来源交易日 | 与 trade_date 比较可追溯降级链 |
| created_at | DATETIME | 创建时间 | 自动 |

> 兼容字段说明：如历史实现仍存在 `big_drop_count`，其语义等同 `strong_down_count`（后续以 strong_down_count 为准）。

> 计数语义说明：`flat_count` 与 `rise_count`/`fall_count` 允许交叉覆盖（例如 `pct_chg=0.3%` 同时计入 `rise_count` 与 `flat_count`），因此三者不构成互斥分桶。

> 参数口径：`flat_threshold` 默认值为 `0.5`（单位：%），建议通过 `system_config` 下发并与聚合逻辑保持一致。

**索引**：
- `PRIMARY KEY (trade_date)`

### 3.2 industry_snapshot 行业快照

| 字段 | 类型 | 说明 |
|------|------|------|
| trade_date | VARCHAR(8) | 交易日期 |
| industry_code | VARCHAR(10) | 行业代码 |
| industry_name | VARCHAR(50) | 行业名称 |
| stock_count | INTEGER | 行业内股票数 |
| rise_count | INTEGER | 上涨家数 |
| fall_count | INTEGER | 下跌家数 |
| flat_count | INTEGER | 平盘家数 |
| industry_close | DECIMAL(12,4) | 行业收盘指数 |
| industry_pct_chg | DECIMAL(10,4) | 行业涨跌幅(聚合) |
| industry_amount | DECIMAL(20,2) | 行业成交额(聚合) |
| industry_turnover | DECIMAL(10,4) | 行业平均换手率 |
| industry_pe_ttm | DECIMAL(12,4) | 行业市盈率（TTM，先过滤<=0，再1%-99% Winsorize，最后取中位数） |
| industry_pb | DECIMAL(12,4) | 行业市净率（先过滤<=0，再1%-99% Winsorize，最后取中位数） |
| limit_up_count | INTEGER | 涨停家数 |
| limit_down_count | INTEGER | 跌停家数 |
| new_100d_high_count | INTEGER | 100日新高数 |
| new_100d_low_count | INTEGER | 100日新低数 |
| top5_codes | JSON | 行业 Top5 股票代码 |
| top5_pct_chg | JSON | 行业 Top5 涨跌幅 |
| top5_limit_up | INTEGER | Top5 中涨停数量 |
| yesterday_limit_up_today_avg_pct | DECIMAL(10,4) | 昨涨停今平均涨幅 |
| data_quality | VARCHAR(20) | 数据质量标记 normal/stale/cold_start |
| stale_days | INTEGER | 距离源数据最近有效交易日的天数 |
| source_trade_date | VARCHAR(8) | 本条快照实际来源交易日 |
| created_at | DATETIME | 创建时间 |

> 兼容字段说明：如历史实现仍存在 `total_stocks`，其语义等同 `stock_count`（后续以 stock_count 为准）。

> 估值聚合口径（IRS 对齐）：先过滤 `pe_ttm <= 0`，再做 1%-99% Winsorize，最后取行业中位数；样本不足 8 只时沿用前值。

> JSON 序列化契约（IndustrySnapshot 对齐）：
> - Python 侧 `top5_codes: list[str]`、`top5_pct_chg: list[float]`
> - 持久化前统一执行 `json.dumps(..., ensure_ascii=False)` 写入 JSON 列
> - 读取后由仓库层反序列化回 Python 列表，不依赖驱动隐式转换

**索引**：
- `PRIMARY KEY (trade_date, industry_code)`

### 3.3 stock_gene_cache 牛股基因缓存

| 字段 | 类型 | 说明 |
|------|------|------|
| stock_code | VARCHAR(20) | 股票代码 (PK) |
| stock_name | VARCHAR(50) | 股票名称 |
| limit_up_count_1y | INTEGER | 近1年涨停次数 |
| limit_up_dates_1y | JSON | 涨停日期列表 |
| max_continuous_board | INTEGER | 最大连板数 |
| continuous_board_2d_count | INTEGER | 2连板次数 |
| continuous_board_3d_plus_count | INTEGER | 3+连板次数 |
| new_high_count_1y | INTEGER | 近1年新高次数 |
| new_high_dates_1y | JSON | 新高日期列表 |
| limit_up_count_120d | INTEGER | 近120日涨停次数（PAS使用） |
| new_high_count_60d | INTEGER | 近60日新高次数（PAS使用） |
| max_pct_chg_history | DECIMAL(10,4) | 历史单日最大涨幅（PAS使用，百分数口径，15 表示 15%） |
| limit_up_success_rate | DECIMAL(8,4) | 涨停成功率 |
| avg_gain_after_limit_up | DECIMAL(10,4) | 涨停后平均涨幅 |
| max_single_day_gain | DECIMAL(10,4) | 单日最大涨幅 |
| avg_volatility | DECIMAL(10,4) | 平均波动率 |
| explosive_score | DECIMAL(8,4) | 爆发力评分 |
| gene_score | DECIMAL(8,4) | 基因综合评分 |
| gene_level | VARCHAR(10) | 基因等级 S/A/B/C/D |
| time_decay_factor | DECIMAL(8,4) | 时间衰减因子 |
| last_update_date | VARCHAR(8) | 最后更新日期 |
| created_at | DATETIME | 创建时间 |

> 窗口滚动策略（PAS 对齐）：
> - `limit_up_count_120d`：每日滚动 120 交易日窗口；
> - `new_high_count_60d`：每日滚动 60 交易日窗口；
> - `max_pct_chg_history`：仅在出现更高历史涨幅时更新。

**索引**：
- `PRIMARY KEY (stock_code)`
- `INDEX idx_gene_score (gene_score DESC)`
- `INDEX idx_gene_level (gene_level)`

---

## 4. L3 运行时表

### 4.1 mss_panorama MSS全景

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键ID |
| trade_date | VARCHAR(8) | 交易日期（业务唯一键） |
| temperature | DECIMAL(8,4) | 市场温度 0-100 |
| cycle | VARCHAR(20) | 周期阶段 |
| trend | VARCHAR(20) | 趋势方向 up/down/sideways |
| position_advice | VARCHAR(20) | 仓位建议 |
| market_coefficient | DECIMAL(8,4) | 大盘系数得分 0-100 |
| profit_effect | DECIMAL(8,4) | 赚钱效应得分 0-100 |
| loss_effect | DECIMAL(8,4) | 亏钱效应得分 0-100 |
| continuity_factor | DECIMAL(8,4) | 连续性因子得分 0-100 |
| extreme_factor | DECIMAL(8,4) | 极端因子得分 0-100 |
| volatility_factor | DECIMAL(8,4) | 波动因子得分 0-100 |
| neutrality | DECIMAL(8,4) | 中性度 0-1（越接近1越中性，越接近0信号越极端） |
| rank | INTEGER | 历史排名 |
| percentile | DECIMAL(8,4) | 百分位排名 0-100 |
| created_at | DATETIME | 创建时间 |

**cycle周期取值**（七阶段，与 MSS 算法对齐）：
- emergence（萌芽期）：<30°C + up
- fermentation（发酵期）：30-45°C + up
- acceleration（加速期）：45-60°C + up
- divergence（分歧期）：60-75°C + up/sideways
- climax（高潮期）：≥75°C
- diffusion（扩散期）：60-75°C + down
- recession（退潮期）：<60°C + down/sideways

**索引**：
- `PRIMARY KEY (id)`
- `UNIQUE KEY uk_trade_date (trade_date)`

### 4.2 irs_industry_daily IRS行业评分

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键ID |
| trade_date | VARCHAR(8) | 交易日期 |
| industry_code | VARCHAR(10) | 行业代码 |
| industry_name | VARCHAR(50) | 行业名称 |
| industry_score | DECIMAL(8,4) | 行业综合评分 0-100 |
| rank | INTEGER | 行业排名 1-31 |
| rotation_status | VARCHAR(20) | 轮动状态 IN/OUT/HOLD |
| rotation_detail | VARCHAR(50) | 轮动详情 |
| allocation_advice | VARCHAR(20) | 配置建议 超配/标配/减配/回避 |
| relative_strength | DECIMAL(8,4) | 相对强度得分 (25%) |
| continuity_factor | DECIMAL(8,4) | 连续性因子得分 (20%) |
| capital_flow | DECIMAL(8,4) | 资金流向得分 (20%) |
| valuation | DECIMAL(8,4) | 估值得分 (15%) |
| leader_score | DECIMAL(8,4) | 龙头因子得分 (12%) |
| gene_score | DECIMAL(8,4) | 行业基因库得分 (8%) |
| quality_flag | VARCHAR(20) | 质量标记 normal/cold_start/stale |
| sample_days | INTEGER | 有效样本天数 |
| neutrality | DECIMAL(8,4) | 中性度 0-1（越接近1越中性，越接近0信号越极端） |
| created_at | DATETIME | 创建时间 |

**索引**：
- `PRIMARY KEY (id)`
- `UNIQUE KEY uk_trade_date_industry (trade_date, industry_code)`
- `INDEX idx_rank (trade_date, rank)`

### 4.3 stock_pas_daily PAS每日评分

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键ID |
| trade_date | VARCHAR(8) | 交易日期 |
| stock_code | VARCHAR(20) | 股票代码 |
| stock_name | VARCHAR(50) | 股票名称 |
| industry_code | VARCHAR(10) | 行业代码 |
| opportunity_score | DECIMAL(8,4) | 机会评分 0-100 |
| opportunity_grade | VARCHAR(10) | 机会等级 S/A/B/C/D |
| direction | VARCHAR(20) | 方向 bullish/bearish/neutral |
| risk_reward_ratio | DECIMAL(8,4) | 风险收益比 |
| bull_gene_score | DECIMAL(8,4) | 牛股基因得分 |
| structure_score | DECIMAL(8,4) | 结构位置得分 |
| behavior_score | DECIMAL(8,4) | 行为确认得分 |
| neutrality | DECIMAL(8,4) | 中性度 0-1（越接近1越中性，越接近0信号越极端） |
| entry | DECIMAL(12,4) | 建议入场价 |
| stop | DECIMAL(12,4) | 建议止损价 |
| target | DECIMAL(12,4) | 建议目标价 |
| created_at | DATETIME | 创建时间 |

**索引**：
- `PRIMARY KEY (id)`
- `UNIQUE KEY uk_trade_date_stock_code (trade_date, stock_code)`
- `INDEX idx_score (trade_date, opportunity_score DESC)`
- `INDEX idx_grade (trade_date, opportunity_grade)`

### 4.4 integrated_recommendation 三三制集成

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键ID |
| trade_date | VARCHAR(8) | 交易日期 |
| stock_code | VARCHAR(20) | 股票代码 |
| stock_name | VARCHAR(50) | 股票名称 |
| industry_code | VARCHAR(10) | 行业代码 |
| industry_name | VARCHAR(50) | 行业名称 |
| mss_score | DECIMAL(8,4) | MSS评分 |
| irs_score | DECIMAL(8,4) | IRS评分 |
| pas_score | DECIMAL(8,4) | PAS评分 |
| final_score | DECIMAL(8,4) | 综合评分 0-100 |
| direction | VARCHAR(20) | 综合方向 |
| consistency | VARCHAR(20) | 方向一致性 consistent/partial/divergent |
| integration_mode | VARCHAR(20) | 集成模式 top_down/bottom_up/dual_verify/complementary |
| weight_plan_id | VARCHAR(40) | 权重方案ID baseline/candidate |
| w_mss | DECIMAL(6,4) | MSS 权重快照 |
| w_irs | DECIMAL(6,4) | IRS 权重快照 |
| w_pas | DECIMAL(6,4) | PAS 权重快照 |
| validation_gate | VARCHAR(10) | 验证门禁 PASS/WARN/FAIL |
| recommendation | VARCHAR(20) | 推荐等级 |
| position_size | DECIMAL(8,4) | 建议仓位 0-1 |
| mss_cycle | VARCHAR(20) | 当日 MSS 周期（追溯 STRONG_BUY 条件） |
| opportunity_grade | VARCHAR(10) | PAS 机会等级快照 S/A/B/C/D |
| neutrality | DECIMAL(8,4) | 中性度 0-1（越接近1越中性，越接近0信号越极端） |
| entry | DECIMAL(12,4) | 入场价 |
| stop | DECIMAL(12,4) | 止损价 |
| target | DECIMAL(12,4) | 目标价 |
| risk_reward_ratio | DECIMAL(8,4) | 风险收益比 |
| created_at | DATETIME | 创建时间 |

**recommendation取值**（大写存储）：
- STRONG_BUY（强烈买入）：≥ 75分 + MSS周期∈{emergence,fermentation}
- BUY（买入）：≥ 70分，且不满足 STRONG_BUY 附加条件
- HOLD（持有）：50-69分
- SELL（卖出）：30-49分
- AVOID（回避）：< 30分

**索引**：
- `PRIMARY KEY (id)`
- `UNIQUE KEY uk_trade_date_stock_code (trade_date, stock_code)`
- `INDEX idx_final_score (trade_date, final_score DESC)`

**逻辑DDL（节选）**：

```sql
CREATE TABLE integrated_recommendation (
    id INTEGER PRIMARY KEY,
    trade_date VARCHAR(8) NOT NULL,
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(50),
    industry_code VARCHAR(10),
    industry_name VARCHAR(50),
    mss_score DECIMAL(8,4),
    irs_score DECIMAL(8,4),
    pas_score DECIMAL(8,4),
    final_score DECIMAL(8,4),
    direction VARCHAR(20),
    consistency VARCHAR(20),
    integration_mode VARCHAR(20),
    weight_plan_id VARCHAR(40),
    w_mss DECIMAL(6,4),
    w_irs DECIMAL(6,4),
    w_pas DECIMAL(6,4),
    validation_gate VARCHAR(10),
    recommendation VARCHAR(20),
    position_size DECIMAL(8,4),
    mss_cycle VARCHAR(20),
    opportunity_grade VARCHAR(10),
    neutrality DECIMAL(8,4),
    entry DECIMAL(12,4),
    stop DECIMAL(12,4),
    target DECIMAL(12,4),
    risk_reward_ratio DECIMAL(8,4),
    created_at DATETIME,
    UNIQUE KEY uk_trade_date_stock_code (trade_date, stock_code)
);
```

---

### 4.5 pas_breadth_daily PAS广度聚合（派生）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键ID |
| trade_date | VARCHAR(8) | 交易日期 |
| scope | VARCHAR(20) | market/industry |
| industry_code | VARCHAR(10) | 行业代码（scope=industry时） |
| industry_name | VARCHAR(50) | 行业名称 |
| pas_sa_count | INTEGER | S/A数量 |
| pas_sa_ratio | DECIMAL(8,4) | S/A占比 |
| pas_grade_distribution | JSON | S/A/B/C/D分布 |
| industry_sa_count | INTEGER | 行业内S/A数量 |
| industry_sa_ratio | DECIMAL(8,4) | 行业内S/A占比 |
| industry_top_k_concentration | DECIMAL(8,4) | TopK行业S/A集中度 |
| created_at | DATETIME | 创建时间 |

> market 级记录可用 `scope=market` 且 `industry_code` 为空或 `ALL` 表示。

**索引**：
- `PRIMARY KEY (trade_date, scope, industry_code)`

### 4.6 validation_* Validation 运行时表

Validation 运行数据纳入 L3 正式数据架构（DuckDB 权威存储），详细字段与 DDL 见  
`docs/design/validation/factor-weight-validation-data-models.md` §3。

| 表名 | 主键/唯一键 | 说明 |
|------|-------------|------|
| validation_factor_report | `id` + `uk_trade_factor_window` | 因子有效性验证结果（IC/RankIC/衰减/覆盖） |
| validation_weight_report | `id` + `uk_trade_candidate_window` | 候选权重 Walk-Forward 评估结果 |
| validation_gate_decision | `id` + `uk_trade_date` | 当日 Gate 决策（PASS/WARN/FAIL） |
| validation_weight_plan | `id` + `uk_trade_plan` | `selected_weight_plan` 到 `WeightPlan` 的数值桥接 |
| validation_run_manifest | `run_id` | Validation 运行轨迹与闭环证据元数据 |

---

## 5. L4 分析层（由 Analysis 模块产出）

L4 为业务分析层，表结构详见 [analysis-data-models.md](../analysis/analysis-data-models.md)。

| 表名 | 说明 |
|------|------|
| daily_report | 日度分析报告 |
| performance_metrics | 绩效指标 |
| signal_attribution | 信号归因 |

---

## 6. 运维/元数据表（非L1-L4）

### 6.1 system_config 系统配置

| 字段 | 类型 | 说明 |
|------|------|------|
| config_key | VARCHAR(100) | 配置键 (PK) |
| config_value | TEXT | 配置值 |
| config_type | VARCHAR(20) | 类型 string/int/float/json |
| description | VARCHAR(255) | 说明 |
| is_encrypted | BOOLEAN | 是否加密 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

推荐配置键（Data Layer 聚合相关）：
- `flat_threshold`（默认 `0.5`，单位 `%`）

### 6.2 data_version_log 数据版本日志

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| data_type | VARCHAR(50) | 数据类型 |
| trade_date | VARCHAR(8) | 交易日期 |
| source_version | VARCHAR(20) | 源版本 |
| local_version | VARCHAR(20) | 本地版本 |
| record_count | INTEGER | 记录数 |
| status | VARCHAR(20) | 状态 SUCCESS/FAILED |
| created_at | DATETIME | 创建时间 |

### 6.3 task_execution_log 任务执行日志

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| task_name | VARCHAR(50) | 任务名称 |
| trade_date | VARCHAR(8) | 交易日期 |
| start_time | DATETIME | 开始时间 |
| end_time | DATETIME | 结束时间 |
| duration_seconds | REAL | 耗时(秒) |
| status | VARCHAR(20) | 状态 |
| error_message | TEXT | 错误信息 |
| created_at | DATETIME | 创建时间 |

### 6.4 data_quality_report 数据质量报告

| 字段 | 类型 | 说明 |
|------|------|------|
| trade_date | VARCHAR(8) | 交易日期 |
| check_item | VARCHAR(50) | 检查项 |
| expected_value | TEXT | 期望值 |
| actual_value | TEXT | 实际值 |
| deviation | DECIMAL(10,4) | 偏差 |
| status | VARCHAR(20) | 状态 PASS/WARN/FAIL |
| created_at | DATETIME | 创建时间 |

---

## 7. 业务数据表

### 7.1 trade_records 交易记录

| 字段 | 类型 | 说明 |
|------|------|------|
| trade_id | VARCHAR(50) | 成交ID (PK) |
| trade_date | VARCHAR(8) | 交易日期 |
| stock_code | VARCHAR(20) | 股票代码 |
| stock_name | VARCHAR(50) | 股票名称 |
| industry_code | VARCHAR(10) | 行业代码 |
| direction | VARCHAR(10) | 方向 buy/sell |
| order_type | VARCHAR(20) | 订单类型 auction/market/limit/stop |
| price | DECIMAL(12,4) | 成交价格 |
| shares | INTEGER | 成交数量 |
| amount | DECIMAL(16,2) | 成交金额 |
| commission | DECIMAL(12,2) | 佣金 |
| stamp_tax | DECIMAL(12,2) | 印花税 |
| transfer_fee | DECIMAL(12,4) | 过户费 |
| slippage | DECIMAL(12,4) | 滑点 |
| total_fee | DECIMAL(16,2) | 总费用 |
| status | VARCHAR(20) | 状态 filled/partially_filled/rejected |
| signal_id | VARCHAR(50) | 触发信号ID |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 7.2 positions 持仓记录

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| stock_code | VARCHAR(20) | 股票代码 (UNIQUE) |
| stock_name | VARCHAR(50) | 股票名称 |
| industry_code | VARCHAR(10) | 行业代码 |
| direction | VARCHAR(10) | 方向 long |
| shares | INTEGER | 持仓数量 |
| cost_price | DECIMAL(12,4) | 成本价 |
| cost_amount | DECIMAL(16,2) | 成本金额 |
| market_price | DECIMAL(12,4) | 市价 |
| market_value | DECIMAL(16,2) | 市值 |
| unrealized_pnl | DECIMAL(16,2) | 未实现盈亏 |
| unrealized_pnl_pct | DECIMAL(8,4) | 未实现盈亏比例 |
| buy_date | VARCHAR(8) | 买入日期 |
| can_sell_date | VARCHAR(8) | 可卖日期(T+1) |
| is_frozen | BOOLEAN | 是否冻结 |
| signal_id | VARCHAR(50) | 触发信号ID |
| stop_price | DECIMAL(12,4) | 止损价 |
| target_price | DECIMAL(12,4) | 目标价 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 7.3 t1_frozen T+1冻结记录

| 字段 | 类型 | 说明 |
|------|------|------|
| stock_code | VARCHAR(20) | 股票代码 |
| buy_date | VARCHAR(8) | 买入日期 |
| frozen_shares | INTEGER | 冻结股数 |
| PRIMARY KEY | | (stock_code, buy_date) |

### 7.4 backtest_trade_records 回测交易记录

| 字段 | 类型 | 说明 |
|------|------|------|
| trade_id | VARCHAR(50) | 交易ID (PK) |
| signal_date | VARCHAR(8) | 信号日期 |
| execute_date | VARCHAR(8) | 成交日期 |
| stock_code | VARCHAR(20) | 股票代码 |
| stock_name | VARCHAR(50) | 股票名称 |
| direction | VARCHAR(10) | buy/sell |
| order_type | VARCHAR(20) | auction/limit |
| signal_price | DECIMAL(12,4) | 信号价格 |
| filled_price | DECIMAL(12,4) | 成交价格 |
| shares | INTEGER | 股数 |
| amount | DECIMAL(16,2) | 成交金额 |
| commission | DECIMAL(12,2) | 佣金 |
| stamp_tax | DECIMAL(12,2) | 印花税 |
| transfer_fee | DECIMAL(12,4) | 过户费 |
| slippage | DECIMAL(12,4) | 滑点 |
| total_fee | DECIMAL(16,2) | 总费用 |
| status | VARCHAR(20) | 状态 |
| filled_time | VARCHAR(20) | 成交时间 |
| filled_reason | VARCHAR(50) | 成交原因 |
| pnl | DECIMAL(16,2) | 盈亏 |
| pnl_pct | DECIMAL(8,4) | 盈亏比例 |
| hold_days | INTEGER | 持仓天数 |
| signal_score | DECIMAL(8,4) | 信号评分 |
| signal_source | VARCHAR(20) | 信号来源 |
| integration_mode | VARCHAR(20) | 集成模式 top_down/bottom_up/dual_verify/complementary |
| recommendation | VARCHAR(20) | 推荐等级 STRONG_BUY/BUY/HOLD/SELL/AVOID |
| signal_id | VARCHAR(50) | 信号ID |
| created_at | DATETIME | 创建时间 |

### 7.5 backtest_results 回测结果

表结构详见 [backtest-data-models.md](../backtest/backtest-data-models.md)。

---

## 8. 字段规范

### 8.1 编码规范

**重要约定**：
- **内部使用 `stock_code`**：系统内部统一使用 `stock_code` 作为股票代码字段名
- **对接 TuShare 保留 `ts_code`**：L1 原始数据层保留 TuShare 的 `ts_code` 格式
- **转换时机**：L1→L2 时将 `ts_code` 转换为 `stock_code`

| 字段 | 格式 | 示例 | 说明 |
|------|------|------|------|
| ts_code | {code}.{exchange} | 000001.SZ | TuShare原始代码（仅L1层） |
| stock_code | {code} | 000001 | 内部统一代码（6位，L2+使用） |
| trade_date | YYYYMMDD | 20260131 | 交易日期 |
| industry_code | {code} | 801780 | 申万行业代码 |

### 8.2 评分规范

| 字段类型 | 范围 | 说明 |
|----------|------|------|
| temperature | 0-100 | 越高越热 |
| score | 0-100 | 越高越强 |
| neutrality | 0-1 | 中性度（越接近1越中性，越接近0信号越极端） |
| position_size | 0-1 | 仓位比例 |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.2.5 | 2026-02-09 | 修复 R30：§1.1 L3 总览图补充 `validation_*` 行，与 §4.6 Validation 表清单保持一致 |
| v3.2.4 | 2026-02-09 | 修复 R29：L3 表清单补充 Validation 持久化表（`validation_factor_report/validation_weight_report/validation_gate_decision/validation_weight_plan/validation_run_manifest`），明确 Validation 运行数据纳入正式数据架构 |
| v3.2.3 | 2026-02-09 | 修复 R28：`integrated_recommendation` 补齐 `consistency/w_mss/w_irs/w_pas/mss_cycle/opportunity_grade`；`irs_industry_daily` 补齐 `quality_flag/sample_days`；L3 主键策略统一为 `id` 主键 + 业务唯一键；`direction` 宽度统一为 `VARCHAR(20)` |
| v3.2.2 | 2026-02-09 | 修复 R26：`market_snapshot/industry_snapshot` 增加 `data_quality/stale_days/source_trade_date` 质量追溯字段；`stock_gene_cache` 补充 120/60 日窗口滚动策略说明 |
| v3.2.1 | 2026-02-09 | 修复 R23：`industry_snapshot` 估值口径改为“过滤+Winsorize+中位数”显式描述；`flat_count` 注释补单位与默认值；补充 `integrated_recommendation` 逻辑DDL（含 `id` 主键） |
| v3.2.0 | 2026-02-08 | 修复 R15：`trade_records` 增加 `industry_code`；`backtest_trade_records` 增加 `integration_mode/recommendation`，与 Trading/Backtest 对齐 |
| v3.1.9 | 2026-02-08 | 修复 R14：`flat_count` 阈值改为配置参数 `flat_threshold` 并补充 system_config 推荐键；`trade_records.order_type` 枚举统一为 `auction/market/limit/stop` |
| v3.1.8 | 2026-02-07 | 修复 R8 P2：`stock_gene_cache.max_pct_chg_history` 明确为百分数口径（15 表示 15%） |
| v3.1.7 | 2026-02-07 | 修复 R5：补充 IndustrySnapshot `top5_codes/top5_pct_chg` 的 JSON 序列化契约（json.dumps/json.loads） |
| v3.1.6 | 2026-02-07 | 同步 Integration v3.4.x：`integrated_recommendation` 增加 `weight_plan_id`/`validation_gate`；补充 market_snapshot 计数交叉语义说明 |
| v3.1.5 | 2026-02-07 | 同步 MSS 周期边界：recession 条件更新为 <60°C + down/sideways |
| v3.1.4 | 2026-02-07 | 同步 Integration/命名规范：STRONG_BUY 阈值调整为 75 分 |
| v3.1.3 | 2026-02-06 | 增加 t1_frozen 业务表；对齐 trade_records/positions 字段口径 |
| v3.1.2 | 2026-02-05 | PAS相关字段命名与核心算法/路线图对齐（count/history命名） |
| v3.1.1 | 2026-02-05 | 回测交易记录字段补充 signal_date/execute_date |
| v3.1.0 | 2026-02-04 | 对齐 MSS/IRS/PAS/Integration：更新行业快照字段、IRS 连续性因子、集成模式、PAS 广度派生表 |
| v3.0.1 | 2026-02-04 | 补齐 market_snapshot 字段以支持 MSS v3.1.0（strong_up/down、连续新高、极端行为、pct_chg_std、amount_volatility 等） |
| v3.0.0 | 2026-01-31 | 重构版：统一字段命名、分层清晰 |

---

**关联文档**：
- 数据管线设计：[data-layer-algorithm.md](./data-layer-algorithm.md)
- API接口：[data-layer-api.md](./data-layer-api.md)
- 信息流：[data-layer-information-flow.md](./data-layer-information-flow.md)

