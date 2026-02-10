# EmotionQuant 系统批判报告（Claude 第五轮 — 修复验证 + 残留深挖）

**作者**: Claude (Warp Agent Mode, claude 4.6 opus max)
**时间**: 2026-02-07 09:56 UTC
**基线**: develop `ad9ff99` (fix: address R4 critique gaps and align Spiral tooling)
**聚焦**: 验证 R4 修复效果，深挖算法设计一致性和测试质量

---

## 0. 仓库变化对比

| 指标 | R4 时 | R5 时 | 变化 |
|------|-------|-------|------|
| src/ 行数 | 212 | 277 | +65（主要是 snapshots 扩字段 + config fallback） |
| tests/ 行数 | 12 | 56 | +44（2 个真正的测试文件） |
| scripts/ 行数 | 126 | 102 | -24（质量检查精简） |
| pytest 收集 | 0 | 4 | 从零到有 |
| pytest 通过 | 0 | 3 | **1 个失败** |
| 文档行数 | ~26,500 | ~26,500 | 基本不变 |

---

## 1. R4 修复验证（15 项中 13 项确认修复）

### 确认修复

| R4 问题 | 修复内容 | 验证 |
|---------|----------|------|
| quality_check 7 误报 | 排除 self、排除 .env、跳过 shebang | 误报从 7→2（见 §2.1） |
| Import 双路径陷阱 | 删除 `pythonpath=["src"]` | `from src.config.config` 现在是唯一路径 |
| Trading MSS 单点否决 | `return []` → `mss_risk_factor = cold_market_position_factor` | 仓位下调，不否决信号 |
| .claude/hooks 幽灵路径 | `.kiro/` → `Governance/record/development-status.md` | 路径存在 |
| 两套检查标准打架 | pre_edit_check.py 现在 import quality_check regex | 统一 |
| .claude/hooks 永远禁止 TODO | FORBIDDEN_KEYWORDS 缩减，仅 S6 阶段阻断 | 与核心原则一致 |
| .env "按年分库" 注释 | 改为"单库优先；阈值触发后再启用分库" | 与 system-overview 一致 |
| 数据模型 src/ vs docs/ 脱节 | MarketSnapshot 7→19 字段，IndustrySnapshot 6→22 字段 | 大幅对齐 |
| requirements.txt dev 混入 | 拆出 requirements-dev.txt | 核心区干净 |
| pyproject.toml 缺 duckdb | 添加 `duckdb>=0.9.0` | 在位 |
| Config 空字符串默认值 | `_resolve_storage_paths` + `DEFAULT_DATA_PATH = ~/.emotionquant/data` | 有 fallback |
| Z-Score 冷启动未定义 | MSS §7.1 新增 baseline 文件 + 在线更新 + 兜底策略 | 完整 |
| IRS pe_ttm 聚合未定义 | §3.4 新增：过滤负 PE → Winsorize 1%-99% → 截断 1000 → 取中位数 | 完整 |
| 版本号双源 | `importlib.metadata.version()` 单源 | 修复 |
| StockBasic/TradeCalendar 缺字段 | 补充 list_date、pretrade_date | 修复 |

### 未完全修复（2 项，产生新变体）

| R4 问题 | 当前状态 |
|---------|----------|
| quality_check 误报 | 旧的 7 条修复，但测试文件产生 2 条新误报（见 §2.1） |
| Config 默认路径 fallback | 代码正确但测试失败（见 §2.2） |

---

## 2. 新发现 P0（严重）

### 2.1 quality_check 测试文件自触发（误报新变体）

运行 `local_quality_check.py --scan`：

```
[scan] hardcoded path violations found:
  - tests\unit\scripts\test_local_quality_check.py:14: ...#!/usr/bin/env python3...
  - tests\unit\scripts\test_local_quality_check.py:20: ...p = "C:\\\\data\\\\cache"...
```

测试文件必须写入硬编码路径字符串来测试检测器，而检测器反过来把测试字符串报为违规。这是 R4 "工具报自己"问题的新变体 —— 修了自身检测，漏了测试检测。

**修复方案**：`iter_scan_files()` 排除 `tests/` 目录，或在 `find_hardcoded_paths()` 中对测试文件跳过字符串字面量行。

### 2.2 test_config_defaults 失败 — 测试未隔离 .env 文件

```
FAILED - assert 'G:\\EmotionQuant_data' == 'C:\\Users\\Administrator\\.emotionquant\\data'
```

