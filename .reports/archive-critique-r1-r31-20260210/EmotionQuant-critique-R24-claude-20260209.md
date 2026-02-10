# EmotionQuant R24 深度审查报告

**审查时间**: 2026-02-09  
**审查轮次**: R24  
**审查模块**: Validation 模块四位一体  
**审查角度**: 内部一致性 + 上游契约对齐 + 权重选择逻辑完整性  

---

## 审查范围

| 文件 | 版本 | 最后更新 | 状态 |
|------|------|----------|------|
| factor-weight-validation-algorithm.md | v2.0.0 | 2026-02-07 | 已审查 |
| factor-weight-validation-data-models.md | v2.0.0 | 2026-02-07 | 已审查 |
| factor-weight-validation-api.md | v2.0.0 | 2026-02-07 | 已审查 |
| factor-weight-validation-information-flow.md | v2.0.0 | 2026-02-07 | 已审查 |

---

## 问题汇总

| 优先级 | 数量 | 类型 |
|--------|------|------|
| P1 | 5 | 字段映射不清晰、时间戳缺失、上游依赖错误 |
| P2 | 5 | 参数说明不足、错误处理场景缺失、决策规则模糊 |
| **合计** | **10** | - |

---

## P1 级问题（必须修复）

### P1-R24-01: Algorithm §3.2 指标名与中文描述缺少映射表

**文件**: `factor-weight-validation-algorithm.md`  
**位置**: 行 50-56  

**问题描述**:
- Algorithm §3.2 混用中文描述与英文字段名
- 例如：54行写"正 IC 比例"，但§3.3 门禁表（64行）写 `positive_ic_ratio`
- 缺少明确的中英文映射表，读者需要猜测对应关系

**当前表述**:
```markdown
### 3.2 必算指标

- `mean_ic`（Pearson）
- `mean_rank_ic`（Spearman）
- `icir`（`mean_ic / std(ic)`）
- `positive_ic_ratio`（正 IC 比例）
- `decay_1d / decay_3d / decay_5d / decay_10d`
- `coverage_ratio`（有效样本覆盖率）
```

**修复建议**:
补充完整映射表：
```markdown
### 3.2 必算指标

| 字段名 | 说明 | 计算口径 |
|--------|------|----------|
| `mean_ic` | 平均IC | Pearson相关系数 |
| `mean_rank_ic` | 平均RankIC | Spearman秩相关 |
| `icir` | ICIR | mean_ic / std(ic) |
| `positive_ic_ratio` | 正IC比例 | IC>0的样本比例 |
| `decay_1d/3d/5d/10d` | 衰减系数 | 因子持续预测力 |
| `coverage_ratio` | 样本覆盖率 | 有效样本 / 全市场样本 |
```

**修复位置**: `factor-weight-validation-algorithm.md` §3.2

---

### P1-R24-02: Data-Models §3 ValidationGateDecision 缺 `created_at` 时间戳

**文件**: `factor-weight-validation-data-models.md`  
**位置**: 行 51-63  

**问题描述**:
- ValidationGateDecision 作为关键决策产物，缺少时间戳字段
- 其他 L3 输出表都有 `created_at`（如 `mss_panorama`、`integrated_recommendation`）
- 无法审计 Gate 决策生成时间，调试时难以追溯

**当前字段**:
```markdown
| trade_date | str | 交易日 |
| factor_gate | str | PASS/WARN/FAIL |
| weight_gate | str | PASS/WARN/FAIL |
| final_gate | str | PASS/WARN/FAIL |
| selected_weight_plan | str | baseline/candidate_id |
| stale_days | int | 距离上次有效验证的天数 |
| fallback_plan | str | FAIL/WARN 时回退策略 |
| reason | str | 决策原因 |
```

**修复建议**:
补充时间戳字段：
```markdown
| created_at | datetime | 决策生成时间（用于审计与调试） |
```

**修复位置**: `factor-weight-validation-data-models.md` §3 行 63

---

### P1-R24-03: API §3.1 decide_gate 参数类型注解风格不一致

