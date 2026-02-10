# EmotionQuant 设计文档审查报告 — 第 28 轮

**审查主题**: DDL 表结构 vs Python dataclass 全量对齐  
**审查日期**: 2026-02-09  
**审查范围**: 全 9 模块 `*-data-models.md`（MSS / IRS / PAS / Integration / Data Layer / Backtest / Trading / GUI / Analysis）  
**累计轮次**: R1-R28（累计 271 项）  
**本轮发现**: 12 项（P1 × 5，P2 × 7）

---

## 审查方法

逐模块对比三层结构：
1. **Python dataclass**（§2-3 输入/输出数据模型）
2. **模块 DDL**（§4 SQL CREATE TABLE / 字段表）
3. **Data Layer 镜像表**（data-layer-data-models.md §3-7 对应表）

检查项：字段覆盖完整性、类型映射一致性、VARCHAR 宽度、命名规范、主键策略、索引充分性。

---

## P1 问题（5 项）

### P1-R28-01: Data Layer `integrated_recommendation` 字段表+DDL 缺少 6 个追溯字段

**位置**: `docs/design/data-layer/data-layer-data-models.md` §4.4（行 408-473）  
**对比来源**: `docs/design/core-algorithms/integration/integration-data-models.md` §3.1 + §4.1

**现状**:  
Integration 模块的 `IntegratedRecommendation` dataclass 和 DDL 均包含以下 6 个追溯字段：
- `consistency VARCHAR(20)` — 方向一致性
- `w_mss DECIMAL(6,4)` — MSS 权重快照
- `w_irs DECIMAL(6,4)` — IRS 权重快照
- `w_pas DECIMAL(6,4)` — PAS 权重快照
- `mss_cycle VARCHAR(20)` — 当日 MSS 周期
- `opportunity_grade VARCHAR(5)` — PAS 机会等级快照

Data Layer §4.4 的字段表（22 列）和下方的逻辑 DDL 片段均**缺少这 6 个字段**。

**影响**: Data Layer 作为持久化权威表，缺失追溯字段将导致 STRONG_BUY 条件无法审计、权重方案无法复现。  
**修复**: 在 data-layer-data-models.md §4.4 字段表和逻辑 DDL 中补齐 6 个字段。

---

### P1-R28-02: Data Layer `irs_industry_daily` 缺少 `quality_flag` 和 `sample_days`

**位置**: `docs/design/data-layer/data-layer-data-models.md` §4.2（行 355-380）  
**对比来源**: `docs/design/core-algorithms/irs/irs-data-models.md` §3.1 + §4.1

**现状**:  
IRS 模块的 `IrsIndustryDaily` dataclass 和 DDL 均包含：
- `quality_flag: str` — 质量标记 normal/cold_start/stale
- `sample_days: int` — 有效样本天数

Data Layer §4.2 `irs_industry_daily` 字段表（16 列）**缺少这 2 个字段**。

**影响**: 下游 Integration 依赖 `quality_flag` 进行冷启动处理（R27 修复项），Data Layer 不存储将断链。  
**修复**: 在 data-layer-data-models.md §4.2 字段表中补齐 `quality_flag VARCHAR(20)` 和 `sample_days INTEGER`。

---

### P1-R28-03: Analysis `DailyReport` dataclass 缺少 `total_return` 字段

**位置**: `docs/design/analysis/analysis-data-models.md` §1.2（行 54-79）vs §3.1（行 217-237）

**现状**:  
DDL `daily_report` 表（R21 新增）包含 `total_return DECIMAL(10,4)`，但 `DailyReport` dataclass **没有**该字段。

dataclass 有 `max_drawdown`/`sharpe_ratio`/`win_rate` 等绩效字段，唯独缺少 `total_return`。

**影响**: 实现时 DDL 与 dataclass 不对齐，ORM/序列化将出错。  
**修复**: 在 DailyReport dataclass "绩效指标"区域添加 `total_return: float`。

---

### P1-R28-04: Trading DDL 使用 TEXT/REAL 类型体系 vs Data Layer 使用 VARCHAR/DECIMAL

**位置**:  
- `docs/design/trading/trading-data-models.md` §4.1-4.3（行 240-301）
- `docs/design/data-layer/data-layer-data-models.md` §7.1-7.3（行 574-631）

**现状**:  
Trading 模块 DDL 对 `trade_records` / `positions` / `t1_frozen` 使用 DuckDB 原生类型（TEXT, REAL, INTEGER），Data Layer 对相同表使用 MySQL 风格类型（VARCHAR(50), DECIMAL(12,4)）。

