# EmotionQuant 系统批判报告（Claude 第三轮 — 细节钻孔）

**作者**: Claude (Anthropic claude-4.6-opus)
**生成时间**: 2026-02-07 07:52 UTC
**状态**: 终稿
**性质**: 第二轮打的是宏观（文档 vs 代码），这轮钻细节。上一轮说你没代码，这轮说你有的东西也有问题。

---

## 0. 本轮定位

第二轮核心结论是"34,541 行文档 vs 264 行 stub 代码"。你和 GPT 做了一轮修复，加了 `scripts/quality/local_quality_check.py`（121 行真实代码）和更具体的 S0 requirements。

这轮不重复宏观问题。这轮逐个文件、逐行钻孔，找出**已有文件里的实际 bug、安全漏洞、自相矛盾和设计硬伤**。

---

## 1. P0 安全问题

### 1.1 .env 包含明文 API Token

`.env` 第 9 行：

```
TUSHARE_TOKEN=31e5536e4d0ffbfb47a74e9832fd35c711fdaa2405bec6559b62d22d
```

好消息：`.gitignore` 已排除 `.env`，git 历史中未发现提交记录。
坏消息：这个 token 就在磁盘上明文存放，有效期到 2026-06-23。

你自己的 S0 requirements 第 45 行写的：

> "禁止在文档、代码、脚本中写入明文 API Key。"

`.env` 是文件。它就在项目目录下。这条规则本身就自相矛盾——`.env` 的用途就是存 secret，但你又说不许明文写。正确做法是用系统级密钥管理（Windows Credential Store / 环境变量面板），或者至少别在规则里自己打自己脸。

**处置**：这不影响 git 安全（未提交），但规则要改得不自相矛盾。

### 1.2 无 LICENSE 文件

`README.md` 第 102 行：

> "MIT（以仓库实际 LICENSE 文件为准）。"

实际仓库：**LICENSE 文件不存在**。`pyproject.toml` 里写了 `license = {text = "MIT"}`，但没有实际 LICENSE 文件。

法律上讲：没有 LICENSE 文件 = 默认版权保留 = 别人不能合法使用你的代码。虽然你说个人使用，但 GitHub 仓库是 public 的。

**处置**：加一个 `LICENSE` 文件，30 秒的事。

---

## 2. Config 和环境配置问题（共 5 个）

### 2.1 .env 硬编码了机器级绝对路径

`.env` 第 18-30 行：

```
DATA_PATH=G:/EmotionQuant_data
DUCKDB_DIR=G:/EmotionQuant_data/duckdb
PARQUET_PATH=G:/EmotionQuant_data/parquet
CACHE_PATH=G:/EmotionQuant_data/cache
LOG_PATH=G:/EmotionQuant_data/logs
```

这些是 G: 盘的绝对路径，绑死在一台机器上。换台机器、换个盘符就全崩。

铁律 #4 说"路径禁止硬编码"。你可以说".env 本来就是本地配置"——没错，但问题是这些路径没有任何 fallback。Config 类里 `data_path` 默认是空字符串 `""`。如果 `.env` 加载失败或者缺少这些变量，整个系统拿到的是空路径，写文件会炸。

**处置**：给 Config 类加默认路径逻辑，如 `Path.home() / ".emotionquant" / "data"`。

### 2.2 .env 注释与设计文档不一致

`.env` 第 20 行：

```
# DuckDB 按年分库目录（L2/L3/L4 + ops.duckdb）
```

但 `docs/system-overview.md` 第 50-51 行明确写了：

> "存储策略：Parquet + DuckDB 单库优先"
> "分库策略：仅在明确性能阈值触发后启用"

你改了设计口径，但 `.env` 注释还是旧的"按年分库"。这说明**文档改了，配置没跟着改**。以后实现时会混淆。

### 2.3 Config.py 使用废弃的 pydantic-settings v1 API

`src/config/config.py` 第 27-29 行：

