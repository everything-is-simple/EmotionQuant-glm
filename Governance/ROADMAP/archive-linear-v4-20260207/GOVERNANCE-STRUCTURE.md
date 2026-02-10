# EmotionQuant 治理结构与目录规范

**版本**: v1.1.1
**创建日期**: 2026-02-01
**最后更新**: 2026-02-04
**适用范围**: 全仓库

---

## 1. 目录结构总览

### 1.1 根目录治理约定

| 目录 | 定位 | 强制规则 |
|------|------|----------|
| `.reports/` | 报告统一存放点 | 报告必须放入该目录，命名必须包含日期+时间 |
| `.archive/` | 归档统一存放点 | 历史归档仅放入该目录 |
| `Governance/` | 系统治理文件入口 | 治理文件必须在该目录内维护 |

### 1.2 Governance 子目录定位

| 子目录 | 定位 | 说明 |
|--------|------|------|
| `Governance/steering/` | 系统原则与约束 | 存放核心原则、铁律、工作流等治理准则 |
| `Governance/ROADMAP/` | 系统实现路线图 | 存放路线图与阶段目标 |
| `Governance/specs/` | Phase 设计与任务分解 | 每个 Phase 的规范、拆解与执行记录 |
| `Governance/record/` | 治理记录 | 技术债、开发状态、可复用资产等记录 |

---

## 2. 报告与命名规范

### 2.1 报告存放

- 所有报告统一存放于 `.reports/`。
- 禁止将报告散落在模块目录或设计文档目录中。

### 2.2 报告命名

- 统一命名规则：`报告名称_YYYYMMDD_HHMMSS.md`
- 示例：`一致性检查报告_20260201_121500.md`

---

## 3. 归档规范

- 归档文件统一存放于 `.archive/`。
- 建议按日期或领域分层归档（例如 `.archive/analysis/202602/`）。

---

## 4. 治理文件归档规范

- 系统原则文件统一存放于 `Governance/steering/`。
- 工作流文档归档于 `Governance/steering/workflow/`。

| 历史位置（已归档） | 当前路径 |
|--------|----------|
| 旧工作流文档 | `Governance/steering/workflow/6A-WORKFLOW-task-to-step.md` |
| 旧工作流文档 | `Governance/steering/workflow/6A-WORKFLOW-phase-to-task.md` |

---

## 5. 记录文件归档规范

- 治理记录统一存放于 `Governance/record/`。

| 历史位置（已归档） | 当前路径 |
|--------|----------|
| 旧技术债记录 | `Governance/record/debts.md` |
| 旧开发状态记录 | `Governance/record/development-status.md` |
| 旧复用资产记录 | `Governance/record/reusable-assets.md` |

---

## 6. Specs 归档策略

### 6.1 归档触发条件

- Phase 完成并合并到 main/master 后
- 或 Phase 状态超过 6 个月未活跃

### 6.2 归档操作

1. 移动 `Governance/specs/phase-XX-task-*` 到 `.archive/specs/phase-XX/`
2. 保留 `Governance/specs/` 中活跃的 Phase

### 6.3 保留内容

- 仅保留当前活跃 Phase 和前一个 Phase 的 specs
- 其余归档

---

## 7. 四位一体文档适用范围

### 7.1 适用范围

| 模块类型 | 示例 | 文档要求 |
|----------|------|----------|
| 核心算法 | MSS/IRS/PAS/Integration | 必须四位一体 |
| 基础设施 | data-layer/backtest/trading/gui/analysis | 四位一体 |
| 工具类 | utils/config | 纳入所属模块，不单独成文 |

### 7.2 四位一体文档

- `{module}-algorithm.md` — 算法逻辑
- `{module}-data-models.md` — 数据模型
- `{module}-api.md` — 接口定义
- `{module}-information-flow.md` — 信息流

### 7.3 例外情况

- 工具类模块（utils/config）不需要单独的四位一体文档
- 可纳入其所属的基础设施模块（如 data-layer）中描述

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.1.1 | 2026-02-04 | 治理结构对齐系统重构版本 |
| v1.1.0 | 2026-02-03 | 新增 Specs 归档策略、四位一体文档适用范围 |
| v1.0.0 | 2026-02-01 | 新增治理结构与目录规范 |
