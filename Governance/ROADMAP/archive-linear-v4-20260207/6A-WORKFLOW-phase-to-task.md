---
inclusion: always
---

# EmotionQuant Phase→Task 工作流（6A）

**版本**: v3.1.3
**最后更新**: 2026-02-05
**用途**: 定义 Phase 级别任务分解的标准流程（Phase → Task）
**适用范围**: 所有 Phase 规划必须遵守，并与 Task→Step 工作流保持一致

---

## 文档对齐声明

> 本工作流与以下文档保持一致：
> - 系统总览：`docs/system-overview.md`
> - 模块索引：`docs/module-index.md`
> - 核心原则：`Governance/steering/CORE-PRINCIPLES.md`
> - 系统铁律：`Governance/steering/系统铁律.md`

## 1. 核心概念

### 1.1 三层结构

```text
Phase（阶段）→ Task（开发任务）→ Step（执行步骤）
```

| 层级 | 示例 | 粒度 | 文档位置 |
|------|------|------|----------|
| **Phase** | Phase 01: Data Layer | 4周 | `Governance/ROADMAP/ROADMAP-PHASE-*.md` |
| **Task** | Task 2: L1 数据采集 | 3-5天 | `Governance/specs/phase-XX-task-Y/` |
| **Step** | Step-2.1: 实现 fetch_daily | 1-4小时 | `Governance/specs/phase-XX-task-Y/tasks.md` |

### 1.2 Phase-Task 映射

| Phase | 名称 | Task 1 | Task 2 | Task 3 | Task 4 |
|-------|------|--------|--------|--------|--------|
| 01 | Data Layer | 架构设计 | L1采集 | L2计算 | 集成测试 |
| 02 | MSS | 算法设计 | 温度/周期 | 趋势/联动 | 验证优化 |
| 03 | IRS | 算法设计 | 六因子 | 轮动判定 | 验证优化 |
| 04 | PAS | 算法设计 | 核心因子 | 评分系统 | 验证优化 |
| 05 | Integration | 集成设计 | 等权融合 | 推荐系统 | 端到端测试 |
| 06 | Backtest | 引擎设计 | 策略执行 | 绩效计算 | 优化验证 |
| 07 | Trading | 风控设计 | 订单管理 | 交易执行 | 压力测试 |
| 08 | GUI | 界面设计 | 仪表盘 | 交互功能 | 性能优化 |
| 09 | Analysis | 报告设计 | 指标计算 | 报告生成 | 自动化验证 |

> **详细 Task 规范**: 见各 Phase 文档的 Task 章节，格式遵循 `Governance/ROADMAP/TASK-TEMPLATE.md`

### 1.3 五类文档

| 类型 | 位置 | 角色 | 操作时机 |
|------|------|------|----------|
| **设计基准** | `docs/design/` | 定义"应该是什么样" | 只读（变更需评审） |
| **Task规范** | `Governance/ROADMAP/ROADMAP-PHASE-*.md` | 定义Task的输入/输出/验收 | 规划时更新 |
| **项目记录** | `Governance/record/` | 记录进度/资产/债务 | **A1读取，A6更新** |
| **实现记录** | `Governance/specs/phase-XX-task-Y/` | 记录"实际怎么做" | 实现时更新 |
| **治理规范** | `Governance/steering/` | 定义"怎么做" | 版本化管理 |

---

## 2. Git 分支管理（Task 级别）

### 2.1 Task 开始：创建干净分支

目标：干净基线 → feature 分支准备

每个 Task 开始时，必须执行以下步骤：

```bash
# 1. 切换到 develop 分支
git checkout develop

# 2. 拉取远端最新代码（确保是经过全测试的干净版本）
git pull origin develop

# 3. 验证基线健康度（确认测试通过）
pytest tests/ -v

# 4. 创建 feature 分支（使用标准命名）
git checkout -b feature/phase-XX-task-Y-description

# 示例：
# git checkout -b feature/phase-01-task-2-l1-collection
# git checkout -b feature/phase-02-task-1-mss-design
```

### 2.2 Task 结束：合并到 develop

目标：全测通过 → 合并到 develop

每个 Task 结束时（A6 Assess 之后），必须执行以下步骤：