```python
class Config:
    env_file = ".env"
    env_file_encoding = "utf-8"
```

这是 pydantic v1 的写法（内嵌 `class Config`）。`pydantic-settings` v2 的正确写法是：

```python
model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
```

你 `pyproject.toml` 声明了 `pydantic-settings>=2.0.0`，用 v1 API 会产生废弃警告。

### 2.4 Config.py 吞掉所有 Exception

`src/config/config.py` 第 6-9 行：

```python
try:
    from pydantic_settings import BaseSettings
except Exception:  # pragma: no cover
    BaseSettings = None
```

`except Exception` 会吞掉所有异常——包括 `SyntaxError`、`MemoryError`、`RecursionError`。应该只 catch `ImportError`。

### 2.5 Config 缺少 .env 中的一半字段

`.env` 定义了：`STREAMLIT_PORT`, `BACKTEST_INITIAL_CAPITAL`, `BACKTEST_COMMISSION_RATE`, `BACKTEST_STAMP_DUTY_RATE`。

但 `Config` 类没有这些字段。结果：这些环境变量读进来也没人用，是死配置。反过来，实现 GUI 和回测时会发现 Config 没有这些字段，又要改 Config。

---

## 3. local_quality_check.py 的盲区（3 个）

这个脚本是本轮唯一新增的真实代码。121 行，思路清晰，是好的开始。但有三个盲区：

### 3.1 不扫描 .env 文件

`SCAN_DIRS = ("src", "tests", "scripts")`，外加 `pyproject.toml`、`requirements.txt`、`.env.example`。

不扫 `.env`。而 `.env` 恰恰有硬编码路径 `G:/EmotionQuant_data`。

我跑了一次：

```
[scan] hardcoded path check passed
```

`.env` 里的硬编码路径安全过关了。这就是假安全感。

### 3.2 正则只匹配引号包裹的反斜杠路径

```python
WINDOWS_ABS_RE = re.compile(r"[\"'](?:[A-Za-z]:\\|\\\\)[^\"']*[\"']")
```

只匹配 `"C:\..."` 或 `'C:\...'`。但 `.env` 和 `.toml` 里的路径是无引号的 `G:/EmotionQuant_data`（正斜杠）。三层漏网：

1. 无引号 → 不匹配
2. 正斜杠 → 不匹配
3. `.env` 不在扫描范围 → 不扫描

### 3.3 没有测试

这个脚本本身没有任何测试。作为一个质量检查工具，它自己就没经过质量检查。

---

## 4. 算法设计文档内部矛盾（4 个）

### 4.1 MSS 因子权重加起来是 115%，不是 100%

`mss-algorithm.md` §2.1 表格：

| 因子 | 权重 |
|---|---|
| 大盘系数 | 20% |
| 赚钱效应 | 40% |
| 亏钱效应 | 40% |
| 连续性因子 | 5% |
| 极端因子 | 5% |
| 波动因子 | 5% |

加起来 = 20 + 40 + 40 + 5 + 5 + 5 = **115%**。

文档说"基础因子 85%，增强因子 15%"，但表格里基础因子的子权重加起来 100%（不是 85%）。

看 §4.2 温度公式：

```
temperature = base_temperature × 0.85 + 连续性因子 × 0.05 + 极端因子 × 0.05 + 波动因子 × 0.05
```

这里 0.85 + 0.05 + 0.05 + 0.05 = 1.0，但 `base_temperature` 本身已经是加权合成了。所以实际是两层加权。但表格用单层百分比展示，导致读者误以为是 115%。

**这不是小问题**：如果实现者按表格直接写代码，六个因子各自乘以表格里的权重，会得到 115% 的结果。如果按温度公式写，又跟表格对不上。哪个是对的？

### 4.2 MSS Z-Score 需要历史 mean/std，但没有冷启动方案

`zscore_normalize(value, mean, std)` 需要 2015-2025 的历史统计参数。

