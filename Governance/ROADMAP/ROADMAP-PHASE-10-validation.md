# ROADMAP Capability Pack CP-10｜Validation（因子与权重验证）

**兼容文件名**: `ROADMAP-PHASE-10-validation.md`  
**版本**: v1.0.0  
**最后更新**: 2026-02-07

---

## 1. 定位

为 MSS/IRS/PAS 因子与 Integration 权重提供统一门禁证据，输出可执行 Gate，阻断无证据参数漂移。

---

## 2. 稳定契约

### 2.1 输入

| 输入 | 来源 | 就绪条件 | 失败处理 |
|---|---|---|---|
| `factor_series` | CP-02/03/04 | 因子序列可读取 | P0 |
| `future_returns` | CP-01 | 前瞻收益可计算 | P0 |
| `signal_candidates` | CP-05 输入侧 | baseline/候选集合齐全 | P1 降级 baseline |
| `prices` / `trade_calendar` | CP-01 | 数据窗口完整 | P0 |

### 2.2 输出

| 输出 | 消费方 | 验收 |
|---|---|---|
| `factor_validation_report` | CP-05/治理 | 指标与窗口完整 |
| `weight_validation_report` | CP-05/治理 | baseline 对照完整 |
| `validation_gate_decision` | CP-05/06/07 | `PASS/WARN/FAIL` + reason 可追溯 |

---

## 3. Slice 库（按需抽取）

| Slice ID | 推荐 Spiral | 说明 | 最小闭环证据 |
|---|---|---|---|
| CP10-S1 | S2 | 因子最小门禁（IC/RankIC/ICIR） | 因子报告 + 测试 |
| CP10-S2 | S2/S3 | 权重 baseline vs candidate 对照 | 权重报告 + 测试 |
| CP10-S3 | S3/S6 | 滚动窗口/WFA 与漂移监控 | 漂移报告 |

---

## 4. Entry / Exit Gate

### 4.1 Entry

- CP-01 数据窗口就绪（交易日历 + 行情）
- CP-02/03/04 输出可读
- baseline 与候选权重方案已声明

### 4.2 Exit

- 当日 `validation_gate_decision` 已生成
- `PASS/WARN/FAIL` 判定规则可审计
- FAIL 时已触发回退 baseline

---

## 5. 风险与回退

| 场景 | 级别 | 策略 |
|---|---|---|
| 前瞻收益缺失/错位 | P0 | 阻断 |
| 单因子样本不足 | P1 | 标记 WARN，剔除该因子 |
| 候选权重不优于 baseline | P1 | 回退 baseline |
| 验证任务执行超时 | P2 | 使用最近一次有效结果并标记 stale |

---

## 6. 何时更新本文件

1. 验证输入/输出字段变化
2. Gate 规则变化
3. baseline 或候选权重策略变化
4. 验证窗口/频率变化
5. 回退策略变化

