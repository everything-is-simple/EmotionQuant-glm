# Data Layer API接口

**版本**: v3.1.2（重构版）
**最后更新**: 2026-02-09
**状态**: 设计完成（对齐 MSS/IRS/PAS/Integration；代码未落地）

---

## 实现状态（仓库现状）

- 当前仓库仅提供骨架/占位实现：`src/data/fetcher.py`（TuShareFetcher）、`src/data/repositories/*`（BaseRepository + L1 Repos）、`src/data/models/*`（简化数据类）。
- 本文档中的 `TuShareClient` / `DataFetcher` / `DataProcessor` / `MarketSnapshotRepository` 等为规划接口，尚未在 `src/` 落地。

---

## 1. API总览

### 1.1 服务层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Data Layer API 架构                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  数据获取层 (DataFetcher)                                        │
│  ├── TuShareClient         TuShare API客户端                    │
│  └── DataFetcher           数据获取服务                          │
│                                                                  │
│  数据处理层 (DataProcessor)                                      │
│  ├── DataProcessor         数据清洗/聚合                         │
│  └── GeneCalculator        基因计算服务                          │
│                                                                  │
│  数据存储层 (DataRepository)                                     │
│  ├── MarketSnapshotRepo    市场快照仓库                          │
│  ├── IndustrySnapshotRepo  行业快照仓库                          │
│  ├── StockGeneRepo         牛股基因仓库                          │
│  └── ResultsRepo           算法结果仓库                          │
│                                                                  │
│  调度层 (Scheduler)                                              │
│  ├── DataScheduler         数据调度器                            │
│  └── TaskExecutor          任务执行器                            │
│                                                                  │
│  质量监控层 (Monitoring)                                         │
│  ├── QualityMonitor        质量监控器                            │
│  └── DataBackfill          数据回填服务                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. TuShareClient API

### 2.1 初始化

```python
from src.data.services.tushare_client import TuShareClient

# 从环境变量初始化
client = TuShareClient.from_env()

# 显式初始化
client = TuShareClient(
    token="your_token",
    rate_limit=120  # 每分钟调用次数
)
```

### 2.2 接口方法

```python
class TuShareClient:
    """TuShare API客户端"""
    
    def get_daily(
        self, 
        trade_date: str,
        ts_code: str = None
    ) -> pd.DataFrame:
        """
        获取日线行情
        
        Args:
            trade_date: 交易日期 YYYYMMDD
            ts_code: 股票代码（可选，不传则获取全部）
        
        Returns:
            DataFrame with columns:
            [ts_code, trade_date, open, high, low, close, 
             pre_close, change, pct_chg, vol, amount]
        """
        pass
    
    def get_daily_basic(
        self,
        trade_date: str
    ) -> pd.DataFrame:
        """
        获取日线基础数据
        
        Returns:
            DataFrame with columns:
            [ts_code, trade_date, turnover_rate, volume_ratio,
             pe_ttm, pe, pb, total_mv, circ_mv]
        """
        pass
    
    def get_limit_list(
        self,
        trade_date: str
    ) -> pd.DataFrame:
        """
        获取涨跌停列表（TuShare接口：limit_list_d）
        
        Returns:
            DataFrame with columns:
            [ts_code, trade_date, name, close, pct_chg,
             limit, fc_ratio, fd_amount, first_time, last_time]
        """
        pass
    
    def get_index_daily(
        self,
        trade_date: str,
        ts_code: str = None
    ) -> pd.DataFrame:
        """
        获取指数日线
        
        Args:
            ts_code: 指数代码（如 000001.SH）
        """
        pass
    
    def get_index_member(
        self,
        index_code: str = None
    ) -> pd.DataFrame:
        """
        获取行业成分股
        
        Args:
            index_code: 行业指数代码（可选）
        """
        pass
    
    def get_trade_calendar(
        self,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        获取交易日历（TuShare接口：trade_cal）
        
        Returns:
            DataFrame with columns:
            [cal_date, is_open, pretrade_date]
        """
        pass
```

---

## 3. DataFetcher API

### 3.1 批量获取

```python
from src.data.services.data_fetcher import DataFetcher

fetcher = DataFetcher(client)

# 获取当日所有数据
result = fetcher.fetch_all(trade_date="20260131")
# result.daily: DataFrame
# result.daily_basic: DataFrame
# result.limit_list: DataFrame（来源 limit_list_d，落库 raw_limit_list）
# result.index_daily: DataFrame
```