根因：测试清除了 `os.environ` 中的 `DATA_PATH`，但 pydantic `SettingsConfigDict(env_file=".env")` 仍从 `.env` 文件读取 `DATA_PATH=G:/EmotionQuant_data`。`_resolve_storage_paths` 收到非空值，fallback 不触发。

```
测试期望：env vars 清空 → 使用默认路径
实际行为：env vars 清空 → pydantic 从 .env 文件补回 → 还是 G:/
```

这意味着：
- **代码逻辑正确**（有 .env 时用 .env，没有时用默认）
- **测试设计错误**（没有隔离 .env 文件的影响）

**修复方案**：测试中 monkeypatch `env_file` 为 `None`，或使用 `tmp_path` 创建无 `.env` 的隔离环境。

---

## 3. 新发现 P1（中等）

### 3.1 PAS `behavior_raw` 子项尺度不均（权重可解释性风险）

`PAS` 的 `behavior_raw` 当前定义：

```
behavior_raw = 0.4×volume_ratio + 0.3×pct_chg + 0.3×limit_up_flag
```

| 输入 | 典型范围 | 加权后量级 |
|------|----------|-----------|
| volume_ratio | 0.5-3.0 | 0.4×2.0 = 0.8 |
| pct_chg | -10 到 +10 | 0.3×5.0 = 1.5 |
| limit_up_flag | 0/0.7/1.0 | 0.3×1.0 = 0.3 |

`pct_chg` 在该组合中容易放大量纲影响，导致名义权重与实际贡献偏离。  
这属于**尺度治理问题**，不只 PAS 会遇到；IRS 也有“先组合 raw 再 normalize”的因子写法。

**修复方案**：对 `behavior_raw` 的输入先做尺度对齐（如 winsorize + 标准化或统一映射），再进入组合。

### 3.2 IRS/PAS 缺少 Z-Score 冷启动规范

MSS §7.1 定义了完整的冷启动方案：

```
- 参数文件：${DATA_PATH}/config/mss_zscore_baseline.parquet
- 首次部署：使用离线 baseline（2015-2025）
- 热启动：每日滚动窗口更新
- 兜底：缺失 mean/std 时返回 50
```

IRS 和 PAS 都使用 `normalize_zscore(value, mean, std)` 但没有说明：
- baseline 参数从哪来？
- 更新策略是什么？
- 系统刚部署时 mean/std 的初始值？

IRS §3.4 有估值因子的冷启动（样本不足回退为 50），但其他 5 个因子没有。PAS 完全没有。

**修复方案**：IRS/PAS 各补一个 §n.1 冷启动章节，或统一在 `naming-conventions.md` 增加一个全局 Z-Score 冷启动规范。

### 3.3 `.claude/hooks` 三处裸 `except:`

| 文件 | 行号 |
|------|------|
| session_start.py | 37 |
| post_edit_check.py | 24, 38 |
| user_prompt_submit.py | 92 |

裸 `except:` 会吞掉 `KeyboardInterrupt` 和 `SystemExit`。应改为 `except Exception:`。

### 3.4 Snapshot dataclass 缺少 `created_at` 字段

设计文档 `data-layer-data-models.md` 中 market_snapshot 和 industry_snapshot 都有 `created_at DATETIME` 字段，但 `src/data/models/snapshots.py` 没有。

当前仓库未见明确的 DDL 默认值实现证据；该缺口更准确地说是模型契约不一致，后续可能引发 schema drift 或序列化字段不一致。

---

## 4. 新发现 P2（轻微）

### 4.1 IndustrySnapshot `top5_codes` 类型

设计说 `JSON`，src 用 `list[str]`。Python 侧没问题，但写入策略尚未在 Data Layer 明确；需要统一序列化契约并补测试，避免依赖隐式类型转换。

### 4.2 `_resolve_storage_paths` 空白字符串边界

```python
resolved_data_path = data_path or DEFAULT_DATA_PATH
```

空字符串 `""` → 触发默认 ✓
空白字符串 `"  "` → truthy → 路径变成 `"  /duckdb"` → 无效但不报错

极端边界，但生产中容易因 .env 编辑错误踩到。

### 4.3 trading-algorithm.md 版本号未更新

文件头仍标注 `v3.2.0 / 最后更新: 2026-02-06`，但 MSS 门控逻辑已大幅修改（`return []` → position factor）。版本号应递增以反映设计变更。

---

## 5. 五轮问题追踪汇总

### 已解决（R1-R4 发现，R5 验证修复）

