# ROADMAP Phase 07｜交易与风控（Trading）

**版本**: v4.1.0
**创建日期**: 2026-01-31
**最后更新**: 2026-02-06
**时间范围**: Phase 07
**核心交付**: 订单管理、T+1追踪、风控规则
**前置依赖**: Phase 05 (Integration)
**实现状态**: 未实现（截至 2026-02-06：`src/` 仅有 Skeleton/占位与少量基础骨架，详见 `Governance/ROADMAP/ROADMAP-OVERVIEW.md`）

---
## 文档对齐声明

> **权威设计文档**: `docs/design/trading/`

---

## 1. Phase 目标与量化验收标准

> **一句话**: 实现订单管理与风险控制

### 1.1 量化验收指标

| 指标项 | 验收标准 | 测量方法 | 优先级 |
|--------|----------|----------|--------|
| 订单状态机转换 | 所有转换测试通过 | 单元测试 | P0 |
| T+1规则合规 | T日买入不可卖出 | 单元测试 | P0 |
| 单股仓位限制 | 不超过10% | 集成测试 | P0 |
| 单股比例限制 | 不超过20% | 集成测试 | P0 |
| 行业仓位限制 | 不超过30% | 集成测试 | P0 |
| 总仓位限制 | 不超过80% | 集成测试 | P0 |
| 止损触发 | 8%亏损自动触发 | 单元测试 | P0 |
| 最大回撤限制 | 15%回撤触发风控 | 单元测试 | P0 |
| 测试覆盖率 | ≥ 80% | pytest-cov | P1 |

### 1.2 里程碑检查点

| 里程碑 | 交付物 | 验收条件 | 预期时间 |
|--------|--------|----------|----------|
| M7.1 | 订单状态机 | 所有状态转换测试通过 | Task 1 |
| M7.2 | T+1持仓管理 | T+1规则验证通过 | Task 2 |
| M7.3 | 仓位风控 | 单股/行业/总仓位限制测试通过 | Task 3 |
| M7.4 | 止损风控 | 止损/回撤限制测试通过 | Task 4 |

### 1.3 铁律约束（零容忍）

| 铁律 | 要求 | 检查方式 | 违反后果 |
|------|------|----------|----------|
| **T+1限制** | T日买入不可卖出 | 单元测试+实时检查 | 交易拒绝 |
| **风控不可绕过** | 所有交易必须过风控检查 | 代码审查 | 交易拒绝 |
| **订单幂等** | 相同订单不重复提交 | 幂等性测试 | 订单拒绝 |

---

## 2. 输入规范

### 2.1 数据依赖矩阵

| 输入表/接口 | 来源 | 关键字段 | 更新频率 | 必需 |
|-------------|------|----------|----------|------|
| integrated_recommendation | Phase 05 | final_score, recommendation, direction, integration_mode, entry/stop/target | 每交易日 | ✅ |
| stock_pas_daily | Phase 04 | entry, stop, target | 每交易日 | ✅ |
| raw_daily | Phase 01 L1 | close, pct_chg | 每交易日 | ✅ |
| raw_stock_basic | Phase 01 L1 | industry | 月度 | ✅ |
| raw_trade_cal | Phase 01 L1 | is_open | 年度 | ✅ |

### 2.2 订单输入

```python
@dataclass
class OrderRequest:
    """订单请求"""
    order_id: str                # 订单ID（客户端生成）
    stock_code: str              # 股票代码
    direction: str               # 交易方向 buy/sell
    order_type: str              # 订单类型 auction_open/market/limit/stop
    price: float                 # 委托价格
    quantity: int                # 委托数量（100的整数倍）
    order_time: datetime         # 委托时间
    signal_source: str           # 信号来源（integration/manual）
    signal_score: float          # 信号评分（如果来自信号）
    integration_mode: str = ""   # 集成模式（信号单透传）
    source_direction: str = ""   # 原始方向 bullish/bearish/neutral（信号单透传）
```

### 2.3 输入验证规则

| 验证项 | 规则 | 错误处理 |
|--------|------|----------|
| stock_code | 有效股票代码 | 拒绝订单 |
| quantity | > 0 且是100的倍数 | 拒绝订单 |
| price | > 0 | 拒绝订单 |
| direction | ∈ {buy, sell} | 拒绝订单 |
| order_type | ∈ {auction_open, market, limit, stop} | 拒绝订单 |
| 交易时间 | 在交易时段内 | 拒绝订单 |

