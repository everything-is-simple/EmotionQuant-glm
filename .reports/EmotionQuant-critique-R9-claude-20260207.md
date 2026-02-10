# EmotionQuant 第九轮批判性审查报告

**审查人**: Claude (claude 4.6 opus)
**日期**: 2026-02-07
**基线**: `develop` @ `d9372b6`（R8 修复已全部提交，工作区 clean）
**审查角度**: GUI 层全面审查 · 跨层数据契约端到端比对 · Backtest 追溯链补漏

---

## 本轮方法论

R8 聚焦公式数学验证和 Backtest/PAS 端到端走查。本轮（R9）方法：

1. **GUI 层全面审查**：gui-algorithm / gui-data-models / gui-information-flow 三件套对照核心算法层，检查阈值、枚举、颜色映射是否同步。
2. **跨层数据契约审计**：从 MSS → Integration → Trading → Backtest → GUI 全链路逐字段比对 field name / type / 语义。
3. **Backtest 追溯链补漏**：R8 修复了 BacktestTrade 和 Position 的 signal_id，检查 BacktestSignal 是否也同步。
4. **验收规格 vs 数据模型交叉验证**：IRS §9.1 必备字段声明与实际数据模型对照。

---

## 本次复查结论（Codex）

- 复查结果：R9 列出的 9 项问题在当前基线均可复现（9/9 成立）
- 修复进展（2026-02-07）：报告所列修复项经 2026-02-08 二次复核，确认为 **8 项已在基线修复 + 1 项文档残留**（见下方纠偏记录）

### 复查纠偏记录（2026-02-08）

- 纠偏结论：原“R9 9/9 已修复并提交”结论不完全准确，存在 1 项残留未完全对齐。
- 残留项：`docs/design/gui/gui-data-models.md` 中 `TemperatureLevel` 仍写为 `40/80` 分段，未与 `docs/design/gui/gui-algorithm.md` 的 `30/45/80` 分段保持一致。
- 处理动作：已在 `docs/design/gui/gui-data-models.md` 修正为 `>80 / 45-80 / 30-44 / <30`，并补充 `COOL` 等级；文档版本同步至 `v3.1.4`（2026-02-08）。
- 复核结论：截至 2026-02-08，R9 报告列出的 9 项问题已全部闭合（OPEN=0）。

---

## 新发现（9 项，已全部修复并提交）

### P0 — 逻辑冲突 / 阈值回归（2 项）

#### ~~P0-R9-01：GUI RecommendationLevel 枚举注释仍标 STRONG_BUY ≥ 80 — R6 修复残留~~

**位置**: `gui-data-models.md` §6.2 (L431-432)

```python
class RecommendationLevel(Enum):
    STRONG_BUY = "STRONG_BUY"  # ≥ 80      ← 错误
    BUY = "BUY"                # 70-79     ← 错误
```

**权威口径（均为 ≥75）**：
- `naming-conventions.md` §5.1: STRONG_BUY = `final_score ≥ 75 + mss_cycle ∈ {emergence, fermentation}`
- `integration-algorithm.md` §5.1: 同上
- `gui-algorithm.md` §2.2 (L53): `if final_score >= 75 and mss_cycle in ("emergence", "fermentation")`

**影响**：
- 枚举注释说 ≥80，算法代码说 ≥75 → 实现者读到枚举先入为主，可能在 GUI 展示侧用 80 做判断
- BUY 注释说 70-79，实际区间应为 70-74（因 ≥75 已归 STRONG_BUY）
- 这是 R6 修复 STRONG_BUY 阈值时的遗漏 — gui-algorithm.md 更新了但 gui-data-models.md 的枚举注释没同步

---

#### ~~P0-R9-02：Integration 推荐列表生成用 PAS 等级做硬过滤 — 违反"无单点否决"原则~~

**位置**: `integration-information-flow.md` §2.9 Step 8 (L314-315)

```
筛选条件：
1. opportunity_grade in (S, A, B)     ← PAS 单系统否决
2. allocation_advice != "回避"         ← IRS 单系统否决
3. mss_temperature is not null
4. final_score >= 55
```

**问题**：§2.5 Step 5 明确声明「协同约束规则（**无单点否决**）」，评分层（Step 1-7）严格遵守了这一原则。但 Step 8 的推荐列表生成却使用 PAS `opportunity_grade` 和 IRS `allocation_advice` 做硬过滤，实质上恢复了单点否决。

