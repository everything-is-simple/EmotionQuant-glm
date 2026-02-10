# ROADMAP Phase 09｜分析报告（Analysis）

**版本**: v4.0.1
**创建日期**: 2026-01-31
**最后更新**: 2026-02-06
**时间范围**: Phase 09
**核心交付**: 绩效分析、信号归因、日报生成
**前置依赖**: Phase 01-07
**实现状态**: 未实现（截至 2026-02-06：`src/` 仅有 Skeleton/占位与少量基础骨架，详见 `Governance/ROADMAP/ROADMAP-OVERVIEW.md`）

---
## 文档对齐声明

> **权威设计文档**: `docs/design/analysis/`

---

## 1. Phase 目标与量化验收标准

> **一句话**: 分析策略绩效，生成投资报告

### 1.1 量化验收指标

| 指标项 | 验收标准 | 测量方法 | 优先级 |
|--------|----------|----------|--------|
| 绩效指标计算 | 误差 < 0.01% | 与手工计算对比 | P0 |
| 信号归因正确性 | MSS+IRS+PAS贡献符合预期 | 统计验证 | P0 |
| 日报生成成功率 | 100% | 自动化测试 | P0 |
| 报告生成时间 | ≤ 30秒 | 性能测试 | P1 |
| 测试覆盖率 | ≥ 80% | pytest-cov | P1 |

### 1.2 里程碑检查点

| 里程碑 | 交付物 | 验收条件 | 预期时间 |
|--------|--------|----------|----------|
| M9.1 | 绩效指标计算 | 所有指标测试通过 | Task 1 |
| M9.2 | 信号归因分析 | MSS/IRS/PAS贡献计算正确 | Task 2 |
| M9.3 | 日报生成器 | 日报自动生成可用 | Task 3 |
| M9.4 | 落库与调度 | performance_metrics数据完整 | Task 4 |

---

## 2. 输入规范

### 2.1 数据依赖矩阵

| 输入表/接口 | 来源 | 关键字段 | 更新频率 | 必需 |
|-------------|------|----------|----------|------|
| mss_panorama | Phase 02 | temperature, cycle, trend | 每交易日 | ✅ |
| irs_industry_daily | Phase 03 | industry_score, rotation_status | 每交易日 | ✅ |
| stock_pas_daily | Phase 04 | opportunity_score, opportunity_grade | 每交易日 | ✅ |
| integrated_recommendation | Phase 05 | final_score, recommendation | 每交易日 | ✅ |
| backtest_results | Phase 06 | 绩效指标 | 按需 | ✅ |
| trade_records | Phase 07 | 交易记录 | 每交易日 | ✅ |
| positions | Phase 07 | 持仓信息 | 实时 | ✅ |

### 2.2 分析配置输入

```python
@dataclass
class AnalysisConfig:
    """分析配置"""
    # 时间范围
    start_date: str              # 开始日期 YYYYMMDD
    end_date: str                # 结束日期 YYYYMMDD
    
    # 报告类型
    report_type: str             # daily/weekly/monthly
    
    # 归因配置
    attribution_method: str      # simple/regression
    
    # 基准
    benchmark: str               # HS300/ZZ500/None
    risk_free_rate: float        # 无风险利率（默认0.03）
```

### 2.3 输入验证规则

| 验证项 | 规则 | 错误处理 |
|--------|------|----------|
| start_date | ≤ end_date | 抛出 ValueError |
| report_type | ∈ {daily, weekly, monthly} | 默认daily |
| risk_free_rate | ∈ [0, 0.1] | 截断到边界 |

---

## 3. 核心算法

### 3.1 绩效指标计算

