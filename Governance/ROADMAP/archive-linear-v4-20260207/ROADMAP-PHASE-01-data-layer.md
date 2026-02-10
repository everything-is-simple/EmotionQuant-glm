# ROADMAP Phase 01｜数据层（Data Layer）

**版本**: v4.0.2（量化版）
**创建日期**: 2026-01-31
**最后更新**: 2026-02-06
**时间范围**: Phase 01
**核心交付**: L1-L4数据架构、Repository模式、数据质量监控
**预估工期**: 4周
**前置依赖**: 无
**实现状态**: 未实现（截至 2026-02-06：`src/` 仅有 Skeleton/占位与少量基础骨架，详见 `Governance/ROADMAP/ROADMAP-OVERVIEW.md`）

---
## 文档对齐声明

> **权威设计文档**: `docs/design/data-layer/`
> - 算法：`data-layer-algorithm.md`
> - 数据模型：`data-layer-data-models.md`
> - API：`data-layer-api.md`
> - 信息流：`data-layer-information-flow.md`

---

## 1. Phase 目标

> **一句话**: 建立稳定、高效、可扩展的数据基础设施

### 1.1 量化验收目标

| 目标项 | 量化指标 | 验收标准 | 验证方法 |
||--------|----------|----------|----------|
|| L1数据接入 | 8类TuShare数据完整采集 | 完整率≥99% | `COUNT(*) vs 市场标的总数` |
|| TuShare 调用合规性 | API 日调用量/积分配额 | 日调用量≤配额80%，无429/限流错误 | `API调用计数 + 错误码统计` |
|| L2快照生成 | 市场快照+31行业快照 | 生成成功率≥95% | `成功天数/交易日数` |
|| 数据延迟 | 采集到入库时间 | ≤30分钟 | `入库时间-收盘时间` |
|| 数据质量 | 字段空值率 | ≤1% | `NULL比例检查` |
|| Repository可用 | API接口实现 | 100%覆盖 | `单元测试通过` |
|| 处理性能 | 日度ETL总时间 | ≤30分钟 | `时间戳统计` |

---

## 2. 输入输出规范

### 2.0 本地路径约束（零容忍）
- 数据根目录通过环境变量 `DATA_PATH` 提供（由部署环境配置，不写死默认路径）
- 代码实现必须通过 `Config.from_env()` 读取路径，禁止硬编码磁盘路径

### 2.1 输入规范

| 输入源 | 数据类型 | 频率 | 记录数/次 | 关键字段 |
|--------|----------|------|-----------|----------|
| TuShare daily | 个股日线 | 日度 | ~5000 | ts_code, trade_date, open, high, low, close, vol, amount |
| TuShare daily_basic | 日线指标 | 日度 | ~5000 | turnover_rate, pe, pb, total_mv, circ_mv |
| TuShare limit_list_d | 涨跌停列表 | 日度 | ~50-300 | limit (U/D/Z), fc_ratio, first_time |
| TuShare index_daily | 指数日线 | 日度 | ~100 | ts_code, close, pct_chg |
| TuShare index_member | 行业成分 | 月度 | ~5000 | index_code, con_code |
| TuShare index_classify | 行业分类 | 半年/年度（低频） | 31 | index_code, index_name |
| TuShare stock_basic | 股票基本信息 | 月度 | ~5000 | ts_code, name, list_date |
| TuShare trade_cal | 交易日历 | 年度 | ~250 | cal_date, is_open |

### 2.2 输出规范

| 输出表 | 层级 | 频率 | 记录数/日 | 关键字段 | 输出校验 |
|--------|------|------|-----------|----------|----------|
| raw_daily | L1 | 日度 | ~5000 | ts_code, OHLCV | 记录数≥95%市场标的 |
| raw_daily_basic | L1 | 日度 | ~5000 | turnover_rate, pe | 记录数与raw_daily一致 |
| raw_limit_list | L1 | 日度 | ~50-300 | limit(U/D/Z) | limit字段非空 |
| raw_index_daily | L1 | 日度 | ~100 | close, pct_chg | 基准指数必存在 |
| raw_index_member | L1 | 月度 | ~5000 | index_code, con_code | 与 index_classify 匹配 |
| raw_index_classify | L1 | 半年/年度 | 31 | index_code, index_name, level | 31行业全覆盖 |
| raw_stock_basic | L1 | 月度 | ~5000 | ts_code, name, list_date | 记录数与市场一致 |
| raw_trade_cal | L1 | 年度 | ~250 | cal_date, is_open | 覆盖最近交易日 |
| market_snapshot | L2 | 日度 | 1 | 见下表 | 关键字段非空 |
| industry_snapshot | L2 | 日度 | 31 | 见下表 | 31行业全覆盖 |
| stock_gene_cache | L2 | 日度 | ~5000 | limit_up_count_120d, new_high_count_60d, max_pct_chg_history | PAS依赖字段非空 |

### 2.3 market_snapshot 输出字段明细

