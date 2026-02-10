# ROADMAP Phase 06｜回测引擎（Backtest）

**版本**: v4.1.4
**创建日期**: 2026-01-31
**最后更新**: 2026-02-06
**时间范围**: Phase 06
**核心交付**: 回测接入与适配（优先 backtrader，qlib 为规划/实验项需技术选型变更）、覆盖 TD/BU、绩效计算
**前置依赖**: Phase 05 (Integration)
**实现状态**: 未实现（截至 2026-02-06：`src/` 仅有 Skeleton/占位与少量基础骨架，详见 `Governance/ROADMAP/ROADMAP-OVERVIEW.md`）

---
## 文档对齐声明

> **权威设计文档**: `docs/design/backtest/`

---

## 1. Phase 目标与量化验收标准

> **一句话**: 验证策略有效性，计算历史绩效

> **实现策略（MVP 优先）**：本 Phase 的首个可运行版本优先采用 backtrader 完成回测闭环；qlib 为规划/实验项，需走技术选型变更流程后再接入。通过 SignalProvider 消费 `integrated_recommendation`（`integration_mode=top_down` 默认，`bottom_up` 为实验）；仅使用本地 L1/L3 数据。
> **时间对齐**：信号在 `signal_date=T` 生成，订单在 `execute_date=T+1` 开盘执行，禁止未来函数。

### 1.1 量化验收指标

| 指标项 | 验收标准 | 测量方法 | 优先级 |
|--------|----------|----------|--------|
| T+1规则正确性 | 当日买入不可卖出 | 单元测试 | P0 |
| 集合竞价成交 | 成交概率模型测试通过 | 回测验证 | P0 |
| 收益率计算 | 误差 < 0.01% | 与手工计算对比 | P0 |
| 最大回撤计算 | 误差 < 0.01% | 与手工计算对比 | P0 |
| 夏普比率计算 | 误差 < 0.01 | 与标准公式对比 | P0 |
| 涨跌停限制 | 涨停不可买入，跌停不可卖出 | 边界测试 | P0 |
| 未来函数检查 | signal_date < execute_date | 代码审查/测试 | P0 |
| 测试覆盖率 | ≥ 80% | pytest-cov | P1 |
| 回测速度 | 1年数据 ≤ 30秒/股 | 性能测试 | P1 |

### 1.2 里程碑检查点

| 里程碑 | 交付物 | 验收条件 | 预期时间 |
|--------|--------|----------|----------|
| M6.1 | 回测引擎框架 | T+1规则测试通过 | Task 1 |
| M6.2 | 集合竞价模型 | 成交概率验证通过 | Task 2 |
| M6.3 | 绩效计算模块 | 所有指标计算测试通过 | Task 3 |
| M6.4 | 落库与API | backtest_results数据完整 | Task 4 |

### 1.3 铁律约束（零容忍）

| 铁律 | 要求 | 检查方式 | 违反后果 |
|------|------|----------|----------|
| **T+1限制** | 当日买入股票不可当日卖出 | 单元测试 | 回测结果无效 |
| **涨停不可买** | 涨停价不允许买入 | 单元测试 | 回测结果无效 |
| **跌停不可卖** | 跌停价不允许卖出 | 单元测试 | 回测结果无效 |
| **无未来函数** | 禁止使用未来数据 | 代码审查 | 回测结果无效 |

---

## 2. 输入规范

### 2.1 数据依赖矩阵

| 输入表/接口 | 来源 | 关键字段 | 更新频率 | 必需 |
|-------------|------|----------|----------|------|
| integrated_recommendation | Phase 05 | final_score, recommendation, position_size, entry/stop/target, integration_mode | 每交易日 | ✅ |
| raw_daily | Phase 01 L1 | open, high, low, close, vol | 每交易日 | ✅ |
| raw_limit_list | Phase 01 L1 | limit（U/D/Z） | 每交易日 | ✅ |
| raw_trade_cal | Phase 01 L1 | is_open | 年度 | ✅ |
| pas_breadth_daily | Phase 01/05 | pas_sa_ratio, industry_sa_ratio | 每交易日 | ⚠️BU可选 |

### 2.2 回测配置输入

