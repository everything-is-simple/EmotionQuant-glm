# EmotionQuant 设计文档审查报告 - R26（端到端集成扫描）

**审查日期**: 2026-02-09  
**审查人**: Claude (Sonnet 3.5)  
**审查范围**: 端到端集成一致性（降级路径、边界条件、枚举值全链追溯）  
**文档版本**: 各模块最新版本  

---

## 执行摘要

### 审查目标

R26 是第 26 轮深度审查，专注于**端到端集成一致性**：

1. **降级路径一致性**：MSS → IRS → PAS → Validation → Integration → Backtest → Trading 全链降级策略对齐
2. **边界条件处理**：缺失/越界/异常数据的跨模块处理一致性
3. **枚举值全链追溯**：MSS.cycle / IRS.rotation_status / PAS.opportunity_grade / Integration.recommendation 跨模块传递完整性
4. **依赖声明完整性**：模块间依赖关系是否覆盖降级/异常场景

### 审查方法

- 跨文档全局搜索：`降级/fallback/default/缺失/越界/边界/exception`（38 文件命中）
- 关键链路深度分析：Integration → Backtest → Trading → GUI 降级策略
- 枚举值全链追溯：MSS.cycle → Integration → Backtest 传递完整性
- 对照验证：四位一体文档（Algorithm / DataModels / API / InfoFlow）降级口径对齐

### 审查结果

**发现 10 个问题**：
- **P1 级别（中等）**：5 个（降级策略/边界处理/枚举追溯不对齐）
- **P2 级别（轻微）**：5 个（文档完整性/追溯性不足）

---

## 问题清单

### P1-R26-01: Integration Gate FAIL 降级策略与 Backtest/Trading 不一致

**文件**:  
- `integration-algorithm.md` (v3.4.6, line 110-111)  
- `backtest-algorithm.md` (v3.4.6, line 74-77)  
- `trading-algorithm.md` (v3.2.4, line 31-52)  

**问题**:  
Integration 明确规定 `final_gate=FAIL → 拒绝进入集成 + 抛出 ValidationGateError`（line 111），但：

- Backtest §3.0 数据就绪检查仅返回空列表 `if not readiness.is_ready: return []`（line 76-77），无显式 Gate FAIL 处理
- Trading §2.1 信号生成流程无 Gate 前置检查，直接读取 `integrated_recommendation`（line 36），若 Integration 已因 FAIL 阻断，Trading 如何获知？

**根因**:  
Integration 的 Gate FAIL 阻断机制在下游未传递：
- Backtest 的 `check_data_ready` 未覆盖 Gate FAIL 检测
- Trading 缺少 Gate 前置检查步骤

**建议**:  
1. Backtest §3.0 增加 Gate 检查：
   ```python
   gate = get_validation_gate_decision(signal_date)
   if gate.final_gate == "FAIL":
       log.warning(f"Gate=FAIL on {signal_date}, skip signal generation")
       return []
   ```
2. Trading §2.1 信号生成前增加类似检查
3. 统一降级策略：Gate FAIL → 下游模块跳过信号生成 + 记录日志

**影响**:  
- Gate FAIL 时 Trading 可能尝试读取空的 `integrated_recommendation`，引发空集异常
- 回测结果可能因未过滤 Gate FAIL 日而失真

---

### P1-R26-02: MSS cycle="unknown" 的下游传递与仓位建议不一致

**文件**:  
- `mss-algorithm.md` (v3.1.4, line 268-281)  
- `integration-algorithm.md` (v3.4.6, line 189-196)  
- `naming-conventions.md` (v2.0.2, line 22)  

**问题**:  
MSS §5.2 新增 `cycle="unknown"` 作为异常兜底（line 280），但：

- Integration §5.1 信号映射规则仅覆盖已知 7 周期（line 189-196），不含 `unknown` 分支
- `naming-conventions.md` §1 周期定义表未包含 `unknown` 枚举值（line 22 仅含 7 个周期）

**根因**:  
MSS 新增兜底枚举未同步到下游消费方与命名规范

