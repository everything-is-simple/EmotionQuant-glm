# ROADMAP Capability Pack CP-09｜Analysis（分析报告）

**兼容文件名**: `ROADMAP-PHASE-09-analysis.md`  
**版本**: v6.0.0  
**最后更新**: 2026-02-07

---

## 1. 定位

输出可追溯绩效指标与信号归因报告，为治理和复盘提供证据。

---

## 2. 稳定契约

### 2.1 输入

| 输入 | 来源 | 就绪条件 | 失败处理 |
|---|---|---|---|
| `backtest_results` / `backtest_trade_records` / `trade_records` | CP-06/07 | 可读 | P1 降级 |
| `mss/irs/pas/integrated` | CP-02/03/04/05 | 可读 | P1 部分缺失 |
| `factor_validation_report` / `weight_validation_report` | CP-10 | 可读 | P1 标记缺失 |

### 2.2 输出

| 输出 | 消费方 | 验收 |
|---|---|---|
| `performance_metrics` | 治理/研究 | 指标完整 |
| `signal_attribution` | 治理/研究 | 归因可解释 |
| `daily_report` | CP-08/用户 | 可生成与归档 |

---

## 3. Slice 库（按需抽取）

| Slice ID | 推荐 Spiral | 说明 | 最小闭环证据 |
|---|---|---|---|
| CP09-S1 | S3 | 最小绩效摘要 | 指标文件 |
| CP09-S2 | S5 | 自动日报 | 日报文件 |
| CP09-S3 | S6 | 归因与漂移报告 | 归因报告 |

---

## 4. Entry / Exit Gate

### 4.1 Entry

- CP-06 或 CP-07 至少一路可用
- CP-05 信号输出可追溯
- CP-10 验证报告可读取（缺失可降级并标记）

### 4.2 Exit

- 报告可自动生成
- 指标来源可追溯
- 与回测/交易口径一致

---

## 5. 风险与回退

| 场景 | 级别 | 策略 |
|---|---|---|
| 回测结果缺失 | P1 | 降级为信号摘要版 |
| 归因计算失败 | P1 | 标记缺失并继续生成主报告 |

---

## 6. 何时更新本文件

1. 报告输入源变化
2. 指标或归因模型变化
3. 输出格式变化
4. 降级策略变化
