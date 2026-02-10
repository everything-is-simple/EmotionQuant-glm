# Trading API 接口

**版本**: v3.1.5（重构版）
**最后更新**: 2026-02-09
**状态**: 设计完成（代码未落地）

---

## 实现状态（仓库现状）

- `src/trading/` 当前仅有 `__init__.py` 占位；交易/风控实现尚未落地。
- 本文档中的模块结构与接口为规划口径。

---

## 1. 模块结构（规划）

```
trading/
├── order_manager.py       # 订单管理器
├── executor.py            # 交易执行器
├── position_manager.py    # 持仓管理器
├── risk_manager.py        # 风险管理器
├── t1_tracker.py          # T+1追踪器
├── commission.py          # 佣金计算
├── slippage.py            # 滑点模型
└── v2/
    └── signal_validator.py # 信号质量验证器（v2.0）
```

---

## 2. OrderManager（订单管理器）

### 2.1 类定义

```python
class OrderManager:
    """订单管理器"""

    def __init__(self, db: Database) -> None:
        """
        初始化订单管理器

        Args:
            db: 数据库连接
        """
```

### 2.2 create_order

```python
def create_order(
    self,
    trade_date: str,
    stock_code: str,
    direction: str,
    shares: int,
    price: float = None,
    order_type: str = "auction"
) -> Order:
    """
    创建订单

    Args:
        trade_date: 交易日期 (YYYYMMDD)
        stock_code: 股票代码（内部格式，000001）
        direction: 交易方向 (buy/sell)
        shares: 股数（必须为100的整数倍）
        price: 委托价格（市价单可为空）
        order_type: 订单类型 (auction/market/limit/stop)

    Returns:
        Order: 创建的订单对象

    Raises:
        ValueError: 股数不是100的整数倍
        ValueError: 无效的direction或order_type

    Example:
        order = manager.create_order(
            trade_date="20260131",
            stock_code="000001",
            direction="buy",
            shares=1000,
            price=12.50
        )
    """
```

### 2.3 submit_order

```python
def submit_order(self, order: Order) -> bool:
    """
    提交订单（含风控检查）

    Args:
        order: 待提交的订单

    Returns:
        bool: 是否提交成功

    Note:
        提交前会自动进行风控检查
        检查通过后状态变为 submitted
    """
```

### 2.4 cancel_order

```python
def cancel_order(self, order_id: str) -> bool:
    """
    取消订单

    Args:
        order_id: 订单ID

    Returns:
        bool: 是否取消成功

    Note:
        仅 pending/submitted 状态的订单可取消
    """
```

### 2.5 get_order

```python
def get_order(self, order_id: str) -> Optional[Order]:
    """
    获取订单

    Args:
        order_id: 订单ID

    Returns:
        Order: 订单对象，不存在返回None
    """
```

### 2.6 get_orders_by_date

```python
def get_orders_by_date(
    self,
    trade_date: str,
    status: str = None
) -> List[Order]:
    """
    获取指定日期的订单列表

    Args:
        trade_date: 交易日期
        status: 订单状态过滤（可选）

    Returns:
        List[Order]: 订单列表
    """
```

---

## 3. AuctionExecutor（集合竞价执行器）

### 3.1 类定义

```python
class AuctionExecutor:
    """集合竞价执行器"""

    def __init__(
        self,
        db: Database,
        t1_tracker: T1Tracker,
        commission_model: CommissionModel
    ) -> None:
        """
        初始化执行器

        Args:
            db: 数据库连接
            t1_tracker: T+1追踪器
            commission_model: 佣金模型
        """
```

### 3.2 execute_auction

```python
def execute_auction(
    self,
    order: Order,
    trade_date: str
) -> Order:
    """
    执行集合竞价

    Args:
        order: 待执行订单
        trade_date: 交易日期

    Returns:
        Order: 执行后的订单（含成交信息）

    Note:
        - 自动获取开盘价
        - 开盘价成交（滑点默认为0）
        - 更新T+1冻结状态
        - 持久化成交记录
    """
```

### 3.3 execute_limit