**建议**:  
1. `integration-algorithm.md` §5.1 补充：
   ```python
   elif mss_cycle == "unknown":
       return "HOLD"  # 异常周期降级为观望
   ```
2. `naming-conventions.md` §1 补充第 8 行：
   ```markdown
   | unknown | 异常兜底 | - | 0%-20% |
   ```
3. Integration §5.3 协同约束中增加 `unknown` 处理说明（仅作为观察周期，不生成 STRONG_BUY）

**影响**:  
- Integration 遇到 `cycle="unknown"` 时可能触发未定义枚举值错误
- 无法处理 MSS 异常周期的兜底场景

---

### P1-R26-03: IRS 估值因子冷启动"样本不足 → 返回 50"与 Integration 中性度语义混淆

**文件**:  
- `irs-algorithm.md` (v3.2.8, line 190-192)  
- `integration-algorithm.md` (v3.4.6, line 133-151)  

**问题**:  
IRS §3.4 估值因子冷启动规定"历史窗口不足 60 交易日 → 估值因子分数回退为 50（中性）"（line 192），但：

- Integration §3.2 使用 `irs_score` 直接加权（line 133），无法区分"真实中性 50 分"与"冷启动降级 50 分"
- Integration §3.3 边界校准仅做 `max(0, min(100, score))`（line 151），不处理冷启动标记

**根因**:  
IRS 冷启动降级值（50）与正常评分（50）语义重叠，Integration 无法识别数据质量

**建议**:  
1. IRS 输出增加质量标记字段：
   ```python
   irs_output = {
       "industry_score": 50.0,
       "quality_flag": "cold_start",  # normal/cold_start/stale
       "sample_days": 45  # < 60 触发冷启动
   }
   ```
2. Integration §3.1 Gate 检查中增加：
   ```python
   if irs_output.quality_flag == "cold_start":
       log.warning("IRS in cold start, using baseline weights")
       return BASELINE_WEIGHTS, "WARN"
   ```
3. `irs-data-models.md` 补充 `quality_flag` 字段定义

**影响**:  
- 无法区分 IRS 真实中性与数据不足降级
- Integration 可能基于不可靠数据生成 STRONG_BUY 信号

---

### P1-R26-04: PAS 风险收益比边界定义在 Backtest/Trading 执行层缺失

**文件**:  
- `pas-algorithm.md` (v3.1.10, line 248-283)  
- `backtest-algorithm.md` (v3.4.6, line 106-109)  
- `trading-algorithm.md` (v3.2.4, line 58-60)  

**问题**:  
PAS §6 风险收益比规定：
- 突破场景：`RR = (target - entry) / (entry - stop) ≥ 1.5`（line 266）
- 回调场景：`RR = (target - entry) / (entry - stop) ≥ 2.0`（line 275）

但 Backtest/Trading 在使用 `risk_reward_ratio` 时：
- Backtest §3.1 直接透传 `row.risk_reward_ratio`（line 108），无边界校验
- Trading §2.1 同样直接透传（line 78），无 `RR < 1.0` 过滤

**根因**:  
PAS 的风险收益比下限（1.5/2.0）未在下游执行层强制校验

**建议**:  
1. Backtest §3.1 增加软过滤：
   ```python
   if row.risk_reward_ratio < 1.0:
       log.warning(f"{row.stock_code} RR={row.risk_reward_ratio:.2f} < 1.0, skip")
       continue
   ```
2. Trading §2.1 增加类似校验
3. `pas-algorithm.md` §9.4 输出合法性补充：
   ```markdown
   - risk_reward_ratio ≥ 1.0（最低可接受风险收益比）
   ```

**影响**:  
- 可能执行 `RR < 1` 的劣质信号（预期亏损）
- 回测结果可能包含不符合 PAS 设计意图的交易

---

### P1-R26-05: Data Layer 缺口降级"沿用前值"与 MSS/IRS 统计窗口不对齐