```python
class PerformanceCalculator:
    """绩效计算器"""
    
    def calculate_total_return(self, equity_curve: List[float]) -> float:
        """
        总收益率 = (equity_end - equity_start) / equity_start
        """
        return (equity_curve[-1] - equity_curve[0]) / equity_curve[0]
    
    def calculate_annual_return(self, total_return: float, days: int) -> float:
        """
        年化收益率 = (1 + total_return)^(252/N) - 1
        """
        return (1 + total_return) ** (252 / days) - 1
    
    def calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """
        最大回撤 = max((peak - trough) / peak)
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
    
    def calculate_sharpe_ratio(
        self, 
        daily_returns: List[float], 
        risk_free_rate: float = 0.03
    ) -> float:
        """
        夏普比率 = sqrt(252) × (mean(r) - rf/252) / std(r)
        """
        import numpy as np
        excess_returns = np.array(daily_returns) - risk_free_rate / 252
        return np.sqrt(252) * np.mean(excess_returns) / np.std(excess_returns)
    
    def calculate_win_rate(self, trades: List[Trade]) -> float:
        """
        胜率 = 盈利交易数 / 总交易数
        """
        if not trades:
            return 0
        winning = sum(1 for t in trades if t.pnl > 0)
        return winning / len(trades)
    
    def calculate_profit_factor(self, trades: List[Trade]) -> float:
        """
        盈亏比 = total_profit / total_loss
        """
        if not trades:
            return 0
        total_profit = sum(t.pnl for t in trades if t.pnl > 0)
        total_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
        if total_loss == 0:
            return float('inf')
        return total_profit / total_loss
    
    def calculate_calmar_ratio(
        self, 
        annual_return: float, 
        max_drawdown: float
    ) -> float:
        """
        卡玛比率 = 年化收益率 / 最大回撤
        """
        if max_drawdown == 0:
            return 0
        return annual_return / max_drawdown
```

### 3.2 信号归因分析

```python
class SignalAttribution:
    """信号归因分析"""
    
    def calculate_attribution(
        self, 
        trades: List[Trade],
        signals: Dict[str, SignalData]  # trade_id -> SignalData
    ) -> AttributionResult:
        """
        计算MSS/IRS/PAS各自的绩效贡献
        
        方法：简单加权
        contribution = sum(score × pnl) / sum(|pnl|)
        """
        mss_attribution = 0
        irs_attribution = 0
        pas_attribution = 0
        total_abs_pnl = sum(abs(t.pnl) for t in trades)
        
        if total_abs_pnl == 0:
            return AttributionResult(0, 0, 0)
        
        for trade in trades:
            signal = signals.get(trade.trade_id)
            if signal:
                # 按1/3原则分配
                mss_attribution += (signal.mss_score / 100) * trade.pnl / 3
                irs_attribution += (signal.irs_score / 100) * trade.pnl / 3
                pas_attribution += (signal.pas_score / 100) * trade.pnl / 3
        
        return AttributionResult(
            mss_attribution=mss_attribution / total_abs_pnl,
            irs_attribution=irs_attribution / total_abs_pnl,
            pas_attribution=pas_attribution / total_abs_pnl
        )
    
    def calculate_signal_accuracy(
        self, 
        signals: List[SignalData],
        outcomes: List[float]  # 实际收益
    ) -> Dict[str, float]:
        """
        计算信号准确率
        
        对于每个信号级别，计算实际盈利比例
        """
        accuracy = {}
        for grade in ['S', 'A', 'B', 'C', 'D']:
            grade_signals = [(s, o) for s, o in zip(signals, outcomes) 
                           if s.opportunity_grade == grade]
            if grade_signals:
                profitable = sum(1 for _, o in grade_signals if o > 0)
                accuracy[grade] = profitable / len(grade_signals)
        return accuracy
```

### 3.3 日报生成器

