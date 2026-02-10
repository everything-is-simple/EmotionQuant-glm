# CLAUDE.md

本文件保留为代理兼容入口，但已与当前 Spiral 开发基线同步。

## 文档定位

- 作用：给自动化代理提供最小、可执行的仓库工作规则。
- 权威架构入口：`docs/system-overview.md`
- 权威路线入口：`Governance/ROADMAP/ROADMAP-OVERVIEW.md`
- 权威治理入口：`Governance/steering/`

## 当前执行模型

- 执行模型：Spiral（螺旋闭环），非线性 Stage 流水线。
- 默认节奏：7 天一圈。
- 路线术语：Capability Pack（CP），兼容旧 `ROADMAP-PHASE-*` 文件名。
- 每圈闭环：`run + test + artifact + review + sync`。

## 核心约束

1. 情绪优先，单指标不得独立决策。
2. 本地数据优先，远端只做补采。
3. 路径/密钥必须配置注入，禁止硬编码。
4. 严守 A 股规则。
5. 缺闭环证据不得标记完成。

详见：`Governance/steering/系统铁律.md`

## 工作流（分级治理）

### 默认模式（个人开发）

`Scope -> Build -> Verify -> Sync`

适用绝大多数任务。

### 升级模式（Strict 6A）

仅在以下场景启用完整 6A：

- 交易执行路径重大改动
- 风控规则重大改动
- 数据契约破坏性变更
- 引入影响主流程的新外部依赖

详见：

- `Governance/steering/workflow/6A-WORKFLOW-phase-to-task.md`
- `Governance/steering/workflow/6A-WORKFLOW-task-to-step.md`

## 文档同步要求（最小集）

每圈收口强制同步：

1. `Governance/specs/spiral-s{N}/final.md`
2. `Governance/record/development-status.md`
3. `Governance/record/debts.md`
4. `Governance/record/reusable-assets.md`
5. `Governance/ROADMAP/ROADMAP-OVERVIEW.md`

`ROADMAP-PHASE-*.md` 仅在契约变化时更新。

## 技术栈口径（当前）

- Python `>=3.10`
- 数据：Parquet + DuckDB（单库优先）
- GUI 主线：Streamlit + Plotly
- 回测：接口优先，可替换实现（`backtrader` 为可选适配）

详见：

- `pyproject.toml`
- `requirements.txt`
- `docs/design/backtest/backtest-engine-selection.md`

## 仓库远端

- `origin`: `https://github.com/everything-is-simple/EmotionQuant_beta.git`

## 历史说明

- 旧版线性文档已归档至：
  - `Governance/ROADMAP/archive-linear-v4-20260207/`
- 本文件不再维护线性 Stage 叙述。