**文件**:  
- `data-layer-information-flow.md` (v3.1.1, line 86-89)  
- `mss-algorithm.md` (v3.1.4, line 364-368)  
- `irs-algorithm.md` (v3.2.8, line 190-192)  

**问题**:  
Data Layer §1 缺口处理规定"缺失时允许使用'上次可用数据'降级"（line 86-89），但：

- MSS §7.1 冷启动规定"样本窗口 < 60 交易日 → 沿用 baseline 参数"（line 367-368）
- IRS §3.4 估值因子规定"当日有效样本数 < 8 → 沿用前一交易日有效值"（line 191）

降级策略混乱：
- Data Layer 降级到"上次可用数据"，但未定义"上次"是否已经是"沿用降级值"（可能传递陈旧数据）
- MSS/IRS 各自定义冷启动阈值（60 vs 无定义），Data Layer 无统一冷启动标记

**根因**:  
Data Layer 降级策略未与上游算法冷启动条件对齐

**建议**:  
1. Data Layer §5.1 增加数据质量标记：
   ```python
   market_snapshot = {
       "trade_date": "20260207",
       "total_stocks": 5234,
       "data_quality": "stale",  # normal/stale/cold_start
       "stale_days": 3  # 沿用数据已过多少天
   }
   ```
2. MSS/IRS 在读取 L2 时检查 `stale_days`：
   ```python
   if snapshot.stale_days > 3:
       raise DataQualityError("market_snapshot stale > 3 days")
   ```
3. 统一冷启动阈值：建议 `min_sample_days=60` 作为全局约束

**影响**:  
- MSS/IRS 可能基于陈旧数据生成评分
- 无法识别"降级链"长度（降级值又被降级）

---

### P2-R26-06: Integration mode 枚举值在 GUI 展示层缺少完整映射

**文件**:  
- `integration-algorithm.md` (v3.4.6, line 476-489)  
- `gui-information-flow.md` (v3.1.5, line 125-138)  
- `backtest-algorithm.md` (v3.4.6, line 42-48)  

**问题**:  
Integration §10.6 定义 4 种模式（line 476-489）：
- `top_down` / `bottom_up` / `dual_verify` / `complementary`

但 GUI §2.1 Dashboard 数据流程仅渲染基础字段（line 125-138），未包含 `integration_mode` 展示

**建议**:  
1. GUI §2.1 Dashboard 增加模式展示：
   ```python
   dashboard_data.integration_mode_badge = format_integration_mode(
       rec.integration_mode
   )
   ```
2. `gui-data-models.md` 补充 `integration_mode_badge` 字段定义
3. 增加模式中文映射：`top_down="传统模式" / bottom_up="实验模式"`

**影响**:  
- 用户无法从 GUI 识别信号来源模式
- 回测对比时需手动查询数据库

---

### P2-R26-07: PAS opportunity_grade 边界 S/A/B/C/D 在 Trading 过滤逻辑中缺失

**文件**:  
- `pas-algorithm.md` (v3.1.10, line 226-233)  
- `integration-algorithm.md` (v3.4.6, line 203-230)  
- `trading-algorithm.md` (v3.2.4, line 38-45)  

**问题**:  
PAS §5.1 等级边界明确定义 5 级（line 226-233），Integration §6.1 推荐列表使用 PAS 等级软排序（line 218-219），但：

- Trading §2.1 过滤规则仅基于 `final_score` + `recommendation`（line 38-45），不考虑 `opportunity_grade`
- 可能生成 `opportunity_grade=D` 但 `final_score ≥ 55` 的信号（Integration 不会过滤，Trading 也不会过滤）

**建议**:  
Trading §2.1 增加软过滤：
```python
if row.opportunity_grade in {"D"}:
    log.info(f"{row.stock_code} grade=D, skip")
    continue
```

**影响**:  
- 可能执行低质量 PAS 信号
- 与 Integration 的"PAS 软排序"设计意图不完全对齐

---

### P2-R26-08: MSS neutrality 计算公式在 Integration 中性度聚合时未加权

**文件**:  
- `mss-algorithm.md` (v3.1.4, line 309-317)  
- `integration-algorithm.md` (v3.4.6, line 304-327)  