```python
class DailyReportGenerator:
    """日报生成器"""
    
    def generate(self, report_date: str) -> DailyReportData:
        """
        生成日报数据
        
        包含模块：
        1. 市场概况（MSS）
        2. 行业轮动（IRS Top5）
        3. 信号统计
        4. 绩效摘要
        5. 推荐列表
        6. 风险提示
        """
        market_overview = self._generate_market_overview(report_date)
        industry_rotation = self._generate_industry_rotation(report_date)
        signal_stats = self._generate_signal_stats(report_date)
        performance = self._generate_performance_summary(report_date)
        top_recommendations = self._generate_recommendations(report_date, top_n=20)
        risk_summary = self._generate_risk_summary(top_recommendations)
        
        return DailyReportData(
            report_date=report_date,
            market_overview=market_overview,
            industry_rotation=industry_rotation,
            signal_stats=signal_stats,
            performance=performance,
            top_recommendations=top_recommendations,
            risk_summary=risk_summary
        )
    
    def _generate_market_overview(self, report_date: str) -> MarketOverview:
        """生成市场概况"""
        mss = get_mss_panorama(report_date)
        return MarketOverview(
            temperature=mss.temperature,
            temperature_level=self._temperature_level(mss.temperature),
            cycle=mss.cycle,
            cycle_label=self._cycle_label(mss.cycle),
            trend=mss.trend,
            position_advice=mss.position_advice
        )
    
    def _generate_industry_rotation(self, report_date: str) -> IndustryRotation:
        """生成行业轮动"""
        industries = get_irs_industry_daily(report_date)
        top5 = sorted(industries, key=lambda x: x.industry_score, reverse=True)[:5]
        in_rotation = [i for i in industries if i.rotation_status == 'IN']
        out_rotation = [i for i in industries if i.rotation_status == 'OUT']
        strong = [i for i in industries if i.rotation_status == 'STRONG']
        
        return IndustryRotation(
            top5=[(i.industry_name, i.industry_score) for i in top5],
            in_count=len(in_rotation),
            out_count=len(out_rotation),
            strong_count=len(strong)
        )
    
    def _generate_signal_stats(self, report_date: str) -> SignalStats:
        """生成信号统计"""
        signals = get_integrated_recommendations(report_date)
        trades = get_trades_by_date(report_date)
        filled_count = sum(1 for t in trades if t.status == 'filled')
        reject_count = sum(1 for t in trades if t.status == 'rejected')
        signal_count = len(signals)
        pending_count = max(signal_count - filled_count - reject_count, 0)
        fill_rate = filled_count / signal_count if signal_count else 0
        
        return SignalStats(
            signal_count=signal_count,
            filled_count=filled_count,
            reject_count=reject_count,
            pending_count=pending_count,
            fill_rate=fill_rate
        )
    
    def _generate_performance_summary(self, report_date: str) -> PerformanceSummary:
        """生成绩效摘要"""
        metrics = get_performance_metrics(report_date)
        return PerformanceSummary(
            total_return=metrics.total_return,
            total_return_pct=format_pct(metrics.total_return),
            max_drawdown=metrics.max_drawdown,
            max_drawdown_pct=format_pct(metrics.max_drawdown),
            sharpe_ratio=metrics.sharpe_ratio,
            win_rate=metrics.win_rate,
            win_rate_pct=format_pct(metrics.win_rate)
        )
    
    def _generate_recommendations(
        self, report_date: str, top_n: int = 20
    ) -> List[RecommendationSummary]:
        """生成推荐列表（前N名）"""
        recommendations = get_integrated_recommendations(report_date)
        top = sorted(recommendations, key=lambda x: x.final_score, reverse=True)[:top_n]
        return [
            RecommendationSummary(
                rank=idx + 1,
                stock_code=r.stock_code,
                stock_name=r.stock_name,
                industry_name=r.industry_name,
                final_score=r.final_score,
                position_size=r.position_size,
                entry=r.entry,
                stop=r.stop,
                target=r.target,
                recommendation=r.recommendation
            )
            for idx, r in enumerate(top)
        ]
    
    def _generate_risk_summary(
        self, recommendations: List[RecommendationSummary]
    ) -> RiskSummary:
        """生成风险摘要"""
        summary = calculate_risk_distribution(recommendations)
        return RiskSummary(
            low_risk_count=summary["low_count"],
            medium_risk_count=summary["medium_count"],
            high_risk_count=summary["high_count"],
            low_risk_pct=summary["low_pct"],
            medium_risk_pct=summary["medium_pct"],
            high_risk_pct=summary["high_pct"],
            risk_alert=summary["risk_alert"]
        )
```

