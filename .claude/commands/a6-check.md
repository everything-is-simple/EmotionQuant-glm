# A6 完整检查（Task 收口）

执行 A6 阶段完整质量验证。Task 收口前的完整检查，包括测试、文档同步、技术债登记。

## 执行步骤

### 1. 测试验证（前置条件）

```bash
# 运行全量回归测试
pytest tests/ -v
```

检查项：

- [ ] 当前 Task 单元测试通过

- [ ] **全量回归测试通过**

- [ ] 测试覆盖率达标（建议 ≥80%）

### 2. Gate 完整检查

使用斜杠命令直接执行：

```text
/a6-check [phase]
```

或者手动执行零容忍检查：

```bash
# 检查路径硬编码
grep -r "G:/EmotionQuant_data\|C:/\|D:/" --include="*.py" src/ tests/ 2>/dev/null

# 检查技术指标
grep -r "talib\|MA\|RSI\|MACD\|KDJ\|BOLL\|EMA\|SMA\|ATR\|DMI\|ADX" --include="*.py" src/ tests/ 2>/dev/null
```

如果用户没有提供 phase 参数，请询问当前是哪个 Phase。

检查项：

- [ ] 路径硬编码检查通过

- [ ] 技术指标检查通过（禁用 MA/RSI/MACD/KDJ/BOLL）

- [ ] 数据契约一致性

- [ ] 无简化方案（TODO/FIXME/HACK/mock/fake）

### 3. 文档同步检查

检查以下文件是否已更新：

- [ ] `Governance/specs/phase-XX-task-Y/` 目录下 6A 文档完整

- [ ] `Governance/record/development-status.md` 状态已更新

- [ ] `Governance/record/reusable-assets.md` 可复用资产已登记

### 4. 复用资产登记

- [ ] 识别可复用资产（数据模型、API、工具函数）

- [ ] 登记到 `Governance/record/reusable-assets.md`

### 5. 技术债处理

- [ ] 新增技术债已登记到 `Governance/record/debts.md`

### 6. 输出格式

```text
## A6 完整检查结果

**Phase**: XX | **Task**: [Task名称] | **时间**: YYYY-MM-DD HH:MM

### 测试验证
- 单元测试: ✅ / ❌
- 回归测试: ✅ / ❌
- 覆盖率: XX%

### Gate 检查
- 全部通过: ✅ / ❌

### 文档同步
- 6A 文档完整: ✅ / ❌
- 开发状态: ✅ / ❌

### 复用资产
- 已登记 X 个资产

### 结论
[✅ Task 完成 / ❌ 需补充后重新检查]
```

### 7. 产物清单

完成 A6 后必须产出：

1. `review.md` - 评审记录文档

2. `final.md` - 最终总结文档（含经验教训）

3. 更新后的开发状态文档
