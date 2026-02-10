# Trading 核心算法

**版本**: v3.2.5（重构版）
**最后更新**: 2026-02-09
**状态**: 设计完成（代码未落地）

---

## 实现状态（仓库现状）

- `src/trading/` 当前仅有 `__init__.py` 占位；交易/风控实现尚未落地。
- 本文档为设计口径；实现阶段需以此为准并同步更新记录。

---

## 1. 算法定位

Trading层负责将算法层（MSS/IRS/PAS集成推荐）输出转化为实际交易执行，核心职责：

1. **信号转化**：将integrated_recommendation转化为TradeSignal
2. **风险管理**：执行前风控检查
3. **交易执行**：集合竞价/限价单执行
4. **持仓管理**：T+1追踪、止损止盈

---

## 2. 信号生成算法

### 2.1 信号构建流程

```
输入: trade_date, config
输出: List[TradeSignal]

1. 获取集成推荐
   gate = get_validation_gate_decision(trade_date)
   if gate.final_gate == "FAIL":
       log.warning(f"Gate=FAIL on {trade_date}, skip trading signal generation")
       return []

   recs = get_integrated_recommendation(trade_date, top_n=config.top_n)

2. 主门槛过滤（与 Integration / Backtest 对齐）
   filtered_recs = []
   for row in recs:
       if row.final_score < config.min_final_score:
           continue
       if row.recommendation in {"AVOID", "SELL"}:
           continue
       if row.opportunity_grade == "D":
           continue
       if row.risk_reward_ratio < 1.0:
           continue
       filtered_recs.append(row)

3. 逐个构建信号
   for row in filtered_recs:
       signal_direction = row.direction  # bullish/bearish/neutral
       direction = map_signal_direction(signal_direction)
       if direction == "hold":
           continue

       # 计算入场/止损/目标价（入场价必须来自价格数据）
       entry = row.entry or get_market_price(row.stock_code, trade_date)
       if entry is None:
           continue
       stop = row.stop or entry * (1 - config.stop_loss_pct)
       target = row.target or entry * (1 + config.take_profit_pct)

       signal = TradeSignal(
           signal_id=f"SIG_{trade_date}_{row.stock_code}",
           trade_date=trade_date,
           stock_code=row.stock_code,
           stock_name=row.stock_name,
           industry_code=row.industry_code,
           direction=direction,
           source_direction=signal_direction,
           source="integrated",
           integration_mode=row.integration_mode,
           score=row.final_score,
           # Integration 已完成仓位缩放；Trading 仅做全局硬上限保护（默认 20%）
           position_size=min(row.position_size, config.max_position_pct),
           entry=entry,
           stop=stop,
           target=target,
           neutrality=row.neutrality,
           risk_reward_ratio=row.risk_reward_ratio,
           recommendation=row.recommendation,
           mss_score=row.mss_score,
           irs_score=row.irs_score,
           pas_score=row.pas_score
       )
       signals.append(signal)

   return signals
```

### 2.2 Integration 桥接规则

```python
def map_signal_direction(signal_direction: str) -> str:
    mapping = {"bullish": "buy", "bearish": "sell", "neutral": "hold"}
    return mapping.get(signal_direction, "hold")
```

- `source_direction` 保留原始方向（bullish/bearish/neutral）用于追溯。
- `direction` 仅允许 `buy/sell`；`hold` 不生成订单。
- `integration_mode` 从 `integrated_recommendation` 原样透传到 `TradeSignal`。

### 2.3 默认配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| min_final_score | 55 | final_score 主门槛（与 Integration/Backtest 对齐） |
| top_n | 20 | 每日最大推荐数 |
| max_position_pct | 0.20 | Trading 全局硬上限（应不低于 Integration 的 S 级上限 20%） |
| stop_loss_pct | 0.08 | 默认止损比例 |
| take_profit_pct | 0.15 | 默认止盈比例 |

---

## 3. 风险管理算法

### 3.1 订单风控检查