```bash
# 1. 确认所有测试通过（含覆盖率）
pytest tests/ -v --cov=src --cov-report=term-missing

# 2. 确认在 feature 分支
git branch  # 应显示 * feature/phase-XX-task-Y

# 3. 提交所有更改
git add .
git commit -m "[Phase-XX][Task-Y] 完成：简短描述"

# 4. 推送 feature 分支到远端
git push -u origin feature/phase-XX-task-Y

# 5. 切换到 develop 分支
git checkout develop

# 6. 拉取最新 develop（可能有其他人的更新）
git pull origin develop

# 7. 合并 feature 分支（使用 --no-ff 保留历史）
git merge --no-ff feature/phase-XX-task-Y -m "Merge: [Phase-XX][Task-Y] 完成：简短描述"

# 8. 推送合并结果到远端
git push origin develop

# 9. 可选：删除 feature 分支
git branch -d feature/phase-XX-task-Y
git push origin --delete feature/phase-XX-task-Y
```

### 2.3 分支命名规范

```text
feature/phase-XX-task-Y-description

示例：
feature/phase-01-task-2-l1-collection     # Phase 01 Task 2: L1数据采集
feature/phase-02-task-1-mss-design        # Phase 02 Task 1: MSS算法设计
feature/phase-05-task-3-recommendation    # Phase 05 Task 3: 推荐系统
```

### 2.4 分支策略说明

**develop vs main/master 合并时机**：

| 分支 | 用途 | 合并时机 | 合并来源 |
|------|------|----------|----------|
| **develop** | 开发主分支 | 每个Task完成后 | feature分支 |
| **main/master** | 生产发布分支 | Phase完成后（里程碑） | develop分支 |

**关键原则**：

- ✅ **Task结束**：feature分支 → **develop** 分支
- ✅ **Phase里程碑**：develop → **main/master**
- ❌ **禁止**：feature分支直接合并到main/master

**示例**：
```text
feature/phase-01-task-1 → develop    # Task 1完成
feature/phase-01-task-2 → develop    # Task 2完成
feature/phase-01-task-3 → develop    # Task 3完成
feature/phase-01-task-4 → develop    # Task 4完成
develop → main/master                # Phase 01完成，里程碑M1
```

### 2.5 强制规则

| 规则 | 说明 | 后果 |
|------|------|------|
| **禁止直接在main/master开发** | 所有开发必须在feature分支进行 | pre-commit hook拒绝 |
| **分支准备必须执行** | Task开始前必须拉取develop干净基线并创建feature分支 | 基线污染风险 |
| **A6合并必须执行** | Task结束前必须全测并合并到develop | develop不稳定 |
| **保持develop可集成** | develop分支应始终可集成 | 阻塞其他开发 |
| **Phase完成才合并到main/master** | 4个Task全部完成后才合并 | main/master保持稳定 |
| **Task 必须遵循 6A** | 每个 Task 必须完整走完 A1-A6 | 合规性不通过 |

---

## 3. Task 分解流程

### 3.1 流程概览

目标：Phase规划 → Task定义 → Step列表

```text
Phase ROADMAP → Task 规范（模板） → Step 列表 → 6A 执行
```

**Task 规范来源**：`Governance/ROADMAP/ROADMAP-PHASE-*.md` 中的 Task 章节

**Task 规范模板**：`Governance/ROADMAP/TASK-TEMPLATE.md`

### 3.2 Task 规范内容（必须包含）

根据 TASK-TEMPLATE，每个 Task 必须定义：

| 内容 | 说明 |
|------|------|
| **目标** | 一句话描述本Task核心目标 |
| **输入依赖** | 依赖项、来源、就绪条件、缺失处理 |
| **输出交付** | 交付物、类型、验收标准、存储位置 |
| **成功标准** | 量化指标、验证方法 |
| **错误处理** | 错误场景、处理策略、升级条件 |
| **验收检查** | 检查清单 |

### 3.3 Task 到 Step 映射示例

以 Phase 01 Task 2 为例：

| Step | 名称 | 预估工时 |
|------|------|----------|
| Step 2.1 | TuShareFetcher 实现 | 4小时 |
| Step 2.2 | 数据采集脚本 | 4小时 |
| Step 2.3 | 数据完整性验证 | 2小时 |
| Step 2.4 | 错误处理与重试 | 2小时 |

---

## 4. 项目记录与复用资产

> **强制规则**：每个 Task 必须在 A1 读取、在 A6 更新项目记录

### 4.1 项目记录文件

