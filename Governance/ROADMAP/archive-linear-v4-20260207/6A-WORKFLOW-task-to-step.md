---
inclusion: always
---

# EmotionQuant Task→Step 工作流（6A）

**版本**: v3.1.3
**最后更新**: 2026-02-05
**用途**: 定义 Task 级别 6A 工作流的执行顺序、产物和 Gate 要求（Task → Step）
**适用范围**: 所有 Task（`Governance/specs/phase-XX-task-Y/`）必须遵守

---

## 文档对齐声明

> 本工作流与以下文档保持一致：
> - 系统总览：`docs/system-overview.md`
> - 模块索引：`docs/module-index.md`
> - 核心原则：`Governance/steering/CORE-PRINCIPLES.md`
> - 系统铁律：`Governance/steering/系统铁律.md`

## 1. 6A 工作流总览

### 1.1 阶段定义

| 阶段 | 名称 | 核心问题 | 产物 |
|------|------|----------|------|
| **A1** | Align 对齐 | 做什么？为什么？ | `requirements.md` |
| **A2** | Architect 架构 | 怎么设计？ | `design.md` |
| **A3** | Atomize 原子化 | 怎么拆分？ | `tasks.md` |
| **A4** | Approve 审批 | 设计可行吗？ | `approve.md` |
| **A5** | Automate 实现 | 怎么做？ | 代码 + 测试 + `review.md` |
| **A6** | Assess 评估 | 做完了吗？ | `final.md` |

### 1.2 任务分级（重要）

> **核心原则**：规范服务于质量，而非形式。对于个人项目，采用分级执行策略。

| 类型 | 判断标准 | 流程 | 产物 |
|------|----------|------|------|
| **重型任务** | 预估工时 > 8 小时 **或** 核心算法（MSS/IRS/PAS/Integration） | 完整 6A | 6 个文档 |
| **轻型任务** | 预估工时 ≤ 8 小时 **且** 非核心算法 | A1 + A5 + A6 | 3 个文档 |

**轻型任务简化流程**：

```text
A1 Align → A5 Automate → A6 Assess
   │            │            │
   ▼            ▼            ▼
[需求+分支]  [TDD实现]    [验证+合并]
```

**轻型任务产物**：
- `requirements.md`（简化版，含设计要点）
- `review.md`（实现记录）
- `final.md`（总结）

**典型轻型任务示例**：
- Bug 修复
- 工具函数添加
- 配置调整
- 文档补充
- 小功能增强

### 1.3 强制规则

- **分级执行**：根据 1.2 判断任务类型，选择对应流程
- **分支隔离**：A1 完成分支准备，禁止直接在 main/master 上开发
- **自检批准**：个人项目可自检确认（在文档中标注 `self_approved: true`）
- **产物齐全**：重型任务 6 个文档，轻型任务 3 个文档

### 1.4 时序图

**重型任务（完整 6A）**：

```text
A1 Align ──► A2 Architect ──► A3 Atomize
   │              │               │
   ▼              ▼               ▼
[分支准备+自检]  [三维设计]      [Step拆分]
                                  │
                  A4 Approve ◄────┘
                       │
                       ▼
                  [自检确认]
                       │
           A5 Automate ◄┘
                │
                ▼
           [TDD实现]
                │
           A6 Assess ◄┘
                │
                ▼
           [最终验证+合并远端]
```

**轻型任务（简化 3A）**：

```text
A1 Align ──────────────► A5 Automate ──────► A6 Assess
   │                          │                  │
   ▼                          ▼                  ▼
[需求+分支+设计要点]       [TDD实现]         [验证+合并]
```

### 1.4 分支管理原则