**数值反例**：
- PAS: opportunity_score = 54（C 级）
- MSS: temperature = 80
- IRS: industry_score = 85
- final_score = 54×⅓ + 80×⅓ + 85×⅓ = **73.0** → recommendation = **BUY**
- 但 Step 8 条件 1 判定 `opportunity_grade = C` → **排除**

三三制融合计算出 BUY 信号，却因 PAS 一个子系统的等级而丢弃。整个 Integration 计算对这只股票来说是无效功。

**修复建议**：
- 方案 A：将 opportunity_grade 过滤改为 soft filter（降低排序权重而非排除）
- 方案 B：改用 `opportunity_score >= 55`（与 final_score 阈值同口径）替代等级硬过滤
- allocation_advice != "回避" 同理：已在 Step 5 通过 `pas_score *= 0.85` 做了折扣，再硬排除属于双重惩罚

---

### P1 — 规格冲突 / 数据契约缺口（5 项）

#### ~~P1-R9-03：BacktestSignal 缺少 signal_id — 回测追溯链起点断裂~~

**位置**: `backtest-data-models.md` §1.2 BacktestSignal (L58-86)

R8 修复了 BacktestTrade（补 signal_id，L97）和 Position（补 signal_id，L155），但 BacktestSignal 本身没有 `signal_id` 字段。

**对比**：
- Trading: `TradeSignal.signal_id: str` ✅（格式 `SIG_{date}_{code}`）
- Backtest: `BacktestSignal` → ❌ 无 signal_id
- Backtest: `BacktestTrade.signal_id` / `Position.signal_id` 引用了不存在的源字段

**影响**：BacktestTrade 和 Position 的 signal_id 无法从 BacktestSignal 获取。实现者要么需要在信号→交易转换时临时生成 ID（但规则未定义），要么 signal_id 为空。

---

#### ~~P1-R9-04：IRS §9.1 验收规格声称 benchmark_pct_chg 来自 industry_snapshot，实际来自 BenchmarkData~~

**位置**:
- `irs-algorithm.md` §9.1 (L370): "industry_snapshot 必须提供 … 连续类：industry_pct_chg、**benchmark_pct_chg**"
- `irs-data-models.md` §2.1 IrsIndustrySnapshot: 无 benchmark_pct_chg 字段
- `irs-data-models.md` §2.2 BenchmarkData: `pct_chg: float`（这才是 benchmark_pct_chg 的来源）
- `data-layer-data-models.md` §3.2 industry_snapshot 表: 无 benchmark_pct_chg 列

§9.1 的字段声明将实现者引导到 industry_snapshot 中找 benchmark_pct_chg，但该字段实际来自单独的 BenchmarkData（基于 `raw_index_daily`）。IRS data-models §1.2 正确记录了来源为 `raw_daily + raw_index_daily`，但验收规格与数据模型矛盾。

---

#### ~~P1-R9-05：GUI 温度颜色分界与 MSS 冷/热市场阈值不对齐~~

**位置**:
- `gui-algorithm.md` §2.1 (L32-37): `< 40 → blue/low`, `40-80 → orange/medium`, `≥ 80 → red/high`
- MSS/Integration/PAS: `< 30 → 冰点（冷市场缩减）`, `> 80 → 过热`

| 温度值 | GUI 显示 | 算法行为 |
|--------|----------|----------|
| 25 | 🔵 blue/low | ❄️ 冰点：仓位缩减 + neutrality 上调 |
| 35 | 🔵 blue/low | ✅ 正常：无冷市场动作 |
| 79 | 🟠 orange/medium | ✅ 正常：无过热动作 |

温度 35 在 GUI 显示为"低温/蓝色"，暗示市场冷淡，但算法层并未触发任何冷市场调整（阈值是 30）。用户看到蓝色可能误以为系统正在下调仓位。

**修复建议**：将 GUI blue/low 阈值改为 `< 30`，并增加一档 30-45 = cyan/cool（对应 fermentation 下界）。

---

#### ~~P1-R9-06：GUI 周期映射表缺少 UNKNOWN — MSS 冷启动时 GUI 无法渲染~~

**位置**:
- `naming-conventions.md` §1.3 MssCycle 枚举: 包含 `UNKNOWN = "unknown"`（共 8 值）
- `gui-data-models.md` §3.2 CycleBadgeData (L305): 仅列 7 个周期，无 UNKNOWN
- `gui-data-models.md` §3.2 周期中英文映射表 (L311-319): 7 行，无 UNKNOWN