---

### 2.4 集成信号桥接规则（Integration → Trading）

为确保与 Phase 05 / `docs/design/core-algorithms/integration/**` 口径一致，交易侧按以下规则桥接：

| 来源字段（integrated_recommendation） | 交易侧字段 | 规则 |
|--------------------------------------|------------|------|
| direction (bullish/bearish/neutral) | direction (buy/sell) | bullish→buy；bearish→sell；neutral→不下单（过滤） |
| integration_mode | integration_mode | 原样透传到信号上下文；订单落库通过 `signal_id` 回溯来源 |
| entry/stop/target | price/risk refs | 优先使用 integrated 字段；缺失时允许按风控参数补齐 |

```python
def map_signal_direction(signal_direction: str) -> str:
    mapping = {"bullish": "buy", "bearish": "sell", "neutral": "hold"}
    return mapping.get(signal_direction, "hold")
```

> 说明：`map_signal_direction(...) == "hold"` 的信号不生成订单。

---

## 3. 核心算法

### 3.1 订单状态机

```python
class OrderStatus(Enum):
    PENDING = "pending"       # 待提交
    SUBMITTED = "submitted"   # 已提交
    FILLED = "filled"         # 已成交
    PARTIALLY_FILLED = "partially_filled"  # 部分成交
    REJECTED = "rejected"     # 已拒绝
    CANCELLED = "cancelled"   # 已撤销

class OrderStateMachine:
    """
    订单状态机
    
    有效转换：
    PENDING -> SUBMITTED
    SUBMITTED -> FILLED
    SUBMITTED -> PARTIALLY_FILLED
    SUBMITTED -> REJECTED
    SUBMITTED -> CANCELLED
    PARTIALLY_FILLED -> FILLED
    PARTIALLY_FILLED -> CANCELLED
    """
    
    VALID_TRANSITIONS = {
        OrderStatus.PENDING: [OrderStatus.SUBMITTED],
        OrderStatus.SUBMITTED: [
            OrderStatus.FILLED, 
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.REJECTED,
            OrderStatus.CANCELLED
        ],
        OrderStatus.PARTIALLY_FILLED: [
            OrderStatus.FILLED,
            OrderStatus.CANCELLED
        ],
        OrderStatus.FILLED: [],
        OrderStatus.REJECTED: [],
        OrderStatus.CANCELLED: []
    }
    
    def transition(self, current: OrderStatus, target: OrderStatus) -> bool:
        """check if transition is valid"""
        return target in self.VALID_TRANSITIONS.get(current, [])
```

### 3.2 T+1 持仓管理

```python
@dataclass
class Position:
    """持仓记录"""
    stock_code: str
    quantity: int                # 持仓数量
    available_quantity: int      # 可卖数量（T+1后）
    avg_cost: float              # 平均成本
    buy_date: str                # 买入日期
    industry_code: str           # 所属行业

def update_available_quantity(position: Position, trade_date: str) -> Position:
    """
    T+1 规则：更新可卖数量
    
    规则：买入日的持仓不可卖出，T+1后自动解锁
    """
    if position.buy_date < trade_date:
        # T+1后，所有持仓可卖
        position.available_quantity = position.quantity
    else:
        # T日，当日买入不可卖
        position.available_quantity = 0
    return position

def check_sell_available(position: Position, sell_quantity: int) -> bool:
    """检查是否可卖出"""
    return position.available_quantity >= sell_quantity
```

### 3.3 风控规则引擎