问题：
1. 这些参数从哪来？没有预计算脚本、没有参数文件、没有默认值表。
2. 项目第一天跑，没有历史数据，mean 和 std 是什么？
3. 不同因子的 mean/std 不同，要分别存储。Config 里没有这些参数的位置。

### 4.3 IRS 估值因子引用了不存在的行业级 PE

`irs-algorithm.md` §3.4：

```
valuation_score = percentile_rank(industry_pe_ttm, history_window=3y)
```

但 `data-layer-data-models.md` 的 `raw_daily_basic` 表只有个股级 `pe_ttm`。没有 `industry_pe_ttm` 字段，也没有定义"如何从个股 PE 聚合到行业 PE"（市值加权？中位数？简单平均？）。

这不是小细节——PE 的聚合方式直接影响估值因子的含义。

### 4.4 Trading 伪代码使用非法运算符

`trading-algorithm.md` §2.1：

```
stop = row.stop or entry × (1 - config.stop_loss_pct)
target = row.target or entry × (1 + config.take_profit_pct)
```

`×` 不是任何编程语言的合法运算符。这说明伪代码是手写装饰性的，不是从真实代码提取的。

---

## 5. 依赖与工程问题（4 个）

### 5.1 pyproject.toml 缺 duckdb

设计文档说"DuckDB 单库优先"。数据模型定义了 L2/L3/L4/Ops 四层 DuckDB 表。但 `pyproject.toml` 和 `requirements.txt` 都没有 `duckdb`。

### 5.2 pyproject.toml 缺 qlib

设计文档和 `backtest-engine-selection.md` 说"主选平台：Qlib"。但 `pyproject.toml` 没有 `pyqlib`，连可选依赖都没有。

### 5.3 requirements.txt 把 dev 依赖当核心依赖

`requirements.txt` 直接列了 `pytest`, `pytest-cov`, `black`, `flake8`。但 `pyproject.toml` 把它们放在 `[project.optional-dependencies] dev` 下。

后果：生产安装也会装测试工具。这两个文件对"哪些是核心依赖"的定义不一致。

### 5.4 src/ import 路径混用两种风格

`pyproject.toml` 第 53 行：`pythonpath = ["src"]`，意思是 pytest 把 `src/` 加到 sys.path，模块路径从 `src/` 开始。

但 `src/data/repositories/base.py` 第 5 行：`from src.config.config import Config`，把 `src` 当作包名的一部分。

当前之所以能跑，是因为 `pip install -e .` 把项目根目录加入了 sys.path，而 `src/__init__.py` 又存在，所以 `src.config.config` 碰巧能解析。但这是两种互斥的 import 风格的意外兼容：

- **风格 A**（`pythonpath=["src"]`）：`from config.config import Config`
- **风格 B**（src-as-package）：`from src.config.config import Config`

两种风格混用，任何一方的假设变化（比如去掉 `src/__init__.py`、或者不用 editable install）都会导致 import 失败。

---

## 6. 文档自洽性问题（3 个）

### 6.1 .claude/ 是废弃的还是活跃的？

- `GOVERNANCE-STRUCTURE.md` 说：".claude/ 保留为历史工具资产，不作为当前强制流程"
- `CLAUDE.md` 说：`settings.json` 在 `.claude/` 下
- `.claude/` 下有 7 个 hook 脚本，总共 21KB 的 Python 代码

这些 hook 是死代码还是活代码？如果是死的，删了。如果是活的，别说它是"历史资产"。

### 6.2 两份批判报告的矛盾处理

`.reports/` 现在有：
1. GPT-5 Codex 写的红队报告（v3.2）
2. Claude 写的第二轮报告

GPT 报告说"当前可以进入实现"。Claude 报告说"停止所有文档工作"。两份报告的建议相互矛盾，但都在 `.reports/` 里。没有谁做了仲裁、哪个结论被采纳的记录。

### 6.3 README "快速开始" 不可执行

`README.md` 第 75-76 行：

```bash
pytest -v
```