**文件**: `factor-weight-validation-api.md`  
**位置**: 行 69-73  

**问题描述**:
- 72行使用 Python 3.10+ 语法：`ValidationGateDecision | None = None`
- 项目其他文件使用传统语法：`Optional[ValidationGateDecision]`
- 类型注解风格不统一，低版本 Python 可能不兼容

**当前签名**:
```python
def decide_gate(
    factor_results: list[FactorValidationResult],
    weight_result: WeightValidationResult,
    previous_gate: ValidationGateDecision | None = None,
) -> ValidationGateDecision
```

**修复建议**:
统一为传统语法，或在文档开头声明 Python 版本要求：
```python
from typing import Optional

def decide_gate(
    factor_results: list[FactorValidationResult],
    weight_result: WeightValidationResult,
    previous_gate: Optional[ValidationGateDecision] = None,
) -> ValidationGateDecision
```

**修复位置**: `factor-weight-validation-api.md` §3.1 行 72

---

### P1-R24-04: Algorithm §4.3 核心指标缺少权重三元组说明

**文件**: `factor-weight-validation-algorithm.md`  
**位置**: 行 86-92  

**问题描述**:
- Algorithm §4.3 列举指标：`oos_return / max_drawdown / sharpe / turnover / cost_sensitivity`
- Data-Models §2 WeightValidationResult 包含 `w_mss / w_irs / w_pas`（37-39行）
- Algorithm 未说明权重三元组也是核心指标的一部分

**当前表述**:
```markdown
### 4.3 核心指标

- `oos_return`
- `max_drawdown`
- `sharpe`
- `turnover`
- `cost_sensitivity`（成本敏感性）
```

**修复建议**:
补充权重三元组：
```markdown
### 4.3 核心指标

**权重三元组**（必须归一化）:
- `w_mss`：MSS权重（≥0, ≤0.60）
- `w_irs`：IRS权重（≥0, ≤0.60）
- `w_pas`：PAS权重（≥0, ≤0.60）
- 约束：`w_mss + w_irs + w_pas = 1`

**绩效指标**:
- `oos_return`：样本外收益率
- `max_drawdown`：最大回撤
- `sharpe`：夏普比率
- `turnover`：换手率
- `cost_sensitivity`：成本敏感性（高换手时的收益衰减）
```

**修复位置**: `factor-weight-validation-algorithm.md` §4.3

---

### P1-R24-05: Info-Flow §4 输入边界上游依赖错误

**文件**: `factor-weight-validation-information-flow.md`  
**位置**: 行 47-54  

**问题描述**:
- 50行写 `factor_series | CP-02/03/04 | 必需`
- 但 CP-02/03/04 是 MSS/IRS/PAS，输出的是**评分结果**，而非**因子序列**
- 因子序列应该来自 Data Layer 的 L2 聚合（`market_snapshot` / `industry_snapshot`）
- 上游依赖描述错误，会导致实现时混淆

**当前表述**:
```markdown
| 输入 | 来源 | 必要性 |
|------|------|--------|
| factor_series | CP-02/03/04 | 必需 |
| future_returns | CP-01 | 必需 |
| signals | CP-05 输入侧 | 必需 |
| prices | CP-01 | 必需 |
| trade_calendar | CP-01 | 必需 |
```

**修复建议**:
修正上游来源：
```markdown
| 输入 | 来源 | 必要性 | 说明 |
|------|------|--------|------|
| factor_series | Data Layer L2 (market_snapshot/industry_snapshot/stock_gene_cache) | 必需 | 原始因子序列（涨跌家数、涨停数等），非评分 |
| future_returns | Data Layer L1 (raw_daily) | 必需 | 未来H日收益率（用于计算IC） |
| signals | Integration 输出 (integrated_recommendation) | 必需 | 集成信号（用于回测权重） |
| prices | Data Layer L1 (raw_daily) | 必需 | OHLC价格数据 |
| trade_calendar | Data Layer L1 (raw_trade_cal) | 必需 | 交易日历 |
```

**修复位置**: `factor-weight-validation-information-flow.md` §4 行 50-54

