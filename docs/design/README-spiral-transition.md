# 设计迁移声明（Spiral Transition）

**版本**: v1.0.0
**最后更新**: 2026-02-07
**用途**: 在实现前过渡阶段，统一新旧设计口径冲突

---

## 1. 背景

`docs/design/**` 中部分历史文档仍保留线性阶段口径（如零技术指标绝对禁令、backtrader固定、DuckDB按年分库）。

为避免实现阶段出现“同仓多套规则”，本声明定义过渡期优先级。

---

## 2. 优先级（高 -> 低）

1. `Governance/steering/系统铁律.md`
2. `Governance/steering/CORE-PRINCIPLES.md`
3. `Governance/ROADMAP/ROADMAP-OVERVIEW.md`
4. `docs/system-overview.md`
5. `docs/module-index.md`
6. `docs/design/**` 历史细节文档

若低优先级文档与高优先级文档冲突，以高优先级口径为准。

---

## 3. 当前统一口径（实现前基线）

1. 单指标不得独立决策（替代零技术指标绝对禁令）。
2. 回测选型为接口优先、实现可替换。
3. DuckDB 单库优先，分库需阈值触发。
4. GUI 主线使用 Streamlit + Plotly。
5. 因子验证与权重验证为独立 Gate 模块。

---

## 4. 清理计划

- S0-S1：优先更新核心入口文档与 ROADMAP。
- S2-S3：逐步清理 `docs/design/core-algorithms/**` 与 `docs/design/backtest/**` 冲突段落。
- S4 以后：完成全仓一致性检查。

---

## 5. 执行要求

在冲突尚未全部清理前，所有实现 PR/提交必须在 `review.md` 或 `final.md` 中注明：

- 是否触发了本声明
- 按哪条优先级规则处理

