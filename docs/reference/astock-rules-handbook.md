# A股市场规则参考手册

**版本**: v3.1.1（重构版）
**最后更新**: 2026-02-05
**适用范围**: EmotionQuant项目 A股交易规则 + TuShare数据映射
**数据源**: TuShare Pro + 上交所/深交所/北交所官方规则
**定位**: 参考资料（非设计规范）
**路线图口径**: Spiral + CP（兼容文件名 `ROADMAP-PHASE-*`，以 `Governance/ROADMAP/ROADMAP-OVERVIEW.md` 为准）
**冲突处理**: 若与 `docs/design/` 冲突，以设计文档为准

**合规声明**:
- ✅ 遵循系统铁律（单指标不得独立决策、情绪优先、本地数据优先、路径硬编码绝对禁止、A股专属）
- ✅ 路径/密钥/配置通过环境变量或配置注入

---

## 1. 交易所概述

### 1.1 三大交易所

| 交易所 | 简称 | 主要板块 | 涨跌停限制 |
|--------|------|----------|------------|
| 上海证券交易所 | 上交所/SSE | 主板、科创板 | 主板±10%、科创±20% |
| 深圳证券交易所 | 深交所/SZSE | 主板、创业板 | 主板±10%、创业±20% |
| 北京证券交易所 | 北交所/BSE | 创新层、基础层 | ±30% |

### 1.2 股票代码规则

