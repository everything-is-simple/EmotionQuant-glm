# Backtest 测试用例与边界场景清单

**版本**: v1.0.0
**最后更新**: 2026-02-05
**状态**: 设计校验清单（用于 CP-06 实现与验收，兼容文件名 Phase 06）

---

## 1. 约束与时间轴类

1. **T+1 规则**
   - 用例：T 日买入，T 日尝试卖出
   - 预期：卖出被拒绝（不可卖）

2. **signal_date/execute_date**
   - 用例：signal_date=T，execute_date=T+1
   - 预期：成交发生在 T+1 开盘；T 日不成交

3. **非交易日**
   - 用例：signal_date 落在休市日
   - 预期：跳过，不生成交易

4. **停牌日**
   - 用例：execute_date 停牌
   - 预期：无成交，持仓顺延，持仓天数不增加

---

## 2. 涨跌停与成交可行性

1. **涨停不可买**
   - 用例：execute_date 开盘即涨停
   - 预期：买单拒绝或成交概率=0

2. **跌停不可卖**
   - 用例：execute_date 开盘即跌停
   - 预期：卖单拒绝或成交概率=0

3. **涨跌停边界**
   - 用例：开盘价接近涨停（但未涨停）
   - 预期：允许买入，但成交概率受影响

---

## 3. 成交与滑点

1. **集合竞价成交**
   - 用例：order_type=auction
   - 预期：成交价=开盘价±滑点

2. **固定滑点**
   - 用例：slippage_type=fixed，slippage_value=0.001
   - 预期：买入价=开盘×(1+0.001)，卖出价=开盘×(1-0.001)

3. **量能相关滑点**
   - 用例：slippage_type=variable
   - 预期：成交价随量能调整但不越界

---

## 4. 费用模型

1. **佣金最低收费**
   - 用例：小额成交
   - 预期：佣金= min_commission

2. **印花税仅卖出**
   - 用例：买入与卖出
   - 预期：买入不收印花税，卖出收取

3. **过户费双边**
   - 用例：买入与卖出
   - 预期：双边收取

---

## 5. 仓位与资金管理

1. **100 股整手**
   - 用例：现金不足 100 股
   - 预期：不成交

2. **单票上限**
   - 用例：position_size > max_position_pct
   - 预期：按 max_position_pct 限制

3. **最大持仓数**
   - 用例：已达 max_positions
   - 预期：新增买入被拒绝

4. **先卖后买**
   - 用例：当日既有卖又有买
   - 预期：先卖出释放现金，再买入

---

## 6. 出场逻辑

1. **止损触发**
   - 用例：开盘跌破 stop_loss_pct
   - 预期：卖出

2. **止盈触发**
   - 用例：开盘涨幅 ≥ take_profit_pct
   - 预期：卖出

3. **最大持仓天数**
   - 用例：持仓天数达到上限
   - 预期：强制卖出

---

## 7. 数据缺失与降级

1. **L1 日线缺失**
   - 用例：raw_daily 缺失某股
   - 预期：跳过该股

2. **L3 信号缺失**
   - 用例：integrated_recommendation 缺失
   - 预期：回退上一可用日，标记 degraded

3. **BU 活跃度不足**
   - 用例：pas_breadth_daily.pas_sa_ratio < 阈值
   - 预期：禁用 BU，回退 TD

---

## 8. 绩效指标

1. **收益率**
   - 用例：固定收益序列
   - 预期：total_return/annual_return 与手工计算一致

2. **最大回撤**
   - 用例：单峰-回撤序列
   - 预期：max_drawdown 与手工计算一致

3. **夏普/索提诺/卡玛**
   - 用例：已知均值/波动率序列
   - 预期：误差 < 0.01

---

## 9. 集成模式覆盖

1. **Top-Down**
   - 用例：integration_mode=top_down
   - 预期：按 TD 信号运行

2. **Bottom-Up**
   - 用例：integration_mode=bottom_up
   - 预期：通过 pas_breadth 门槛后运行

3. **Dual/Complementary**
   - 用例：integration_mode=dual_verify/complementary
   - 预期：不突破 TD 上限

---

## 10. 质量门禁

1. **无未来函数**
   - 用例：所有成交仅使用 execute_date 的数据
   - 预期：历史无未来引用

2. **T+1 合规扫描**
   - 用例：交易记录回放
   - 预期：无当日买卖同股

3. **涨跌停合规扫描**
   - 用例：交易记录回放
   - 预期：无涨停买/跌停卖

---

## 关联文档

- `docs/design/backtest/backtest-algorithm.md`
- `docs/design/backtest/backtest-data-models.md`
- `docs/design/backtest/backtest-api.md`
- `docs/design/backtest/backtest-information-flow.md`