| 原则 | 说明 | 命令 |
|------|------|------|
| **禁止直接在main/master开发** | 所有开发必须在feature分支进行 | `git checkout -b feature/phase-XX-task-Y` |
| **A1分支准备** | 从远端develop拉取最新测试通过的代码并创建feature分支 | `git checkout -b feature/phase-XX-task-Y` |
| **A6合并前全测** | 确保所有测试通过后再合并 | `pytest tests/` |
| **develop分支策略** | 每个Task完成后合并到develop | `git merge --no-ff feature/xxx` |
| **main/master分支策略** | Phase完成后才合并到main/master | 仅里程碑 |

### 1.5 分支策略说明

**develop vs main/master 合并时机**：

| 分支 | 用途 | 合并时机 | 合并来源 |
|------|------|----------|----------|
| **develop** | 开发主分支 | 每个Task（spec）完成A6后 | feature分支 |
| **main/master** | 生产发布分支 | Phase完成后 | develop分支 |

**关键原则**：

- ✅ **A6阶段**：feature分支 → **develop** 分支（每个spec完成后）
- ✅ **Phase里程碑**：develop → **main/master**（Phase完成后）
- ❌ **禁止**：feature分支直接合并到main/master

**示例**：
```text
feature/phase-01-task-1 → develop    # Task 1完成，合并到develop
feature/phase-01-task-2 → develop    # Task 2完成，合并到develop
feature/phase-01-task-3 → develop    # Task 3完成，合并到develop
feature/phase-01-task-4 → develop    # Task 4完成，合并到develop
develop → main/master                # Phase 01完成，里程碑发布
```

**为什么需要两层合并？**

- **develop分支**：保持开发进度可见，每个spec完成后即可集成
- **main/master分支**：保持生产稳定，只有完整Phase经过充分验证后才合并

---

## 2. A1 Align（对齐）

### 2.1 目标

**目标:** 需求澄清 → requirements.md → 分支准备

### 2.2 分支准备

按以下步骤完成分支准备：

1. **切换到develop分支**

   ```bash
   git checkout develop
   ```

2. **拉取远端最新代码**（确保是经过全测试的干净版本）

   ```bash
   git pull origin develop
   ```

3. **确认测试通过**（验证基线健康度）

   ```bash
   pytest tests/ -v
   ```

4. **创建feature分支**

   ```bash
   git checkout -b feature/phase-XX-task-Y-description
   ```

### 2.3 执行步骤

按以下步骤完成需求对齐：

1. **读取项目记录（必须）**：
   - `Governance/record/development-status.md` — 了解当前进度
   - `Governance/record/reusable-assets.md` — 识别可继承资产
   - `Governance/record/debts.md` — 确认未清偿债务
- **在 `requirements.md` 写入 `## 项目记录快照`**：记录当前Phase/Task状态、拟复用资产ID清单、相关债务ID与处理决策（阻塞/纳入本Task清偿/登记计划）。

2. 读取路线图中的 Phase/Task 定义
3. 读取 Task 规范（`Governance/ROADMAP/ROADMAP-PHASE-*.md` 中对应章节）
4. 读取设计基准文档（`docs/design/`）
5. **标注继承资产**：列出本 Task 将复用的 S/A/B 级资产
6. **确认债务状态**：检查是否有 P0/P1 债务阻塞当前 Task
7. 提取功能需求（P0/P1/P2 优先级）
8. 识别约束条件（零容忍规则）
9. 标注不确定性（P0 级问题）
10. **等待用户批准或自检确认**

### 2.4 产物

```text
Governance/specs/phase-XX-task-Y/requirements.md
```

### 2.5 完成标准

- [ ] 已从远端拉取最新develop代码
- [ ] 基线测试全部通过
- [ ] feature分支已创建
- [ ] 当前在feature分支上（`git branch`确认）
- [ ] **已读取 Governance/record/ 三个文件**
- [ ] **requirements.md 已包含 `## 项目记录快照`**
- [ ] **已标注继承资产清单**
- [ ] **无 P0/P1 债务阻塞**（或已计划解决）
- [ ] 功能需求清单完整
- [ ] 约束条件明确
- [ ] P0 问题已暴露
- [ ] 用户已批准或 `self_approved: true`

### 2.6 常见错误