| 字段 | 类型 | 范围 | 计算逻辑 | 非空 |
|------|------|------|----------|------|
| trade_date | VARCHAR(8) | YYYYMMDD | PK | ✅ |
| total_stocks | INT | 3000-6000 | COUNT(daily) | ✅ |
| rise_count | INT | 0-total | pct_chg > 0 | ✅ |
| fall_count | INT | 0-total | pct_chg < 0 | ✅ |
| flat_count | INT | 0-total | abs(pct_chg) <= 0.5% | ✅ |
| strong_up_count | INT | 0-total | pct_chg > 5% | ✅ |
| strong_down_count | INT | 0-total | pct_chg < -5% | ✅ |
| limit_up_count | INT | 0-300 | limit='U' | ✅ |
| limit_down_count | INT | 0-300 | limit='D' | ✅ |
| touched_limit_up | INT | 0-500 | limit∈{'U','Z'} | ✅ |
| new_100d_high_count | INT | 0-total | close>max(close,100d) | ✅ |
| new_100d_low_count | INT | 0-total | close<min(close,100d) | ✅ |
| continuous_limit_up_2d | INT | 0-100 | 派生计算 | ✅ |
| continuous_limit_up_3d_plus | INT | 0-50 | 派生计算 | ✅ |
| continuous_new_high_2d_plus | INT | 0-100 | 派生计算 | ✅ |
| high_open_low_close_count | INT | 0-total | open>pre_close*1.02 且 close<open*0.94 | ✅ |
| low_open_high_close_count | INT | 0-total | open<pre_close*0.98 且 close>open*1.06 | ✅ |
| pct_chg_std | DECIMAL | >=0 | std(pct_chg) | ✅ |
| amount_volatility | DECIMAL | - | 成交额相对20日均值波动率 | ✅ |
| yesterday_limit_up_today_avg_pct | DECIMAL | -10~10 | 聚合计算 | ✅ |
| created_at | DATETIME | - | 自动 | ✅ |

> 兼容说明：历史口径中的 `big_drop_count` 统一为 `strong_down_count`。

### 2.4 industry_snapshot 输出字段明细

> 完整字段与口径详见 `docs/design/data-layer/data-layer-data-models.md` §3.2。

| 字段 | 类型 | 说明 |
|------|------|------|
| trade_date | VARCHAR(8) | 交易日期（PK） |
| industry_code | VARCHAR(10) | 申万一级行业代码（PK） |
| industry_name | VARCHAR(50) | 行业名称 |
| industry_pct_chg | DECIMAL | 行业当日涨跌幅 |
| stock_count | INT | 行业内股票数 |
| rise_count | INT | 上涨家数 |
| fall_count | INT | 下跌家数 |
| flat_count | INT | 平盘家数（abs(pct_chg) <= 0.5%） |
| limit_up_count | INT | 涨停家数 |
| limit_down_count | INT | 跌停家数 |
| new_100d_high_count | INT | 100日新高家数 |
| new_100d_low_count | INT | 100日新低家数 |
| industry_amount | DECIMAL | 行业成交额（聚合） |
| industry_turnover | DECIMAL | 行业平均换手率 |
| industry_pe_ttm | DECIMAL | 行业市盈率（TTM） |
| industry_pb | DECIMAL | 行业市净率 |
| top5_codes | JSON | 行业 Top5 股票代码 |
| top5_pct_chg | JSON | Top5 涨跌幅 |
| top5_limit_up | INT | Top5 中涨停数量 |

### 2.5 stock_gene_cache 输出字段明细（PAS依赖）

> 完整字段与口径详见 `docs/design/data-layer/data-layer-data-models.md` §3.3。

| 字段 | 类型 | 说明 |
|------|------|------|
| stock_code | VARCHAR(20) | 股票代码（PK） |
| limit_up_count_120d | INT | 近120日涨停次数 |
| new_high_count_60d | INT | 近60日新高次数 |
| max_pct_chg_history | DECIMAL | 历史单日最大涨幅 |

---

## 3. 四层架构详细设计

### 3.1 架构总览

```
┌─────────────────────────────────────────────────────────┐
│  TuShare API (5000积分)                                      │
└───────────────────────────┴─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  L1: 原始数据层 (Parquet)                                    │
│  raw_daily | raw_daily_basic | raw_limit_list | ...         │
└───────────────────────────┴─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  L2: 特征层 (DuckDB 按年分库)                                  │
│  market_snapshot | industry_snapshot | stock_gene_cache     │
└───────────────────────────┴─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  L3: 算法输出层 (DuckDB 按年分库) - Phase 02-05 写入           │
│  mss_panorama | irs_industry_daily | stock_pas_daily | ...   │
└───────────────────────────┴─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  L4: 分析层 (DuckDB 按年分库 + MD) - Phase 09 写入             │
│  daily_report | performance_metrics | signal_attribution      │
└───────────────────────────┴─────────────────────────────┘
```

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v4.0.2 | 2026-02-05 | 补齐 market_snapshot 字段口径，与 data-layer-data-models 对齐 |
| v4.0.1 | 2026-02-04 | 统一存储口径为 DuckDB 按年分库，移除硬编码路径表述 |
| v4.0.0 | 2026-02-02 | 量化版：添加输入输出规范、错误处理、验收检查清单 |
| v3.0.0 | 2026-01-31 | 重构版：与 docs/design 对齐 |

---

**关联文档**：
- 设计文档：`docs/design/data-layer/`
- 下游Phase：Phase 02 (MSS), Phase 03 (IRS), Phase 04 (PAS)


