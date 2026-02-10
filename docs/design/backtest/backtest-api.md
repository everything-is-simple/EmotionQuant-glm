# Backtest API接口

**版本**: v3.4.2（重构版）
**最后更新**: 2026-02-09
**状态**: 设计完成（代码未落地）

---

## 实现状态（仓库现状）

- `src/backtest/` 当前仅有 `__init__.py` 占位；回测引擎与接口尚未落地。
- 本文档为设计口径；实现阶段需以此为准并同步更新记录。

---

## 1. 核心类

### 1.1 BacktestRunner 回测调度器

```python
from backtest.runner import BacktestRunner
from backtest.config import BacktestConfig

class BacktestRunner:
    """回测调度器：选择引擎与模式并运行"""

    def __init__(self, config: BacktestConfig, repo: DataRepository):
        """
        Args:
            config: 回测配置（含 engine_type / integration_mode）
            repo: 数据仓库（本地落库数据）
        """
        pass

    def run(self) -> BacktestResult:
        """
        运行回测（内部选择引擎与信号提供者）

        约束：
        - signal_date = T（信号生成日）
        - execute_date = T+1（开盘执行）
        """
        pass
```

### 1.2 引擎适配器

```python
from backtest.engines import LocalVectorizedEngine, QlibEngine, BacktraderCompatEngine

class QlibEngine:
    """Qlib 研究回测引擎（主选）"""
    def run(self, strategy: Strategy) -> BacktestResult:
        pass


class LocalVectorizedEngine:
    """本地向量化回测引擎（执行口径基线）"""
    def run(self, strategy: Strategy) -> BacktestResult:
        pass


class BacktraderCompatEngine:
    """基于 backtrader 的兼容引擎（非主选）"""
    def run(self, strategy: Strategy) -> BacktestResult:
        pass
```

### 1.3 SignalProvider 信号提供者

```python
class IntegrationSignalProvider:
    """从 L3 集成信号生成 BacktestSignal"""

    def __init__(self, repo: DataRepository, config: BacktestConfig):
        pass

    def generate(self, signal_date: str) -> List[BacktestSignal]:
        """
        - 读取 integrated_recommendation（按 integration_mode）
        - 应用 min_final_score / min_recommendation
        - 输出 BacktestSignal（signal_date = signal_date）
        """
        pass
```

### 1.4 ExecutionPolicy 执行策略

```python
class ExecutionPolicy:
    """交易执行策略（T+1/涨跌停/整手/费用/滑点）"""

    def can_buy(self, daily_data) -> bool:
        """涨停/停牌校验"""
        pass

    def can_sell(self, daily_data, position) -> bool:
        """跌停/T+1校验"""
        pass

    def calc_entry_price(self, daily_data, slippage) -> float:
        """开盘价 + 滑点"""
        pass

    def calc_exit_price(self, daily_data, slippage) -> float:
        """开盘价 - 滑点"""
        pass
```

### 1.5 FeeModel 费用模型

```python
class FeeModel:
    """佣金/印花税/过户费模型"""

    def buy_cost(self, amount: float) -> float:
        pass

    def sell_cost(self, amount: float) -> float:
        pass
```

### 1.6 OrderSequencer 订单顺序

```python
class OrderSequencer:
    """当日订单排序：先卖后买"""
    def sort(self, orders: list) -> list:
        pass
```

### 1.7 DataAdapter 数据适配器

```python
class BacktraderDataAdapter:
    """将 L1 Parquet 转为 backtrader DataFeed（兼容）"""
    def get_feed(self, stock_code: str, start_date: str, end_date: str):
        pass


class QlibDataAdapter:
    """将本地 DuckDB/Parquet 提供给 qlib（主选研究平台）"""
    def get_dataset(self, start_date: str, end_date: str):
        pass
```

---

## 2. 配置与接口

### 2.1 BacktestConfig