```python
def execute_limit(
    self,
    order: Order,
    trade_date: str,
    current_price: float
) -> Order:
    """
    执行限价单

    Args:
        order: 待执行限价单
        trade_date: 交易日期
        current_price: 当前市价

    Returns:
        Order: 执行后的订单

    Note:
        买单：current_price <= order.price 时成交
        卖单：current_price >= order.price 时成交
    """
```

---

## 4. PositionManager（持仓管理器）

### 4.1 类定义

```python
class PositionManager:
    """持仓管理器"""

    def __init__(self, db: Database) -> None:
        """
        初始化持仓管理器

        Args:
            db: 数据库连接
        """
```

### 4.2 get_positions

```python
def get_positions(self) -> Dict[str, Position]:
    """
    获取所有持仓

    Returns:
        Dict[str, Position]: 持仓字典 {stock_code: Position}
    """
```

### 4.3 get_position

```python
def get_position(self, stock_code: str) -> Optional[Position]:
    """
    获取单个持仓

    Args:
        stock_code: 股票代码

    Returns:
        Position: 持仓对象，无持仓返回None
    """
```

### 4.4 add_position

```python
def add_position(
    self,
    stock_code: str,
    stock_name: str,
    shares: int,
    cost_price: float,
    buy_date: str,
    industry_code: str,
    signal_id: str = None,
    stop_price: float = None,
    target_price: float = None
) -> Position:
    """
    新增持仓

    Args:
        stock_code: 股票代码
        stock_name: 股票名称
        shares: 股数
        cost_price: 成本价
        buy_date: 买入日期
        industry_code: 行业代码
        signal_id: 关联信号ID
        stop_price: 止损价
        target_price: 目标价

    Returns:
        Position: 新增的持仓对象

    Note:
        如果已有持仓，自动计算加权平均成本
    """
```

### 4.5 reduce_position

```python
def reduce_position(
    self,
    stock_code: str,
    shares: int
) -> Tuple[Position, float]:
    """
    减少持仓

    Args:
        stock_code: 股票代码
        shares: 卖出股数

    Returns:
        Tuple[Position, float]: (更新后持仓, 实现盈亏)

    Raises:
        ValueError: 持仓不足
    """
```

### 4.6 update_market_price

```python
def update_market_price(
    self,
    stock_code: str,
    market_price: float
) -> Position:
    """
    更新持仓市价

    Args:
        stock_code: 股票代码
        market_price: 当前市价

    Returns:
        Position: 更新后的持仓

    Note:
        自动计算市值和未实现盈亏
    """
```

### 4.7 get_cash / get_market_value

```python
def get_cash(self) -> float:
    """获取可用现金"""

def get_market_value(self) -> float:
    """获取持仓总市值"""

def get_total_equity(self) -> float:
    """获取总权益（现金 + 市值）"""
```

---

## 5. RiskManager（风险管理器）

### 5.1 类定义

```python
class RiskManager:
    """风险管理器"""

    def __init__(
        self,
        config: RiskConfig,
        db: Database
    ) -> None:
        """
        初始化风险管理器

        Args:
            config: 风控配置
            db: 数据库连接
        """
```

### 5.2 check_order

```python
def check_order(
    self,
    order: Order,
    positions: Dict[str, Position],
    cash: float,
    total_equity: float
) -> Tuple[bool, str]:
    """
    检查订单是否通过风控

    Args:
        order: 待检查订单
        positions: 当前持仓
        cash: 可用现金
        total_equity: 总权益

    Returns:
        Tuple[bool, str]: (是否通过, 拒绝原因)

    检查项:
        1. 资金充足性（买单）
        2. 单股仓位上限（买单）
        3. 总仓位上限（买单）
        4. T+1限制（卖单）
        5. 涨跌停限制
        6. 行业集中度上限（买单，默认30%）
    """
```

### 5.3 check_stop_loss

```python
def check_stop_loss(
    self,
    positions: Dict[str, Position],
    current_prices: Dict[str, float]
) -> List[dict]:
    """
    检查是否触发止损

    Args:
        positions: 当前持仓
        current_prices: 当前价格字典

    Returns:
        List[dict]: 需要止损的持仓列表
            [{
                "position": Position,
                "current_price": float,
                "loss_ratio": float
            }]
    """
```