**问题**:  
MSS §6 中性度定义：`neutrality = 1 - |temperature - 50| / 50`（line 310）  
Integration §7.3 聚合中性度公式：`neutrality = (mss_neutrality + irs_neutrality + pas_neutrality) / 3`（line 324）

但未考虑三算法权重差异：
- Integration §3.2 使用权重三元组 `(w_mss, w_irs, w_pas)`
- 中性度聚合应与评分权重一致

**建议**:  
Integration §7.3 修正为加权平均：
```python
neutrality = (
    mss_neutrality * w_mss
    + irs_neutrality * w_irs
    + pas_neutrality * w_pas
)
```

**影响**:  
- 中性度语义与加权评分不对齐
- 极端情况：高权重算法的中性信号可能被低权重算法稀释

---

### P2-R26-09: Backtest/Trading 中 MSS recession 周期处理与 Integration 协同约束不一致

**文件**:  
- `mss-algorithm.md` (v3.1.4, line 268-279)  
- `integration-algorithm.md` (v3.4.6, line 251-284)  
- `backtest-algorithm.md` (v3.4.6, line 86-96)  

**问题**:  
MSS §5.2 定义 `recession` 周期边界为 `<60 + down/sideways`（line 268-279）  
Integration §5.3 协同约束规定退潮期 `pas_score × 0.8`（line 279）  
但 Backtest §3.1 软门控过滤仅基于 `final_score`（line 86-93），未显式处理 `recession` 场景

**建议**:  
Backtest §3.2 增加说明：
```markdown
说明：recession 周期调整已在 Integration 完成（PAS 折扣 0.8），Backtest 仅消费 final_score
```

**影响**:  
- 文档追溯性不足
- 读者可能误以为 Backtest 需单独处理 recession

---

### P2-R26-10: Data Layer L2 `stock_gene_cache` 更新频率与 PAS 牛股基因因子窗口不对齐

**文件**:  
- `data-layer-information-flow.md` (v3.1.1, line 150-156)  
- `pas-algorithm.md` (v3.1.10, line 105-118)  

**问题**:  
Data Layer §2.1 规定 `stock_gene_cache` 每日更新（line 150-156）  
PAS §3.1 牛股基因因子使用 `limit_up_120d_ratio`（line 106）

但未明确：
- `stock_gene_cache` 是否每日滚动更新 120 日窗口？
- 若不是，PAS 如何获取最新 120 日统计？

**建议**:  
`data-layer-information-flow.md` §2.1 增加说明：
```markdown
stock_gene_cache 更新策略：
- 每日滚动更新 120 日窗口（limit_up_count_120d）
- 缓存 60 日新高统计（new_high_count_60d）
- 历史最大涨幅（max_pct_chg_history）仅在新记录时更新
```

**影响**:  
- PAS 可能读取陈旧的牛股基因统计
- 文档未明确窗口滚动策略

---

## 严重性分布

| 优先级 | 数量 | 问题类型 |
|--------|------|----------|
| P1 | 5 | 降级策略不一致、边界处理缺失、枚举追溯断链 |
| P2 | 5 | 文档完整性、追溯性不足 |
| **总计** | **10** | - |

---

## 按模块分类

| 模块 | 涉及问题 |
|------|----------|
| Integration | P1-R26-01, P1-R26-02, P1-R26-03, P2-R26-08 |
| Backtest | P1-R26-01, P1-R26-04, P2-R26-09 |
| Trading | P1-R26-01, P1-R26-04, P2-R26-07 |
| MSS | P1-R26-02, P1-R26-05 |
| IRS | P1-R26-03, P1-R26-05 |
| PAS | P1-R26-04, P2-R26-07, P2-R26-10 |
| Data Layer | P1-R26-05, P2-R26-10 |
| GUI | P2-R26-06 |

---

## 修复优先级建议

