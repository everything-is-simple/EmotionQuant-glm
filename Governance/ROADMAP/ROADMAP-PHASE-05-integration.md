# ROADMAP Capability Pack CP-05｜Integration（三系统集成）

**兼容文件名**: `ROADMAP-PHASE-05-integration.md`  
**版本**: v6.0.0  
**最后更新**: 2026-02-07

---

## 1. 定位

合成统一推荐信号，作为 CP-06/07/08/09 的唯一上游输出。

---

## 2. 稳定契约

### 2.1 输入

| 输入 | 来源 | 就绪条件 | 失败处理 |
|---|---|---|---|
| `mss_panorama` | CP-02 | 当日数据存在 | P0 |
| `irs_industry_daily` | CP-03 | 当日数据存在 | P0 |
| `stock_pas_daily` | CP-04 | 当日数据存在 | P0 |
| `validation_gate_decision` | CP-10 | Gate 非 FAIL | FAIL 阻断 |

### 2.2 输出

| 输出 | 消费方 | 验收 |
|---|---|---|
| `integrated_recommendation` | CP-06/07/08/09 | 字段完整且可追溯 |

---

## 3. Slice 库（按需抽取）

| Slice ID | 推荐 Spiral | 说明 | 最小闭环证据 |
|---|---|---|---|
| CP05-S1 | S2 | baseline 集成输出 | 集成表 + 测试 |
| CP05-S2 | S3 | 风险约束接入 | 约束测试 |
| CP05-S3 | S4 | 阈值校准 | 校准报告 |

---

## 4. Entry / Exit Gate

### 4.1 Entry

- CP-02/03/04 输出就绪
- 验证 Gate 非 FAIL

### 4.2 Exit

- baseline 与候选权重对比证据齐全
- 输出可被 CP-06/07 直接消费
- 至少 1 条集成自动化测试通过

---

## 5. 风险与回退

| 场景 | 级别 | 策略 |
|---|---|---|
| 任一核心输入缺失 | P0 | 阻断 |
| 权重候选验证失败 | P1 | 回退 baseline |

---

## 6. 何时更新本文件

1. 集成输入/输出字段变化
2. 权重策略变化
3. Gate 规则变化
4. 回退策略变化