### 3.2 增量获取

```python
# 获取日期范围数据
fetcher.fetch_range(
    start_date="20260101",
    end_date="20260131",
    data_types=["daily", "limit_list"]  # limit_list_d → raw_limit_list
)

# 获取缺失数据
missing = fetcher.check_missing(trade_date="20260131")
if missing:
    fetcher.fetch_missing(missing)
```

---

## 4. DataProcessor API

### 4.1 数据清洗

```python
from src.data.services.data_processor import DataProcessor

processor = DataProcessor()

# 标准化日期格式
df = processor.standardize_date(df, column="trade_date")

# 标准化股票代码
df = processor.standardize_ts_code(df)  # 000001.SZ → 000001

# 处理缺失值
df = processor.handle_missing_values(
    df,
    strategy="forward_fill",  # forward_fill/backward_fill/drop/fill_zero
    columns=["close", "vol"]
)

# 异常值处理
df = processor.handle_outliers(
    df,
    column="pct_chg",
    method="clip",  # clip/winsorize/drop
    lower=-11,
    upper=11
)
```

### 4.2 聚合计算

```python
# 生成市场快照
snapshot = processor.aggregate_market_snapshot(
    daily_df=daily_data,
    limit_df=limit_data
)

# 生成行业快照
industry_snapshots = processor.aggregate_industry_snapshots(
    daily_df=daily_data,
    limit_df=limit_data,
    member_df=index_member
)
# 生成 PAS 广度聚合（BU入口，派生表）
# stock_pas_daily 来自 PAS 算法输出
pas_breadth = processor.aggregate_pas_breadth(
    stock_pas_daily=stock_pas_daily
)

# 计算100日新高/新低
new_highs = processor.calculate_new_highs(
    daily_df=daily_data,
    lookback_days=100
)
```

---

## 5. DataRepository API

> 说明：本节为规划接口定义。当前仓库仅落地 L1 仓库骨架：DailyRepository / LimitListRepository / StockBasicRepository / TradeCalendarsRepository。

### 5.1 MarketSnapshotRepository

```python
from src.data.repositories import MarketSnapshotRepository

repo = MarketSnapshotRepository(db_path)

# 保存
repo.save(snapshot: MarketSnapshot)
repo.save_batch(snapshots: List[MarketSnapshot])

# 查询
snapshot = repo.get_by_date(trade_date="20260131")
snapshots = repo.get_range(
    start_date="20260101",
    end_date="20260131"
)

# 获取最新
latest = repo.get_latest()

# 检查存在
exists = repo.exists(trade_date="20260131")
```

### 5.2 IndustrySnapshotRepository

```python
from src.data.repositories import IndustrySnapshotRepository

repo = IndustrySnapshotRepository(db_path)

# 按日期和行业查询
snapshot = repo.get_by_date_industry(
    trade_date="20260131",
    industry_code="801780"
)

# 按日期获取所有行业
snapshots = repo.get_all_industries(trade_date="20260131")

# 按行业获取历史
history = repo.get_industry_history(
    industry_code="801780",
    start_date="20260101",
    end_date="20260131"
)
```

### 5.3 StockGeneRepository

```python
from src.data.repositories import StockGeneRepository

repo = StockGeneRepository(db_path)

# 按股票代码查询
gene = repo.get_by_stock(stock_code="000001")

# 按基因等级筛选
s_level = repo.get_by_level(level="S")
ab_level = repo.get_by_levels(levels=["S", "A", "B"])

# 按评分排序
top_genes = repo.get_top_by_score(limit=50)

# 更新
repo.update(gene: StockGene)
repo.update_batch(genes: List[StockGene])
```

### 5.4 ResultsRepository

```python
from src.data.repositories import ResultsRepository

repo = ResultsRepository(db_path)

# MSS结果
mss = repo.get_mss(trade_date="20260131")
mss_history = repo.get_mss_range(start_date, end_date)

# IRS结果
irs = repo.get_irs(trade_date="20260131", industry_code="801780")
irs_all = repo.get_irs_all_industries(trade_date="20260131")

# PAS结果
pas = repo.get_pas(trade_date="20260131", stock_code="000001")
pas_top = repo.get_pas_top(trade_date="20260131", limit=20)

# 集成结果
integrated = repo.get_integrated_top(trade_date="20260131", limit=20)

# PAS广度聚合（BU入口）
pas_breadth_market = repo.get_pas_breadth_market(trade_date="20260131")
pas_breadth_industries = repo.get_pas_breadth_industries(trade_date="20260131")
```