示例：
| 字段 | Trading DDL | Data Layer DDL |
|------|-------------|----------------|
| price | REAL | DECIMAL(12,4) |
| amount | REAL | DECIMAL(16,2) |
| commission | REAL | DECIMAL(12,2) |
| stock_code | TEXT | VARCHAR(20) |

**影响**: 同一张表在两份文档中有不兼容的类型声明，实现时需选择其一，当前无法判断哪个为权威。  
**修复**: 统一 Trading DDL 为 VARCHAR/DECIMAL 风格（与其他所有模块 DDL 保持一致，Data Layer 作为持久化权威）。

---

### P1-R28-05: MSS/IRS/PAS 模块 DDL `trade_date DATE` vs Data Layer `trade_date VARCHAR(8)`

**位置**:  
- `mss-data-models.md` §4.1: `trade_date DATE NOT NULL`
- `irs-data-models.md` §4.1: `trade_date DATE NOT NULL`
- `pas-data-models.md` §4.1: `trade_date DATE NOT NULL`
- `integration-data-models.md` §4.1: `trade_date DATE NOT NULL`
- `data-layer-data-models.md` §4.1-4.4: `trade_date VARCHAR(8)`

**现状**:  
4 个核心算法模块 DDL 使用 `DATE` 类型，Data Layer 统一使用 `VARCHAR(8)`。这两种类型在 DuckDB 中行为不同（DATE 有日期运算、比较语义；VARCHAR(8) 需手动转换）。

dataclass 均为 `trade_date: str`（YYYYMMDD 格式），与 VARCHAR(8) 天然对齐。

**影响**: 跨模块 JOIN 可能产生隐式类型转换，或需额外 CAST。  
**修复**: 统一 MSS/IRS/PAS/Integration DDL 的 `trade_date` 为 `VARCHAR(8)`（与 Data Layer 和 dataclass 对齐）。

---

## P2 问题（7 项）

### P2-R28-06: VARCHAR 宽度系统性不一致（模块 DDL vs Data Layer）

**位置**: MSS/IRS/PAS/Integration 各模块 DDL §4 vs data-layer-data-models.md §4

**汇总**:

| 字段 | 模块 DDL 宽度 | Data Layer 宽度 | 影响表 |
|------|---------------|-----------------|--------|
| stock_code | VARCHAR(10) | VARCHAR(20) | PAS, Integration |
| stock_name | VARCHAR(20) | VARCHAR(50) | PAS, Integration |
| industry_name | VARCHAR(20) | VARCHAR(50) | IRS, Integration |
| direction | VARCHAR(20) | VARCHAR(10) | PAS, Integration |
| opportunity_grade | VARCHAR(5) | VARCHAR(10) | PAS |

**注意**: `direction` 实际值 max 7 字符（bullish），两侧宽度均足够但方向相反。

**修复**: 以 Data Layer 宽度为准（更宽更安全），统一模块 DDL。`direction` 统一为 VARCHAR(20) 或 VARCHAR(10) 均可（值不超过 10 字符）。

---

### P2-R28-07: 时间戳字段命名不一致 — `create_time` vs `created_at`

**位置**: MSS/IRS/PAS/Integration DDL 使用 `create_time` / `update_time`；Data Layer / Backtest / Trading / Analysis 使用 `created_at` / `updated_at`

**现状**: 4 个核心算法模块 DDL 用 `create_time/update_time`，其余模块和 Data Layer 用 `created_at/updated_at`。

**修复**: 全局统一为 `created_at` / `updated_at`（Data Layer 作为权威，且 Rails/Django 社区惯例均为 `_at` 后缀）。

---

### P2-R28-08: MSS/IRS/PAS/Integration DDL 有 `update_time` 但 Data Layer L3 表无 `updated_at`

**位置**:  
- MSS DDL: `update_time DATETIME`
- IRS DDL: `update_time DATETIME`
- PAS DDL: `update_time DATETIME`
- Integration DDL: `update_time DATETIME`
- Data Layer L3 §4.1-4.4: 仅 `created_at DATETIME`

**现状**: 模块 DDL 定义了 `update_time` 列，但 Data Layer 的 L3 镜像表均只有 `created_at`，无更新时间戳。

**影响**: 如果需要追溯记录修改时间（如数据补正），Data Layer 无法记录。  
**修复**: 决策：要么 Data Layer L3 表补齐 `updated_at`，要么模块 DDL 移除 `update_time`（L3 通常为每日追加，不修改）。建议：L3 表为 append-only，移除 `update_time` 更合理。

---

### P2-R28-09: Trading `positions.is_frozen` INTEGER(0/1) vs Data Layer BOOLEAN

**位置**:  
- `trading-data-models.md` §4.2: `is_frozen | INTEGER | 是否冻结 (0/1)`
- `data-layer-data-models.md` §7.2: `is_frozen | BOOLEAN | 是否冻结`