```python
@dataclass
class BacktestConfig:
    # 引擎与模式
    engine_type: str = "qlib"  # qlib/local_vectorized/backtrader_compat
    integration_mode: str = "top_down"  # top_down/bottom_up/dual_verify/complementary

    # 时间范围
    start_date: str
    end_date: str
    initial_cash: float = 1000000.0
    risk_free_rate: float = 0.015

    # 信号筛选
    min_recommendation: str = "BUY"   # 最低推荐等级（仅纳入该等级及以上）；Recommendation: STRONG_BUY > BUY > HOLD > SELL > AVOID
    min_final_score: float = 55.0
    top_n: int = 20
    min_pas_breadth_ratio: float = 0.03  # BU 活跃度门槛

    # 交易与成本
    order_type: str = "auction"       # auction/limit
    slippage_type: str = "auction"    # auction/fixed/variable
    slippage_value: float = 0.001
    fee_config: AShareFeeConfig = field(default_factory=AShareFeeConfig)

    # 风控与仓位
    max_positions: int = 10
    max_position_pct: float = 0.2
    max_holding_days: int = 10
    stop_loss_pct: float = 0.08
    take_profit_pct: float = 0.15
```

---

## 3. 使用示例

### 3.1 基本回测

```python
from backtest.runner import BacktestRunner
from backtest.config import BacktestConfig
from src.data.repositories import DataRepository

config = BacktestConfig(
    start_date="20240101",
    end_date="20240131",
    engine_type="qlib",
    integration_mode="top_down",
    min_recommendation="BUY",
    min_final_score=55.0,
    max_positions=10,
    max_position_pct=0.1,
)

repo = DataRepository.from_env()
runner = BacktestRunner(config=config, repo=repo)
result = runner.run()

print(f"总收益率: {result.metrics.total_return:.2%}")
print(f"最大回撤: {result.metrics.max_drawdown:.2%}")
print(f"夏普比率: {result.metrics.sharpe_ratio:.2f}")
```

### 3.2 BU 实验回测

```python
config = BacktestConfig(
    start_date="20240101",
    end_date="20240131",
    engine_type="qlib",
    integration_mode="bottom_up",
    min_pas_breadth_ratio=0.03,
)

result = BacktestRunner(config=config, repo=repo).run()
```

---

## 4. 数据仓库 API

```python
class BacktestRepository:
    def save_result(self, result: BacktestResult) -> None:
        pass

    def get_result_by_id(self, backtest_id: str) -> BacktestResult:
        pass

    def get_results_by_date_range(self, start: str, end: str) -> List[BacktestResult]:
        pass
```

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.4.2 | 2026-02-09 | 修复 R27：`BacktestConfig` 费率字段改为 `fee_config: AShareFeeConfig`（与 data-models 对齐）；`min_recommendation` 注释改为 Recommendation 枚举语义 |
| v3.4.1 | 2026-02-08 | 修复 R10：BacktestConfig 增加 `risk_free_rate`；同步 `max_position_pct=0.20`、`take_profit_pct=0.15` 与数据模型一致 |
| v3.4.0 | 2026-02-07 | 统一选型：Qlib 主选；新增本地向量化基线与 backtrader 兼容引擎命名 |
| v3.3.2 | 2026-02-06 | 标注实现状态；引擎口径明确 backtrader 优先，qlib 规划项；修正代码块与编号 |
| v3.3.1 | 2026-02-05 | 增加执行策略/费用模型/订单顺序接口 |
| v3.3.0 | 2026-02-05 | 明确 signal_date/execute_date 语义与数据适配器接口 |
| v3.2.0 | 2026-02-05 | 对齐 Integration 双模式与回测引擎适配；新增 integration_mode 配置与 SignalProvider |
| v3.1.0 | 2026-02-05 | 对齐 backtrader/qlib 与双模式：新增 Runner/Engine/Strategy 说明 |
| v3.0.0 | 2026-01-31 | 重构版：统一API设计 |

---

**关联文档**：
- 算法设计：[backtest-algorithm.md](./backtest-algorithm.md)
- 数据模型：[backtest-data-models.md](./backtest-data-models.md)
- 信息流：[backtest-information-flow.md](./backtest-information-flow.md)