```python
@dataclass
class RiskControlConfig:
    """风控配置"""
    max_position_pct: float = 0.10      # 单股最大仓位比例 10%
    max_position_ratio: float = 0.20    # 单股最大资金比例 20%
    max_industry_ratio: float = 0.30    # 行业最大仓位比例 30%
    max_total_position: float = 0.80    # 总仓位上限 80%
    stop_loss_ratio: float = 0.08       # 止损比例 8%
    max_drawdown_limit: float = 0.15    # 最大回撤限制 15%

class RiskControlEngine:
    """风控引擎"""
    
    def check_order(self, order: OrderRequest, portfolio: Portfolio) -> RiskCheckResult:
        """
        订单风控检查
        
        检查顺序：
        1. T+1限制（卖出时）
        2. 单股仓位限制（买入时）
        3. 行业仓位限制（买入时）
        4. 总仓位限制（买入时）
        """
        if order.direction == 'sell':
            return self._check_sell_risk(order, portfolio)
        else:
            return self._check_buy_risk(order, portfolio)
    
    def _check_sell_risk(self, order: OrderRequest, portfolio: Portfolio) -> RiskCheckResult:
        """check sell order risk"""
        position = portfolio.get_position(order.stock_code)
        
        # T+1 check
        if not check_sell_available(position, order.quantity):
            return RiskCheckResult(passed=False, reason='T+1_LIMIT', 
                                   message=f'可卖数量不足: {position.available_quantity}')
        
        return RiskCheckResult(passed=True)
    
    def _check_buy_risk(self, order: OrderRequest, portfolio: Portfolio) -> RiskCheckResult:
        """check buy order risk"""
        order_value = order.price * order.quantity
        total_equity = portfolio.total_equity
        
        # 1. 单股仓位检查
        current_position_value = portfolio.get_position_value(order.stock_code)
        new_position_value = current_position_value + order_value
        if new_position_value / total_equity > self.config.max_position_ratio:
            return RiskCheckResult(passed=False, reason='MAX_POSITION_RATIO',
                                   message=f'超过单股最大比例{self.config.max_position_ratio*100}%')
        
        # 2. 行业仓位检查
        industry_code = get_stock_industry(order.stock_code)
        current_industry_value = portfolio.get_industry_value(industry_code)
        new_industry_value = current_industry_value + order_value
        if new_industry_value / total_equity > self.config.max_industry_ratio:
            return RiskCheckResult(passed=False, reason='MAX_INDUSTRY_RATIO',
                                   message=f'超过行业最大比例{self.config.max_industry_ratio*100}%')
        
        # 3. 总仓位检查
        current_total_position = portfolio.total_position_value
        new_total_position = current_total_position + order_value
        if new_total_position / total_equity > self.config.max_total_position:
            return RiskCheckResult(passed=False, reason='MAX_TOTAL_POSITION',
                                   message=f'超过总仓位上限{self.config.max_total_position*100}%')
        
        return RiskCheckResult(passed=True)
```

### 3.4 止损监控

```python
def check_stop_loss(position: Position, current_price: float, config: RiskControlConfig) -> bool:
    """
    检查止损条件
    
    Returns:
        True: 触发止损
        False: 未触发
    """
    pnl_pct = (current_price - position.avg_cost) / position.avg_cost
    return pnl_pct <= -config.stop_loss_ratio

def check_max_drawdown(portfolio: Portfolio, config: RiskControlConfig) -> bool:
    """
    检查最大回撤限制
    
    Returns:
        True: 触发回撤限制
        False: 未触发
    """
    current_drawdown = (portfolio.peak_equity - portfolio.total_equity) / portfolio.peak_equity
    return current_drawdown >= config.max_drawdown_limit
```

---

## 4. 输出规范

### 4.1 订单记录输出

```python
@dataclass
class Order:
    """订单记录（输出）"""
    order_id: str                # 订单ID
    trade_date: str              # 交易日期
    stock_code: str              # 股票代码
    direction: str               # buy/sell
    order_type: str              # auction_open/market/limit/stop
    price: float                 # 委托价格
    quantity: int                # 委托数量
    filled_price: float          # 成交价格
    filled_quantity: int         # 成交数量
    status: str                  # 订单状态
    order_time: datetime         # 委托时间
    filled_time: datetime        # 成交时间
    commission: float            # 佣金
    stamp_tax: float             # 印花税
    reject_reason: str           # 拒绝原因
```

### 4.2 持仓输出

```python
@dataclass
class PositionRecord:
    """持仓记录（输出）"""
    stock_code: str              # 股票代码
    stock_name: str              # 股票名称
    quantity: int                # 持仓数量
    available_quantity: int      # 可卖数量
    avg_cost: float              # 平均成本
    current_price: float         # 当前价格
    market_value: float          # 市值
    pnl: float                   # 浮动盈亏
    pnl_pct: float               # 盈亏比例
    buy_date: str                # 买入日期
    holding_days: int            # 持仓天数
    industry_code: str           # 行业代码
```

### 4.3 数据库表结构

