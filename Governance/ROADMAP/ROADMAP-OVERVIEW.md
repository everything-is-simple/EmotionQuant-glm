# EmotionQuant ROADMAP 总览（Spiral 闭环主控）

**版本**: v6.1.0  
**最后更新**: 2026-02-07  
**适用对象**: 个人开发、个人使用

---

## 1. 这份文档管什么

本文件是路线图唯一主控入口，回答 4 个问题：

1. 下一圈做什么（目标）
2. 这一圈怎么判定完成（闭环证据）
3. 需要碰哪些能力包（CP）
4. 本圈最少要同步哪些文档（同步契约）

> 决策口径：先保闭环，再扩范围。禁止“看起来完成、实际不可运行”。

---

## 2. 术语统一（去线性）

- Spiral：一圈开发周期，默认 7 天。
- CP（Capability Pack）：能力包。现有 `ROADMAP-PHASE-*.md` 文件名保留，仅作兼容。
- Slice：能力包中的最小可交付切片（1 天内可完成）。
- 闭环证据：`run + test + artifact + review + sync` 五件套。

---

## 3. 执行铁则（个人版）

1. 一圈只允许 1 个主目标。
2. 一圈只取 1-3 个 Slice。
3. 任何 Slice 超过 1 天必须继续拆分。
4. 缺少任一闭环证据不得收口。
5. 如遇阻塞，优先缩圈，不做跨圈并行扩张。

---

## 4. Spiral 主路线（S0-S6）

| Spiral | 主目标 | 推荐 CP 组合 | 最小闭环证据 |
|---|---|---|---|
| S0 | 数据最小闭环 | CP-01 | 1 条可运行命令 + 1 个自动化测试 + 1 个数据产物 |
| S1 | MSS 闭环 | CP-01, CP-02 | 当日温度/周期可复现 + 结果文件 |
| S2 | 信号生成闭环 | CP-03, CP-04, CP-10, CP-05 | TopN 推荐 + 集成输出可追溯 |
| S3 | 回测闭环 | CP-10, CP-06, CP-09 | 基线回测报告 + 指标摘要 |
| S4 | 纸上交易闭环 | CP-07, CP-09 | 订单/持仓/风控日志可重放 |
| S5 | 展示闭环 | CP-08, CP-09 | GUI 可启动 + 日报导出 |
| S6 | 稳定化闭环 | 全部 | 重跑一致性 + 债务清偿记录 |

---

## 5. CP 映射（兼容旧文件名）

| CP | 能力 | 文件（兼容命名） |
|---|---|---|
| CP-01 | Data Layer | `Governance/ROADMAP/ROADMAP-PHASE-01-data-layer.md` |
| CP-02 | MSS | `Governance/ROADMAP/ROADMAP-PHASE-02-mss.md` |
| CP-03 | IRS | `Governance/ROADMAP/ROADMAP-PHASE-03-irs.md` |
| CP-04 | PAS | `Governance/ROADMAP/ROADMAP-PHASE-04-pas.md` |
| CP-05 | Integration | `Governance/ROADMAP/ROADMAP-PHASE-05-integration.md` |
| CP-06 | Backtest | `Governance/ROADMAP/ROADMAP-PHASE-06-backtest.md` |
| CP-07 | Trading | `Governance/ROADMAP/ROADMAP-PHASE-07-trading.md` |
| CP-08 | GUI | `Governance/ROADMAP/ROADMAP-PHASE-08-gui.md` |
| CP-09 | Analysis | `Governance/ROADMAP/ROADMAP-PHASE-09-analysis.md` |
| CP-10 | Validation | `Governance/ROADMAP/ROADMAP-PHASE-10-validation.md` |

---

## 6. 全局边界（所有 Spiral 生效）

### 6.1 输入边界

- 主流程只读本地数据。
- 远端数据必须先落地再进入主流程。

### 6.2 输出边界

- CP-05 输出必须可被 CP-06/07/08/09 复用。
- 分析报告必须可追溯到输入数据和参数。

### 6.3 错误分级

| 级别 | 定义 | 处理 |
|---|---|---|
| P0 | 核心输入缺失、规则冲突、合规违规 | 阻断 |
| P1 | 局部数据缺失、局部计算失败 | 降级 + 标记 |
| P2 | 非关键异常 | 重试 + 记录 |

---

## 7. 每圈最小同步契约（降负担）

每圈收口只强制更新以下 5 处：

1. `Governance/specs/spiral-s{N}/final.md`
2. `Governance/record/development-status.md`
3. `Governance/record/debts.md`
4. `Governance/record/reusable-assets.md`
5. `Governance/ROADMAP/ROADMAP-OVERVIEW.md`（只更新当圈状态）

能力包文档（CP）仅在“契约变化”时更新，不要求每圈都改。

---

## 8. 什么时候必须改 CP 文档

满足任一条件时，必须更新对应 CP 文件：

1. 输入字段变化
2. 输出字段变化
3. 错误处理策略变化
4. DoD 门禁变化
5. 上下游依赖变化

---

## 9. 归档说明

- 线性旧版：`Governance/ROADMAP/archive-linear-v4-20260207/`
- 该目录只读，不再继续演进。

---

## 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v6.1.0 | 2026-02-07 | 增加 CP-10 Validation；S2/S3 显式引入验证闭环 |
| v6.0.0 | 2026-02-07 | 重构为 Spiral 主控文档；引入 CP 术语；明确个人开发降负担同步契约 |
| v5.1.0 | 2026-02-07 | Spiral 路线与边界约束基线 |