| 错误 | 症状 | 修正 |
|------|------|------|
| 在旧develop上创建分支 | 未执行`git pull` | 删除分支，重新从最新develop创建 |
| 测试失败的基线 | 拉取后测试不通过 | 不要在此基线上开发，等待develop修复 |
| 分支命名不规范 | 难以追溯 | 使用标准命名格式 |

---

## 3. A2 Architect（架构）

### 3.1 目标

**目标:** 需求 → 设计方案 → 三维一致 → 规范符合

### 3.2 设计基准文档

| 文档 | 位置 | 用途 |
|------|------|------|
| 数据模型 | `docs/design/**/**-data-models.md` | 字段定义 |
| API 参考 | `docs/design/**/**-api.md` | 接口契约 |
| 信息流 | `docs/design/**/**-information-flow.md` | 数据流向 |
| 模块级规范 | `docs/design/core-algorithms/*/` | 算法细节 |
| GUI 规范 | `docs/design/gui/` | 界面/权限 |
| 回测规范 | `docs/design/backtest/` | 回测逻辑 |
| 交易规范 | `docs/design/trading/` | 风控/下单 |

### 3.3 A2 阶段强制规范检查

> **Claude 工具集成**: 在 A2 阶段必须执行 `/a2-check` 命令验证规范符合性

#### 3.3.1 规范加载

```bash
# 加载三维规范（Claude 自动执行）
/a2-check --load-specs
```

#### 3.3.2 规范版本记录

在 design.md 中**必须**包含以下规范引用表：

```markdown
## 规范引用

| 规范文件 | 版本 | 引用章节 | 最后更新 |
|----------|------|----------|----------|
| {module}-data-models.md | v2.0 | §3.2, §4.1 | 2026-01-20 |
| {module}-api.md | v2.0 | §2.1 | 2026-01-20 |
| {module}-information-flow.md | v2.0 | §3.1 | 2026-01-20 |
```

#### 3.3.3 三维一致性检查

| 检查项 | 说明 | 检查方法 |
|--------|------|----------|
| 数据模型 ↔ API | 字段定义与接口参数一致 | `/a2-check --validate-models` |
| API ↔ 信息流 | 接口输入输出与数据流向一致 | `/a2-check --validate-apis` |
| 信息流 ↔ 数据模型 | 数据流向与存储结构一致 | `/a2-check --validate-flows` |

### 3.4 执行步骤

按以下步骤完成架构设计：

1. **加载适用规范** (`/a2-check --load-specs`)
2. **分析继承资产** vs 新增资产
3. **记录复用资产**（不设硬性比例）
4. **编写技术设计方案**
5. **记录规范版本引用**
6. **执行规范检查** (`/a2-check`)
7. **修复检查失败项**
8. **自查三维一致性**

### 3.5 产物

```text
Governance/specs/phase-XX-task-Y/design.md
```

**design.md 必须包含**：

- [ ] 规范引用表（含版本号）
- [ ] 三维设计完整
- [ ] 复用资产已标注
- [ ] 模块级规范符合性声明

### 3.6 完成标准

- [ ] `/a2-check` 检查通过
- [ ] 规范引用表完整（含版本号）
- [ ] 三维设计完整且一致
- [ ] 复用资产已标注
- [ ] 不违反零容忍规则
- [ ] 可进入 A3 阶段

---

## 4. A3 Atomize（原子化）

### 4.1 目标

**目标:** 设计方案 → Step 列表 → 依赖清晰

### 4.2 执行步骤

按以下步骤完成拆分：

1. 根据 A2 设计拆分 Step
2. 每个 Step 应可独立实现（≤ 4 小时）
3. 标注 Step 依赖关系
4. 识别高风险 Step
5. 估算工时

### 4.3 产物

```text
Governance/specs/phase-XX-task-Y/tasks.md
```

### 4.4 完成标准

- [ ] Step 粒度合理（≤ 4 小时/Step）
- [ ] 依赖关系清晰（无循环）
- [ ] 高风险 Step 已标注
- [ ] 工时估算合理