```sql
CREATE TABLE trade_records (
    trade_id VARCHAR(50) PRIMARY KEY,
    trade_date VARCHAR(8) NOT NULL,
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(50),
    direction VARCHAR(10) NOT NULL CHECK(direction IN ('buy','sell')),
    order_type VARCHAR(20) NOT NULL CHECK(order_type IN ('auction_open','market','limit','stop')),
    price DECIMAL(12,4),
    shares INTEGER,
    amount DECIMAL(16,2),
    commission DECIMAL(12,2),
    stamp_tax DECIMAL(12,2),
    transfer_fee DECIMAL(12,4),
    slippage DECIMAL(12,4),
    total_fee DECIMAL(16,2),
    status VARCHAR(20) NOT NULL CHECK(status IN ('filled','partially_filled','rejected')),
    signal_id VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code VARCHAR(20) NOT NULL,
    quantity INTEGER NOT NULL,
    available_quantity INTEGER NOT NULL,
    avg_cost DECIMAL(12,4) NOT NULL,
    buy_date VARCHAR(8) NOT NULL,
    industry_code VARCHAR(10),
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code)
);

CREATE INDEX idx_trade_stock ON trade_records(stock_code);
CREATE INDEX idx_trade_status ON trade_records(status);
CREATE INDEX idx_trade_date ON trade_records(trade_date);
```

### 4.4 输出验证规则

| 字段 | 验证规则 | 错误处理 |
|------|----------|----------|
| status | ∈ 有效状态集 | 抛出异常 |
| quantity | 是100的倍数 | 拒绝订单 |
| filled_quantity | ≤ quantity | 记录警告 |
| pnl_pct | ∈ [-1, +∞) | 记录警告 |

---

## 5. API 接口规范

```python
class OrderManager:
    """订单管理器接口"""
    
    def submit_order(self, order: OrderRequest) -> Order:
        """
        提交订单
        
        流程：
        1. 输入验证
        2. 风控检查
        3. 状态机转换
        4. 持久化
        """
        pass
    
    def cancel_order(self, order_id: str) -> Order:
        """撤销订单"""
        pass
    
    def get_order(self, order_id: str) -> Order:
        """查询订单"""
        pass
    
    def get_pending_orders(self) -> List[Order]:
        """获取待处理订单"""
        pass


class PositionManager:
    """持仓管理器接口"""
    
    def get_position(self, stock_code: str) -> Position:
        """获取持仓"""
        pass
    
    def get_all_positions(self) -> List[Position]:
        """获取所有持仓"""
        pass
    
    def update_t1_status(self, trade_date: str) -> None:
        """更新T+1状态"""
        pass


class RiskControlEngine:
    """风控引擎接口"""
    
    def check_order(self, order: OrderRequest, portfolio: Portfolio) -> RiskCheckResult:
        """订单风控检查"""
        pass
    
    def check_stop_loss_all(self, portfolio: Portfolio, prices: Dict[str, float]) -> List[str]:
        """检查所有持仓的止损条件，返回需止损的股票代码"""
        pass
    
    def check_drawdown(self, portfolio: Portfolio) -> bool:
        """检查最大回撤"""
        pass
```

---

## 6. 错误处理策略

### 6.1 错误分类与处理

| 错误场景 | 错误码 | 严重等级 | 处理策略 | 重试 |
|----------|--------|----------|----------|------|
| 输入参数无效 | TR_E001 | P0 | 拒绝订单 | 否 |
| T+1限制违反 | TR_E002 | P0 | 拒绝订单 | 否 |
| 仓位超限 | TR_E003 | P0 | 拒绝订单 | 否 |
| 资金不足 | TR_E004 | P1 | 拒绝订单 | 否 |
| 无效状态转换 | TR_E005 | P0 | 抛出异常 | 否 |
| 数据库写入失败 | TR_E006 | P0 | 重试3次 | ✅(3次) |
| 止损触发 | TR_E007 | P1 | 自动生成卖出订单 | 否 |
| 回撤限制触发 | TR_E008 | P0 | 警报+禁止新开仓 | 否 |

### 6.2 风控拒绝处理

```python
@dataclass
class RiskCheckResult:
    """risk check result"""
    passed: bool                 # 是否通过
    reason: str = None           # 拒绝原因码
    message: str = None          # 拒绝信息
    suggested_quantity: int = 0  # 建议数量（如果可部分执行）
```

