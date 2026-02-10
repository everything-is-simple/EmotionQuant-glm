# EmotionQuant 系统批判报告（Claude 第四轮 — 细节深挖）

**作者**: Claude (Warp Agent Mode, claude 4.6 opus max)
**时间**: 2026-02-07 08:53 UTC
**基线**: develop 分支
**聚焦**: 细节级别的交叉矛盾、工具自相矛盾、数据模型断层

---

## 0. 当前仓库体检数据

| 类别 | 文件数 | 总行数 | 说明 |
|------|--------|--------|------|
| docs/ | 59 md | 15,366 | 设计文档 |
| Governance/ | 62 md | 9,297 | 治理文档 |
| .claude/ | 16 md | 1,843 | Claude Code 配置文档 |
| **文档合计** | **137** | **26,506** | — |
| src/ | 28 py | 212 | 源码（config.py 74行有逻辑，其余全 stub） |
| tests/ | 9 py | 12 | 全是空 `__init__.py` |
| scripts/ | 1 py | 126 | quality_check（唯一真正可执行代码） |
| **代码合计** | **38** | **350** | 真正有逻辑的约 200 行 |

**文档:代码 = 76:1**

---

## 1. 第三轮修复验证

### 已修复

| 问题 | 状态 |
|------|------|
| MSS 权重 115% | 修正为 17+34+34+5+5+5=100% |
| LICENSE 缺失 | 已添加 MIT |
| Config.py `except Exception` | 改为 `except ImportError` |
| Config.py pydantic v1 内部类 | 改为 `SettingsConfigDict(...)` |
| Config.py 缺少字段 | 新增 streamlit_port / backtest_* |
| quality_check.py 不扫描 .env | 现在扫描了 |

### ~~未修复（遗留）~~（复查后已收敛）

| 问题 | 说明 |
|------|------|
| ~~`requirements.txt` dev 依赖混入核心~~ | ✅ 已修复：开发依赖迁移为 `requirements-dev.txt` 口径 |
| ~~`pyproject.toml` 缺 duckdb~~ | ✅ 已修复：已显式加入 duckdb 依赖 |
| ~~Config 空字符串默认值~~ | ✅ 已修复：空白字符串会 strip 后回退默认路径 |
| ~~Z-Score 冷启动未定义~~ | ✅ 已修复：IRS/PAS 文档补齐 baseline/fallback 规则 |
| ~~IRS `industry_pe_ttm` 聚合方式未定义~~ | ✅ 已修复：已定义过滤、winsorize 与中位数聚合 |
| ~~README `pytest -v` 收集 0 个测试~~ | ✅ 已修复：已新增有效单元测试 |
| ~~quality_check.py 无自测试~~ | ✅ 已修复：已补测试覆盖关键边界 |

---

## 2. 新发现 P0（严重）

### 2.1 quality_check.py 产生 7 个误报、0 个真报

运行 `local_quality_check.py --scan` 完整输出：

```
[scan] hardcoded path violations found:
  - scripts\quality\local_quality_check.py:1: #!/usr/bin/env python3
  - scripts\quality\local_quality_check.py:24: r"(?:[\"'](?:[A-Za-z]:...
  - .env:18: DATA_PATH=G:/EmotionQuant_data
  - .env:21: DUCKDB_DIR=G:/EmotionQuant_data/duckdb
  - .env:24: PARQUET_PATH=G:/EmotionQuant_data/parquet
  - .env:27: CACHE_PATH=G:/EmotionQuant_data/cache
  - .env:30: LOG_PATH=G:/EmotionQuant_data/logs
```

全部 7 条都是误报：

| 误报 | 原因 |
|------|------|
| shebang `#!/usr/bin/env python3` | UNIX_ABS_RE 匹配了 `/usr/` |
| 正则字符串自身 | WINDOWS_ABS_RE 匹配了自己的模式定义 |
| .env 的 5 条路径 | `.env` 本身就是配置注入点，铁律要求路径写在这里 |

质量检查工具当前状态：**既不能抓真问题（src/ 全是 stub），又在误报自己和配置文件**。比不存在更糟——它训练用户忽略告警。