| 文件 | 用途 | A1 操作 | A6 操作 |
|------|------|---------|----------|
| `development-status.md` | 开发进度 | 了解当前状态 | 更新Phase/Task状态 |
| `reusable-assets.md` | 可复用资产 | 识别可继承资产 | 登记新增资产（复用率可选） |
| `debts.md` | 技术债务 | 确认阻塞性债务 | 登记新增债务，更新已解决债务 |

### 4.2 债务清零原则

| 债务等级 | 解决时限 | 说明 |
|----------|----------|------|
| **P0** | 当前 Step | 阻塞性，必须立即解决 |
| **P1** | 当前 Task | 影响核心功能，本Task解决 |
| **P2** | 2-4 Task | 可延后，必须登记计划 |
| **P3** | 有空时 | 优化类，不阻塞前进 |

> **原则**：P0/P1 债务未清零，不得合并到 develop

### 4.3 资产分类

目标：复用资产 → 统一分类

| 资产类型 | 等级 | 示例 | 说明 |
|----------|------|------|------|
| **核心基础设施** | S级 | Config、BaseRepository | 所有 Task 通用 |
| **模块组件** | A级 | DailyRepository、MSS算法 | 特定模块复用 |
| **局部工具** | B级 | MarketSnapshot模型 | 单个 Task 局部复用 |

### 4.4 复用率计算（可选）

```text
复用率 = 继承资产数 / (继承资产数 + 新增资产数)
```

**说明**：

- 复用率仅用于参考，不作为门控指标
- Phase 01 是第一个实现阶段，代码资产复用率 = 0%
- 数据资产和规范资产可以继承

---

## 5. Task 定义标准

### 5.1 Task 属性

目标：Task 定义 → 属性齐全

每个 Task 必须包含：

| 属性 | 说明 | 示例 |
|------|------|------|
| Task ID | Phase-Task序号 | P01-T2 |
| 名称 | 简短描述 | L1 数据采集 |
| 优先级 | P0/P1/P2 | P0（阻塞性） |
| 预估工时 | 天 | 3-5天 |
| 依赖 | 前置条件 | P01-T1 完成 |

### 5.2 Task 文档结构

```text
Governance/specs/phase-XX-task-Y/
├── requirements.md    # A1 产物：需求文档
├── design.md          # A2 产物：设计文档
├── tasks.md           # A3 产物：Step 列表
├── approve.md         # A4 产物：审批记录
├── review.md          # A5 产物：实现评审
└── final.md           # A6 产物：最终总结
```

---

## 6. 与设计文档对齐

### 6.1 设计基准文档

目标：设计基准 → Task 对齐

| 文档 | 位置 | 内容 |
|------|------|------|
| **数据模型** | `docs/design/{module}/{module}-data-models.md` | 模块数据模型定义 |
| **API 参考** | `docs/design/{module}/{module}-api.md` | 模块 API 定义 |
| **信息流** | `docs/design/{module}/{module}-information-flow.md` | 模块信息流定义 |

### 6.2 核心算法文档

| 模块 | 位置 | 内容 |
|------|------|------|
| **MSS** | `docs/design/core-algorithms/mss/` | 市场情绪评分 |
| **IRS** | `docs/design/core-algorithms/irs/` | 行业轮动评分 |
| **PAS** | `docs/design/core-algorithms/pas/` | 价格行为评分 |
| **集成** | `docs/design/core-algorithms/integration/` | 三三制集成 |

### 6.3 Phase→Task 规范继承

> **A2 阶段规范传递**: Phase 规划时必须识别涉及的规范，并在 Task A2 阶段强制引用

#### 6.3.1 规范继承链

```text
Phase ROADMAP（Task规范）
    ↓ 定义输入/输出/验收
Task A1 (requirements.md)
    ↓ 引用 Task 规范
Task A2 (design.md)
    ↓ 加载并验证规范
    ↓ 记录规范版本
    ↓ 执行 /a2-check
Task A3 (tasks.md)
    ↓ 继承 A2 规范引用
...
```

#### 6.3.2 Task 规范识别清单

在 Task 规划阶段，识别并记录涉及的规范：

```markdown
## Phase XX Task Y 规范识别

### 涉及的三维规范
- [ ] {module}-data-models.md (§3.2, §4.1)
- [ ] {module}-api.md (§2.1)
- [ ] {module}-information-flow.md (§3.1)

### 涉及的模块级规范
- [ ] MSS 算法规范（如果涉及市场情绪）
- [ ] IRS 算法规范（如果涉及行业轮动）
- [ ] PAS 算法规范（如果涉及价格行为）
- [ ] GUI 规范（如果涉及界面）
- [ ] 回测规范（如果涉及回测）
- [ ] 交易规范（如果涉及风控）
```