```
输入: order, positions, cash, total_equity
输出: (passed: bool, reason: str)

1. 资金检查（仅买单）
   if order.direction == "buy":
       required = order.amount + order.commission
       if required > cash:
           return (False, "资金不足")

2. 单股仓位检查（仅买单）
   if order.direction == "buy":
       current_value = positions[order.stock_code].market_value or 0
       new_value = current_value + order.amount
       new_ratio = new_value / total_equity
       if new_ratio > config.max_position_ratio:  # 默认20%
           return (False, f"单股仓位超限 ({new_ratio:.1%})")

2.5 行业集中度检查（仅买单）
   if order.direction == "buy":
       industry_value = sum(
           p.market_value for p in positions.values()
           if p.industry_code == order.industry_code
       )
       new_industry_ratio = (industry_value + order.amount) / total_equity
       if new_industry_ratio > config.max_industry_ratio:  # 默认30%
           return (False, f"行业仓位超限 ({new_industry_ratio:.1%})")

3. 总仓位检查（仅买单）
   if order.direction == "buy":
       total_position = sum(p.market_value for p in positions.values())
       new_total_ratio = (total_position + order.amount) / total_equity
       if new_total_ratio > config.max_total_position:  # 默认80%
           return (False, f"总仓位超限 ({new_total_ratio:.1%})")

4. T+1检查（仅卖单）
   if order.direction == "sell":
       if not t1_tracker.can_sell(order.stock_code, order.shares, order.trade_date):
           return (False, "T+1限制，今日买入不能卖出")

5. 涨跌停检查
   if is_limit_up(order.stock_code, order.trade_date) and order.direction == "buy":
       return (False, "涨停无法买入")
   if is_limit_down(order.stock_code, order.trade_date) and order.direction == "sell":
       return (False, "跌停无法卖出")

return (True, "")
```

### 3.2 风控配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| max_position_ratio | 0.20 | 单股最大仓位20% |
| max_industry_ratio | 0.30 | 行业最大仓位30% |
| max_total_position | 0.80 | 总仓位上限80% |
| stop_loss_ratio | 0.08 | 止损线8% |
| max_drawdown_limit | 0.15 | 最大回撤限制15% |

### 3.3 止损检查算法

```
输入: positions, current_prices
输出: List[StopLossOrder]

for pos in positions.values():
    current_price = current_prices[pos.stock_code]
    if current_price is None:
        continue

    # 计算亏损比例
    pct_loss = (current_price - pos.cost_price) / pos.cost_price

    if pct_loss <= -config.stop_loss_ratio:  # 默认-8%
        to_stop.append({
            "position": pos,
            "current_price": current_price,
            "loss_ratio": pct_loss,
        })

return to_stop
```

### 3.4 最大回撤检查

```
输入: equity_curve (净值曲线)
输出: (is_triggered: bool, current_drawdown: float)

peak = max(equity_curve)
current = equity_curve[-1]
drawdown = (peak - current) / peak

return (drawdown >= config.max_drawdown_limit, drawdown)
```

---

## 4. 信号质量验证（v2.0）

### 4.1 ValidationResult计算

```
输入: signal
输出: ValidationResult

1. 质量评分
   quality_score = signal.score
   neutrality = signal.neutrality

2. 风险分级（基于中性度，越低信号越极端）
   if neutrality <= 0.3:
       risk_level = "low"      # 中性度低→信号极端→全仓位
       position_adjustment = 1.0
   elif neutrality <= 0.6:
       risk_level = "medium"
       position_adjustment = 0.8
   else:
       risk_level = "high"     # 中性度高→信号不明确→6折仓位
       position_adjustment = 0.6

3. 可交易判断
   is_tradeable = quality_score >= config.min_quality_score  # 默认55

4. 构建原因
   reasons = []
   if not is_tradeable:
       reasons.append(f"信号质量不足: {quality_score:.1f}")

return ValidationResult(is_tradeable, risk_level, position_adjustment, reasons)
```

### 4.2 v2.0风控增强

基于ValidationResult调整仓位：

| risk_level | position_adjustment | 说明 |
|------------|---------------------|------|
| low | 1.0 | 全额仓位 |
| medium | 0.8 | 降仓20% |
| high | 0.6 | 降仓40% |

---

## 5. 交易执行算法

### 5.1 集合竞价执行

```
输入: order, trade_date
输出: executed_order

1. 获取开盘价
   open_price = get_open_price(order.stock_code, trade_date)
   if open_price is None:
       open_price = get_prev_close(order.stock_code, trade_date)
   if open_price is None:
       return reject("no_open_price")

2. 开盘价成交（集合竞价）
   filled_price = open_price
   slippage = 0.0

3. 成交数量
   filled_shares = order.shares  # 默认全额成交（风控已前置）

4. 计算费用
   commission = calculate_fee(filled_shares * filled_price, order.direction)

5. 更新订单
   order.filled_price = filled_price
   order.filled_shares = filled_shares
   order.filled_amount = filled_shares * filled_price
   order.commission = commission
   order.slippage = slippage
   order.status = "filled"

6. T+1处理
   if order.direction == "buy":
       t1_tracker.buy(order.stock_code, filled_shares, trade_date)

return order
```