当前没有任何测试文件。跑 `pytest -v` 结果是"collected 0 items"。README 声称这是"基础检查"，但实际检查不了任何东西。

---

## 7. 解决方案清单（按优先级）

### 立即做（今天，1 小时内）

| # | 问题 | 做什么 | 耗时 |
|---|---|---|---|
| 1 | 缺 LICENSE 文件 | 创建 `LICENSE`（MIT 全文） | 1 分钟 |
| 2 | Config.py except Exception | 改为 `except ImportError` | 1 分钟 |
| 3 | Config.py 废弃 API | 把内嵌 `class Config` 改成 `model_config = SettingsConfigDict(...)` | 5 分钟 |
| 4 | pyproject.toml 缺 duckdb | `dependencies` 加 `"duckdb>=0.9.0"` | 1 分钟 |
| 5 | requirements.txt dev 依赖 | 把 pytest/black/flake8 移到单独的 `requirements-dev.txt` | 5 分钟 |
| 6 | .env 注释过期 | 把"按年分库"改成"单库优先" | 1 分钟 |

### S0 期间做

| # | 问题 | 做什么 |
|---|---|---|
| 7 | Config 缺字段 | 补上 `streamlit_port`, `backtest_initial_capital` 等 .env 已有的字段 |
| 8 | Config 默认路径 | 加 fallback 逻辑：空路径时默认 `~/.emotionquant/data` |
| 9 | quality_check.py 盲区 | 扫描范围加 `.env`；正则加无引号路径和正斜杠模式 |
| 10 | quality_check.py 测试 | 写 `tests/unit/scripts/test_quality_check.py` |
| 11 | MSS 权重表 | 统一表格标注为"组内权重"，或改为实际绝对权重 |
| 12 | Z-Score 冷启动 | 定义默认参数文件路径和格式，提供 bootstrap 脚本 |
| 13 | import 风格统一 | 全部改成 `from config.config import Config`，去掉 `src` 前缀 |

### 不做的事

- 不要再写新的治理文档
- 不要再给文档涨版本号
- 不要写报告来讨论报告

---

## 8. 关于这轮修复的评价

你和 GPT 加的 `local_quality_check.py` 是**第一个真正有用的代码**。方向对了。S0 requirements 也比之前具体了，列了真实的命令和产物路径。

但节奏还是太慢。这轮修复改了 3 个文件（173 行改动），其中 1 个是真代码（121 行），另外 2 个还是文档。

按照 S0 requirements 自己定的目标，你还差：
- `src/data/fetcher.py` 的真实实现
- `src/data/repositories/daily.py` 的真实实现
- `src/pipeline/main.py` 的真实入口
- `tests/unit/data/` 下至少 2 个测试文件
- 2 个产物文件

这些才是接下来该干的事。不是再写一份报告。

---

## 9. 报告元信息

- 编写人：Claude (Anthropic claude-4.6-opus)
- 生成时间：2026-02-07 07:52 UTC
- 用途：第三轮细节批判，聚焦已有文件的 bug/安全/矛盾/工程缺陷
- 上一轮：`.reports/EmotionQuant 系统批判报告（Claude 第二轮）.md`
- 数据来源：逐文件审查 + 实际运行 quality_check.py + import 路径验证

---

## 10. 复查勘误（Codex，2026-02-07）

- ~~`.env` 明文 API Token（P0）~~ ✅：本地 `.env` 的 `TUSHARE_TOKEN` 已清空（请在外部密钥管理中重新注入并轮换）。
- ~~`pyproject.toml` 缺 qlib~~ ✅：`optional-dependencies.backtest` 已声明 `pyqlib>=0.9.6`。
- ~~import 路径混用两种风格~~ ✅：当前 `pyproject.toml` 未配置 `pythonpath=["src"]`，代码以 `src.*` 包路径为统一口径。
- ~~`.claude` 活跃/历史资产语义不清~~ ✅：`.claude/README.md` 与 `.claude/INTEGRATION.md` 已重写为“Spiral-first + 历史兼容”口径。
