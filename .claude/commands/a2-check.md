# A2 设计规范检查（强制执行）

**版本**: v1.0
**用途**: 在 A2 Architect 阶段验证设计输出符合 `docs/design/` 四位一体规范
**触发时机**: A2 Architect 阶段完成 design.md 后

---

## 1. 规范映射总览

### 1.1 三维规范清单

| 维度 | 规范文件 | 章节 | 用途 |
| ------ | ---------- | ------ | ------ |
| **数据模型** | `docs/design/{module}/{module}-data-models.md` | §1-§5 | 字段定义、数据契约 |
| **API 接口** | `docs/design/{module}/{module}-api.md` | §1-§4 | 接口契约、参数规范 |
| **信息流** | `docs/design/{module}/{module}-information-flow.md` | §1-§4 | 数据流向、Stage 映射 |

### 1.2 模块级规范

| 模块 | 规范文件 | 触发条件 |
| ------ | ---------- | ---------- |
| 数据层 | `docs/design/data-layer/*.md` | 涉及数据仓储、模型 |
| 算法层 | `docs/design/core-algorithms/*/` | 涉及 MSS/IRS/PAS |
| GUI | `docs/design/gui/` | 涉及界面、权限 |
| 回测 | `docs/design/backtest/` | 涉及回测逻辑 |
| 交易 | `docs/design/trading/` | 涉及风控、下单 |

---

## 2. 执行步骤

### 2.1 加载适用规范

```bash
# 加载四位一体规范（按模块替换 {module}）
cat docs/design/{module}/{module}-data-models.md
cat docs/design/{module}/{module}-api.md
cat docs/design/{module}/{module}-information-flow.md

# 加载模块级规范（根据 Task 类型）
cat docs/design/core-algorithms/mss/mss-*.md  # MSS 相关
cat docs/design/core-algorithms/irs/irs-*.md  # IRS 相关
cat docs/design/core-algorithms/pas/pas-*.md  # PAS 相关
cat docs/design/gui/gui-*.md  # GUI 相关
cat docs/design/backtest/backtest-*.md  # 回测相关
cat docs/design/trading/trading-*.md  # 交易相关
```

### 2.2 规范版本记录

在 design.md 中记录引用的规范版本：

```markdown
## 规范引用

| 规范 | 版本 | 引用章节 |
|------|------|----------|
| {module}-data-models.md | v2.0 | §3.2, §4.1 |
| {module}-api.md | v2.0 | §2.1 |
| {module}-information-flow.md | v2.0 | §3.1 |
```

### 2.3 执行检查

使用 `/a2-check` 命令自动执行：

```text
/a2-check
```

或者手动执行：

```bash
# 检查 design.md 是否包含规范引用
grep -n "规范引用\|docs/design/" Governance/specs/phase-XX-task-Y/design.md

# 检查字段定义是否符合 {module}-data-models.md
python -c "from spec_validator import validate_design; validate_design('design.md')"

# 检查 API 契约是否符合 {module}-api.md
python -c "from spec_validator import validate_api; validate_api('design.md')"
```

---

## 3. 检查清单

### 3.1 数据模型一致性

- [ ] 字段命名符合 `{module}-data-models.md` 规范

- [ ] 数据类型与定义一致

- [ ] 必填字段已完整定义

- [ ] 外键关系已标注

### 3.2 API 接口一致性

- [ ] 接口命名符合 `{module}-api.md` 规范

- [ ] 参数列表完整且类型正确

- [ ] 返回值结构符合定义

- [ ] 异常处理已定义

### 3.3 信息流一致性

- [ ] 数据流向符合 `{module}-information-flow.md` 定义

- [ ] Stage 映射正确（IF-01 ~ IF-09）

- [ ] 输入输出契约明确

- [ ] 依赖关系已标注

### 3.4 模块级一致性

根据 Task 类型检查：

| 检查项 | MSS | IRS | PAS | GUI | 回测 | 交易 |
| -------- | ----- | ----- | ----- | ----- | ------ | ------ |
| 算法公式 | ✅ | ✅ | ✅ | - | - | - |
| 轮动规则 | - | ✅ | - | - | - | - |
| 机会评分 | - | - | ✅ | - | - | - |
| 权限定义 | - | - | - | ✅ | - | - |
| A 股规则 | - | - | - | - | ✅ | ✅ |
| 风控参数 | - | - | - | - | - | ✅ |

---

## 4. 输出格式

```text
## A2 设计规范检查结果

**Phase**: XX | **Task**: xxx | **时间**: YYYY-MM-DD HH:MM

### 规范版本记录
| 规范文件 | 版本 | 最后更新 |
|----------|------|----------|
| {module}-data-models.md | v2.0 | 2026-01-20 |
| {module}-api.md | v2.0 | 2026-01-20 |
| {module}-information-flow.md | v2.0 | 2026-01-20 |

### 三维一致性检查
- 数据模型 ↔ API: ✅ 通过 / ❌ 失败
- API ↔ 信息流: ✅ 通过 / ❌ 失败
- 信息流 ↔ 数据模型: ✅ 通过 / ❌ 失败

### 模块级检查
- [ ] 符合 MSS/IRS/PAS 算法规范（如适用）
- [ ] 符合 GUI 权限定义（如适用）
- [ ] 符合 A 股规则约束（如适用）

### 规范引用检查
- design.md 包含规范引用表: ✅ / ❌
- 引用版本与实际一致: ✅ / ❌

### 结论
[✅ 可进入 A3 阶段 / ❌ 需修复后重新检查]
```

---

## 5. 失败处理

如果任何检查项失败：

1. **列出所有失败项**

2. **提供具体修复建议**

3. **引用对应规范章节**

4. **修复后必须重新运行 `/a2-check`**

5. **不允许跳过直接进入 A3**

---

## 6. 规范更新同步

### 6.1 变更检测

当 `docs/design/` 目录下的模块设计文档发生变更时：

1. **自动检测**: Claude 启动时检查规范文件 hash

2. **影响分析**: 识别受影响的 Task

3. **通知机制**: 提示相关 Task 重新执行 A2 检查

### 6.2 同步检查命令

```bash
# 检查规范文件是否有更新
python -c "from spec_sync import check_updates; check_updates()"

# 列出受影响的 Task
python -c "from spec_sync import list_affected_tasks; list_affected_tasks()"
```

---

## 7. 与其他 Gate 的关系

| Gate | 检查重点 | 前置条件 |
| ------ | ---------- | ---------- |
| **A2 Check** | 规范符合性 | design.md 已完成 |
| **A4 Check** | 零容忍 + 三维一致性 | tasks.md 已完成 |
| **A6 Check** | 完整质量验证 | 代码 + 测试已完成 |

**执行顺序**: A2 Check → A3 Atomize → A4 Check → A5 Automate → A6 Check

---

**相关命令**:

- `/a2-check` - 执行 A2 设计规范检查

- `/a4-check` - 执行 A4 零容忍门禁

- `/a6-check` - 执行 A6 完整检查

- `/doc-check` - 执行文档一致性检查