---

## 4. 输出规范

### 4.1 绩效指标输出

```python
@dataclass
class PerformanceMetrics:
    """绩效指标（输出）"""
    # 标识
    metric_date: str             # 指标日期 YYYYMMDD
    
    # 收益指标
    total_return: float          # 总收益率
    annual_return: float         # 年化收益率
    
    # 风险指标
    max_drawdown: float          # 最大回撤
    sharpe_ratio: float          # 夏普比率
    sortino_ratio: float         # 索提诺比率
    calmar_ratio: float          # 卡玛比率
    
    # 交易指标
    win_rate: float              # 胜率
    profit_factor: float         # 盈亏比
    total_trades: int            # 总交易数
    avg_holding_days: float      # 平均持仓天数
    
    # 元数据
    created_at: datetime         # 创建时间
```

### 4.2 日报输出

```python
@dataclass
class DailyReport:
    """日报（输出）"""
    report_date: str             # 报告日期
    # 市场概况
    market_temperature: float    # MSS温度
    cycle: str                   # 周期阶段
    trend: str                   # 趋势方向
    position_advice: str         # 仓位建议
    # 信号统计
    signal_count: int            # 信号数
    filled_count: int            # 成交数
    reject_count: int            # 拒绝数
    # 有效性指标
    hit_rate: float              # 命中率
    avg_return_5d: float         # 5日平均收益
    avg_holding_days: float      # 平均持仓天数
    # 绩效指标
    max_drawdown: float          # 最大回撤
    sharpe_ratio: float          # 夏普比率
    win_rate: float              # 胜率
    # 详情
    top_recommendations: List[dict]  # Top N推荐（JSON）
    risk_summary: dict           # 风险摘要（JSON）
    created_at: datetime         # 创建时间
```

### 4.3 数据库表结构

```sql
CREATE TABLE performance_metrics (
    metric_date VARCHAR(8) PRIMARY KEY,
    total_return DECIMAL(10,4),
    annual_return DECIMAL(10,4),
    max_drawdown DECIMAL(10,4),
    sharpe_ratio DECIMAL(10,4),
    sortino_ratio DECIMAL(10,4),
    calmar_ratio DECIMAL(10,4),
    win_rate DECIMAL(8,4),
    profit_factor DECIMAL(10,4),
    total_trades INT,
    avg_holding_days DECIMAL(8,2),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE daily_report (
    report_date VARCHAR(8) PRIMARY KEY,
    market_temperature DECIMAL(8,4),
    cycle VARCHAR(20),
    trend VARCHAR(20),
    position_advice VARCHAR(50),
    signal_count INT,
    filled_count INT,
    reject_count INT,
    hit_rate DECIMAL(8,4),
    avg_return_5d DECIMAL(8,4),
    avg_holding_days DECIMAL(8,2),
    max_drawdown DECIMAL(8,4),
    sharpe_ratio DECIMAL(8,4),
    win_rate DECIMAL(8,4),
    top_recommendations JSON,
    risk_summary JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE signal_attribution (
    trade_date VARCHAR(8) PRIMARY KEY,
    mss_attribution DECIMAL(10,6),
    irs_attribution DECIMAL(10,6),
    pas_attribution DECIMAL(10,6),
    sample_count INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_metrics_date ON performance_metrics(metric_date);
CREATE INDEX idx_report_date ON daily_report(report_date);
CREATE INDEX idx_signal_attr_date ON signal_attribution(trade_date);
```