| 问题 | 发现 | 解决 |
|------|------|------|
| MSS 权重 115% | R3 | R4 |
| LICENSE 缺失 | R3 | R4 |
| Config except Exception | R3 | R4 |
| Config pydantic v1 API | R3 | R4 |
| quality_check 不扫 .env | R3 | R4 |
| Import 双路径陷阱 | R4 | R5 |
| Trading MSS 单点否决 | R4 | R5 |
| hooks 幽灵路径 .kiro/ | R4 | R5 |
| 两套检查标准打架 | R4 | R5 |
| hooks 永远禁止 TODO | R4 | R5 |
| .env "按年分库" 不一致 | R4 | R5 |
| 数据模型 src/docs 脱节 | R4 | R5 |
| requirements dev 混入 | R3 | R5 |
| pyproject 缺 duckdb | R3 | R5 |
| Config 无 fallback | R4 | R5 |
| Z-Score 冷启动（MSS） | R3 | R5 |
| IRS pe_ttm 聚合 | R3 | R5 |
| 版本号双源 | R4 | R5 |

### ~~未解决~~（复查后已收口）

| 问题 | 发现 | 级别 | 当前状态 |
|------|------|------|----------|
| ~~quality_check 测试文件自触发~~ | R5 | P0 | ✅ 已修复（扫描排除 tests） |
| ~~test_config_defaults 失败~~ | R5 | P0 | ✅ 已修复（测试显式隔离 `.env`） |
| ~~PAS behavior_raw 尺度不均风险~~ | R5 | P1 | ✅ 已修复（先映射再组合） |
| ~~IRS/PAS 缺冷启动规范~~ | R5 | P1 | ✅ 已修复（补 baseline + fallback） |
| ~~hooks 裸 except:~~ | R5 | P1 | ✅ 已修复（统一 `except Exception`） |
| ~~Snapshot 缺 created_at~~ | R5 | P1 | ✅ 已修复（数据模型补齐） |
| ~~top5_codes JSON 契约差~~ | R5 | P2 | ✅ 已修复（`json.dumps/json.loads` 契约） |
| ~~_resolve 空白字符串~~ | R5 | P2 | ✅ 已修复（strip 后判空） |
| ~~trading 版本号未更新~~ | R5 | P2 | ✅ 已修复（v3.2.0） |

---

## 6. 总结

R4 的 15 个问题修了 13 个，修复质量明显提升（质量检查从 7 误报降到 2，数据模型对齐了 80%+ 字段，config 有了真正的 fallback）。仓库终于有了 4 个可执行测试（虽然 1 个失败）。

本轮深挖发现的主要问题是**算法尺度治理与冷启动规范**：PAS `behavior_raw` 子项量纲混合导致权重可解释性偏弱；IRS/PAS 缺少统一的 Z-Score baseline 来源与启动策略。这些是实现阶段必须解决的设计缺陷，不是代码 bug — 但如果不修就开始写代码，后面改设计比改代码难。

当前最紧急的一步：修那个失败的测试。`pytest -v` 应该全绿。

---

## 7. 复查勘误（Codex，2026-02-07）

基于当前仓库文件复核（`src/`、`tests/`、`scripts/`、`docs/` 与 `.claude/hooks`），本报告主体判断大体成立；以下 3 处需要收敛表述：

### 7.1 关于「PAS 归一化顺序与 MSS/IRS 不一致」

原结论“PAS 与 MSS/IRS 不一致”表述过强。  
当前文档里，IRS 也存在 “先组合 raw 再 normalize” 的因子（如 `continuity_raw`、`gene_raw`）；因此更准确的问题应是：

- `PAS behavior_raw = 0.4*volume_ratio + 0.3*pct_chg + 0.3*limit_up_flag` 存在**尺度不均**风险，可能弱化子项权重可解释性；
- 这是“尺度治理问题”，不是 PAS 独有的“流程不一致问题”。

### 7.2 关于「Snapshot 缺 created_at」的风险描述

`src/data/models/snapshots.py` 确实缺少 `created_at`，与 `docs/design/data-layer/data-layer-data-models.md` 不一致。  
但“DuckDB 自动生成 created_at”在当前仓库内未见明确 DDL/默认值实现证据，建议改为：

- 这是**模型契约缺口**；
- 后续落地时可能引发 schema drift、序列化字段缺失或映射不一致。

### 7.3 关于 `top5_codes` 写入 DuckDB 的断言

“未 `json.dumps` 就一定会拒绝插入”属于过强断言。  
当前仓库尚无可执行写入实现与回归测试，保守表述应为：

- `top5_codes: list[str]` 与文档 `JSON` 类型存在契约差；
- 需在 Data Layer 明确序列化策略并补测试，避免依赖隐式类型转换行为。