```python
@dataclass
class BacktestConfig:
    """回测配置"""
    # 引擎与模式
    engine_type: str = "backtrader"     # backtrader（qlib为规划项，需技术选型变更）
    integration_mode: str = "top_down"  # top_down/bottom_up/dual_verify/complementary

    # 时间范围
    start_date: str                     # 开始日期 YYYYMMDD
    end_date: str                       # 结束日期 YYYYMMDD
    initial_cash: float = 1000000.0     # 初始资金

    # 信号筛选
    min_recommendation: str = "BUY"     # STRONG_BUY/BUY/HOLD
    min_final_score: float = 55.0
    top_n: int = 20
    min_pas_breadth_ratio: float = 0.03 # BU 活跃度门槛

    # 交易与成本
    order_type: str = "auction"         # auction/limit
    slippage_type: str = "auction"      # auction/fixed/variable
    slippage_value: float = 0.001
    commission_rate: float = 0.0003
    stamp_duty_rate: float = 0.001
    transfer_fee_rate: float = 0.00002
    min_commission: float = 5.0

    # 风控与仓位
    max_positions: int = 10
    max_position_pct: float = 0.1
    max_holding_days: int = 10
    stop_loss_pct: float = 0.08
    take_profit_pct: float = 0.2
```

### 2.3 输入验证规则

| 验证项 | 规则 | 错误处理 |
|--------|------|----------|
| start_date | ≤ end_date | 抛出 ValueError |
| initial_cash | > 0 | 抛出 ValueError |
| stop_loss_pct | ∈ (0, 1) | 截断并警告 |
| commission_rate | ∈ [0, 0.01] | 截断并警告 |
| 交易日 | 必须是有效交易日 | 跳过非交易日 |
| signal_date/execute_date | execute_date 为下一交易日 | 违规即阻断 |

---

## 3. 核心算法

### 3.1 回测引擎框架

```python
class BacktestRunner:
    """
    回测调度器核心逻辑（引擎适配 + 信号提供）
    - 引擎：backtrader（qlib为规划项，需技术选型变更）
    - 信号：integrated_recommendation（按 integration_mode）
    """

    def run(self, config: BacktestConfig) -> BacktestResult:
        engine = EngineFactory.create(config.engine_type)
        signal_provider = IntegrationSignalProvider(repo, config)

        for signal_date in get_trading_dates(config.start_date, config.end_date):
            execute_date = next_trading_day(signal_date)
            signals = signal_provider.generate(signal_date)
            engine.on_bar(execute_date, signals)  # 内部执行 T+1/涨跌停/整手/费用

        return engine.finalize()
```

### 3.2 T+1 交易限制

```python
def check_t1_constraint(position: Position, trade_date: str) -> bool:
    """
    T+1 检查：当日买入不可卖出
    
    Returns:
        True: 可以卖出
        False: T+1限制，不可卖出
    """
    if position.buy_date == trade_date:
        return False  # 当日买入，不可卖出
    return True

def calculate_holding_days(buy_date: str, current_date: str) -> int:
    """
    计算持仓天数（从T+1开始计算）
    
    T日买入 -> T日持仓0天
    T+1日 -> 持仓1天
    T+2日 -> 持仓2天
    """
    trading_days = get_trading_days_between(buy_date, current_date)
    return max(0, trading_days - 1)  # 不含买入日
```

### 3.3 集合竞价成交模型

```python
def calculate_fill_probability(
    open_price: float,
    prev_close: float,
    limit_up_price: float,
    limit_down_price: float,
    volume: float,
    avg_volume_20d: float
) -> float:
    """
    集合竞价成交概率模型
    
    考虑因素：
    1. 涨跌停距离
    2. 成交量水平
    """
    # 1. 涨停距离因子
    if open_price >= limit_up_price:
        return 0.0  # 涨停开盘，无法买入
    
    pct_to_limit = (limit_up_price - open_price) / limit_up_price
    limit_factor = min(1.0, pct_to_limit / 0.05)  # 距离涨停5%以上则因子=1
    
    # 2. 成交量因子
    if avg_volume_20d > 0:
        volume_ratio = volume / avg_volume_20d
        volume_factor = min(1.0, volume_ratio / 1.5)  # 量比1.5以上则因子=1
    else:
        volume_factor = 0.5
    
    # 3. 综合成交概率
    fill_probability = limit_factor * 0.6 + volume_factor * 0.4
    
    return fill_probability

def get_entry_price(daily_data: DailyData, slippage_value: float) -> float:
    """
    入场价 = 开盘价 × (1 + 滑点)
    """
    return daily_data.open * (1 + slippage_value)

def get_exit_price(daily_data: DailyData, slippage_value: float) -> float:
    """
    出场价 = 开盘价 × (1 - 滑点)
    """
    return daily_data.open * (1 - slippage_value)
```