---

## P2 级问题（建议修复）

### P2-R24-06: Algorithm §4.2 Walk-Forward 窗口参数缺少单位说明

**文件**: `factor-weight-validation-algorithm.md`  
**位置**: 行 80-83  

**问题描述**:
- 81行写 `窗口：train=252 交易日，validate=63 交易日，oos=63 交易日`
- 252/63 是常见的交易日数量，但缺少"为何选择这些数字"的说明
- 读者不清楚窗口设计依据

**修复建议**:
补充说明：
```markdown
- 窗口设计（Walk-Forward）:
  - `train=252` 交易日（约1年）：用于训练权重
  - `validate=63` 交易日（约3个月）：用于初步验证
  - `oos=63` 交易日（约3个月）：用于样本外测试
  - 设计依据：平衡样本量与市场周期（252日约覆盖1个完整市场周期）
```

**修复位置**: `factor-weight-validation-algorithm.md` §4.2 行 81

---

### P2-R24-07: Data-Models §4 ValidationRunManifest 缺少 `failed_reason` 字段

**文件**: `factor-weight-validation-data-models.md`  
**位置**: 行 66-78  

**问题描述**:
- 77行 `status | str | SUCCESS/FAILED`
- 但缺少 `failed_reason` 字段记录失败原因
- 调试时需要查日志才能知道失败原因，运维效率低

**修复建议**:
补充字段：
```markdown
| failed_reason | str | 失败原因（status=FAILED时记录错误信息） |
```

**修复位置**: `factor-weight-validation-data-models.md` §4 行 77 后

---

### P2-R24-08: API §4.1 run_daily_gate 返回类型与下游消费不一致

**文件**: `factor-weight-validation-api.md` + `factor-weight-validation-information-flow.md`  
**位置**: API 83-86行，Info-Flow 24-30行  

**问题描述**:
- API 86行返回类型：`-> ValidationGateDecision`
- Info-Flow 28行写 `CP-05 读取 gate + weight_plan`
- 不清楚 `weight_plan` 是否包含在 `ValidationGateDecision` 内部，还是需要额外查询

**修复建议**:
Data-Models §3 明确 `selected_weight_plan` 字段说明：
```markdown
| selected_weight_plan | str | baseline/candidate_id（具体权重值从 weight_validation_report 查询，格式：{"w_mss": 0.33, "w_irs": 0.33, "w_pas": 0.34}） |
```

**修复位置**: `factor-weight-validation-data-models.md` §3 行 59

---

### P2-R24-09: Algorithm §5 Gate 决策规则缺少 WARN 边界条件

**文件**: `factor-weight-validation-algorithm.md`  
**位置**: 行 103-112  

**问题描述**:
- 110行写 `无 FAIL 且至少一个 WARN | WARN`
- 111行写 `因子与权重均 PASS | PASS`
- 但缺少"因子 PASS + 权重 WARN"或"因子 WARN + 权重 PASS"的明确规则
- 可能导致实现时逻辑分支遗漏

**当前规则**:
```markdown
| 条件 | final_gate |
|------|------------|
| 任一核心输入缺失 | FAIL |
| 因子门禁 FAIL | FAIL |
| 权重门禁 FAIL | FAIL |
| 无 FAIL 且至少一个 WARN | WARN |
| 因子与权重均 PASS | PASS |
```

**修复建议**:
明确所有组合：
```markdown
| 条件 | final_gate | 说明 |
|------|------------|------|
| 任一核心输入缺失 | FAIL | 阻断 |
| 因子 FAIL 或 权重 FAIL | FAIL | 阻断 |
| 因子 WARN 且 权重 PASS | WARN | 允许进入但标记风险 |
| 因子 PASS 且 权重 WARN | WARN | 允许进入但标记风险 |
| 因子 WARN 且 权重 WARN | WARN | 允许进入但标记风险 |
| 因子 PASS 且 权重 PASS | PASS | 完全通过 |
```

**修复位置**: `factor-weight-validation-algorithm.md` §5 行 105-111

