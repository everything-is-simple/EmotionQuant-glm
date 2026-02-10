# 文档一致性检查

对 Task 的四份规格文档（requirements.md, design.md, tasks.md, approve.md）进行一致性验证。

这是关键的质量门禁检查，确保在进入 A5 实施阶段前，四文档的关键字段完全一致。

## 执行验证

### 1. 手动检查清单

检查 `Governance/specs/phase-XX-task-Y/` 目录下的四份文档：

| 检查项 | 说明 |
| -------- | ------ |
| 工时一致性 | 四份文档中的预估工时应一致 |
| Step 数量 | tasks.md 中的 Step 数量应与 design.md 对齐 |
| 日期格式 | 统一使用 YYYY-MM-DD 格式 |
| 阶段引用 | 确认当前处于正确的 6A 阶段 |
| 无 Mock 关键词 | A4 阶段后禁止 TODO/HACK/FIXME/mock |

### 2. 快速检查命令

```bash
# 检查 Mock 关键词
grep -rn "TODO\|HACK\|FIXME\|mock\|fake" Governance/specs/phase-*-task-*/

# 检查日期格式
grep -rn "[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}" Governance/specs/phase-*-task-*/
```

### 3. 文档结构验证

确认每个 Task 目录包含完整的 6A 文档：

```text
Governance/specs/phase-XX-task-Y/
├── requirements.md    # A1 产物
├── design.md          # A2 产物
├── tasks.md           # A3 产物
├── approve.md         # A4 产物
├── review.md          # A5 产物（实现后）
└── final.md           # A6 产物（完成后）
```

## 检查通过标准

- [ ] 工时一致（四份文档）

- [ ] Step 数量一致（design.md ↔ tasks.md）

- [ ] 日期格式统一

- [ ] 无 Mock 关键词（A4 阶段后）

- [ ] Step 编号唯一

- [ ] 无重复章节

**验证通过后即可进入 A5 实施阶段。**
