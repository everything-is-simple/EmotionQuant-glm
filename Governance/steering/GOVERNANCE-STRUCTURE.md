# EmotionQuant 治理结构与目录规范（Spiral 版）

**版本**: v3.0.0  
**最后更新**: 2026-02-07

---

## 1. 治理目录

- `Governance/ROADMAP/`：Spiral 主路线与能力包（CP）
- `Governance/steering/`：铁律、原则、流程
- `Governance/record/`：状态、债务、复用资产
- `Governance/specs/spiral-s*/`：每圈 specs 与复盘
- `Governance/ROADMAP/archive-linear-v4-20260207/`：线性旧版只读归档

---

## 2. 单一事实源（SoT）

| 场景 | 唯一权威文件 |
|---|---|
| 本圈做什么 | `Governance/ROADMAP/ROADMAP-OVERVIEW.md` |
| 能力契约是什么 | `Governance/ROADMAP/ROADMAP-PHASE-*.md`（CP） |
| 任务如何写 | `Governance/ROADMAP/TASK-TEMPLATE.md` |
| 任务如何执行 | `Governance/steering/workflow/6A-WORKFLOW-task-to-step.md` |
| 规划如何拆分 | `Governance/steering/workflow/6A-WORKFLOW-phase-to-task.md` |
| 不可违反什么 | `Governance/steering/系统铁律.md` |

---

## 3. 每圈最小同步

每圈收口强制更新 5 项：

1. `Governance/specs/spiral-s{N}/final.md`
2. `Governance/record/development-status.md`
3. `Governance/record/debts.md`
4. `Governance/record/reusable-assets.md`
5. `Governance/ROADMAP/ROADMAP-OVERVIEW.md`

CP 文档仅在契约变化时更新。

---

## 4. .claude 资产处理原则

- `.claude/` 保留为历史工具资产，不作为当前强制流程。
- 可复用内容迁移方向：
  - 命令级检查逻辑 -> `Governance/steering/workflow/`
  - 规则类约束 -> `Governance/steering/系统铁律.md`
  - 经验模板 -> `Governance/ROADMAP/TASK-TEMPLATE.md`

---

## 5. 归档策略

1. 路线模型代际变化必须归档（如线性 -> 螺旋）。
2. 归档目录命名：`archive-{model}-{version}-{date}`。
3. 归档目录只读，不再迭代。

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|---|---|---|
| v3.0.0 | 2026-02-07 | 增加单一事实源矩阵与 .claude 资产迁移原则 |
| v2.0.0 | 2026-02-07 | Spiral 治理结构初稿 |