---

## 6. DataScheduler API

### 6.1 调度器配置

```python
from src.data.services.scheduler import DataScheduler

scheduler = DataScheduler(
    fetcher=fetcher,
    processor=processor,
    repo=repo
)

# 配置每日任务
scheduler.setup_daily_tasks(
    time="16:00",
    timezone="Asia/Shanghai"
)

# 启动调度器
scheduler.start()  # 阻塞运行
scheduler.start_background()  # 后台运行
```

### 6.2 手动执行

```python
from src.data.services.scheduler import TaskExecutor

executor = TaskExecutor(scheduler)

# 执行单个任务
result = executor.run_task("download_daily")
result = executor.run_task("calculate_snapshot")
result = executor.run_task("calculate_pas")
result = executor.run_task("calculate_pas_breadth")

# 执行完整流水线
executor.run_pipeline(trade_date="20260131")

# 重试失败任务
executor.retry_failed(trade_date="20260131")
```

---

## 7. QualityMonitor API

### 7.1 质量检查

```python
from src.monitoring import QualityMonitor

monitor = QualityMonitor()

# 执行全量检查
result = monitor.run_full_check(
    tables=["daily", "limit_list", "trade_cal"]
)

# 执行单项检查
completeness = monitor.check_completeness(trade_date="20260131")
accuracy = monitor.check_accuracy(trade_date="20260131")
consistency = monitor.check_consistency(trade_date="20260131")
timeliness = monitor.check_timeliness()

# 生成报告
report = monitor.generate_report(result, format="markdown")
```

### 7.2 数据回填

```python
from src.backfill import DataBackfill

backfill = DataBackfill()

# 执行回填
result = backfill.backfill(
    table_name="daily",
    start_date="20260101",
    end_date="20260131"
)

# 回滚
backfill.rollback(task_id=result.task_id)

# 检查回填状态
status = backfill.get_status(task_id=result.task_id)
```

---

## 8. 数据就绪检查 API

### 8.1 就绪检查器

```python
from src.data.services.readiness_checker import DataReadinessChecker

checker = DataReadinessChecker(db)

# 检查数据就绪性
report = checker.check(trade_date="20260131")

if report.is_ready:
    print("数据就绪，可以执行算法")
else:
    print(f"缺失数据: {report.missing_data}")
    print(f"过期数据: {report.stale_data}")
    print(f"质量问题: {report.quality_issues}")
```

### 8.2 报告结构

```python
@dataclass
class ReadinessReport:
    trade_date: str
    is_ready: bool
    missing_data: List[str]  # 缺失的数据类型
    stale_data: List[str]    # 过期的数据类型
    quality_issues: List[str]  # 质量问题
    check_time: datetime
```

---

## 9. 股票代码转换工具

> **设计目标**：统一 L1（TuShare `ts_code`）与 L2+（内部 `stock_code`）的代码转换逻辑，避免转换代码分散。

### 9.1 工具函数

```python
from src.data.utils.code_converter import (
    normalize_code,
    to_ts_code,
    infer_exchange,
    normalize_codes,
)

# 单值转换：ts_code → stock_code
stock_code = normalize_code("000001.SZ")  # → "000001"
stock_code = normalize_code("600519.SH")  # → "600519"
stock_code = normalize_code("000001")     # → "000001" (已是内部格式，原样返回)

# 单值转换：stock_code → ts_code
ts_code = to_ts_code("000001", exchange="SZ")  # → "000001.SZ"
ts_code = to_ts_code("600519", exchange="SH")  # → "600519.SH"
ts_code = to_ts_code("000001")  # → "000001.SZ" (自动推断交易所)

# 推断交易所
exchange = infer_exchange("000001")  # → "SZ"
exchange = infer_exchange("600519")  # → "SH"
exchange = infer_exchange("300750")  # → "SZ" (创业板)
exchange = infer_exchange("688001")  # → "SH" (科创板)

# 批量转换
stock_codes = normalize_codes(["000001.SZ", "600519.SH", "300750.SZ"])
# → ["000001", "600519", "300750"]
```

