# EmotionQuant Spiral→Task 工作流（个人版）

**版本**: v5.0.0  
**最后更新**: 2026-02-07  
**用途**: 指导“每圈怎么拆任务、怎么收口”

---

## 1. 对象定义

- Spiral：一圈交付周期（默认 7 天）
- CP（Capability Pack）：能力包（兼容旧文件名 `ROADMAP-PHASE-*`）
- Task：1 天内可完成的最小闭环单元

---

## 2. 规划步骤（先规划，再实现）

1. 选定 1 个本圈主目标。
2. 选择 1-3 个 CP Slice。
3. 生成 Task 列表（每个 Task 不超过 1 天）。
4. 为每个 Task 填写 `TASK-TEMPLATE.md`。
5. 预先定义本圈闭环证据：`run/test/artifact/review/sync`。

---

## 3. 任务拆分规则

1. 一个 Task 只对应一个最小问题。
2. 任何 Task 需要跨模块时，必须先明确输入输出契约。
3. 预计超过 1 天的 Task 必须拆分，禁止“超大 Task”。

---

## 4. 分支策略

- 分支命名：`feature/spiral-s{N}-{topic}`
- 合并节奏：每圈至少合并一次到 `develop`
- `main/master` 只用于里程碑发布

---

## 5. 每圈最小同步（降负担）

每圈收口强制更新：

1. `Governance/specs/spiral-s{N}/final.md`
2. `Governance/record/development-status.md`
3. `Governance/record/debts.md`
4. `Governance/record/reusable-assets.md`
5. `Governance/ROADMAP/ROADMAP-OVERVIEW.md`（更新圈状态）

CP 文档仅在契约变化时更新，不要求每圈都改。

---

## 6. Specs 目录约定

- 推荐新目录：`Governance/specs/spiral-s{N}/`
- 历史目录：`Governance/specs/phase-*`（保留，不再作为新圈命名）
- 新圈开始时先创建 `requirements.md`, `review.md`, `final.md`

---
## 7. 退出条件（圈级）

以下任一未满足，本圈不能完成：

- 无可运行命令
- 无自动化测试
- 无产物文件
- 无复盘记录
- 无同步记录

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|---|---|---|
| v5.0.0 | 2026-02-07 | 重写为个人版 Spiral→Task；引入“最小同步”策略 |
| v4.0.0 | 2026-02-07 | Spiral 迁移初版 |