#### 6.3.3 A2 阶段规范检查

每个 Task 在 A2 阶段必须执行：

```bash
# Claude 自动执行
/a2-check --load-specs --validate --report
```

**A2 阶段产物要求**：

- design.md 包含规范引用表（含版本号）
- 验证通过后记录 `spec_validation_passed: true`
- 任何规范偏离必须记录并说明原因

### 6.4 三维一致性

每个 Task 必须保持三维一致：

```text
数据模型 ↔ API 接口 ↔ 信息流
```

- 数据模型变更 → 同步更新 API
- API 变更 → 同步更新信息流
- 任何变更需经过 A4 质量门控（Gate）检查
- **A2 阶段必须使用 `/a2-check` 验证一致性**

---

## 7. 质量门控（Gate）

### 7.1 门控分级

| 门控类型 | 规则 | 检查时机 | 处理 |
|----------|------|----------|------|
| **零容忍** | 路径硬编码、技术指标、三维不一致 | A4、A5、A6 | 必须阻断 |
| **警告** | TODO/HACK/FIXME | 开发中允许 | 合并前清理 |
| **分级** | TDD覆盖率 | A5、A6 | 按模块分级要求 |

### 7.2 TDD覆盖率分级

| 模块类型 | 覆盖率 |
|----------|--------|
| 核心算法（MSS/IRS/PAS/Integration） | ≥ 80% |
| 数据层/回测/交易 | ≥ 70% |
| GUI | ≥ 50% |
| 工具类 | ≥ 60% |

### 7.3 TODO/HACK/FIXME 规则

| 阶段 | 处理 |
|------|------|
| 开发中 | ✅ 允许 |
| 合并到 develop | ❌ 必须清理或登记债务 |

### 7.4 配置加载标准

```python
# ✅ 正确
from src.config.config import Config
config = Config.from_env()
duckdb_dir = config.duckdb_dir

# ❌ 禁止
db_path = "G:/EmotionQuant_data/emotionquant.db"
```

---

## 8. 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-02-04 | v3.1.2 | 文档对齐声明与版本更新 |
| 2026-02-03 | v3.1.1 | **复用率规则对齐**: 复用率改为可选记录，文档表述统一 |
| 2026-02-03 | v3.1.0 | **门控分级优化**: TDD分级、TODO规则调整、复用率简化 |
| 2026-02-02 | v3.0.0 | **术语统一**: Phase→Task→Step，消除层级歧义 |
| 2026-02-02 | v2.3.1 | **文档一致性修正**: 明确文档类型数量，修正章节编号 |
| 2026-02-02 | v2.3.0 | **项目记录集成**: A1/A6强制读写record/，债务清零原则，资产分级复用 |
| 2026-02-02 | v2.2.0 | **Phase→Task对齐**: 明确Phase/Task结构，引用TASK-TEMPLATE，修复编码问题 |
| 2026-01-26 | v2.0 | **规范继承机制**: 新增 Phase→Task 规范继承链，A2 阶段强制 `/a2-check` 检查 |
| 2026-01-23 | v1.5 | **合并A0/A7**：分支准备并入A1，合并流程并入A6，流程回归6阶段 |
| 2026-01-15 | v1.4 | **明确分支策略**：区分develop和main/master的合并时机 |
| 2026-01-15 | v1.3 | **新增Git分支管理章节** |
| 2025-12-23 | v1.1 | 添加资产登记表和技术债表引用 |
| 2025-12-22 | v1.0 | 完全重构：精简流程、对齐实际项目结构、明确复用定义 |

---

**权威来源**：

- `Governance/ROADMAP/ROADMAP-OVERVIEW.md` - Phase 总览
- `Governance/ROADMAP/ROADMAP-PHASE-*.md` - 各 Phase 详细规划（含 Task 规范）
- `Governance/ROADMAP/TASK-TEMPLATE.md` - Task 规范模板
- `docs/module-index.md` - 四位一体规范索引
- `Governance/steering/workflow/6A-WORKFLOW-task-to-step.md` - Task→Step 工作流
- `Governance/steering/CORE-PRINCIPLES.md` - 核心原则
- `Governance/record/reusable-assets.md` - 可复用资产登记表
- `Governance/record/debts.md` - 技术债登记表