| 代码前缀 | 板块 | 涨跌停 |
|----------|------|--------|
| 60xxxx | 上交所主板 | ±10% |
| 000xxx/001xxx | 深交所主板 | ±10% |
| 688xxx | 科创板 | ±20% |
| 300xxx | 创业板 | ±20% |
| 43xxxx/83xxxx | 北交所 | ±30% |
| ST/*ST | 风险警示 | ±5% |

---

## 2. 交易时间规则

### 2.1 标准交易时段

| 时段 | 时间 | 说明 |
|------|------|------|
| 开盘集合竞价 | 9:15-9:25 | 9:15-9:20可撤单，9:20-9:25不可撤单 |
| 上午连续竞价 | 9:30-11:30 | 主力资金活跃时段 |
| 午间休市 | 11:30-13:00 | 无交易 |
| 下午连续竞价 | 13:00-14:57 | 日内情绪波动关键期 |
| 收盘集合竞价 | 14:57-15:00 | 只能申报不能撤单 |

### 2.2 交易日历（TuShare）

```python
# TuShare接口
df_cal = pro.trade_cal(start_date='20200101', end_date='20261231', is_open='1')
# 关键字段: cal_date, is_open, pretrade_date
```

---

## 3. 涨跌停板制度

### 3.1 涨跌停规则

| 板块 | 涨停幅度 | 跌停幅度 | 新股首日 |
|------|----------|----------|----------|
| 主板 (沪深60/000) | +10% | -10% | 有限制 |
| 科创板 (688) | +20% | -20% | 前5日无限制 |
| 创业板 (300) | +20% | -20% | 前5日无限制 |
| 北交所 (43/83) | +30% | -30% | 首日无限制 |
| ST股票 | +5% | -5% | 无特殊 |

### 3.2 涨跌停价格计算

```python
def calculate_limit_prices(stock_code: str, prev_close: float) -> dict:
    """计算涨跌停价格"""
    code = stock_code.split('.')[0] if '.' in stock_code else stock_code
    
    # 判断板块
    if code.startswith('688'):
        limit_pct = 20.0  # 科创板
    elif code.startswith('300'):
        limit_pct = 20.0  # 创业板
    elif code.startswith('43') or code.startswith('83'):
        limit_pct = 30.0  # 北交所
    else:
        limit_pct = 10.0  # 主板
    
    limit_up = round(prev_close * (1 + limit_pct / 100), 2)
    limit_down = round(prev_close * (1 - limit_pct / 100), 2)
    
    return {
        'limit_up': limit_up,
        'limit_down': limit_down,
        'limit_pct': limit_pct
    }
```

---

## 4. T+1交易制度

### 4.1 核心规则

| 规则 | 说明 |
|------|------|
| 买入限制 | 当日买入的股票，当日不能卖出 |
| 卖出时间 | T+1日（下一交易日）起可卖出 |
| 资金交收 | T+1日资金到账 |
| 股票交收 | T+1日股票到账 |

### 4.2 回测实现

```python
def can_sell(buy_date: str, current_date: str) -> bool:
    """判断是否可以卖出"""
    buy_dt = datetime.strptime(buy_date, '%Y%m%d')
    current_dt = datetime.strptime(current_date, '%Y%m%d')
    
    # T+1: 买入次日可卖
    next_trade_date = get_next_trade_date(buy_date)
    return current_date >= next_trade_date
```

---

## 5. 交易费用

### 5.1 费用构成

| 费用类型 | 费率 | 说明 |
|----------|------|------|
| 佣金 | 0.03% | 最低5元，买卖双向 |
| 印花税 | 0.1% | 仅卖出收取 |
| 过户费 | 0.002% | 仅上交所 |

### 5.2 费用计算

```python
def calculate_trade_cost(amount: float, direction: str, exchange: str) -> float:
    """计算交易费用"""
    commission = max(amount * 0.0003, 5)  # 佣金，最低5元
    stamp_tax = amount * 0.001 if direction == 'sell' else 0  # 印花税
    transfer_fee = amount * 0.00002 if exchange == 'SSE' else 0  # 过户费
    
    return commission + stamp_tax + transfer_fee
```

---

## 6. TuShare数据映射

### 6.1 核心接口（5000积分）

| 接口 | 用途 | 频率 |
|------|------|------|
| trade_cal | 交易日历 | 年度 |
| stock_basic | 股票基本信息 | 日度 |
| daily | 个股日线 | 日度 |
| daily_basic | 个股指标 | 日度 |
| limit_list_d | 涨跌停列表 | 日度 |
| index_daily | 指数日线 | 日度 |
| index_member | 指数成分 | 月度 |
| index_classify | 行业分类 | 年度 |

### 6.2 MSS数据映射

| 系统字段 | TuShare来源 | 说明 |
|----------|-------------|------|
| total_stocks | stock_basic | 统计总数 |
| rise_count | daily.pct_chg > 0 | 上涨股票数 |
| fall_count | daily.pct_chg < 0 | 下跌股票数 |
| limit_up_count | limit_list_d.limit='U' | 涨停数 |
| limit_down_count | limit_list_d.limit='D' | 跌停数 |

### 6.3 IRS数据映射

| 系统字段 | TuShare来源 | 说明 |
|----------|-------------|------|
| industry_code | index_classify.index_code | 申万行业代码 |
| industry_name | index_classify.index_name | 申万行业名称 |
| return_pct | index_daily.pct_chg | 行业涨跌幅 |
| turnover_rate | index_daily.turnover_rate | 行业换手率 |

### 6.4 PAS数据映射

| 系统字段 | TuShare来源 | 说明 |
|----------|-------------|------|
| stock_code | daily.ts_code | 股票代码 |
| open/high/low/close | daily | OHLC价格 |
| volume | daily.vol | 成交量 |
| turnover_rate | daily_basic.turnover_rate | 换手率 |
| pe_ttm | daily_basic.pe_ttm | 市盈率 |

---

## 7. 数据下载顺序

### 7.1 推荐顺序

```
1. trade_cal          → 交易日历（基础）
2. stock_basic        → 股票列表（基础）
3. index_classify     → 行业分类（基础）
4. index_member       → 行业成分（月度）
5. daily              → 个股日线（日度）
6. daily_basic        → 个股指标（日度）
7. limit_list_d       → 涨跌停（日度）
8. index_daily        → 指数日线（日度）
```

### 7.2 增量更新策略

```python
def get_missing_dates(table_name: str, start_date: str, end_date: str) -> List[str]:
    """获取缺失的交易日"""
    existing_dates = get_existing_dates(table_name)
    all_trade_dates = get_trade_dates(start_date, end_date)
    
    return [d for d in all_trade_dates if d not in existing_dates]
```

---

## 8. 数据质量检查

### 8.1 检查清单

| 检查项 | 标准 | 告警级别 |
|--------|------|----------|
| 数据完整性 | 齐全率 ≥ 99% | P0 |
| 日期连续性 | 无缺失交易日 | P0 |
| 价格有效性 | 无负值/极端值 | P1 |
| 涨跌停一致性 | 与计算值一致 | P2 |

### 8.2 检查函数

```python
def check_data_quality(df: pd.DataFrame, table_name: str) -> dict:
    """数据质量检查"""
    return {
        'row_count': len(df),
        'null_rate': df.isnull().sum().sum() / df.size,
        'date_range': f"{df['trade_date'].min()} - {df['trade_date'].max()}",
        'duplicates': df.duplicated().sum()
    }
```

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.1.0 | 2026-02-04 | 增加参考口径与路线图对齐声明 |
| v3.0.0 | 2026-01-31 | 重构版：精简整合 |
| v4.1 | 2026-01-23 | v2.1设计集收口 |
| v4.0 | 2026-01-21 | TuShare 5000积分对齐 |

---

**关联文档**：
- 数据层设计：[../design/data-layer/](../design/data-layer/)
- 回测设计：[../design/backtest/](../design/backtest/)
