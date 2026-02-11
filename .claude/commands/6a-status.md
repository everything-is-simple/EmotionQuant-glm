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
| A3 | Act 实现 | 最小实现怎么落地？ | 代码 + 最小自动化测试 |
| A4 | Assert 验证 | run/test/artifact 是否可复现？ | 验证结果 |
| A5 | Archive 归档 | 证据链是否完整归档？ | review.md + final.md |
| A6 | Advance 推进 | 五项同步是否完成？ | 同步记录 |

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
- A3 Act: ✅ / 🔄 / ⏳
- A4 Assert: ✅ / 🔄 / ⏳
- A5 Archive: ✅ / 🔄 / ⏳
- A6 Advance: ✅ / 🔄 / ⏳

### 下一步行动
[根据当前阶段给出建议]
```

### 4. 阶段建议

根据当前阶段提供下一步建议：

- **A1**: 确认需求理解，等待用户批准

- **A2**: 完成三维设计，运行一致性自查

- **A3**: 落地最小实现，并补齐至少 1 条自动化测试

- **A4**: 运行 `/a4-check`，验证 run/test/artifact 可复现

- **A5**: 归档 `review.md` 与 `final.md`，补全证据链

- **A6**: 运行 `/a6-check`，完成五项最小同步

### 5. 相关命令

- `/a4-check [phase]` - A4 Gate 检查

- `/a6-check [phase]` - A6 完整检查

- `/tdd` - TDD 提醒

- `/phase-start` - Phase 启动检查