### 3.4 涨跌停限制

```python
def check_limit_constraint(
    daily_data: DailyData,
    trade_type: str  # 'buy' or 'sell'
) -> bool:
    """
    涨跌停限制检查
    
    Returns:
        True: 可以交易
        False: 涨跌停限制，不可交易
    """
    if trade_type == 'buy':
        # 涨停不可买入
        if daily_data.is_limit_up:
            return False
    elif trade_type == 'sell':
        # 跌停不可卖出
        if daily_data.is_limit_down:
            return False
    return True
```

### 3.5 入场逻辑

```python
def check_entry_signal(
    stock_code: str,
    signal_date: str,
    config: BacktestConfig
) -> Optional[BacktestSignal]:
    """
    检查入场信号
    """
    # 从 integrated_recommendation 获取推荐
    recommendation = get_recommendation(stock_code, signal_date)
    
    if recommendation is None:
        return None
    
    # 检查推荐等级
    if config.min_recommendation == 'STRONG_BUY':
        if recommendation.recommendation != 'STRONG_BUY':
            return None
    elif config.min_recommendation == 'BUY':
        if recommendation.recommendation not in ['STRONG_BUY', 'BUY']:
            return None
    
    # 仅示意：字段省略，完整结构见 backtest-data-models
    return BacktestSignal(
        stock_code=stock_code,
        signal_date=signal_date,
        final_score=recommendation.final_score,
        recommendation=recommendation.recommendation
    )

def execute_entry(
    portfolio: Portfolio,
    daily_data: DailyData,
    signal: BacktestSignal,
    config: BacktestConfig
) -> Optional[BacktestTrade]:
    """
    执行入场
    """
    # 1. 检查涨停限制
    if not check_limit_constraint(daily_data, 'buy'):
        return None
    
    # 2. 计算成交概率
    fill_prob = calculate_fill_probability(...)
    if random.random() > fill_prob:
        return None  # 未成交
    
    # 3. 计算入场价（含滑点）
    entry_price = get_entry_price(daily_data, config.slippage_value)
    
    # 4. 计算可买数量（100股整数倍）
    available_cash = portfolio.cash
    shares = int(available_cash / entry_price / 100) * 100
    if shares < 100:
        return None  # 资金不足
    
    # 5. 计算交易成本
    commission = entry_price * shares * config.commission_rate
    total_cost = entry_price * shares + commission
    
    # 6. 更新持仓
    execute_date = daily_data.trade_date  # T+1执行日
    portfolio.buy(signal.stock_code, shares, entry_price, execute_date)
    portfolio.cash -= total_cost
    
    # 仅示意：字段省略，完整结构见 backtest-data-models
    return BacktestTrade(
        stock_code=signal.stock_code,
        signal_date=signal.signal_date,
        execute_date=execute_date,
        direction='buy',
        filled_price=entry_price,
        shares=shares,
        commission=commission
    )
```

### 3.6 出场逻辑

