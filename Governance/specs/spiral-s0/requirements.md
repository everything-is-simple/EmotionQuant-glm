# Spiral S0 Requirements

## 1. 目标

完成数据最小闭环：至少一条数据链路可运行、可测试、可产物化，并满足铁律检查。

## 2. In Scope

- 单日数据拉取：TuShare `daily`（按 `trade_date`）
- 本地数据落盘：Parquet 文件
- 仓库读取验证：从落盘文件读取并输出摘要
- 本地质量检查：硬编码路径检查 + Git 会话状态检查
- 最小自动化测试（至少 2 条）

## 3. Out Scope

- 多源并发调度
- 全市场全量补采
- 回测与交易链路

## 4. 闭环证据

### 4.1 run（必须可复制）

- `.\.venv\Scripts\python.exe scripts/quality/local_quality_check.py --session --scan`
- `.\.venv\Scripts\python.exe -m src.pipeline.main --trade-date 20260206`

### 4.2 test（至少一条自动化）

- `.\.venv\Scripts\pytest.exe tests/unit/data -q`

### 4.3 artifact（必须可检查）

- `artifacts/s0/raw_daily_20260206.parquet`
- `artifacts/s0/run-summary-20260206.json`

## 5. 风险

- TuShare token 不可用
- 本地路径未配置

## 6. 约束与口径

- TuShare 密钥只允许通过环境变量 `TUSHARE_TOKEN` 注入。
- 禁止在文档、代码、脚本中写入明文 API Key。
- 路径通过 Config/env 管理，禁止硬编码绝对路径。

## 7. 执行拆分（1 天内）

1. 实现 `src/data/fetcher.py` 最小可用拉取逻辑。
2. 实现 `src/data/repositories/daily.py` 最小读写逻辑。
3. 实现 `src/pipeline/main.py` 最小 S0 入口。
4. 增加 `tests/unit/data/test_fetcher.py` 与 `tests/unit/data/test_daily_repo.py`。
5. 跑通 run/test 并写入 `review.md` 与 `final.md`。