### 9.2 实现规范

```python
def normalize_code(ts_code: str) -> str:
    """
    将 TuShare 代码转换为内部代码
    
    Args:
        ts_code: TuShare 格式代码（如 000001.SZ）或已是内部格式
    
    Returns:
        6位股票代码（如 000001）
    
    Examples:
        >>> normalize_code("000001.SZ")
        '000001'
        >>> normalize_code("000001")
        '000001'
    """
    if '.' in ts_code:
        return ts_code.split('.')[0]
    return ts_code


def to_ts_code(stock_code: str, exchange: str = None) -> str:
    """
    将内部代码转换为 TuShare 代码
    
    Args:
        stock_code: 6位股票代码
        exchange: 交易所代码（SZ/SH），不传则自动推断
    
    Returns:
        TuShare 格式代码（如 000001.SZ）
    
    Examples:
        >>> to_ts_code("000001", "SZ")
        '000001.SZ'
        >>> to_ts_code("600519")
        '600519.SH'
    """
    if '.' in stock_code:
        return stock_code  # 已是 ts_code 格式
    if exchange is None:
        exchange = infer_exchange(stock_code)
    return f"{stock_code}.{exchange}"


def infer_exchange(stock_code: str) -> str:
    """
    根据股票代码推断交易所
    
    规则:
        - 6/9 开头 → SH（上交所）
        - 0/2/3 开头 → SZ（深交所）
    
    Args:
        stock_code: 6位股票代码
    
    Returns:
        交易所代码（SZ/SH）
    
    Raises:
        ValueError: 无法识别的代码前缀
    """
    code = normalize_code(stock_code)  # 兼容传入 ts_code
    prefix = code[0]
    if prefix in ('6', '9'):
        return 'SH'
    elif prefix in ('0', '2', '3'):
        return 'SZ'
    else:
        raise ValueError(f"无法识别的股票代码前缀: {code}")


def normalize_codes(ts_codes: list) -> list:
    """批量转换 ts_code → stock_code"""
    return [normalize_code(c) for c in ts_codes]
```

### 9.3 使用场景

| 场景 | 输入格式 | 输出格式 | 使用函数 |
|------|----------|----------|----------|
| L1 数据落库 | TuShare API | Parquet | 保持 `ts_code` |
| L1→L2 处理 | Parquet | DuckDB | `normalize_code()` |
| L2+ 内部使用 | DuckDB | DuckDB | 直接使用 `stock_code` |
| 调用 TuShare | DuckDB | TuShare API | `to_ts_code()` |

### 9.4 DataFrame 批量转换

```python
# DataProcessor 中已有的批量方法（内部调用 normalize_code）
df = processor.standardize_ts_code(df)  # 将 ts_code 列转为 stock_code 列
```

---

## 10. 错误处理

### 10.1 异常类型

```python
from src.data.exceptions import (
    DataFetchError,      # 数据获取错误
    DataProcessError,    # 数据处理错误
    DataValidationError, # 数据验证错误
    RateLimitError,      # 限流错误
    ConnectionError,     # 连接错误
)

try:
    data = fetcher.fetch_daily("20260131")
except RateLimitError as e:
    # 限流，等待后重试
    time.sleep(e.retry_after)
    data = fetcher.fetch_daily("20260131")
except DataFetchError as e:
    # 数据获取失败
    logger.error(f"数据获取失败: {e}")
```

### 10.2 重试机制

```python
from src.data.utils import retry_with_backoff

@retry_with_backoff(
    max_retries=3,
    backoff_factor=2,
    exceptions=(RateLimitError, ConnectionError)
)
def fetch_with_retry(trade_date):
    return fetcher.fetch_daily(trade_date)
```

---

## 11. 配置管理

### 11.1 环境变量

```bash
# .env
TUSHARE_TOKEN=your_token
TUSHARE_RATE_LIMIT_PER_MIN=120
DATA_PATH=/path/to/data
DUCKDB_DIR=/path/to/duckdb/    # DuckDB 目录（默认单库）
```

### 11.2 DuckDB 存储结构（单库优先）