---

## 5. A4 Approve（审批）

### 5.1 目标

**目标:** Step 计划 → 质量门控（Gate）→ 用户批准/自检确认

### 5.2 质量门控（Gate）检查项

**门控分级**：

| 门控类型 | 检查项 | 处理 |
|----------|--------|------|
| **零容忍** | 路径硬编码、技术指标、三维不一致 | 必须阻断 |
| **警告** | TODO/HACK/FIXME | 合并前清理 |
| **分级** | TDD覆盖率 | 按模块类型要求 |
| **已简化** | 复用率 | 显式记录即可 |

**TDD覆盖率分级**：

| 模块类型 | 覆盖率要求 |
|----------|------------|
| 核心算法（MSS/IRS/PAS/Integration） | ≥ 80% |
| 数据层/回测/交易 | ≥ 70% |
| GUI | ≥ 50% |
| 工具类 | ≥ 60% |

**TODO/HACK/FIXME 规则**：

| 阶段 | 处理 |
|------|------|
| 开发中 | ✅ 允许使用 |
| feature 分支 | ✅ 允许存在 |
| 合并到 develop | ❌ 必须清理或登记债务 |

### 5.3 执行步骤

按以下步骤完成审批：

1. 运行质量门控（Gate）检查（手动或脚本）
2. 零容忍问题**必须修复**
3. 可暂缓问题登记技术债
4. **等待用户批准或自检确认**

### 5.4 产物

```text
Governance/specs/phase-XX-task-Y/approve.md
```

### 5.5 完成标准

- [ ] 所有零容忍质量门控通过
- [ ] 可暂缓问题已登记
- [ ] 用户已批准或 `self_approved: true`

---

## 6. A5 Automate（实现）

### 6.1 目标

**目标:** 任务执行 → TDD 实现 → review.md

### 6.2 TDD 循环

```text
红灯（写测试）→ 绿灯（写实现）→ 重构（优化代码）
```

### 6.3 执行步骤

按以下步骤执行实现：

1. **先写测试**（红灯）
2. **再写实现**（绿灯）
3. **最后重构**（保持测试通过）
4. 周期性检查：路径硬编码、代码风格
5. 生成 review.md

### 6.4 代码质量

```bash
# 格式化
black src/ tests/

# 检查
flake8 src/ tests/

# 测试
pytest tests/ -v --cov=src --cov-report=term-missing
```

### 6.5 产物

- 实现代码（`src/`）
- 测试代码（`tests/`）
- `review.md`（评审记录）

### 6.6 完成标准

- [ ] 所有 Step 实现完成
- [ ] 测试覆盖率达到分级要求
- [ ] 全量测试通过（`pytest tests/`）
- [ ] 无路径硬编码
- [ ] review.md 已生成

---

## 7. A6 Assess（评估）

### 7.1 目标

**目标:** 完成情况 → 质量评估 → final.md + 合并

### 7.2 执行步骤

按以下步骤完成评估与收口：

1. 运行完整质量门控（Gate）检查
2. 确认全量测试通过
3. **更新项目记录（必须）**：
   - `development-status.md` — 更新当前 Phase/Task 状态
   - `reusable-assets.md` — 登记新增 S/A/B 级资产（复用率可选）
   - `debts.md` — 登记新增债务，更新已解决债务状态
   - **在 `final.md` 写入 `## 项目记录更新`**：摘要本次对三份 record 的更新点（进度/新增资产/债务清偿）。
4. **验证债务清零条件**：
   - P0/P1 债务必须在当前 Task 解决
   - P2/P3 债务可延后但必须登记计划解决时间
5. 记录经验教训
6. Git 提交并推送
7. 合并到 develop

### 7.3 产物

```text
Governance/specs/phase-XX-task-Y/final.md
```

### 7.4 final.md 内容