MSS 冷启动阶段（Z-Score baseline 不足或首次部署）会输出 `cycle = "unknown"`。GUI 的 `mapping.get(cycle)` 找不到匹配项时：
- CycleBadgeData 颜色/标签为 None
- Streamlit 渲染可能报错或显示空白

---

#### ~~P1-R9-07：Backtest take_profit_pct (0.20) 与 Trading (0.15) 不一致~~

**位置**:
- `backtest-data-models.md` §1.1 BacktestConfig (L53): `take_profit_pct: float = 0.2`
- `trading-data-models.md` §2.1 TradeConfig (L155): `take_profit_pct: float = 0.15`

| 层 | take_profit_pct | 说明 |
|----|-----------------|------|
| **Trading** | **0.15** (15%) | 实盘止盈 |
| **Backtest** | **0.20** (20%) | 回测止盈 |

回测使用更宽松的止盈（20% vs 15%），导致回测中持仓时间更长、收益更高。策略的回测表现会系统性优于实盘，造成过拟合假象。

> 注：R8 已修复 max_position_pct（Backtest 与 Trading 统一为 0.20），但 take_profit_pct 未同步。

---

### P2 — 次要不一致（2 项）

#### ~~P2-R9-08：GUI ErrorBoundary 伪代码含 bare `except:` — 与 R5 hooks 修复标准不一致~~

**位置**: `gui-information-flow.md` §7.2 (L482)

```python
except:                    # ← 应为 except Exception:
    show_generic_error()
```

R5 修复了 `.claude/hooks` 三处 bare `except:` → `except Exception:`。GUI 信息流的 ErrorBoundary 伪代码使用相同的反模式。虽然是设计文档中的伪代码，但实现者会直接复制。

#### ~~P2-R9-09：GUI data-models / information-flow 版本滞后于 gui-algorithm~~

| 文档 | 版本 | 日期 |
|------|------|------|
| gui-algorithm.md | v3.1.2 | 2026-02-07 |
| **gui-data-models.md** | **v3.1.0** | **2026-02-06** |
| **gui-information-flow.md** | **v3.1.0** | **2026-02-06** |

gui-algorithm v3.1.2 更新了 STRONG_BUY 阈值（75），但 gui-data-models 和 gui-information-flow 停留在 v3.1.0，未同步相关变更（如 P0-R9-01 的枚举注释）。

---

## R1-R8 遗留更新

全部已关闭（70/70）。

---

## 累计统计

| 轮次 | 新增 | 已修复（committed） | 已修复（working tree） | 当前 OPEN |
|------|------|---------------------|----------------------------------|-----------|
| R1-R4 | 27 | 27 | 27 | 0 |
| R5 | 9 | 9 | 9 | 0 |
| R6 | 13 | 13 | 13 | 0 |
| R7 | 11 | 11 | 11 | 0 |
| R8 | 10 | 10 | 10 | 0 |
| **R9** | **9** | **9** | **9** | **0** |
| **总计** | **79** | **79** | **79** | **0** |

> committed 口径修复率：79/79 = **100.0%**。  
> working tree 口径修复率：79/79 = **100.0%**（与 committed 口径一致）。

---

## 本轮修复优先级建议

**已完成（已提交）**:
1. ~~P0-R9-01: GUI 枚举注释 STRONG_BUY ≥80 → ≥75，BUY 70-79 → 70-74~~
2. ~~P0-R9-02: Integration §2.9 推荐列表硬过滤改为 soft filter / 软排序~~
3. ~~P1-R9-03: BacktestSignal 补 signal_id~~
4. ~~P1-R9-04: IRS §9.1 修正 benchmark_pct_chg 来源说明~~
5. ~~P1-R9-05: GUI 温度颜色分界对齐 MSS 30/80（新增 30-45 cyan/cool）~~
6. ~~P1-R9-06: GUI CycleBadge 补 UNKNOWN 映射~~
7. ~~P1-R9-07: Backtest take_profit_pct 对齐 Trading 0.15~~
8. ~~P2-R9-08: GUI ErrorBoundary 改为 `except Exception:`~~
9. ~~P2-R9-09: GUI data-models / info-flow 版本同步至 v3.1.2+~~

**剩余未修复**:
1. 无（R9 OPEN = 0）

---

*报告结束*