```
${DUCKDB_DIR}/
├── emotionquant.duckdb        # 默认主库（L2/L3/L4 + Business Tables）
└── ops.duckdb                 # 运维元数据
```

### 11.3 配置类

```python
from src.config import DataConfig

config = DataConfig.from_env()
# config.tushare_token
# config.rate_limit
# config.data_path
# config.duckdb_dir
# config.flat_threshold  # 默认 0.5（单位：%）

# 获取主库路径（默认单库）
def get_duckdb_path() -> str:
    return f"{config.duckdb_dir}/emotionquant.duckdb"
```

### 11.4 长窗口查询工具（兼容分库）

**背景**：默认单库即可覆盖大多数窗口查询；若后续因性能阈值触发分库，仍需支持跨库聚合查询（如 100 日新高、120 日涨停统计）。

| 算法需求 | 数据跨度 | 年初影响期 |
|----------|----------|------------|
| MSS 100日新高/新低 | ~5个月 | 1-5月需跨年 |
| PAS 120日涨停统计 | ~6个月 | 1-6月需跨年 |
| PAS 60日价格区间 | ~3个月 | 1-3月需跨年 |
| IRS 历史均值/标准差 | 2015-今 | 始终跨年 |

#### 11.4.1 核心函数

```python
import duckdb
import pandas as pd
from typing import Optional, List
from pathlib import Path


def get_year_range(start_date: str, end_date: str) -> List[int]:
    """获取日期范围涉及的年份列表
    
    Args:
        start_date: 开始日期 (YYYYMMDD)
        end_date: 结束日期 (YYYYMMDD)
    
    Returns:
        年份列表，升序排列
    """
    start_year = int(start_date[:4])
    end_year = int(end_date[:4])
    return list(range(start_year, end_year + 1))


def query_cross_year(
    table: str,
    start_date: str,
    end_date: str,
    columns: Optional[List[str]] = None,
    where_clause: Optional[str] = None,
    order_by: Optional[str] = None
) -> pd.DataFrame:
    """跨年查询，自动合并多个 DuckDB 文件
    
    Args:
        table: 表名（如 'market_snapshot', 'mss_score'）
        start_date: 开始日期 (YYYYMMDD)
        end_date: 结束日期 (YYYYMMDD)
        columns: 查询列，None 表示全部
        where_clause: 额外的 WHERE 条件（不含 WHERE 关键字）
        order_by: 排序字段
    
    Returns:
        合并后的 DataFrame
    
    Example:
        # 查询跨年的 100 日数据
        df = query_cross_year(
            table='market_snapshot',
            start_date='20251001',
            end_date='20260131',
            columns=['trade_date', 'index_close', 'up_count'],
            order_by='trade_date'
        )
    """
    config = DataConfig.from_env()
    years = get_year_range(start_date, end_date)
    
    col_str = ', '.join(columns) if columns else '*'
    dfs = []
    
    for year in years:
        db_path = get_duckdb_path(year)
        if not Path(db_path).exists():
            continue
        
        # 构建 SQL
        sql = f"SELECT {col_str} FROM {table} WHERE trade_date BETWEEN ? AND ?"
        if where_clause:
            sql += f" AND ({where_clause})"
        if order_by:
            sql += f" ORDER BY {order_by}"
        
        try:
            conn = duckdb.connect(db_path, read_only=True)
            df = conn.execute(sql, [start_date, end_date]).df()
            conn.close()
            if not df.empty:
                dfs.append(df)
        except duckdb.CatalogException:
            # 表不存在，跳过
            continue
    
    if not dfs:
        return pd.DataFrame()
    
    result = pd.concat(dfs, ignore_index=True)
    
    # 合并后重新排序
    if order_by and order_by in result.columns:
        result = result.sort_values(order_by).reset_index(drop=True)
    
    return result
```

#### 11.4.2 便捷函数