### 5.4 check_max_drawdown

```python
def check_max_drawdown(
    self,
    equity_curve: List[float]
) -> Tuple[bool, float]:
    """
    检查是否达到最大回撤限制

    Args:
        equity_curve: 净值曲线

    Returns:
        Tuple[bool, float]: (是否触发限制, 当前回撤)
    """
```

---

## 6. RiskManagerV2（v2.0风险管理器）

### 6.1 check_order_v2

```python
def check_order_v2(
    self,
    order: Order,
    positions: Dict[str, Position],
    cash: float,
    total_equity: float,
    validation: ValidationResult
) -> Tuple[bool, str, ValidationResult]:
    """
    v2.0订单检查（基于ValidationResult）

    Args:
        order: 待检查订单
        positions: 当前持仓
        cash: 可用现金
        total_equity: 总权益
        validation: 信号验证结果

    Returns:
        Tuple[bool, str, ValidationResult]: (是否通过, 拒绝原因, 验证结果)

    Note:
        - 执行基础风控检查
        - 检查信号质量
        - 根据risk_level调整仓位系数
    """
```

---

## 7. T1Tracker（T+1追踪器）

### 7.1 类定义

```python
class T1Tracker:
    """T+1追踪器"""

    def __init__(self, db: Database) -> None:
        """
        初始化T+1追踪器

        Args:
            db: 数据库连接
        """
```

### 7.2 buy

```python
def buy(
    self,
    stock_code: str,
    shares: int,
    trade_date: str
) -> None:
    """
    记录买入，冻结相应股数

    Args:
        stock_code: 股票代码
        shares: 买入股数
        trade_date: 买入日期

    Note:
        同一股票同一天的多笔买入会累加
    """
```

### 7.3 can_sell

```python
def can_sell(
    self,
    stock_code: str,
    shares: int,
    trade_date: str
) -> bool:
    """
    检查是否可以卖出

    Args:
        stock_code: 股票代码
        shares: 拟卖出股数
        trade_date: 当前交易日期

    Returns:
        bool: 是否可以卖出

    Note:
        今日买入的股票今日不能卖出
        可卖股数 = 总持仓 - 今日冻结
    """
```

### 7.4 get_frozen_shares

```python
def get_frozen_shares(
    self,
    stock_code: str,
    trade_date: str
) -> int:
    """
    获取指定股票在指定日期的冻结股数

    Args:
        stock_code: 股票代码
        trade_date: 交易日期

    Returns:
        int: 冻结股数
    """
```

### 7.5 clear_expired

```python
def clear_expired(self, trade_date: str) -> None:
    """
    清理过期冻结记录

    Args:
        trade_date: 当前交易日期

    Note:
        删除当日之前的冻结记录（已可卖）
    """
```

---

## 8. SignalValidator（信号验证器）

### 8.1 类定义

```python
class SignalValidator:
    """信号质量验证器（v2.0）"""

    def __init__(self, config: ValidationConfig) -> None:
        """
        初始化验证器

        Args:
            config: 验证配置
        """
```

### 8.2 validate_signal

```python
def validate_signal(
    self,
    signal: TradeSignal,
    mss: MssPanorama,
    irs: IrsIndustryDaily,
    pas: StockPasDaily
) -> ValidationResult:
    """
    验证信号质量

    Args:
        signal: 交易信号
        mss: MSS市场情绪
        irs: IRS行业轮动
        pas: PAS个股评分

    Returns:
        ValidationResult: 验证结果

    Note:
        - 计算质量评分 = max(signal.score, pas.opportunity_score)
        - 基于neutrality确定风险等级（中性度越低，信号越极端）
        - 输出仓位调整系数
    """
```

---

## 9. CommissionConfig（佣金计算）

### 9.1 calculate_buy

```python
def calculate_buy(self, amount: float) -> float:
    """
    计算买入费用

    Args:
        amount: 成交金额

    Returns:
        float: 总费用（佣金 + 过户费）

    Formula:
        commission = max(amount × 0.0003, 5)
        transfer_fee = amount × 0.00002
        total = commission + transfer_fee
    """
```

### 9.2 calculate_sell

