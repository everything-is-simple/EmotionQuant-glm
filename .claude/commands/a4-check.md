# A4 Gate 检查（进入实现前强制）

执行 A4 阶段零容忍门禁检查。在进入 A5 实现阶段前，必须通过所有检查。

## 执行步骤

### 1. 运行 Gate 检查

使用斜杠命令直接执行：

```text
/a4-check [phase]
```

或者手动执行零容忍检查：

```bash
# 检查路径硬编码
grep -r "G:/EmotionQuant_data\|C:/\|D:/" --include="*.py" src/ tests/ 2>/dev/null

# 检查技术指标
grep -r "talib\|MA\|RSI\|MACD\|KDJ\|BOLL\|EMA\|SMA\|ATR\|DMI\|ADX" --include="*.py" src/ tests/ 2>/dev/null
```

如果用户没有提供 phase 参数，请询问当前是哪个 Phase。

### 2. 零容忍检查项

检查以下内容并报告结果：

- [ ] **路径硬编码检查**：代码中不允许存在硬编码的绝对路径

- [ ] **技术指标检查**：不允许引入技术指标（MA/RSI/MACD/KDJ/BOLL等）

- [ ] **数据契约一致性**：数据模型定义与 `docs/design/{module}/{module}-data-models.md` 必须一致

- [ ] **简化方案检查**：不允许 TODO/FIXME/HACK/mock/fake 等

### 3. 三维一致性自查

- [ ] 数据模型 ↔ API 一致性

- [ ] API ↔ 信息流一致性

### 4. 输出格式

```text
## A4 Gate 检查结果

**Phase**: XX | **Stage**: A4 | **时间**: YYYY-MM-DD HH:MM

### 零容忍检查
- 路径硬编码: ✅ 通过 / ❌ 失败
- 技术指标: ✅ 通过 / ❌ 失败
- 数据契约: ✅ 通过 / ❌ 失败
- 简化方案: ✅ 通过 / ❌ 失败

### 三维一致性
- 数据模型↔API: ✅ / ❌
- API↔信息流: ✅ / ❌

### 结论
[✅ 可进入 A5 阶段 / ❌ 需修复后重新检查]
```

### 5. 失败处理

如果任何零容忍检查失败：

1. 列出所有失败项

2. 提供具体修复建议

3. 修复后必须重新运行 `/a4-check`

4. **不允许跳过直接进入 A5**