**修复方案**：
1. `iter_scan_files()` 排除 `.env`（只扫 `.env.example`）
2. `find_hardcoded_paths()` 排除 shebang 行（`line.startswith("#!")`）
3. 排除正则定义行或换用编译后变量间接引用
4. 给 quality_check.py 写测试覆盖这三个 case

---

### 2.2 Import 路径双重陷阱

`src/data/repositories/base.py:5`：

```python
from src.config.config import Config
```

`pyproject.toml:53`：

```toml
pythonpath = ["src"]
```

两个设置同时存在：
- 项目根目录在 sys.path → `from src.config.config import Config` 可用
- src/ 在 sys.path → `from config.config import Config` 可用

同一个 Config 类两条导入路径，Python 会创建两个内存副本。后果：
- `isinstance` 跨模块检查失败
- 单例模式失效
- 调试时 import 追踪混乱

这是 Python 的经典 dual-import trap，一旦写真正代码和测试就会中招。

**修复方案**（二选一）：
- A）去掉 `src/__init__.py`，统一用 `pythonpath=["src"]`，import 写 `from config.config import Config`
- B）去掉 `pythonpath=["src"]`，统一用包路径 `from src.config.config import Config`

---

### 2.3 Trading 算法 MSS 单点否决违反同权协同铁律

`trading-algorithm.md` 2.1 第一步：

```
if mss.temperature < config.min_mss_temperature:
    return []  # 市场过冷，不产生信号
```

MSS 温度低于阈值时 IRS 和 PAS 完全不起作用，直接返回空。

但系统铁律-铁律二明确要求：

> MSS/IRS/PAS 三算法同权协同，集成层不得以单算法硬否决

`integration-algorithm.md` 5.3 已修正为"不做单点否决，仅影响风险与权重"，但 Trading 层绕过了集成层的协同设计，直接做了 MSS 硬否决。

**修复方案**：MSS 温度门控改为仓位约束（极低温时 position_size 下调），而非 `return []`。

---

### 2.4 .claude/hooks 引用不存在的路径

`.claude/hooks/pre_edit_check.py:61`：

```python
status_file = PROJECT_ROOT / ".kiro" / "development-status.md"
```

`.kiro/` 目录在仓库中不存在。后果：
- `detect_current_stage()` 永远返回 `"A5"`
- `FORBIDDEN_KEYWORDS`（TODO/FIXME/HACK/mock/placeholder）在所有阶段都执行
- 但 CORE-PRINCIPLES.md 5.2 明确说"开发中允许 TODO/FIXME，合并前清理"

Hook 永远禁止 TODO，与核心原则直接矛盾。

---

### 2.5 两套路径检查工具、两套标准