**现状**: 同一字段在两份文档中类型不一致。DuckDB 支持 BOOLEAN 类型。

**修复**: 统一为 BOOLEAN（DuckDB 原生支持，语义更清晰）。Trading DDL 改 `is_frozen BOOLEAN`。

---

### P2-R28-10: Backtest `BacktestResult` dataclass 与 DDL 字段差异

**位置**: `backtest-data-models.md` §1.7（行 219-236）vs §2.3（行 317-358）

**现状**:  
- DDL 有 `initial_cash DECIMAL(16,2)` 和 `final_value DECIMAL(16,2)` — dataclass **无** `final_value`（`initial_cash` 来自嵌套 `config`）
- dataclass 有 `position_summary: Dict` — DDL **无**对应列

**影响**: `final_value` 无 dataclass 定义，实现时需额外约定来源（推测为 `equity_curve[-1].equity`）。  
**修复**: 在 BacktestResult dataclass 添加 `final_value: float` 并注释来源；`position_summary` 如需持久化则添加到 DDL 为 JSON 列，或标注"仅运行态，不持久化"。

---

### P2-R28-11: L3 主键策略不一致 — `id` + UNIQUE vs 直接业务键 PK

**位置**: 核心算法模块 DDL vs Data Layer L3 表

**现状**:  
- MSS/IRS/PAS/Integration DDL: `id INTEGER PRIMARY KEY` + `UNIQUE KEY uk_xxx (trade_date, ...)`
- Data Layer L3 mss_panorama: `trade_date VARCHAR(8) | 交易日期 (PK)` — 直接用业务键
- Data Layer L3 integrated_recommendation DDL: `id INTEGER PRIMARY KEY` + `UNIQUE KEY` — 用代理键

Data Layer 内部不一致：mss_panorama/irs_industry_daily/stock_pas_daily 用业务键做 PK，integrated_recommendation 用 id 做 PK。

**修复**: 统一策略。建议全部使用 `id INTEGER PRIMARY KEY` + `UNIQUE` 业务键（兼容 ORM、允许 UPSERT）。

---

### P2-R28-12: PAS `direction` 宽度反向差异

**位置**:  
- `pas-data-models.md` §4.1: `direction VARCHAR(20)`
- `data-layer-data-models.md` §4.3: `direction VARCHAR(10)`

**现状**: 大多数字段是 Data Layer 更宽（安全），唯独 `direction` 是 PAS DDL 更宽 (20) 而 Data Layer 更窄 (10)。PAS 的 direction 取值为 `bullish/bearish/neutral`（max 7 字符），VARCHAR(10) 足够，但口径应统一。

同样的反向差异也存在于 Integration DDL `direction VARCHAR(20)` vs Data Layer `direction VARCHAR(10)`。

**修复**: 统一为 VARCHAR(20)（与其他 VARCHAR 宽度从宽策略一致），或经评审确认 VARCHAR(10) 足够后统一为 VARCHAR(10)。

---

## 统计汇总

| 优先级 | 数量 | 涉及模块 |
|--------|------|----------|
| P1 | 5 | Data Layer(2), Analysis(1), Trading(1), MSS/IRS/PAS/Integration(1) |
| P2 | 7 | 跨模块系统性(5), Backtest(1), PAS/Integration(1) |
| **合计** | **12** | |

### 问题分类

| 类型 | 数量 | 说明 |
|------|------|------|
| 字段缺失 | 3 | P1-01(6字段), P1-02(2字段), P1-03(1字段) |
| 类型体系不一致 | 3 | P1-04, P1-05, P2-09 |
| VARCHAR 宽度不一致 | 2 | P2-06(系统性), P2-12(反向) |
| 命名不一致 | 2 | P2-07(时间戳), P2-08(update缺失) |
| dataclass↔DDL 字段差异 | 1 | P2-10 |
| 主键策略不一致 | 1 | P2-11 |

---

## 累计进度

| 轮次 | 主题 | 发现数 |
|------|------|--------|
| R1-R24 | 单文档→模块内→跨模块 | 229 |
| R25 | 系统级扫描 | 10 |
| R26 | 端到端集成 | 10 |
| R27 | API 跨模块一致性 | 10 |
| **R28** | **DDL vs dataclass 全量对齐** | **12** |
| **累计** | | **271** |

---

## 后续建议

1. **R29（建议）**: Validation 模块深度审查 + 因子权重验证数据模型对齐
2. **R30（建议）**: 回归验证 + 最终扫尾 — 确认 R28 修复后无新增连锁问题
3. 修复 R28 后，系统设计文档预计达到实现就绪（implementation-ready）质量

---

*生成时间: 2026-02-09*  
*审查工具: Claude (Warp Agent Mode)*