### 5.2 费用计算

| 费用类型 | 费率 | 适用场景 |
|----------|------|----------|
| 佣金 | 0.03%（万三） | 买卖 |
| 印花税 | 0.1%（千一） | 仅卖出 |
| 过户费 | 0.002%（万0.2） | 买卖 |
| 最低佣金 | 5元 | 佣金下限 |

```
买入费用 = max(金额 * 0.0003, 5) + 金额 * 0.00002
卖出费用 = 金额 * 0.001 + max(金额 * 0.0003, 5) + 金额 * 0.00002
```

---

## 6. T+1追踪算法

### 6.1 买入冻结

```
buy(stock_code, shares, trade_date):
    frozen[stock_code][trade_date] += shares
    save_to_db()
```

### 6.2 可卖判断

```
can_sell(stock_code, shares, trade_date) -> bool:
    if stock_code not in positions:
        return False

    # 今日冻结数
    frozen_today = frozen.get(stock_code, {}).get(trade_date, 0)
    # 实际总持仓（来自持仓表）
    total_shares = positions[stock_code].shares
    # 可卖数 = 总持仓 - 今日冻结
    available = total_shares - frozen_today

    return shares <= available
```

### 6.3 过期清理

```
clear_expired(trade_date):
    for stock_code in frozen:
        # 删除今日之前的冻结记录（已可卖）
        for d in list(frozen[stock_code].keys()):
            if d < trade_date:
                del frozen[stock_code][d]
```

---

## 7. 订单状态机

```
┌─────────────────────────────────────────────────────────────┐
│                       订单状态机                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   pending ──→ submitted ──→ partially_filled ──→ filled     │
│      │            │                 │                        │
│      │            ▼                 ▼                        │
│      │        rejected          cancelled                    │
│      │                                                       │
│      └────────→ rejected                                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

状态转换规则：
- pending → submitted: 提交订单
- pending → rejected: 风控拒绝
- submitted → partially_filled: 部分成交
- submitted → filled: 全部成交
- submitted → rejected: 执行失败
- partially_filled → filled: 继续成交完成
- partially_filled → cancelled: 撤单

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.2.5 | 2026-02-09 | 修复 R26：§2.1 增加 Validation Gate FAIL 前置阻断；新增 `opportunity_grade=D` 与 `risk_reward_ratio < 1.0` 执行层过滤，避免低质量信号下发 |
| v3.2.4 | 2026-02-09 | 修复 R20：§2.1 移除 IRS/PAS/行业硬截断，统一主门槛为 `final_score + recommendation`；§4.1 `quality_score` 改为 `signal.score`，避免 PAS 权重二次膨胀 |
| v3.2.3 | 2026-02-08 | 修复 R11：订单风控 §3.1 增加行业集中度检查（`max_industry_ratio`）并纳入买单拦截 |
| v3.2.2 | 2026-02-08 | 修复 R10：`can_sell` 在“无持仓”场景改为返回 `False`，避免卖空语义误判 |
| v3.2.1 | 2026-02-07 | 修复 R7：去除 Integration→Trading 冷市场双重仓位缩放；`max_position_pct` 调整为全局硬上限 20%；`can_sell` 改为基于持仓总股数判定；TradeSignal 补齐 `signal_id/industry_code` |
| v3.2.0 | 2026-02-06 | 补齐 Integration→Trading 桥接：direction 映射、integration_mode/source_direction 透传、neutral 信号过滤 |
| v3.1.1 | 2026-02-06 | 标注实现状态（代码未落地） |
| v3.1.0 | 2026-02-04 | 集合竞价开盘价成交与盘前挂单流程对齐 |
| v3.0.0 | 2026-01-31 | 重构版：统一算法描述 |
| v2.1.0 | 2026-01-23 | 对齐三三制集成推荐 |
| v2.0.0 | 2026-01-20 | 增加ValidationResult |

---

**关联文档**：
- 数据模型：[trading-data-models.md](./trading-data-models.md)
- API接口：[trading-api.md](./trading-api.md)
- 信息流：[trading-information-flow.md](./trading-information-flow.md)