| 工具 | 位置 | Windows 匹配范围 | .env 扫描 |
|------|------|-------------------|-----------|
| `local_quality_check.py` | scripts/quality/ | 引号内+引号外 | 扫描（误报） |
| `pre_edit_check.py` | .claude/hooks/ | 仅引号内 `["']C:\` | 不扫描 |

同一个仓库两套标准，一个说通过另一个说违规。

**修复方案**：统一为一套。`pre_edit_check.py` 应调用 `local_quality_check.py` 的函数而非自己重写。

---

## 3. 新发现 P1（中等）

### 3.1 .claude/ 目录整体过时

| 项目 | .claude/ 状态 | 实际状态 |
|------|---------------|----------|
| README.md 版本 | v2.1（2026-01-26） | 系统已到 v4.1.0 Spiral |
| 执行模型 | Phase 线性 6A | 已切 Spiral 闭环 |
| settings.json PreToolUse | 指向 `pre_edit_check.py` | README 说指向 `pre_edit_orchestrator.py` |
| agents/kfc/ | 含 7 个 spec-*.md | README 描述 gate-checker 和 task-executor |
| .kiro/ 引用 | 代码中引用 | 目录不存在 |

`.claude/` 是一个"看起来很专业但实际跑不通"的装饰品。700+ 行 README 指导使用根本无法工作的工具链。

### 3.2 .env 注释与设计文档不一致

`.env:20`：
```
# DuckDB 按年分库目录（L2/L3/L4 + ops.duckdb）
```

`system-overview.md:49`：
```
存储策略：Parquet + DuckDB 单库优先
```

`data-layer-data-models.md:35`：
```
L2 Processed Tables（DuckDB 单库优先，阈值触发分库）
```

.env 说"按年分库"，设计文档说"单库优先"。

### 3.3 数据模型 src/ 与 docs/ 完全脱节

| 模型 | src/ 字段数 | docs/ 字段数 | 差距 |
|------|-------------|--------------|------|
| MarketSnapshot | 7 | 26+ | 缺 rise_ratio / strong_up_count / pct_chg_std 等 MSS 核心输入 |
| IndustrySnapshot | 6 | 20+ | 缺 new_high_count / industry_amount 等 IRS 核心输入 |
| StockBasic | 3 | 4+ | 缺 list_date |
| TradeCalendar | 2 | 3 | 缺 pretrade_date |

占位类至少应声明正确的字段（值为 None 也行），否则后续实现第一件事就是改数据模型。

### 3.4 IRS 估值因子聚合黑洞

IRS 3.4：
```
valuation_score = percentile_rank(industry_pe_ttm, history_window=3y)
数据来源：raw_daily_basic
```

`raw_daily_basic` 的 `pe_ttm` 是个股级别。要得到 `industry_pe_ttm` 需要聚合，但未定义：
- 中位数还是均值？（差异可达 50%+）
- 负 PE（亏损股）如何处理？
- 极端值（PE > 1000）是否截断？
- 行业成分股变动时历史回溯如何处理？

估值因子权重 15%，聚合方式直接决定因子值。

---

## 4. 新发现 P2（轻微）

### 4.1 版本号双源

`src/__init__.py:16`：`__version__ = "0.1.0"`
`pyproject.toml:7`：`version = "0.1.0"`

目前一致，但两处维护迟早忘记同步。应用 `importlib.metadata.version()` 单源。

### 4.2 requirements.txt 定位模糊

`pyproject.toml` 已完整定义所有依赖（核心 + optional），`requirements.txt` 把 pytest/black/flake8 放在核心区而非注释掉或分文件，部署时会装不需要的开发工具。

---

## 5. 四轮问题追踪汇总

| 问题 | 发现 | 状态 | 级别 |
|------|------|------|------|
| ~~quality_check 7误报0真报~~ | R4 | ✅ 已修复 | P0 |
| ~~Import 双路径陷阱~~ | R4 | ✅ 已修复 | P0 |
| ~~Trading MSS 单点否决违反铁律~~ | R4 | ✅ 已修复 | P0 |
| ~~.claude/ hooks 引用幽灵路径 .kiro/~~ | R4 | ✅ 已修复 | P0 |
| ~~两套路径检查工具标准不一~~ | R4 | ✅ 已修复 | P0 |
| ~~.claude/ 整体过时~~ | R4 | ✅ 已修复 | P1 |
| ~~.env 注释与设计文档不一致~~ | R3-R4 | ✅ 已修复 | P1 |
| ~~数据模型 src/ 与 docs/ 脱节~~ | R4 | ✅ 已修复 | P1 |
| ~~IRS industry_pe_ttm 聚合未定义~~ | R3-R4 | ✅ 已修复 | P1 |
| ~~requirements.txt dev 依赖混入~~ | R3-R4 | ✅ 已修复 | P1 |
| ~~pyproject.toml 缺 duckdb~~ | R3-R4 | ✅ 已修复 | P1 |
| ~~Z-Score 冷启动未定义~~ | R3-R4 | ✅ 已修复 | P1 |
| ~~Config 空字符串默认值~~ | R3-R4 | ✅ 已修复 | P1 |
| ~~版本号双源~~ | R4 | ✅ 已修复 | P2 |

当前剩余未修复：**0 项**。

---

## 6. 一句话总结

第三轮修了表面（权重算错、API 过时），第四轮深挖发现：工具链自相矛盾（quality_check 报自己违规、hook 引用幽灵路径、两套标准打架）、设计文档内部有逻辑冲突（铁律说同权协同但 Trading 做单点否决）、数据模型 stub 与设计完全脱节（7 字段 vs 26 字段）。建议停下来用一周只做一件事：让 `pytest -v` 跑出至少一个真正的绿灯测试。