```python
def calculate_sell(self, amount: float) -> float:
    """
    计算卖出费用

    Args:
        amount: 成交金额

    Returns:
        float: 总费用（印花税 + 佣金 + 过户费）

    Formula:
        stamp_duty = amount × 0.001
        commission = max(amount × 0.0003, 5)
        transfer_fee = amount × 0.00002
        total = stamp_duty + commission + transfer_fee
    """
```

---

## 10. SignalBuilder（信号构建器）

### 10.1 build_trade_signals

```python
def build_trade_signals(
    trade_date: str,
    config: TradeConfig
) -> List[TradeSignal]:
    """
    构建交易信号

    Args:
        trade_date: 交易日期
        config: 交易配置

    Returns:
        List[TradeSignal]: 交易信号列表

    Processing:
        1. Gate FAIL 前置检查（读取 validation_gate_decision；若 final_gate=FAIL 则直接返回空列表）
        2. MSS温度门控
        3. IRS行业筛选
        4. 获取集成推荐
        5. 评分过滤
        6. 构建TradeSignal

    Note:
        信号来源优先级：integrated > PAS > IRS
    """
```

---

## 11. 完整调用示例

```python
from trading.order_manager import OrderManager
from trading.executor import AuctionExecutor
from trading.position_manager import PositionManager
from trading.risk_manager import RiskManagerV2
from trading.t1_tracker import T1Tracker
from trading.commission import CommissionConfig
from trading.v2.signal_validator import SignalValidator

# 初始化组件
db = Database.from_env()
t1_tracker = T1Tracker(db)
commission = CommissionConfig()

# 初始化管理器
order_manager = OrderManager(db)
position_manager = PositionManager(db)
signal_validator = SignalValidator(ValidationConfig())
risk_manager = RiskManagerV2(RiskConfigV2(), db)

# 创建订单
order = order_manager.create_order(
    trade_date="20260131",
    stock_code="000001",
    direction="buy",
    shares=1000,
    price=12.50
)

# 获取验证结果
validation = signal_validator.validate_signal(signal, mss, irs, pas)

# 风控检查
positions = position_manager.get_positions()
cash = position_manager.get_cash()
total_equity = position_manager.get_total_equity()

passed, reason, validation = risk_manager.check_order_v2(
    order, positions, cash, total_equity, validation
)

if passed:
    # 提交并执行
    order_manager.submit_order(order)
    executor = AuctionExecutor(db, t1_tracker, commission)
    executed = executor.execute_auction(order, "20260131")
    print(f"成交: {executed.filled_shares}股 @ {executed.filled_price}")
else:
    print(f"订单被拒绝: {reason}")
```

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.1.5 | 2026-02-09 | 修复 R27：`validate_signal` 参数 `pas` 类型改为 `StockPasDaily`；`build_trade_signals` 增补 Gate FAIL 前置检查；`stock_code` 示例统一为内部格式 `000001` |
| v3.1.4 | 2026-02-09 | 修复 R20：`check_order` 检查项补齐“行业集中度上限（买单）”，与 trading-algorithm §3.1 Step 2.5 对齐 |
| v3.1.3 | 2026-02-08 | 修复 R16：`add_position()` 补充必填参数 `industry_code`，与 `Position` 数据模型对齐 |
| v3.1.2 | 2026-02-08 | 修复 R12：订单类型枚举口径统一为 `auction/market/limit/stop`（与 Backtest/Trading Data Models 对齐） |
| v3.1.1 | 2026-02-06 | 标注实现状态（代码未落地） |
| v3.1.0 | 2026-02-04 | 增加 auction_open 订单类型与开盘价成交说明 |
| v3.0.0 | 2026-01-31 | 重构版：统一API接口定义 |
| v2.1.0 | 2026-01-23 | 对齐三三制集成推荐 |
| v2.0.0 | 2026-01-20 | 增加SignalValidator和RiskManagerV2 |

---

**关联文档**：
- 核心算法：[trading-algorithm.md](./trading-algorithm.md)
- 数据模型：[trading-data-models.md](./trading-data-models.md)
- 信息流：[trading-information-flow.md](./trading-information-flow.md)