### 4.4 输出验证规则

| 字段 | 验证规则 | 错误处理 |
|------|----------|----------|
| total_return | ∈ [-1, +∞) | 记录警告 |
| win_rate | ∈ [0, 1] | 截断到边界 |
| sharpe_ratio | ∈ [-10, 10] | 截断到边界 |
| attribution总和 | ≈ 1 | 归一化 |

---

## 5. API 接口规范

```python
class AnalysisService:
    """分析服务接口"""
    
    def calculate_performance(
        self, 
        start_date: str, 
        end_date: str
    ) -> PerformanceMetrics:
        """计算绩效指标"""
        pass
    
    def calculate_attribution(
        self, 
        start_date: str, 
        end_date: str
    ) -> AttributionResult:
        """计算信号归因"""
        pass
    
    def generate_daily_report(self, report_date: str) -> DailyReportData:
        """生成日报"""
        pass
    
    def generate_weekly_report(self, end_date: str) -> WeeklyReport:
        """生成周报"""
        pass
    
    def get_performance_history(
        self, 
        start_date: str,
        end_date: str
    ) -> List[PerformanceMetrics]:
        """获取历史绩效"""
        pass


class ReportRepository:
    """报告数据仓库"""
    
    def save_metrics(self, metrics: PerformanceMetrics) -> None:
        """保存绩效指标"""
        pass
    
    def save_report(self, report: DailyReport) -> None:
        """保存日报"""
        pass
    
    def get_report(self, report_date: str) -> DailyReport:
        """获取日报"""
        pass
```

---

## 6. 错误处理策略

### 6.1 错误分类与处理

| 错误场景 | 错误码 | 严重等级 | 处理策略 | 重试 |
|----------|--------|----------|----------|------|
| 数据不足 | AN_E001 | P1 | 返回空报告+警告 | 否 |
| 计算错误 | AN_E002 | P0 | 抛出异常 | 否 |
| 数据库写入失败 | AN_E003 | P0 | 重试3次 | ✅(3次) |
| 报告生成失败 | AN_E004 | P1 | 重试3次+告警 | ✅(3次) |
| 无交易数据 | AN_E005 | P2 | 生成空报告 | 否 |

---

## 7. 质量监控

### 7.1 质量检查项

| 检查项 | 检查方法 | 预期结果 | 告警阈值 |
|--------|----------|----------|----------|
| 绩效指标计算 | 与手工计算对比 | 误差<0.01% | 超过阈值 |
| 归因总和 | MSS+IRS+PAS | ≈ 1 | 偏差>5% |
| 日报完整性 | 各模块非空 | 所有模块有数据 | 缺失模块 |
| 日报连续性 | 检查日期间隔 | 每交易日有报告 | 缺失日报 |

### 7.2 质量监控表

```sql
CREATE TABLE analysis_quality_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date VARCHAR(8) NOT NULL,
    check_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- 检查结果
    metrics_valid BOOLEAN,
    attribution_valid BOOLEAN,
    report_complete BOOLEAN,
    
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

#### Task 1: 绩效指标计算

**目标**: 实现所有回测和交易绩效指标计算

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| backtest_results | Phase 06 | 回测数据存在 | 返回空报告 |
| trade_records | Phase 07 | 交易记录存在 | 返回空报告 |
| positions | Phase 07 | 持仓记录存在 | 返回空报告 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| PerformanceCalculator | 代码 | 所有指标 | `src/analysis/` |
| ReturnCalculator | 代码 | 收益率计算 | `src/analysis/` |
| DrawdownCalculator | 代码 | 回撤计算 | `src/analysis/` |
| SharpeCalculator | 代码 | 夏普比率 | `src/analysis/` |
| WinRateCalculator | 代码 | 胜率/盈亏比 | `src/analysis/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 收益率误差 | <0.01% | 手工计算对比 |
| 回撤误差 | <0.01% | 手工计算对比 |
| 夏普误差 | <0.01 | 手工计算对比 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 数据不足 | 返回空报告+警告 | 记录警告 |
| 计算错误 | 抛出异常 | 立即阻断 |