```python
def query_recent_n_days(
    table: str,
    end_date: str,
    n_days: int,
    columns: Optional[List[str]] = None,
    where_clause: Optional[str] = None
) -> pd.DataFrame:
    """查询最近 N 个交易日的数据（自动处理跨年）
    
    Args:
        table: 表名
        end_date: 截止日期 (YYYYMMDD)
        n_days: 需要的交易日数（会多查 30% 余量）
        columns: 查询列
        where_clause: 额外条件
    
    Returns:
        最近 N 个交易日的数据
    
    Example:
        # 查询最近 100 个交易日的市场快照
        df = query_recent_n_days(
            table='market_snapshot',
            end_date='20260131',
            n_days=100
        )
    """
    # 估算日历日数（交易日约占 70%）
    calendar_days = int(n_days * 1.5) + 30
    
    # 计算起始日期
    from datetime import datetime, timedelta
    end_dt = datetime.strptime(end_date, '%Y%m%d')
    start_dt = end_dt - timedelta(days=calendar_days)
    start_date = start_dt.strftime('%Y%m%d')
    
    df = query_cross_year(
        table=table,
        start_date=start_date,
        end_date=end_date,
        columns=columns,
        where_clause=where_clause,
        order_by='trade_date'
    )
    
    # 只保留最近 N 个交易日
    if len(df) > n_days:
        df = df.tail(n_days).reset_index(drop=True)
    
    return df


def query_stock_recent_n_days(
    table: str,
    stock_code: str,
    end_date: str,
    n_days: int,
    columns: Optional[List[str]] = None
) -> pd.DataFrame:
    """查询单只股票最近 N 个交易日数据（自动处理跨年）
    
    Example:
        # 查询某股票最近 120 日数据
        df = query_stock_recent_n_days(
            table='daily_bar',
            stock_code='000001',
            end_date='20260131',
            n_days=120
        )
    """
    return query_recent_n_days(
        table=table,
        end_date=end_date,
        n_days=n_days,
        columns=columns,
        where_clause=f"stock_code = '{stock_code}'"
    )
```

#### 11.4.3 IRS 历史基准查询

```python
def query_irs_historical_baseline(
    industry_code: str,
    baseline_start: str = '20150101',
    baseline_end: str = '20251231'
) -> dict:
    """查询行业历史基准统计（跨多年）
    
    用于 IRS 算法计算行业强度时的历史参照。
    
    Args:
        industry_code: 行业代码
        baseline_start: 基准期开始日期
        baseline_end: 基准期结束日期
    
    Returns:
        {
            'mean': float,      # 历史均值
            'std': float,       # 历史标准差
            'min': float,       # 历史最小值
            'max': float,       # 历史最大值
            'count': int        # 样本数
        }
    """
    df = query_cross_year(
        table='industry_daily',
        start_date=baseline_start,
        end_date=baseline_end,
        columns=['trade_date', 'pct_change'],
        where_clause=f"industry_code = '{industry_code}'"
    )
    
    if df.empty:
        return {'mean': 0, 'std': 1, 'min': 0, 'max': 0, 'count': 0}
    
    return {
        'mean': df['pct_change'].mean(),
        'std': df['pct_change'].std(),
        'min': df['pct_change'].min(),
        'max': df['pct_change'].max(),
        'count': len(df)
    }
```

#### 11.4.4 使用场景示例

| 场景 | 函数 | 示例 |
|------|------|------|
| MSS 100日新高 | `query_recent_n_days()` | 查询 market_snapshot 最近 100 日 |
| PAS 120日涨停 | `query_stock_recent_n_days()` | 查询 limit_info 最近 120 日 |
| PAS 60日价格区间 | `query_stock_recent_n_days()` | 查询 daily_bar 最近 60 日 |
| IRS 历史基准 | `query_irs_historical_baseline()` | 查询 2015-2025 行业数据 |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.1.2 | 2026-02-09 | 修复 R31：§5.4 示例代码去除异常转义引号，统一为标准 Python 字符串 |
| v3.1.1 | 2026-02-09 | 修复 R23：配置示例补充 `config.flat_threshold`（默认 `0.5%`），与数据模型/聚合算法口径一致 |
| v3.1.0 | 2026-02-04 | 对齐 MSS/IRS/PAS/Integration：补充 PAS 广度聚合与估值字段、调度任务 |
| v3.0.1 | 2026-02-03 | 新增 §11.4 长窗口查询工具（兼容分库场景的跨库查询需求） |
| v3.0.0 | 2026-01-31 | 重构版：统一API设计 |

---

**关联文档**：
- 数据管线设计：[data-layer-algorithm.md](./data-layer-algorithm.md)
- 数据模型：[data-layer-data-models.md](./data-layer-data-models.md)
- 信息流：[data-layer-information-flow.md](./data-layer-information-flow.md)