| 章节 | 内容 |
|------|------|
| 1. 任务概述 | 目标、实际工时 |
| 2. 完成情况 | 功能状态、质量指标 |
| 3. 经验教训 | 做得好的、可改进的 |
| 4. 可复用资产 | 代码、模式、工具 |
| 5. 文档清单 | 6A 文档完整性确认 |

### 7.5 完成标准

- [ ] 全量测试通过
- [ ] 所有质量门控检查通过
- [ ] final.md 已生成
- [ ] Git 已提交并推送
- [ ] feature分支已合并到develop
- [ ] develop已推送到远端

---

### 7.6 合并步骤

1. **确认所有测试通过**

   ```bash
   pytest tests/ -v --cov=src --cov-report=term-missing
   ```

2. **确认在feature分支**

   ```bash
   git branch  # 应显示 * feature/phase-XX-task-Y
   ```

3. **提交所有更改**

   ```bash
   git add .
   git commit -m "[Phase-XX][Task-Y] 完成任务描述"
   ```

4. **推送feature分支到远端**

   ```bash
   git push -u origin feature/phase-XX-task-Y
   ```

5. **切换到develop分支**

   ```bash
   git checkout develop
   ```

6. **拉取最新develop**（可能有其他人的更新）

   ```bash
   git pull origin develop
   ```

7. **合并feature分支**（使用merge --no-ff保留历史）

   ```bash
   git merge --no-ff feature/phase-XX-task-Y -m "Merge: [Phase-XX][Task-Y] 完成任务描述"
   ```

8. **推送合并结果到远端**

   ```bash
   git push origin develop
   ```

9. **可选：删除feature分支**（合并成功后）

   ```bash
   git branch -d feature/phase-XX-task-Y
   git push origin --delete feature/phase-XX-task-Y
   ```

### 7.7 何时合并到main/master？

**develop → main/master 合并条件**：

当满足以下**Phase里程碑**条件时，才将develop合并到main/master：

| 里程碑类型 | 示例 | 说明 |
|------------|------|------|
| **M1: 数据基础就绪** | Phase 01 完成 | L1-L4数据架构就绪 |
| **M2: 三维分析就绪** | Phase 02-04 完成 | MSS+IRS+PAS独立运行 |
| **M3: 信号生成就绪** | Phase 05 完成 | 三三制集成完成 |
| **M4: 策略验证就绪** | Phase 06-07 完成 | 回测+风控就绪 |
| **M5: 系统上线就绪** | Phase 08-09 完成 | GUI+报告就绪 |

**合并到main/master的决策流程**：

1. Phase的4个Task全部完成
2. 组成的功能经过充分测试
3. 文档完整且同步
4. 用户/团队评审通过
5. 创建里程碑标记（如tag）

**命令示例**：
```bash
# 仅在Phase完成时执行
git checkout main
git pull origin main
git merge --no-ff develop -m "Release: Phase 01 数据层就绪"
git push origin main
git tag -a M1 -m "M1: 数据基础就绪"
git push origin M1
```

### 7.8 冲突处理

如果第7步出现合并冲突：

```bash
# 1. 查看冲突文件
git status

# 2. 手动解决冲突（编辑文件，删除<<<<<<< ======= ======= >>>>>>>标记）

# 3. 标记冲突已解决
git add <conflicted-files>

# 4. 完成合并
git commit

# 5. 再次运行测试确保一切正常
pytest tests/ -v
```

### 7.9 替代方案：Pull Request

对于团队协作，推荐使用PR流程：

```bash
# 步骤1-4同上（推送feature分支）

# 然后在GitHub/GitLab上创建Pull Request
# 等待代码审查通过后再合并
```

### 7.10 常见错误

| 错误 | 症状 | 修正 |
|------|------|------|
| 测试失败就合并 | 合并后develop测试不通过 | 不要合并，先修复测试 |
| 合并冲突未解决 | git status显示冲突状态 | 手动解决冲突后重新提交 |
| 忘记推送到远端 | 本地有远端没有 | 执行git push origin develop |
| 直接在main/master上修改 | main/master分支不干净 | 回退到feature分支完成 |
| feature直接合并到main/master | 违反分支策略 | 必须先合并到develop |