```python
def check_exit_signal(
    portfolio: Portfolio,
    daily_data: DailyData,
    config: BacktestConfig
) -> Optional[str]:
    """
    检查出场信号
    """
    position = portfolio.get_position(daily_data.stock_code)
    
    # 1. T+1检查
    if not check_t1_constraint(position, daily_data.trade_date):
        return None
    
    # 2. 止损检查
    current_pnl_pct = (daily_data.open - position.entry_price) / position.entry_price
    if current_pnl_pct <= -config.stop_loss_pct:
        return 'STOP_LOSS'
    
    # 3. 止盈检查
    if current_pnl_pct >= config.take_profit_pct:
        return 'TAKE_PROFIT'
    
    # 4. 最大持仓天数检查
    holding_days = calculate_holding_days(position.buy_date, daily_data.trade_date)
    if holding_days >= config.max_holding_days:
        return 'MAX_HOLDING_DAYS'
    
    return None

def execute_exit(
    portfolio: Portfolio,
    daily_data: DailyData,
    exit_reason: str,
    config: BacktestConfig
) -> Optional[BacktestTrade]:
    """
    执行出场
    """
    # 1. 检查跌停限制
    if not check_limit_constraint(daily_data, 'sell'):
        return None  # 跌停无法卖出
    
    position = portfolio.get_position(daily_data.stock_code)
    
    # 2. 计算出场价（含滑点）
    exit_price = get_exit_price(daily_data, config.slippage_value)
    
    # 3. 计算交易成本
    commission = exit_price * position.shares * config.commission_rate
    stamp_tax = exit_price * position.shares * config.stamp_duty_rate
    total_cost = commission + stamp_tax
    
    # 4. 计算收益
    proceeds = exit_price * position.shares - total_cost
    pnl = proceeds - (position.entry_price * position.shares)
    
    # 5. 更新持仓
    portfolio.sell(daily_data.stock_code)
    portfolio.cash += proceeds
    
    # 仅示意：字段省略，完整结构见 backtest-data-models
    return BacktestTrade(
        stock_code=daily_data.stock_code,
        signal_date=position.buy_date,
        execute_date=daily_data.trade_date,
        direction='sell',
        filled_price=exit_price,
        shares=position.shares,
        commission=commission,
        stamp_tax=stamp_tax,
        pnl=pnl,
        filled_reason=exit_reason
    )
```

### 3.7 绩效指标计算

```python
def calculate_performance(
    portfolio: Portfolio,
    trades: List[BacktestTrade],
    config: BacktestConfig
) -> BacktestResult:
    """
    计算回测绩效指标
    """
    # 1. 总收益率
    total_return = (portfolio.total_value - config.initial_cash) / config.initial_cash
    
    # 2. 年化收益率
    days = trading_days_between(config.start_date, config.end_date)
    annual_return = (1 + total_return) ** (252 / days) - 1
    
    # 3. 最大回撤
    max_drawdown = calculate_max_drawdown(portfolio.equity_curve)
    
    # 4. 夏普比率（假设无风险利率3%）
    daily_returns = calculate_daily_returns(portfolio.equity_curve)
    sharpe_ratio = (daily_returns.mean() - 0.03/252) / daily_returns.std() * np.sqrt(252)
    
    # 5. 胜率
    winning_trades = [t for t in trades if t.pnl > 0]
    win_rate = len(winning_trades) / len(trades) if trades else 0
    
    # 6. 盈亏比
    avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
    losing_trades = [t for t in trades if t.pnl <= 0]
    avg_loss = abs(np.mean([t.pnl for t in losing_trades])) if losing_trades else 1
    profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
    
    return BacktestResult(
        total_return=total_return,
        annual_return=annual_return,
        max_drawdown=max_drawdown,
        sharpe_ratio=sharpe_ratio,
        win_rate=win_rate,
        profit_loss_ratio=profit_loss_ratio,
        total_trades=len(trades),
        trades=trades
    )

def calculate_max_drawdown(equity_curve: List[float]) -> float:
    """
    计算最大回撤
    
    max_drawdown = max((peak - trough) / peak)
    """
    peak = equity_curve[0]
    max_dd = 0
    
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak
        if dd > max_dd:
            max_dd = dd
    
    return max_dd
```

---

## 4. 输出规范

> 详细字段与表结构以 `docs/design/backtest/backtest-data-models.md` 为准。

### 4.1 BacktestResult 核心字段

- backtest_id / backtest_name / engine_type / integration_mode
- start_date / end_date / initial_cash / final_value
- metrics：total_return / annual_return / max_drawdown / sharpe_ratio / win_rate / profit_factor
- config_params：包含 engine_type / integration_mode / 费用与风控参数快照

### 4.2 持久化表

- `backtest_results`：存放回测结果、配置快照与净值曲线
- `backtest_trade_records`：存放交易明细，包含 integration_mode / recommendation 追溯字段

---

## 5. API 接口规范