---

### P2-R24-10: Info-Flow §6 错误处理缺少"验证数据过期"场景

**文件**: `factor-weight-validation-information-flow.md`  
**位置**: 行 68-76  

**问题描述**:
- Data-Models §3 (60行) 定义了 `stale_days` 字段
- 但 Info-Flow §6 错误处理表没有对应的"验证数据过期"处理规则
- 运维手册不完整

**当前表格**:
```markdown
| 场景 | 级别 | 处理 |
|------|------|------|
| 缺失 future return | P0 | 阻断 |
| 因子样本不足 | P1 | 标记 WARN 并剔除该因子 |
| 候选不优于 baseline | P1 | 回退 baseline |
| 验证任务超时 | P2 | 使用最近有效结果并标记 stale |
```

**修复建议**:
补充场景：
```markdown
| 验证数据过期（stale_days > 阈值，如 3 天） | P1 | 使用最近有效结果并标记 stale，触发告警通知人工介入 |
```

**修复位置**: `factor-weight-validation-information-flow.md` §6 行 75 后

---

## 审查统计

| 维度 | 数量 |
|------|------|
| 审查文件 | 4个 |
| 发现问题 | 10个 |
| P1问题 | 5个 |
| P2问题 | 5个 |
| 涉及字段 | ~12个 |
| 涉及函数 | ~6个 |

---

## 修复优先级建议

### 立即修复（阻塞性）
1. **P1-R24-05**: Info-Flow §4 上游依赖错误（factor_series 来源错误）
2. **P1-R24-02**: ValidationGateDecision 缺时间戳（审计必需）

### 优先修复（影响理解）
3. **P1-R24-01**: Algorithm §3.2 字段映射表缺失
4. **P1-R24-04**: Algorithm §4.3 权重三元组说明缺失
5. **P2-R24-09**: Gate 决策规则边界不清晰

### 建议修复（提升质量）
6. **P1-R24-03**: API 类型注解风格统一
7. **P2-R24-06**: Walk-Forward 窗口参数说明
8. **P2-R24-07**: ValidationRunManifest 补 failed_reason
9. **P2-R24-08**: selected_weight_plan 字段说明
10. **P2-R24-10**: 错误处理补"数据过期"场景

---

## 累计进度（R1-R24）

| 轮次 | 审查模块 | 发现问题 | 状态 |
|------|----------|----------|------|
| R1-R12 | 跨模块一致性 | ~120 | ✅ 已修复 |
| R13 | 核心算法逻辑 | 10 | ✅ 已修复 |
| R14 | Data Layer DDL/契约 | 10 | ✅ 已修复 |
| R15 | GUI/Backtest/Analysis 跨模块 | 10 | ✅ 已修复 |
| R16 | API/DataModel/InfoFlow 对齐 | 10 | ✅ 已修复 |
| R17 | 核心算法四位一体 | 10 | ✅ 已修复 |
| R18 | 跨模块常量/阈值/DDL 追溯 | 10 | ✅ 已修复 |
| R19 | 依赖声明/API-DDL-enum 对齐 | 10 | ✅ 已修复 |
| R20 | Backtest + Trading 四位一体 | 10 | ✅ 已修复 |
| R21 | Analysis 四位一体 | 10 | ✅ 已修复 |
| R22 | GUI 四位一体 | 10 | ✅ 已修复 |
| R23 | Data Layer 四位一体 | 10 | ✅ 已修复 |
| **R24** | **Validation 四位一体** | **10** | **🔶 待修复** |
| **累计** | - | **229** | - |

---

## 下一步建议

1. **立即修复** P1-R24-05/02（阻塞性）
2. **R25 启动**: system-overview + scheduler + monitoring 最终对齐
3. **R26**: 端到端集成扫描（降级路径/边界条件）
4. **R27**: 最终文档一致性复查（查漏补缺）

---

**审查人**: Claude (Warp Agent Mode)  
**报告生成时间**: 2026-02-09  
**下次审查**: R25 - 系统级文档对齐（system-overview + scheduler + monitoring）
