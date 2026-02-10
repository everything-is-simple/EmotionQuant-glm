# EmotionQuant R25 深度审查报告

**审查时间**: 2026-02-09  
**审查轮次**: R25  
**审查模块**: 系统级文档全局扫描  
**审查角度**: system-overview ↔ scheduler ↔ monitoring 三者一致性 + 与模块设计对齐  

---

## 审查范围

| 文件 | 版本 | 最后更新 | 状态 |
|------|------|----------|------|
| system-overview.md | v4.1.0 | 2026-02-07 | 已审查 |
| scheduler-orchestration-design.md | v0.2 | 2026-02-08 | 已审查 |
| monitoring-alerting-design.md | v0.2 | 2026-02-08 | 已审查 |

---

## 问题汇总

| 优先级 | 数量 | 类型 |
|--------|------|------|
| P1 | 5 | Validation Layer 缺失、检查点缺失、分层描述不一致 |
| P2 | 5 | 调度窗口、阈值参数、重试策略不一致 |
| **合计** | **10** | - |

---

## P1 级问题（必须修复）

### P1-R25-01: Scheduler DAG 缺少 Validation Layer

**文件**: `scheduler-orchestration-design.md`  
**位置**: 行 13-27  

**问题描述**:
- `system-overview.md` §3（行 36）明确将 Validation Layer 列为八层之一，并标注"关键新增"
- 但 Scheduler DAG（行 15-27）完全缺少 Validation 节点：
  ```
  Data Layer → MSS/IRS/PAS → Integration → Trading → Analysis/GUI
  ```
- Validation 应位于 MSS/IRS/PAS 之后、Integration 之前

**修复建议**:
```text
Data Layer
  └─ raw_daily / raw_daily_basic / raw_limit_list / trade_calendar
        ↓
MSS / IRS / PAS
        ↓
Validation Gate（因子验证 + 权重验证）
        ↓
Integration
        ↓
Trading
        ↓
Analysis / GUI 刷新
```

**修复位置**: `scheduler-orchestration-design.md` §13 行 15-27

---

### P1-R25-02: Monitoring 监控范围缺少 Validation Layer

**文件**: `monitoring-alerting-design.md`  
**位置**: 行 14-34  

**问题描述**:
- 监控范围（行 14-18）覆盖：数据层/因子层/集成层/交易层/系统层
- **缺少 Validation 层**
- 指标表（行 26-34）未包含 Validation Gate 相关指标

**修复建议**:
监控范围补充：
```markdown
- Validation 层：Gate 决策状态（PASS/WARN/FAIL）、因子 IC 偏离、权重验证失败、stale_days 超阈值
```

指标表补充：
```markdown
| Validation Gate | `final_gate=FAIL` | 1 次即触发 | P0 |
| Validation 过期 | `stale_days > 3` | > 3 天 | P1 |
| 因子验证 | `mean_ic < 0` | 任一因子失效 | P1 |
```

**修复位置**: `monitoring-alerting-design.md` 行 14-34

---

### P1-R25-03: Overview §4.1 L2 分层描述遗漏 stock_gene_cache

**文件**: `system-overview.md`  
**位置**: 行 56  

**问题描述**:
- 行 56 写 `L2：特征与快照（market/industry snapshot）`
- 但 Data Layer Data-Models 定义了 3 个 L2 表：`market_snapshot` / `industry_snapshot` / `stock_gene_cache`
- 遗漏 `stock_gene_cache`

**修复建议**:
```markdown
- L2：特征与快照（market_snapshot / industry_snapshot / stock_gene_cache）
```

**修复位置**: `system-overview.md` 行 56

---

### P1-R25-04: Scheduler 就绪检查点缺少 validation_gate_decision

**文件**: `scheduler-orchestration-design.md`  
**位置**: 行 34-42  

**问题描述**:
- 检查点表包含 5 个节点，但缺少 `validation_gate_decision`
- Validation Info-Flow 明确写"CP-05 读取 gate + weight_plan"
- 调度器可能在 Validation Gate 未就绪时启动 Integration

**修复建议**:
补充检查点：
```markdown
| `validation_gate_decision` | `final_gate` ∈ {PASS, WARN} 且 `selected_weight_plan` 非空 | 2 分钟 |
```

**修复位置**: `scheduler-orchestration-design.md` 行 42 后

---

### P1-R25-05: Scheduler 执行约束缺少 Validation Gate 阻断规则

**文件**: `scheduler-orchestration-design.md`  
**位置**: 行 29-32  

**问题描述**:
- 行 31 写"三个子系统全部成功后才允许 Integration"
- 但 Validation Algorithm §5 规定 `final_gate=FAIL` 时阻断 CP-05
- Scheduler 缺少"Validation Gate 必须 PASS/WARN"的约束

**修复建议**:
补充约束：
```markdown
- `Data Layer` 未完成则禁止 MSS/IRS/PAS 启动
- 三个子系统全部成功后才允许 Validation Gate
- **Validation Gate 必须 PASS 或 WARN（FAIL 则阻断 Integration）**
- Integration 失败时禁止 Trading 下发
```

**修复位置**: `scheduler-orchestration-design.md` 行 29-32

---

## P2 级问题（建议修复）

### P2-R25-06: Scheduler 调度窗口缺少 Validation 执行时间

**文件**: `scheduler-orchestration-design.md`  
**位置**: 行 48-53  

**问题描述**:
- 调度窗口仅列出粗粒度时段，缺少 Validation 执行时间
- Data Layer Info-Flow 写 `17:15-17:20 Validation Gate`

