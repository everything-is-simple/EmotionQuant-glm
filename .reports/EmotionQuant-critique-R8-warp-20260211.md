# EmotionQuant 文档检查报告 — R8

**检查工具**: Warp (claude 4.6 opus max)
**检查时间**: 2026-02-11
**检查范围**: `.claude/agents/kfc/`（7 spec）+ `.claude/commands/`（7 cmd）= 14 文件
**累计轮次**: R1–R8（R1–R7 已修复 29 项）

**前置说明**: `.claude/README.md` 已声明本目录为"historical compatibility assets"，Phase-era 术语视为历史示例。本轮仅报告实际断链、内容矛盾、可能误导代理执行的问题，不逐一标注 Phase 遗留措辞。

---

## 检查范围

| # | 文件 | 结果 |
|---|------|------|
| 1 | .claude/agents/kfc/spec-requirements.md | ✅ Clean Pass |
| 2 | .claude/agents/kfc/spec-design.md | ⚠️ 见 P3-R8-03 |
| 3 | .claude/agents/kfc/spec-impl.md | ✅ Clean Pass |
| 4 | .claude/agents/kfc/spec-test.md | ✅ Clean Pass |
| 5 | .claude/agents/kfc/spec-judge.md | ✅ Clean Pass |
| 6 | .claude/agents/kfc/spec-tasks.md | ✅ Clean Pass |
| 7 | .claude/agents/kfc/spec-system-prompt-loader.md | ⚠️ 见 P2-R8-02 |
| 8 | .claude/commands/6a-status.md | ⚠️ 见 P3-R8-04 |
| 9 | .claude/commands/a2-check.md | ✅ Clean Pass（Phase 术语已被 README 免责） |
| 10 | .claude/commands/a4-check.md | ✅ Clean Pass |
| 11 | .claude/commands/a6-check.md | ✅ Clean Pass |
| 12 | .claude/commands/doc-check.md | ✅ Clean Pass |
| 13 | .claude/commands/phase-start.md | ⚠️ 见 P2-R8-01, P3-R8-05 |
| 14 | .claude/commands/tdd.md | ⚠️ 见 P3-R8-05 |

---

## 问题清单

### P2-R8-01 | phase-start.md L28–29：引用已归档的工作流文件

两个路径均不存在（已归档至 `archive-compat-v6-20260210/`）：

- **L28**: `Governance/steering/workflow/6A-WORKFLOW-task-to-step.md` → 应改为 `Governance/steering/6A-WORKFLOW.md`
- **L29**: `Governance/steering/workflow/6A-WORKFLOW-phase-to-task.md` → 建议删除或注释为已归档

---

### P2-R8-02 | spec-system-prompt-loader.md L20：引用不存在的文件

- **L20**: `.claude/system-prompts/spec-workflow-starter.md` — 该文件不存在
- 该 agent 的唯一功能就是返回此路径，因此整个 agent 当前不可用

**处理方案**: 创建该文件，或在 README 中标注此 agent 为非活动状态。

---

### P3-R8-03 | spec-design.md L145 vs L157：输出路径矛盾

- **L145**: `'.claude/specs/{feature_name}/design.md'`
- **L157**: `'Governance/specs/{feature_name}/design.md'`

两处指定了不同的输出目录，会导致代理行为不确定。

**处理方案**: 统一到一个路径（建议 `.claude/specs/`，与其他 spec agent 一致）。

---

### P3-R8-04 | 6a-status.md L22–28：6A 阶段名称与当前治理不一致

| 阶段 | 文件中写的（旧） | 当前治理口径（新） |
|------|------------------|-------------------|
| A3 | Atomize 原子化 | Act 实现 |
| A4 | Approve 审批 | Assert 验证 |
| A5 | Automate 实现 | Archive 归档 |
| A6 | Assess 评估 | Advance 推进 |

**处理方案**: 更新为当前 `Governance/steering/6A-WORKFLOW.md` 中的名称，或在文件头添加"历史口径"免责声明。

---

### P3-R8-05 | phase-start.md L63 + tdd.md L64–74："零技术指标绝对禁令"与现行铁律 #2 矛盾

- phase-start.md L63: `**零技术指标**: 禁用 MA/RSI/MACD/KDJ/BOLL`
- tdd.md L64–74: `# ❌ 严格禁止 import talib ...`

**现行口径**（WARP.md / CLAUDE.md / 系统铁律.md）: 技术指标可用于对照实验或特征工程，但不得作为独立买卖信号。"零技术指标绝对禁令"属于历史 archive 口径。

**处理方案**: 更新为"技术指标不得独立触发交易"，或添加免责注释指向现行铁律。

---

## 统计

| 等级 | 本轮 | 累计 (R1–R8) |
|------|------|--------------|
| P1 | 0 | 1 |
| P2 | 2 | 14 |
| P3 | 3 | 18 |
| **合计** | **5 项** | **34 项** |

---

## Clean Pass 确认（9 / 14 文件）

- spec-requirements.md ✅
- spec-impl.md ✅
- spec-test.md ✅
- spec-judge.md ✅
- spec-tasks.md ✅
- a2-check.md ✅
- a4-check.md ✅
- a6-check.md ✅
- doc-check.md ✅

---

## 下一轮预告

**R9** 预计范围: `docs/design/core-algorithms/` 第一批模块（mss/ + irs/ = 8 文件）
