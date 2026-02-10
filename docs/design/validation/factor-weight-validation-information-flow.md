# 因子与权重验证信息流

**版本**: v2.1.1
**最后更新**: 2026-02-09

---

## 1. 总流程（含闭环）

```text
L2/L3 输入数据
   -> 因子验证（IC/RankIC/稳定性/衰减）
   -> 权重候选评估（baseline vs candidate）
   -> Gate 决策（PASS/WARN/FAIL）
   -> 输出验证报告
   -> PASS/WARN: 进入 Integration -> Backtest/Trading
   -> FAIL: 阻断 Integration，回退 baseline/上一有效方案
```

---

## 2. 日级时序（交易日）

```text
T=15:30  MSS/IRS/PAS 完成
T+0.2m   Validation.run_daily_gate(trade_date=T)
T+0.6m   生成 validation_gate_decision + validation_weight_plan
T+0.7m   CP-05 从 DuckDB 读取 gate + weight_plan（非 parquet）
T+1.0m   Integration 生成 integrated_recommendation
T+2.0m   CP-06/07 使用 CP-05 输出执行后续流程
```

---

## 3. 圈级时序（Spiral 收口）

```text
Scope: 定义验证窗口与候选权重
Build: 执行 full validation（WFA）
Verify: run/test/artifact 三证据
Sync: 更新 final.md + records + 相关 CP 契约
```

---

## 4. 输入边界

| 输入 | 来源 | 必要性 | 说明 |
|---|---|---|---|
| factor_series | Data Layer L2（`market_snapshot` / `industry_snapshot` / `stock_gene_cache`） | 必需 | 原始因子序列（计数/比率/聚合），非评分结果 |
| future_returns | Data Layer L1（`raw_daily`） | 必需 | 未来 H 日收益率（用于 IC 计算） |
| signals | Integration 输出（`integrated_recommendation`，历史窗口） | 必需 | 权重候选回测输入（非当日实时） |
| prices | Data Layer L1（`raw_daily`） | 必需 | OHLC 价格序列 |
| trade_calendar | Data Layer L1（`raw_trade_cal`） | 必需 | 交易日历与窗口对齐 |

### 4.1 因子名 -> 数据源映射（消除 L2/L3 语义歧义）

| factor_name（ValidatedFactor） | 来源层 | 表 | 字段 |
|---|---|---|---|
| `mss_market_coefficient` | L2 | `market_snapshot` | `yesterday_limit_up_today_avg_pct` 等派生字段 |
| `mss_profit_effect` | L2 | `market_snapshot` | `rise_count/limit_up_count` 相关派生 |
| `mss_loss_effect` | L2 | `market_snapshot` | `fall_count/limit_down_count` 相关派生 |
| `mss_continuity_factor` | L2 | `market_snapshot` | `continuous_limit_up_count` 等连板连续性派生 |
| `mss_extreme_factor` | L2 | `market_snapshot` | `high_open_low_close_count` 等极端分歧派生 |
| `mss_volatility_factor` | L2 | `market_snapshot` | `pct_chg_std/amount_volatility` 等波动派生 |
| `irs_relative_strength` | L2 | `industry_snapshot` | `industry_pct_chg`（相对基准） |
| `irs_continuity_factor` | L2 | `industry_snapshot` | `rise_count/fall_count/new_100d_high_count` 连续性派生 |
| `irs_capital_flow` | L2 | `industry_snapshot` | `industry_amount`（含历史窗口） |
| `irs_valuation` | L2 | `industry_snapshot` | `industry_pe_ttm/industry_pb` |
| `irs_leader_score` | L2 | `industry_snapshot` | `top5_pct_chg/top5_limit_up` 龙头强度派生 |
| `irs_gene_score` | L2 | `stock_gene_cache` + `industry_snapshot` | 牛股基因聚合到行业层后的行业基因分 |
| `pas_bull_gene_score` | L2 | `stock_gene_cache` | `limit_up_count_120d/new_high_count_60d` |
| `pas_structure_score` | L1+L2 | `raw_daily` + `stock_gene_cache` | 价格位置相关字段 |
| `pas_behavior_score` | L1 | `raw_daily` | 连续涨跌/量价行为字段 |

说明：`factor_series` 在 Validation 中表示“可验证因子序列”，允许来自 L2 原始聚合字段，或由 L1+L2 规则计算后的因子序列；不直接消费 Integration 的最终评分作为因子输入。

---

## 5. 输出边界

| 输出 | 消费方 | 用途 |
|---|---|---|
| factor_validation_report | CP-05/治理 | 因子有效性审计 |
| weight_validation_report | CP-05/治理 | 权重替换依据 |
| validation_gate_decision | CP-05/06/07 | 门禁与回退 |
| validation_weight_plan | CP-05/06/07 | `selected_weight_plan` 到 `WeightPlan` 的数值桥接 |
| validation_run_manifest | 治理/审计 | run/test/artifact 运行轨迹 |

---

## 6. 错误处理

| 场景 | 级别 | 处理 |
|---|---|---|
| 缺失 future return | P0 | 阻断 |
| 因子样本不足 | P1 | 标记 WARN 并剔除该因子 |
| 候选不优于 baseline | P1 | 回退 baseline |
| 验证任务超时 | P2 | 使用最近有效结果并标记 stale |
| 验证数据过期（`stale_days > config.stale_days_threshold`） | P1 | 使用最近有效结果并标记 stale，触发告警并要求人工介入 |

---

## 7. 产物目录建议（报告与运行数据分离）

```text
.reports/validation/
  └─ {trade_date}/
      └─ summary_{YYYYMMDD_HHMMSS}.md
```

运行时操作数据统一写入 DuckDB（`validation_*` 表），不以 `.reports/*.parquet` 作为下游读取契约。

---

## 8. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v2.1.1 | 2026-02-09 | 修复 R30：§4.1 因子映射表补齐 15/15（新增 MSS 3 因子 + IRS 3 因子） |
| v2.1.0 | 2026-02-09 | 修复 R29：增加 Validation->Integration 桥接输出（`validation_weight_plan`）；明确 DuckDB `validation_*` 为运行时契约、`.reports` 仅可读摘要 |