```python
class BacktestEngine:
    """回测引擎接口"""
    
    def run_single(self, config: BacktestConfig, stock_code: str) -> BacktestResult:
        """
        运行单只股票回测
        
        Args:
            config: 回测配置
            stock_code: 股票代码
        Returns:
            BacktestResult 对象
        """
        pass
    
    def run_batch(self, config: BacktestConfig, stock_codes: List[str]) -> List[BacktestResult]:
        """
        批量运行多只股票回测（独立回测，非组合）
        
        Args:
            config: 回测配置
            stock_codes: 股票代码列表
        Returns:
            BacktestResult 列表
        """
        pass
    
    def get_equity_curve(self, backtest_id: str) -> List[EquityPoint]:
        """获取资金曲线"""
        pass
    
    def get_trades(self, backtest_id: str) -> List[BacktestTrade]:
        """获取交易记录"""
        pass


class BacktestRepository:
    """回测数据仓库"""
    
    def save(self, result: BacktestResult) -> None:
        """保存回测结果"""
        pass
    
    def get_by_id(self, backtest_id: str) -> BacktestResult:
        """按ID查询"""
        pass
    
    def get_by_stock(self, stock_code: str) -> List[BacktestResult]:
        """按股票查询历史回测"""
        pass
```

---

## 6. 错误处理策略

### 6.1 错误分类与处理

| 错误场景 | 错误码 | 严重等级 | 处理策略 | 重试 |
|----------|--------|----------|----------|------|
| 日线数据缺失 | BT_E001 | P1 | 跳过该交易日 | 否 |
| 配置参数无效 | BT_E002 | P0 | 抛出 ValueError | 否 |
| 资金不足 | BT_E003 | P2 | 记录警告，跳过交易 | 否 |
| T+1规则违反 | BT_E004 | P0 | 抛出 IronLawViolationError | 否 |
| 涨跌停限制 | BT_E005 | P2 | 记录警告，跳过交易 | 否 |
| 数据库写入失败 | BT_E006 | P0 | 重试3次后抛出异常 | ✅(3次) |
| 使用未来函数 | BT_E007 | P0 | 抛出 FutureLeakError | 否 |

### 6.2 铁律违规检测

```python
class IronLawViolationError(Exception):
    """铁律违规异常"""
    pass

class FutureLeakError(Exception):
    """未来函数泄露异常"""
    pass

def validate_t1_rule(trades: List[BacktestTrade]) -> bool:
    """
    验证T+1规则：检查是否存在当日买卖
    """
    for i, sell_trade in enumerate(trades):
        if sell_trade.direction != 'sell':
            continue
        # 查找对应的买入交易
        for buy_trade in trades[:i]:
            if (buy_trade.direction == 'buy' and 
                buy_trade.stock_code == sell_trade.stock_code and
                buy_trade.trade_date == sell_trade.trade_date):
                raise IronLawViolationError(f"T+1 violation: {sell_trade}")
    return True
```

---

## 7. 质量监控

### 7.1 回测质量检查项

| 检查项 | 检查方法 | 预期结果 | 告警阈值 |
|--------|----------|----------|----------|
| T+1合规 | validate_t1_rule | 无违规 | 任何违规 |
| 涨跌停合规 | 检查买入价/卖出价 | 无涨停买入/跌停卖出 | 任何违规 |
| 绩效指标范围 | 边界检查 | 在合理范围内 | 异常值 |
| 资金曲线连续 | 检查断点 | 无断点 | 任何断点 |
| 交易成本正确 | 对比计算 | 误差<0.01% | 超过阈值 |

### 7.2 质量监控表

```sql
CREATE TABLE backtest_quality_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backtest_id VARCHAR(36) NOT NULL,
    check_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- 铁律检查
    t1_compliant BOOLEAN NOT NULL,
    limit_compliant BOOLEAN NOT NULL,
    no_future_leak BOOLEAN NOT NULL,
    
    -- 绩效合理性
    performance_valid BOOLEAN,
    
    -- 异常信息
    error_code VARCHAR(20),
    error_message TEXT,
    
    -- 状态
    status VARCHAR(20) DEFAULT 'PASS'
);
```

---

## 8. 执行计划

### 8.1 Task 级别详细计划

---

#### Task 1: 回测引擎框架（⚠️铁律）