---

## 7. 质量监控

### 7.1 质量检查项

| 检查项 | 检查方法 | 预期结果 | 告警阈值 |
|--------|----------|----------|----------|
| T+1合规 | 卖出订单检查 | 无T日卖出 | 任何违规 |
| 仓位限制合规 | 定期检查 | 在限制内 | 超限 |
| 订单状态一致 | 订单-持仓对账 | 一致 | 不一致 |
| 止损执行 | 检查触发日志 | 及时执行 | 延迟执行 |

### 7.2 质量监控表

```sql
CREATE TABLE trading_quality_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- 铁律检查
    t1_compliant BOOLEAN NOT NULL,
    position_limit_compliant BOOLEAN NOT NULL,
    
    -- 统计信息
    total_orders INTEGER,
    filled_orders INTEGER,
    rejected_orders INTEGER,
    stop_loss_triggered INTEGER,
    
    -- 异常信息
    error_code VARCHAR(20),
    error_message TEXT,
    
    status VARCHAR(20) DEFAULT 'PASS'
);
```

---

## 8. 执行计划

### 8.1 Task 级别详细计划

---

#### Task 1: 订单状态机

**目标**: 实现订单状态机和状态转换逻辑

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| integrated_recommendation | Phase 05 | 数据存在 | 可为空 |
| stock_pas_daily | Phase 04 | 入场/止损价 | 可为空 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| OrderStatus | 枚举 | 6个状态 | `src/trading/` |
| OrderStateMachine | 代码 | 所有转换 | `src/trading/` |
| OrderRequest | 数据类 | 订单请求 | `src/trading/` |
| Order | 数据类 | 订单记录 | `src/trading/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 状态转换 | 所有有效转换测试 | 单元测试 |
| 无效转换 | 拒绝并抛异常 | 单元测试 |
| 幂等性 | 相同订单不重复 | 单元测试 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 无效转换 | 抛出异常 | 立即阻断 |
| 重复订单 | 拒绝并返回原订单 | 记录警告 |

**验收检查**

- [ ] pending→submitted 转换正确
- [ ] submitted→filled/rejected/cancelled 转换正确
- [ ] 无效转换被拒绝
- [ ] 订单幂等性验证

---

#### Task 2: T+1持仓管理（⚠️铁律）

**目标**: 实现 T+1 持仓管理和可卖数量追踪

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| OrderStateMachine | Task 1 | 测试通过 | 阻断 |
| raw_trade_cal | Phase 01 L1 | 交易日历 | 阻断 |
| raw_stock_basic | Phase 01 L1 | 行业映射 | 阻断 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| Position | 数据类 | 持仓记录 | `src/trading/` |
| PositionManager | 代码 | T+1管理 | `src/trading/` |
| T1Checker | 代码 | T+1检查 | `src/trading/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| T+1合规 | T日买入不可卖 | 单元测试 |
| 可卖更新 | T+1后自动解锁 | 单元测试 |
| 持仓追踪 | 平均成本正确 | 单元测试 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| T日卖出 | 拒绝订单 | 立即阻断 |
| 可卖不足 | 拒绝订单 | 记录警告 |

**验收检查**

- [ ] **T+1规则正确**（T日买入不可卖）
- [ ] T+1后可卖数量自动更新
- [ ] 平均成本计算正确
- [ ] 持仓记录正确

---

#### Task 3: 仓位风控