**验收检查**

- [ ] 总收益率计算正确
- [ ] 年化收益率计算正确
- [ ] 最大回撤计算正确
- [ ] 夏普比率计算正确
- [ ] 胜率/盈亏比计算正确

---

#### Task 2: 信号归因分析

**目标**: 实现 MSS/IRS/PAS 三系统绩效贡献分析

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| trade_records | Phase 07 | 交易记录 | 返回空归因 |
| integrated_recommendation | Phase 05 | 信号数据 | 返回空归因 |
| mss_panorama | Phase 02 | MSS评分 | 跳过MSS归因 |
| irs_industry_daily | Phase 03 | IRS评分 | 跳过IRS归因 |
| stock_pas_daily | Phase 04 | PAS评分 | 跳过PAS归因 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| SignalAttribution | 代码 | 归因分析 | `src/analysis/` |
| AttributionResult | 数据类 | MSS/IRS/PAS贡献 | `src/analysis/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 归因总和 | ≈1 | 统计检查 |
| 三系统分离 | MSS/IRS/PAS独立 | 单元测试 |
| 符合预期 | 贡献与信号相关 | 统计验证 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 无交易记录 | 返回空归因 | 记录信息 |
| 归因总和偏差 | 归一化 | 记录警告 |

**验收检查**

- [ ] MSS贡献计算正确
- [ ] IRS贡献计算正确
- [ ] PAS贡献计算正确
- [ ] 归因总和≈1

---

#### Task 3: 日报生成器

**目标**: 实现自动日报生成功能

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| mss_panorama | Phase 02 | 当日数据 | 空模块 |
| irs_industry_daily | Phase 03 | 当日数据 | 空模块 |
| integrated_recommendation | Phase 05 | 当日数据 | 空模块 |
| trade_records | Phase 07 | 当日数据 | 空模块 |
| positions | Phase 07 | 当日数据 | 空模块 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| DailyReportGenerator | 代码 | 日报生成 | `src/analysis/` |
| DailyReportData | 数据类 | 日报数据结构 | `src/analysis/` |
| MarketOverview | 数据类 | 市场概况 | `src/analysis/` |
| IndustryRotation | 数据类 | 行业轮动 | `src/analysis/` |
| SignalStats | 数据类 | 信号统计 | `src/analysis/` |
| PerformanceSummary | 数据类 | 绩效摘要 | `src/analysis/` |
| RecommendationSummary | 数据类 | 推荐摘要 | `src/analysis/` |
| RiskSummary | 数据类 | 风险摘要 | `src/analysis/` |
| DailyReport | 数据类 | 日报落库结构 | `src/analysis/` |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 生成成功 | 100% | 自动化测试 |
| 生成时间 | ≤30秒 | 性能测试 |
| 模块完整 | 5个模块都有数据 | 功能测试 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| 数据不足 | 生成部分报告 | 记录警告 |
| 生成失败 | 重试3次+告警 | 发送告警 |

**验收检查**

- [ ] 市场概况模块生成正确
- [ ] 行业轮动模块生成正确
- [ ] 信号统计模块生成正确
- [ ] 推荐列表模块生成正确
- [ ] 日报自动生成正常

---

#### Task 4: 落库与调度

**目标**: 实现报告持久化和定时调度

**输入依赖**

| 依赖项 | 来源 | 就绪条件 | 缺失处理 |
|--------|------|----------|----------|
| PerformanceCalculator | Task 1 | 测试通过 | 阻断 |
| SignalAttribution | Task 2 | 测试通过 | 阻断 |
| DailyReportGenerator | Task 3 | 测试通过 | 阻断 |
| DuckDB连接 | Phase 01 | 可连接 | 阻断 |

**输出交付**

| 交付物 | 类型 | 验收标准 | 存储位置 |
|--------|------|----------|----------|
| ReportRepository | 代码 | 幂等写入 | `src/analysis/` |
| AnalysisScheduler | 代码 | 定时调度 | `src/analysis/` |
| performance_metrics表 | 数据 | 绩效指标 | L4 DuckDB（按年分库） |
| daily_report表 | 数据 | 日报存储 | L4 DuckDB（按年分库） |

**成功标准**

| 标准项 | 量化指标 | 验证方法 |
|--------|----------|----------|
| 覆盖率 | ≥80% | `pytest --cov` |
| 幂等性 | 重复写入不报错 | 单元测试 |
| 定时调度 | 17:30自动触发 | 集成测试 |

**错误处理**

| 错误场景 | 处理策略 | 升级条件 |
|----------|----------|----------|
| DB写入失败 | 重试3次 | 失败后抛异常 |
| 调度失败 | 重试3次+告警 | 发送告警 |

**验收检查**

- [ ] 数据落库正确
- [ ] 幂等性验证通过
- [ ] 定时调度正确
- [ ] 测试覆盖率≥80%
- [ ] **M9里程碑完成**

### 8.2 日报生成时序

```text
17:30  所有Phase计算完成
  ↓