**目标**: 实现回测核心循环，严格遵守 T+1 规则

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| integrated_recommendation | Phase 05 | 数据存在 | 阻断 |
| raw_daily | Phase 01 | OHLCV存在 | 阻断 |
| raw_limit_list | Phase 01 | 涨跌停标识 | 阻断 |
| raw_trade_cal | Phase 01 | 交易日历 | 阻断 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| BacktestEngine | 代码 | 核心循环 | `src/backtest/` |
| Portfolio | 代码 | 持仓管理 | `src/backtest/` |
| T1Validator | 代码 | T+1规则验证 | `src/backtest/` |
| LimitChecker | 代码 | 涨跌停检查 | `src/backtest/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| T+1合规 | 当日买入不可卖 | 单元测试 |
| 涨停不可买 | 涨停拒绝买入 | 场景测试 |
| 跌停不可卖 | 跌停拒绝卖出 | 场景测试 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| T+1违规 | 抛出 IronLawViolationError | 回测结果无效 |
| 涨跌停限制 | 跳过交易 | 记录警告 |
| 数据缺失 | 跳过该交易日 | 记录警告 |

**验收检查**

- [ ] **T+1规则正确**（当日买入不可卖）
- [ ] **涨停不可买**
- [ ] **跌停不可卖**
- [ ] 核心循环正确执行

---

#### Task 2: 集合竞价模型

**目标**: 实现集合竞价成交概率模型

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| BacktestEngine | Task 1 | 测试通过 | 阻断 |
| raw_daily | Phase 01 | 开盘价/成交量 | 阻断 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| FillProbabilityCalculator | 代码 | 成交概率模型 | `src/backtest/` |
| SlippageCalculator | 代码 | 滑点计算 | `src/backtest/` |
| EntryExecutor | 代码 | 入场执行 | `src/backtest/` |
| ExitExecutor | 代码 | 出场执行 | `src/backtest/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 成交概率 | 涨停0%/正常100% | 场景测试 |
| 滑点计算 | 默认0.2% | 单元测试 |
| 成交价格 | 开盘价±滑点 | 单元测试 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 涨停无法买入 | 成交概率=0 | 记录信息 |
| 跌停无法卖出 | 成交概率=0 | 记录信息 |

**验收检查**

- [ ] 成交概率模型正确
- [ ] 滑点计算正确
- [ ] 入场执行正确
- [ ] 出场执行正确

---

#### Task 3: 绩效计算模块

**目标**: 实现所有回测绩效指标计算

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| BacktestEngine | Task 1 | 测试通过 | 阻断 |
| 交易记录 | 回测运行 | 交易列表 | 阻断 |
| 资金曲线 | 回测运行 | 权益序列 | 阻断 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| PerformanceCalculator | 代码 | 所有指标 | `src/backtest/` |
| ReturnCalculator | 代码 | 收益率计算 | `src/backtest/` |
| DrawdownCalculator | 代码 | 回撤计算 | `src/backtest/` |
| SharpeCalculator | 代码 | 夏普比率 | `src/backtest/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 收益率误差 | <0.01% | 手工计算对比 |
| 最大回撤误差 | <0.01% | 手工计算对比 |
| 夏普比率误差 | <0.01 | 手工计算对比 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 无交易记录 | 返回空绩效 | 记录信息 |
| 指标越界 | 截断到合理范围 | 记录警告 |

**验收检查**

- [ ] 总收益率计算正确
- [ ] 年化收益率计算正确
- [ ] 最大回撤计算正确
- [ ] 夏普比率计算正确
- [ ] 胜率/盈亏比计算正确

---

#### Task 4: 落库与API

**目标**: 实现回测结果持久化和API接口

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| BacktestEngine | Task 1 | 测试通过 | 阻断 |
| PerformanceCalculator | Task 3 | 测试通过 | 阻断 |
| DuckDB连接 | Phase 01 | 可连接 | 阻断 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| BacktestRepository | 代码 | 幂等写入 | `src/backtest/` |
| backtest_results表 | 数据 | 绩效指标 | Business Tables（DuckDB按年分库） |
| backtest_trade_records表 | 数据 | 交易记录 | Business Tables（DuckDB按年分库） |
| 质量监控 | 代码 | 铁律检查 | `scripts/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 覆盖率 | ≥80% | `pytest --cov` |
| 幂等性 | 重复写入不报错 | 单元测试 |
| 回测速度 | ≤1年数30秒/股 | 性能测试 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| DB写入失败 | 重试3次 | 失败后抛异常 |
| 铁律违规 | 抛出 FutureLeakError | 回测结果无效 |

**验收检查**

- [ ] 数据落库正确
- [ ] 幂等性验证通过
- [ ] 测试覆盖率≥80%
- [ ] **无未来函数**
- [ ] **M6里程碑完成**

