# EmotionQuant 模块索引（Spiral 实现版）

**版本**: v4.1.0
**最后更新**: 2026-02-07
**状态**: 实现前最终模块清单

---

## 1. 模块结构

```
docs/
├── system-overview.md
├── module-index.md
├── naming-conventions.md
├── design/
│   ├── core-algorithms/
│   │   ├── mss/
│   │   ├── irs/
│   │   ├── pas/
│   │   └── integration/
│   ├── validation/                # 新增：因子/权重验证
│   │   ├── factor-weight-validation-algorithm.md
│   │   ├── factor-weight-validation-data-models.md
│   │   ├── factor-weight-validation-api.md
│   │   └── factor-weight-validation-information-flow.md
│   ├── data-layer/
│   ├── backtest/
│   │   └── backtest-engine-selection.md
│   ├── trading/
│   ├── gui/
│   └── analysis/
```

---

## 2. 核心算法模块

### 2.1 MSS

- 路径：`docs/design/core-algorithms/mss/`
- 输出：温度、周期、趋势、仓位建议

### 2.2 IRS

- 路径：`docs/design/core-algorithms/irs/`
- 输出：行业评分、轮动状态、行业排名

### 2.3 PAS

- 路径：`docs/design/core-algorithms/pas/`
- 输出：机会评分、等级、方向、风险收益比

### 2.4 Integration

- 路径：`docs/design/core-algorithms/integration/`
- 输出：统一推荐信号与解释字段

---

## 3. 验证模块（新增，必须）

### 3.1 Factor & Weight Validation

- 路径：`docs/design/validation/`
- 作用：
  - 因子有效性验证（IC/RankIC/稳定性/衰减）
  - 权重方案验证（baseline 对照、OOS 评估、风险约束）
  - 输出 Gate 决策（PASS/WARN/FAIL）

> 该模块是实现前必须补齐的“证据层”，避免因子和权重长期拍脑袋。

---

## 4. 基础设施模块

### 4.1 Data Layer

- 路径：`docs/design/data-layer/`
- 存储口径：Parquet + DuckDB 单库优先

### 4.2 Backtest

- 路径：`docs/design/backtest/`
- 选型口径：接口优先，可替换引擎

### 4.3 Trading

- 路径：`docs/design/trading/`
- 重点：纸上交易先行，风险规则可审计

### 4.4 GUI

- 路径：`docs/design/gui/`
- 主线技术：Streamlit + Plotly

### 4.5 Analysis

- 路径：`docs/design/analysis/`
- 重点：绩效归因与日报

---

## 5. 与 ROADMAP 的关系

- ROADMAP 文件采用 Capability Pack（CP）语义，不是线性闸门。
- 文件名 `ROADMAP-PHASE-*.md` 为兼容命名，执行时按 CP 理解。
- Validation 模块在路线图中对应 `CP-10`（`Governance/ROADMAP/ROADMAP-PHASE-10-validation.md`）。
- 每圈 Spiral 从能力包中取切片实现，收口时必须同步更新文档与 record。

---

## 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v4.1.0 | 2026-02-07 | 增补 Validation 对应 CP-10 的路线映射 |
| v4.0.0 | 2026-02-07 | 新增 Validation 模块与回测选型文档；统一 Spiral 口径 |
| v3.1.0 | 2026-02-05 | 线性重构版 |

---

## 6. 设计迁移说明

- 过渡期冲突处理：`docs/design/README-spiral-transition.md`