**目标**: 实现单股/行业/总仓位限制

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| PositionManager | Task 2 | 测试通过 | 阻断 |
| raw_stock_basic | Phase 01 L1 | 行业映射 | 阻断 |
| raw_daily | Phase 01 L1 | 当前价格 | 阻断 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| RiskControlConfig | 配置 | 风控参数 | `src/trading/` |
| RiskControlEngine | 代码 | 仓位检查 | `src/trading/` |
| PositionChecker | 代码 | 单股/行业/总 | `src/trading/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 单股仓位 | 不超过10% | 集成测试 |
| 单股比例 | 不超过20% | 集成测试 |
| 行业仓位 | 不超过30% | 集成测试 |
| 总仓位 | 不超过80% | 集成测试 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 仓位超限 | 拒绝订单 | 记录警告 |
| 建议数量 | 返回建议数量 | 记录信息 |

**验收检查**

- [ ] 单股仓位限制生效（10%）
- [ ] 单股比例限制生效（20%）
- [ ] 行业仓位限制生效（30%）
- [ ] 总仓位限制生效（80%）

---

#### Task 4: 止损风控

**目标**: 实现止损触发和最大回撤限制

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| RiskControlEngine | Task 3 | 测试通过 | 阻断 |
| PositionManager | Task 2 | 测试通过 | 阻断 |
| raw_daily | Phase 01 L1 | 当前价格 | 阻断 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| StopLossMonitor | 代码 | 止损监控 | `src/trading/` |
| DrawdownChecker | 代码 | 回撤检查 | `src/trading/` |
| trade_records表 | 数据 | 交易记录 | Business Tables（DuckDB按年分库） |
| positions表 | 数据 | 持仓记录 | Business Tables（DuckDB按年分库） |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 止损触发 | 8%亏损自动触发 | 单元测试 |
| 回撤限制 | 15%触发风控 | 单元测试 |
| 覆盖率 | ≥80% | `pytest --cov` |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 止损触发 | 自动生成卖出订单 | 记录警告 |
| 回撤超限 | 禁止新开仓 | 记录警告 |

**验收检查**

- [ ] 止损触发正确（8%）
- [ ] 最大回撤限制正确（15%）
- [ ] 测试覆盖率≥80%
- [ ] **M7里程碑完成**

### 8.2 交易执行流程

```text
用户/策略提交订单请求
  ↓
输入验证
  ↓
风控检查
  ├─ 卖出: T+1检查
  └─ 买入: 单股/行业/总仓位检查
  ↓
订单状态 pending -> submitted
  ↓
等待成交回报
  ↓
成交处理
  ├─ filled: 更新持仓
  ├─ rejected: 记录拒绝原因
  └─ cancelled: 记录撤销
  ↓
持久化
```

---

## 9. 验收检查清单

### 9.1 铁律验收（零容忍）

- [ ] **T+1限制**: T日买入不可卖出
- [ ] **风控不可绕过**: 所有交易必须过风控
- [ ] **订单幂等**: 相同订单不重复提交

### 9.2 功能验收

- [ ] 订单状态机所有转换正确
- [ ] T+1持仓追踪正确
- [ ] 单股仓位限制生效（10%/20%）
- [ ] 行业仓位限制生效（30%）
- [ ] 总仓位限制生效（80%）
- [ ] 止损触发正确（8%）
- [ ] 最大回撤限制生效（15%）

### 9.3 质量验收

- [ ] 测试覆盖率 ≥ 80%
- [ ] 订单-持仓对账一致
- [ ] 数据库写入幂等

---

## 10. 参数配置表

### 10.1 风控参数

| 参数 | 代码 | 默认值 | 可调范围 | 说明 |
|------|------|--------|----------|------|
| 单股最大仓位 | max_position_pct | 10% | 5%-20% | 单股仓位上限 |
| 单股最大比例 | max_position_ratio | 20% | 10%-30% | 单股资金比例上限 |
| 行业最大仓位 | max_industry_ratio | 30% | 20%-50% | 行业仓位上限 |
| 总仓位上限 | max_total_position | 80% | 50%-100% | 总仓位上限 |
| 止损比例 | stop_loss_ratio | 8% | 5%-15% | 止损触发比例 |
| 最大回撤限制 | max_drawdown_limit | 15% | 10%-25% | 回撤限制 |

### 10.2 订单状态定义

| 状态 | 说明 | 后续操作 |
|------|------|----------|
| pending | 待提交 | 可取消 |
| submitted | 已提交 | 等待成交 |
| filled | 已成交 | 无 |
| partially_filled | 部分成交 | 可撤销剩余 |
| rejected | 已拒绝 | 无 |
| cancelled | 已撤销 | 无 |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v4.1.0 | 2026-02-06 | 对齐 Trading/Data-Layer：拆分 direction 与 order_type；补充 Integration 桥接规则；trade_records SQL 字段口径统一 |
| v4.0.1 | 2026-02-04 | 交易落库统一到 DuckDB 按年分库 |
| v4.0.0 | 2026-02-02 | 完整重构：添加量化验收标准、I/O规范、订单状态机、风控规则 |
| v3.0.0 | 2026-01-31 | 重构版 |