### 8.2 回测执行流程

```text
用户配置回测参数
  ↓
验证配置有效性
  ↓
加载历史数据（raw_daily, integrated_recommendation）
  ↓
遍历 signal_date（T）
  ├─ 生成信号（integrated_recommendation）
  └─ 在 execute_date（T+1）开盘执行
      ├─ 检查出场条件（已持仓）
      │   ├─ T+1检查
      │   ├─ 止损/止盈/持仓天数检查
      │   └─ 跌停限制检查
      │
      └─ 检查入场条件（无持仓）
          ├─ 推荐信号检查
          ├─ 涨停限制检查
          └─ 成交概率模型
  ↓
计算绩效指标
  ↓
保存回测结果
  ↓
质量检查
```

---

## 9. 验收检查清单

### 9.1 铁律验收（零容忍）

- [ ] **T+1规则**: 当日买入不可当日卖出
- [ ] **涨停不可买**: 涨停开盘或盘中涨停不允许买入
- [ ] **跌停不可卖**: 跌停开盘或盘中跌停不允许卖出
- [ ] **无未来函数**: 不使用任何未来数据

### 9.2 功能验收

- [ ] 回测引擎核心循环正确
- [ ] 集合竞价成交概率模型正确
- [ ] 入场/出场逻辑正确
- [ ] 止损/止盈/最大持仓天数正确
- [ ] 交易成本计算正确（佣金、印花税、滑点）
- [ ] 先卖后买执行顺序正确
- [ ] 停牌日处理正确（不成交、不计持仓天数）

### 9.3 绩效指标验收

- [ ] 总收益率计算正确（误差<0.01%）
- [ ] 年化收益率计算正确（误差<0.01%）
- [ ] 最大回撤计算正确（误差<0.01%）
- [ ] 夏普比率计算正确（误差<0.01）
- [ ] 胜率计算正确
- [ ] 盈亏比计算正确

### 9.4 质量验收

- [ ] 测试覆盖率 ≥ 80%
- [ ] 回测速度 ≤ 30秒/股/年
- [ ] 数据库写入幂等

### 9.5 用例清单对齐

- [ ] `docs/design/backtest/backtest-test-cases.md` 已覆盖所有零容忍场景

---

## 10. 参数配置表

### 10.1 默认配置

| 参数 | 代码 | 默认值 | 可调范围 | 说明 |
|------|------|--------|----------|------|
| 初始资金 | initial_cash | 1000000 | >0 | 回测起始资金 |
| 最大持仓天数 | max_holding_days | 10 | 1-60 | 强制出场 |
| 止损比例 | stop_loss_pct | 8% | 1%-20% | 亏损出场 |
| 止盈比例 | take_profit_pct | 20% | 5%-50% | 盈利出场 |
| 佣金率 | commission_rate | 0.0003 | 0-0.003 | 万三 |
| 印花税 | stamp_duty_rate | 0.001 | 0-0.002 | 卖出千一 |
| 滑点 | slippage_value | 0.001 | 0-0.01 | 0.1% |

### 10.2 出场条件优先级

| 优先级 | 条件 | 说明 |
|--------|------|------|
| 1 | T+1限制 | 当日买入不可卖 |
| 2 | 跌停限制 | 跌停无法卖出 |
| 3 | 止损 | 亏损达到阈值 |
| 4 | 止盈 | 盈利达到阈值 |
| 5 | 最大持仓天数 | 强制出场 |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v4.1.4 | 2026-02-06 | 清理示例伪代码时间字段：entry/exit 示例统一 signal_date/execute_date |
| v4.1.3 | 2026-02-06 | 引擎口径对齐：backtrader为主，qlib为规划项 |
| v4.1.2 | 2026-02-05 | 验收清单对齐回测测试用例清单 |
| v4.1.1 | 2026-02-05 | 补充执行细节：先卖后买、费用与滑点入账时点 |
| v4.1.0 | 2026-02-05 | 增加 signal_date/execute_date 约束，防止未来函数 |
| v4.0.1 | 2026-02-04 | 落库口径调整为 DuckDB 按年分库 |
| v4.0.0 | 2026-02-02 | 完整重构：添加量化验收标准、I/O规范、T+1铁律、绩效计算 |
| v3.0.0 | 2026-01-31 | 重构版 |