**修复建议**:
盘后主计算窗口细化：
```markdown
- 盘后主计算窗口：`15:30 - 18:30`
  - `15:30 - 16:30`：Data Layer（采集 + L2 聚合）
  - `16:30 - 17:00`：MSS / IRS / PAS
  - `17:00 - 17:10`：Validation Gate
  - `17:10 - 17:30`：Integration + Trading
  - `17:30 - 18:30`：Analysis + GUI
```

**修复位置**: `scheduler-orchestration-design.md` 行 50

---

### P2-R25-07: Monitoring 集成质量阈值 "越界" 定义不明确

**文件**: `monitoring-alerting-design.md`  
**位置**: 行 31  

**问题描述**:
- 行 31 写 `集成质量 | final_score 越界数 | > 0 | P0`
- 但未定义"越界"含义（`< 0` 还是 `> 100`？或两者皆是？）

**修复建议**:
```markdown
| 集成质量 | `final_score` 越界数（< 0 或 > 100） | > 0 | P0 |
```

**修复位置**: `monitoring-alerting-design.md` 行 31

---

### P2-R25-08: Overview §6 GUI Altair 移除条件不明确

**文件**: `system-overview.md`  
**位置**: 行 76-78  

**问题描述**:
- 行 77 写 "`Altair` 不作为主线必需依赖，可转可选或移除"
- 但未明确何时移除，实现时会产生歧义

**修复建议**:
```markdown
- 主线组合：`Streamlit + Plotly`（必需）
- `Altair`：已转为可选依赖，待所有 Altair 图表完成 Plotly 迁移后移除
```

**修复位置**: `system-overview.md` 行 76-78

---

### P2-R25-09: Overview §5 回测引擎切换条件缺失

**文件**: `system-overview.md`  
**位置**: 行 62-70  

**问题描述**:
- 行 66-68 列出三种回测引擎（Qlib/本地/backtrader），但未说明切换条件
- 实现时不清楚何时用 Qlib、何时用本地回测器

**修复建议**:
补充切换条件：
```markdown
- 主选研究平台：`Qlib`（因子研究/快速验证阶段）
- 执行口径基线：本地向量化回测器（精确回测/生产决策阶段）
- 兼容适配：`backtrader`（保留为备选，不主动维护）
- 切换条件：因子研究阶段优先 Qlib，最终生产决策走本地回测器
```

**修复位置**: `system-overview.md` 行 66-68

---

### P2-R25-10: Monitoring 重试参数与 Scheduler 不一致

**文件**: `monitoring-alerting-design.md` + `scheduler-orchestration-design.md`  
**位置**: Monitoring 行 54，Scheduler 行 57  

**问题描述**:
- Monitoring 行 54：`base=30s, max_delay=10min, max_retries=5`
- Scheduler 行 57：`最多 5 次，指数退避（30s, 60s, 120s, 240s, 480s）`
- 480s = 8min ≠ 10min，参数不一致

**修复建议**:
统一为：
```markdown
base=30s, max_delay=480s（8min）, max_retries=5
```

**修复位置**: `monitoring-alerting-design.md` 行 54（改 `max_delay=8min`）

---

## 累计进度（R1-R25）

| 轮次 | 审查模块 | 发现问题 | 状态 |
|------|----------|----------|------|
| R1-R12 | 跨模块一致性 | ~120 | ✅ 已修复 |
| R13 | 核心算法逻辑 | 10 | ✅ 已修复 |
| R14 | Data Layer DDL/契约 | 10 | ✅ 已修复 |
| R15 | GUI/Backtest/Analysis 跨模块 | 10 | ✅ 已修复 |
| R16 | API/DataModel/InfoFlow 对齐 | 10 | ✅ 已修复 |
| R17 | 核心算法四位一体 | 10 | ✅ 已修复 |
| R18 | 跨模块常量/阈值/DDL 追溯 | 10 | ✅ 已修复 |
| R19 | 依赖声明/API-DDL-enum 对齐 | 10 | ✅ 已修复 |
| R20 | Backtest + Trading 四位一体 | 10 | ✅ 已修复 |
| R21 | Analysis 四位一体 | 10 | ✅ 已修复 |
| R22 | GUI 四位一体 | 10 | ✅ 已修复 |
| R23 | Data Layer 四位一体 | 10 | ✅ 已修复 |
| R24 | Validation 四位一体 | 10 | ✅ 已修复 |
| **R25** | **系统级文档全局扫描** | **10** | **✅ 已修复（复查通过）** |
| **累计** | - | **239** | - |

---

## 下一步建议

1. **R26**: 端到端集成扫描（降级路径/边界条件/枚举值全链追溯）
2. **R27**: 最终文档一致性复查（查漏补缺）

---

## 复查结论（Codex）

**复查时间**: 2026-02-09  
**结论**: R25 问题清单共 10 项，已在目标文档中全部落地，无剩余未修复项。  

对齐结果：
- `docs/system-overview.md`：P1-R25-03、P2-R25-08、P2-R25-09 已修复
- `docs/design/scheduler-orchestration-design.md`：P1-R25-01、P1-R25-04、P1-R25-05、P2-R25-06 已修复
- `docs/design/monitoring-alerting-design.md`：P1-R25-02、P2-R25-07、P2-R25-10 已修复

---

**审查人**: Claude (Warp Agent Mode)  
**报告生成时间**: 2026-02-09  
**下次审查**: R26 - 端到端集成扫描
