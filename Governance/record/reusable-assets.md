# EmotionQuant 可复用资产登记表（Spiral 版）

**最后更新**: 2026-02-07  
**版本**: v2.0  
**范围**: S0-S6

---

## 分级定义

| 等级 | 说明 |
|---|---|
| S | 可直接复用、稳定 |
| A | 可复用，但需少量适配 |
| B | 结构可参考，需较大改造 |

---

## 治理与流程资产

| ID | 资产 | 路径 | 等级 | 用途 |
|---|---|---|---|---|
| S-GOV-001 | Spiral 主控路线图 | `Governance/ROADMAP/ROADMAP-OVERVIEW.md` | S | 圈级目标、CP 组合、最小同步 |
| S-GOV-002 | CP 能力包模板 | `Governance/ROADMAP/ROADMAP-PHASE-*.md` | S | 契约/Slice/Gate 复用 |
| S-GOV-003 | Task 闭环卡片模板 | `Governance/ROADMAP/TASK-TEMPLATE.md` | S | 每日任务拆解 |
| S-GOV-004 | Task 执行工作流 | `Governance/steering/workflow/6A-WORKFLOW-task-to-step.md` | S | Scope/Build/Verify/Sync |
| S-GOV-005 | Spiral 规划工作流 | `Governance/steering/workflow/6A-WORKFLOW-phase-to-task.md` | S | Spiral 到 Task 拆分 |

---

## 设计资产

| ID | 资产 | 路径 | 等级 | 用途 |
|---|---|---|---|---|
| S-DES-001 | 系统总览（Spiral） | `docs/system-overview.md` | S | 架构基线 |
| S-DES-002 | 模块索引 | `docs/module-index.md` | S | 设计导航 |
| A-DES-003 | 回测选型策略 | `docs/design/backtest/backtest-engine-selection.md` | A | 引擎替换决策 |
| A-DES-004 | 因子/权重验证设计 | `docs/design/validation/*` | A | 验证模块落地 |

---

## 代码与配置资产

| ID | 资产 | 路径 | 等级 | 用途 |
|---|---|---|---|---|
| A-CFG-001 | Python 项目依赖分层 | `pyproject.toml` | A | 主依赖与可选依赖管理 |
| A-CFG-002 | 运行依赖清单 | `requirements.txt` | A | 快速环境安装 |
| B-CODE-003 | Skeleton 目录结构 | `src/` | B | 模块落地骨架 |

---

## 当前空缺（需后续沉淀）

1. 可复用数据下载 CLI（目标 S0/S1）
2. 可复用验证报告生成器（目标 S1/S2）
3. 可复用回测基线 Runner（目标 S3）

---

## 版本历史

| 日期 | 版本 | 变更内容 |
|---|---|---|
| 2026-02-07 | v2.0 | 重建为 Spiral 资产清单，移除旧线性 Task 占位口径 |
| 2026-02-05 | v1.4 | 线性阶段资产登记版本 |