17:31  触发日报生成
  ↓
17:31  获取MSS市场概况
  ↓
17:31  获取IRS行业轮动数据
  ↓
17:31  统计信号分布
  ↓
17:32  计算当日绩效
  ↓
17:32  生成推荐列表
  ↓
17:32  组装日报
  ↓
17:32  保存日报
  ↓
17:33  质量检查
  ↓
17:33  日报生成完成
```

---

## 9. 验收检查清单

### 9.1 功能验收

- [ ] 总收益率计算正确（误差<0.01%）
- [ ] 年化收益率计算正确（误差<0.01%）
- [ ] 最大回撤计算正确（误差<0.01%）
- [ ] 夏普比率计算正确（误差<0.01）
- [ ] 胜率计算正确
- [ ] 盈亏比计算正确
- [ ] MSS/IRS/PAS归因正确
- [ ] 日报各模块完整
- [ ] 日报自动生成正常

### 9.2 质量验收

- [ ] 测试覆盖率 ≥ 80%
- [ ] 报告生成时间 ≤ 30秒
- [ ] 数据库写入幂等

---

## 10. 参数配置表

### 10.1 默认配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 无风险利率 | 3% | 夏普比率计算用 |
| 交易日年化 | 252 | 年化计算用 |
| 推荐列表数量 | 20 | 日报推荐列表上限 |
| Top行业数量 | 5 | 日报行业轮动上限 |

### 10.2 日报模板结构

```markdown
# EmotionQuant 日报 - {report_date}

## 1. 市场概况
- 市场温度：{temperature}（{cycle}）
- 市场趋势：{trend}
- 市场点评：{market_comment}

## 2. 行业轮动
### Top5 行业
{industry_ranking_table}

### 轮动状态
- 轮入行业：{in_rotation_count}个
- 轮出行业：{out_rotation_count}个

## 3. 信号统计
- 总股票数：{total_stocks}
- STRONG_BUY：{strong_buy_count}
- BUY：{buy_count}
- HOLD：{hold_count}
- SELL：{sell_count}
- AVOID：{avoid_count}

## 4. 绩效摘要
- 当日收益：{daily_return}%
- 累计收益：{total_return}%
- 当日交易：{today_trades}笔
- 胜率：{win_rate}%

## 5. 推荐列表
{recommendation_table}
```

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v4.0.1 | 2026-02-04 | 落库位置统一到 L4 DuckDB 按年分库 |
| v4.0.0 | 2026-02-02 | 完整重构：添加量化验收标准、I/O规范、绩效计算、日报生成 |
| v3.0.0 | 2026-01-31 | 重构版 |


