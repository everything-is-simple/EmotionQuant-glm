# 会话启动检查

新会话开始时的上下文加载和状态确认。

## 执行步骤

### 1. 环境确认

```bash
# 检查 Git 分支状态
git status
git branch --show-current
```

确认：

- [ ] 当前在正确的 feature 分支上

- [ ] 工作目录干净或已知变更

### 2. 上下文加载

读取以下核心治理文档：

| 文档 | 路径 | 用途 |
| ------ | ------ | ------ |
| 核心原则 | `Governance/steering/CORE-PRINCIPLES.md` | 零容忍规则 |
| 6A 工作流 | `Governance/steering/workflow/6A-WORKFLOW-task-to-step.md` | A1-A6 执行流程 |
| Phase→Task | `Governance/steering/workflow/6A-WORKFLOW-phase-to-task.md` | Phase 分解流程 |

### 3. 状态确认

读取 `Governance/record/development-status.md`，确认：

- 当前 Phase 和 Task

- 上次会话的进度

- 待处理的技术债（`Governance/record/debts.md`）

### 4. 输出格式

```text
## 会话启动检查完成

### 环境状态
- Git 分支: feature/phase-XX-task-Y-xxx
- 工作目录: ✅ 干净 / ⚠️ 有未提交变更

### 当前进度
- **Phase**: XX - [Phase名称]
- **Task**: Y - [Task名称]
- **6A 阶段**: A[N] - [阶段名称]

### 上次会话进度
[从 development-status.md 提取]

### 待处理事项
- [ ] [待处理项1]
- [ ] [待处理项2]

### 核心约束提醒
1. **零技术指标**: 禁用 MA/RSI/MACD/KDJ/BOLL
2. **路径硬编码**: 必须通过 Config 读取
3. **TDD 强制**: 红灯 → 绿灯 → 重构

### 下一步行动
[根据当前阶段给出建议]
```

### 5. 会话开始问题

如果无法确定当前状态，主动询问用户：

1. 我们在哪个 Phase？

2. 我们在哪个 Task？

3. 上次会话的进度是什么？

### 6. 相关命令

- `/6a-status` - 查看 6A 工作流状态

- `/a4-check [phase]` - A4 Gate 检查

- `/a6-check [phase]` - A6 完整检查

- `/tdd` - TDD 提醒
