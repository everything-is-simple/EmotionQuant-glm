# 因子与权重验证算法设计

**版本**: v2.1.0
**最后更新**: 2026-02-09
**状态**: Spiral 闭环执行基线

---

## 1. 模块目标

Validation 层负责两件事：

1. 验证因子是否仍有预测力（避免失效因子继续入模）。
2. 验证候选权重是否优于 baseline（避免拍脑袋改权重）。

输出统一 `validation_gate_decision` + `validation_weight_plan`（桥接），供 CP-05/06/07 使用。

---

## 2. 触发时点（闭环）

### 2.1 日级 Gate（交易日）

- 时点：`T 日收盘后`，`Integration` 前。
- 目标：快速判定当日是否允许进入集成与回测。
- 产物：`validation_gate_decision`、`validation_weight_plan`、当日简版报告。

### 2.2 圈级验证（每个 Spiral 收口前）

- 时点：`review/final` 前。
- 目标：完成 baseline vs candidate 的 OOS 对照，决定下圈权重计划。
- 产物：完整因子报告 + 权重对照报告 + 回退记录。

### 2.3 月级深度复核（每月）

- 目标：检查因子衰减与参数漂移。
- 产物：漂移报告（是否保留/降权/剔除因子）。

### 2.4 配置注入（禁止阈值散落硬编码）

- 所有阈值与窗口参数统一来自 `ValidationConfig`（见 `factor-weight-validation-data-models.md`）。
- 推荐由 `system_config` 或环境变量注入，未配置时使用 `ValidationConfig` 默认值。

---

## 3. 因子验证（Factor Validation）

### 3.1 输入要求

- `factor_series` 与 `future_returns` 必须按 `trade_date, stock_code` 对齐。
- 禁止未来函数：只允许用 `T` 及之前因子预测 `T+H` 收益。
- 最小样本：每个因子在验证窗口内样本数必须大于阈值（`config.min_sample_count`，默认 5000）。

### 3.2 必算指标

| 字段名 | 中文说明 | 计算口径 |
|---|---|---|
| `mean_ic` | 平均 IC | Pearson 相关系数均值 |
| `mean_rank_ic` | 平均 RankIC | Spearman 秩相关均值 |
| `icir` | ICIR | `mean_ic / std(ic)` |
| `positive_ic_ratio` | 正 IC 比例 | `IC > 0` 的样本比例 |
| `decay_1d / decay_3d / decay_5d / decay_10d` | 衰减系数 | 因子在不同持有期的预测力衰减 |
| `coverage_ratio` | 样本覆盖率 | 有效样本 / 全市场样本 |

### 3.3 门禁阈值（由 `ValidationConfig` 提供默认值）

| 指标 | PASS | WARN | FAIL |
|---|---|---|---|
| `mean_ic` | `> config.ic_pass` | `(config.ic_warn, config.ic_pass]` | `<= config.ic_warn` |
| `icir` | `>= config.icir_pass` | `[config.icir_warn, config.icir_pass)` | `< config.icir_warn` |
| `positive_ic_ratio` | `>= config.positive_ic_ratio_pass` | `[config.positive_ic_ratio_warn, config.positive_ic_ratio_pass)` | `< config.positive_ic_ratio_warn` |
| `coverage_ratio` | `>= config.coverage_pass` | `[config.coverage_warn, config.coverage_pass)` | `< config.coverage_warn` |

---

## 4. 权重验证（Weight Validation）

### 4.1 候选权重约束

- baseline 默认：`[1/3, 1/3, 1/3]`
- candidate 约束：
  - 非负：`w_i >= 0`
  - 归一：`sum(w_i) = 1`
  - 上限：`max(w_i) <= config.max_weight_per_module`（默认 0.60）

### 4.2 评估协议（Walk-Forward）

- 窗口设计：
  - `train=config.wfa_train_days`（默认 252，约 1 年），用于权重训练。
  - `validate=config.wfa_validate_days`（默认 63，约 3 个月），用于候选初筛。
  - `oos=config.wfa_oos_days`（默认 63，约 3 个月），用于样本外评估。
- 设计依据：在样本量与市场状态变化之间做平衡，252 日可覆盖一个年度交易周期。
- 每个窗口评估 baseline 与 candidate。
- 聚合 OOS 结果形成最终决策。

### 4.3 核心指标

**权重三元组（必须归一化）**：

- `w_mss`：MSS 权重（`>=0` 且 `<=0.60`）
- `w_irs`：IRS 权重（`>=0` 且 `<=0.60`）
- `w_pas`：PAS 权重（`>=0` 且 `<=0.60`）
- 约束：`w_mss + w_irs + w_pas = 1`

**绩效指标**：

- `oos_return`（样本外收益率）
- `max_drawdown`（最大回撤）
- `sharpe`（夏普比率）
- `turnover`（换手率）
- `cost_sensitivity`（成本敏感性，高换手下收益衰减）

### 4.4 替换规则

- candidate 同时满足下列条件才可替换 baseline：
  - `oos_return` 高于 baseline
  - `max_drawdown` 不劣于 baseline 超阈值（`config.max_drawdown_tolerance`，默认 2%）
  - `sharpe` 不低于 baseline
- 不满足则回退 baseline，并标记原因。

---

## 5. Gate 决策规则

| 条件 | final_gate | 说明 |
|---|---|---|
| 任一核心输入缺失 | FAIL | 阻断 |
| 因子 FAIL 或 权重 FAIL | FAIL | 阻断 |
| 因子 WARN 且 权重 PASS | WARN | 允许进入但标记风险 |
| 因子 PASS 且 权重 WARN | WARN | 允许进入但标记风险 |
| 因子 WARN 且 权重 WARN | WARN | 允许进入但标记风险 |
| 因子 PASS 且 权重 PASS | PASS | 完全通过 |

> FAIL 不允许进入 CP-05；WARN 允许进入，但必须在分析报告中显式标记风险。

---

## 6. 输出与产物

- DuckDB 持久化（权威）：`validation_factor_report`、`validation_weight_report`、`validation_gate_decision`、`validation_weight_plan`、`validation_run_manifest`
- 可读报告：`.reports/validation/{trade_date}/summary_{YYYYMMDD_HHMMSS}.md`
- 可选导出：parquet 仅用于调试导出，不作为下游契约

### 6.1 Validation -> Integration 权重桥接

```python
gate = repo.get_validation_gate_decision(trade_date)
if gate.final_gate == "FAIL":
    raise ValidationGateError("Gate=FAIL，不允许进入集成")

weight_plan = repo.get_validation_weight_plan(
    trade_date=trade_date,
    plan_id=gate.selected_weight_plan,
)
# Integration.calculate(..., weight_plan=weight_plan, validation_gate_decision=gate)
```

---

## 7. 最小闭环命令（模板）

```bash
run:  python -m src.validation.run_daily_gate --trade-date 20260207
test: pytest tests/validation/test_gate.py -q
```

产物检查：

- `validation_gate_decision`、`validation_weight_plan` 表中存在当日记录
- FAIL/WARN 有 `reason` 与 `fallback_plan` 字段