---

## 8. 快速参考

### 8.1 6A 检查清单

```text
□ A1: 需求理解 → 用户批准/自检确认 → requirements.md
□ A2: 三维设计 → 一致性自查 → design.md
□ A3: Step 拆分 → 依赖分析 → tasks.md
□ A4: 质量门控（Gate）→ 用户批准/自检确认 → approve.md
□ A5: TDD 实现 → 周期检查 → 代码 + review.md
□ A6: 最终评估 → 文档同步 → final.md + 合并到develop
```

### 8.2 Slash Commands

| 命令 | 用途 | 阶段 |
|------|------|------|
| `/phase-start` | 新会话上下文加载 | 会话开始 |
| `/a2-check` | A2 规范一致性检查 | A2 |
| `/a4-check` | A4 零容忍门禁 | A4 |
| `/tdd` | TDD 原则提醒 | A5 |
| `/a6-check` | Task 收口验证 | A6 |
| `/6a-status` | 查看当前进度 | 任意 |

### 8.3 常见错误

| 错误 | 症状 | 修正 |
|------|------|------|
| 跳过 A4 | 未经审批直接实现 | 回退到 A4 |
| 三维不一致 | 数据模型与 API 不匹配 | 修复差异 |
| 硬编码路径 | 代码中存在绝对路径 | 改为 Config.from_env() |
| 测试不足 | 覆盖率未达分级要求 | 补充测试 |

---

## 9. 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-02-04 | v3.1.2 | 文档对齐声明与版本更新 |
| 2026-02-03 | v3.1.1 | **规则表述对齐**: 自检确认、复用率可选、覆盖率分级文本统一 |
| 2026-02-03 | v3.1.0 | **分级执行优化**: 任务分级、TDD分级、TODO规则调整、复用率简化 |
| 2026-02-02 | v3.0.0 | **术语统一**: Phase→Task→Step，消除层级歧义 |
| 2026-02-02 | v2.3.1 | **记录写入规范**: requirements/final 明确要求包含 record 快照/更新小节 |
| 2026-02-02 | v2.3.0 | **项目记录集成**: A1强制读取record/，A6强制更新，债务清零原则 |
| 2026-02-02 | v2.2.0 | **Phase-Task对齐**: 重构为Phase-XX-Task-Y结构，对齐ROADMAP里程碑，修复编码问题 |
| 2026-01-26 | v2.0 | **A2 规范检查点**: 新增 `/a2-check` 强制检查点，规范版本记录要求 |
| 2026-01-23 | v1.5 | **合并A0/A7**：分支准备并入A1，合并流程并入A6，流程回归6阶段 |
| 2026-01-15 | v1.4 | **明确分支策略**：区分develop和main/master的合并时机 |
| 2026-01-15 | v1.3 | **新增Git分支管理**：补充分支准备与合并流程，禁止直接在master上开发 |
| 2025-12-23 | v1.1 | A6 阶段添加资产登记表和技术债表引用 |
| 2025-12-22 | v1.0 | 完全重构：精简流程、去除不存在的引用、对齐实际项目 |

---

**权威来源**：

- `Governance/ROADMAP/ROADMAP-OVERVIEW.md` - Phase 总览与里程碑定义
- `Governance/ROADMAP/ROADMAP-PHASE-*.md` - 各 Phase 详细规划（含 Task 规范）
- `Governance/ROADMAP/TASK-TEMPLATE.md` - Task 规范模板
- `docs/design/` - 四位一体设计文档
- `Governance/steering/CORE-PRINCIPLES.md` - 零容忍规则
- `Governance/steering/workflow/6A-WORKFLOW-phase-to-task.md` - Phase→Task 工作流
- `Governance/record/reusable-assets.md` - 可复用资产登记表
- `Governance/record/debts.md` - 技术债登记表