### 立即修复（P1）
1. **P1-R26-01**: 阻断性问题，Gate FAIL 未传递到 Backtest/Trading
2. **P1-R26-02**: 新增枚举值 `unknown` 未同步到下游
3. **P1-R26-03**: 冷启动降级值与真实中性混淆
4. **P1-R26-04**: 风险收益比边界缺失可能导致劣质信号执行
5. **P1-R26-05**: 数据降级链可能传递陈旧数据

### 近期修复（P2）
6. **P2-R26-06**: GUI 缺少 `integration_mode` 展示
7. **P2-R26-07**: Trading 未过滤 PAS D 级信号
8. **P2-R26-08**: 中性度聚合未加权
9. **P2-R26-09**: 文档追溯性不足（协同约束处理说明）
10. **P2-R26-10**: 牛股基因缓存更新策略未明确

---

## 累计审查统计（R1-R26）

| 轮次 | 问题数 | 已修复 | 本轮新增 | 累计 |
|------|--------|--------|----------|------|
| R1-R24 | 229 | 229 | - | 229 |
| R25 | 10 | 10 | - | 239 |
| **R26** | **10** | **10** | **0** | **249** |

---

## 下一步行动

1. **执行 R27 验证**（验证 R26 修复完整性）

---

## 复查结论（Codex）

**复查时间**: 2026-02-09  
**结论**: R26 问题清单共 10 项，已在目标文档中全部落地，复查 10/10 通过。  

对齐结果：
- `docs/design/core-algorithms/integration/integration-algorithm.md`：P1-R26-02 / P1-R26-03 / P2-R26-08
- `docs/design/core-algorithms/integration/integration-data-models.md`：P1-R26-02 / P1-R26-03（契约追溯）
- `docs/design/backtest/backtest-algorithm.md`：P1-R26-01 / P1-R26-04 / P2-R26-09
- `docs/design/trading/trading-algorithm.md`：P1-R26-01 / P1-R26-04 / P2-R26-07
- `docs/design/core-algorithms/irs/irs-algorithm.md`：P1-R26-03 / P1-R26-05
- `docs/design/core-algorithms/irs/irs-data-models.md`：P1-R26-03（质量字段）
- `docs/design/core-algorithms/mss/mss-algorithm.md`：P1-R26-05（stale 门禁）
- `docs/design/core-algorithms/pas/pas-algorithm.md`：P1-R26-04（RR 执行下限）
- `docs/design/data-layer/data-layer-information-flow.md`：P1-R26-05 / P2-R26-10
- `docs/design/data-layer/data-layer-data-models.md`：P1-R26-05 / P2-R26-10（字段与窗口策略）
- `docs/design/gui/gui-information-flow.md` + `docs/design/gui/gui-data-models.md`：P2-R26-06
- `docs/naming-conventions.md`：P1-R26-02（`unknown` 命名规范）

---

## 审查覆盖度

### 本轮重点文件（已深度审查）
- ✅ `integration-algorithm.md` (v3.4.6)
- ✅ `mss-algorithm.md` (v3.1.4)
- ✅ `irs-algorithm.md` (v3.2.8)
- ✅ `pas-algorithm.md` (v3.1.10)
- ✅ `validation/factor-weight-validation-algorithm.md` (v0.3)
- ✅ `backtest-algorithm.md` (v3.4.6)
- ✅ `trading-algorithm.md` (v3.2.4)
- ✅ `data-layer-information-flow.md` (v3.1.1)
- ✅ `gui-information-flow.md` (v3.1.5)

### 全局搜索覆盖
- 搜索关键词：`降级/fallback/default/缺失/越界/边界/exception`
- 命中文件：38 个
- 深度分析：9 个关键文件

---

**报告结束**

审查范围：端到端集成一致性（降级路径、边界条件、枚举追溯）  
发现问题：10 个（5 P1 + 5 P2）  
累计审查：249 个问题（R1-R26）  
质量评价：降级策略存在跨模块不对齐风险，需补齐 Gate FAIL / 冷启动 / 枚举追溯链

---

**Claude 审查签名**: R26-claude-20260209  
**下一轮预告**: R27 将验证 R26 修复完整性
