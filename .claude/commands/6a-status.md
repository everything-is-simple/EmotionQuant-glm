# 6A 工作流状态查询

查看当前 6A 工作流进度和状态。

## 执行步骤

### 1. 读取开发状态

读取 `Governance/record/development-status.md` 文件，提取：

- 当前 Phase

- 当前 Task

- 当前 6A 阶段（A1-A6）

- 完成进度

### 2. 6A 阶段说明

| 阶段 | 名称 | 核心问题 | 主要产物 |
| ------ | ------ | ---------- | ---------- |
| A1 | Align 对齐 | 做什么？为什么？ | requirements.md |
| A2 | Architect 架构 | 怎么设计？ | design.md |
| A3 | Atomize 原子化 | 怎么拆分？ | tasks.md |
| A4 | Approve 审批 | 设计可行吗？ | approve.md |
| A5 | Automate 实现 | 怎么做？ | 代码 + 测试 + review.md |
| A6 | Assess 评估 | 做完了吗？做得好吗？ | final.md |

### 3. 输出格式

```text
## 6A 工作流状态

**Phase**: X - [Phase名称]
**Task**: XX - [Task名称]
**当前阶段**: A[N] - [阶段名称]
**进度**: [已完成阶段] / 6

### 阶段状态
- A1 Align: ✅ 已完成 / 🔄 进行中 / ⏳ 待开始
- A2 Architect: ✅ / 🔄 / ⏳
- A3 Atomize: ✅ / 🔄 / ⏳
- A4 Approve: ✅ / 🔄 / ⏳
- A5 Automate: ✅ / 🔄 / ⏳
- A6 Assess: ✅ / 🔄 / ⏳

### 下一步行动
[根据当前阶段给出建议]
```

### 4. 阶段建议

根据当前阶段提供下一步建议：

- **A1**: 确认需求理解，等待用户批准

- **A2**: 完成三维设计，运行一致性自查

- **A3**: 拆分 Step，标注依赖关系

- **A4**: 运行 `/a4-check`，等待用户批准

- **A5**: 遵循 TDD，运行 `/tdd` 查看提醒

- **A6**: 运行 `/a6-check`，完成文档同步

### 5. 相关命令

- `/a4-check [phase]` - A4 Gate 检查

- `/a6-check [phase]` - A6 完整检查

- `/tdd` - TDD 提醒

- `/phase-start` - Phase 启动检查
