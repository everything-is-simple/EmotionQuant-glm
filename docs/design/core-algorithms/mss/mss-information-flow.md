# MSS 信息流

**版本**: v3.1.6（重构版）
**最后更新**: 2026-02-08
**状态**: 设计完成（验收口径补齐；代码未落地）

---

## 实现状态（仓库现状）

- 当前仓库 `src/algorithms/mss/` 仅有骨架（`__init__.py`），DataRepository/MssRepository 等为规划接口。
- 本文档为信息流设计规格，具体实现以 CP-02 落地为准（兼容文件名 Phase 02）。

---

## 1. 数据流总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MSS 信息流架构图                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │   TuShare    │    │   本地缓存    │    │   交易日历    │                   │
│  │   API        │    │   Parquet    │    │   DuckDB     │                   │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                   │
│         │                   │                   │                            │
│         └───────────────────┼───────────────────┘                            │
│                             │                                                │
│                             ▼                                                │
│                    ┌────────────────┐                                        │
│                    │  数据预处理层   │                                        │
│                    │ MarketSnapshot │                                        │
│                    │   Aggregator   │                                        │
│                    └────────┬───────┘                                        │
│                             │                                                │
│                             ▼                                                │
│         ┌─────────────────────────────────────────┐                          │
│         │              MSS 计算引擎                │                          │
│         │  ┌─────────────────────────────────┐    │                          │
│         │  │         因子计算层               │    │                          │
│         │  │ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐│    │          │
│         │  │ │大盘 │ │赚钱 │ │亏钱 │ │连续 │ │极端 │ │波动 ││    │          │
│         │  │ │系数 │ │效应 │ │效应 │ │因子 │ │因子 │ │因子 ││    │          │
│         │  │ └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘│    │          │
│         │  │    │       │       │       │       │       │   │    │          │
│         │  │    └───────┴───────┴───────┴───────┴───────┘   │    │          │
│         │  │              │                 │    │                          │
│         │  │              ▼                 │    │                          │
│         │  │      ┌──────────────┐          │    │                          │
│         │  │      │  归一化层     │          │    │                          │
│         │  │      │  Z-Score     │          │    │                          │
│         │  │      └──────┬───────┘          │    │                          │
│         │  │             │                  │    │                          │
│         │  │             ▼                  │    │                          │
│         │  │      ┌──────────────┐          │    │                          │
│         │  │      │  加权求和     │          │    │                          │
│         │  │      │  温度计算     │          │    │                          │
│         │  │      └──────┬───────┘          │    │                          │
│         │  └─────────────┼──────────────────┘    │                          │
│         │                │                       │                          │
│         │                ▼                       │                          │
│         │  ┌─────────────────────────────────┐   │                          │
│         │  │        辅助分析层               │   │                          │
│         │  │ ┌─────────┐  ┌─────────┐       │   │                          │
│         │  │ │周期识别 │  │趋势判断 │       │   │                          │
│         │  │ └────┬────┘  └────┬────┘       │   │                          │
│         │  │      └───────┬────┘            │   │                          │
│         │  └──────────────┼─────────────────┘   │                          │
│         └─────────────────┼─────────────────────┘                          │
│                           │                                                │
│                           ▼                                                │
│                  ┌────────────────┐                                        │
│                  │  MssPanorama   │                                        │
│                  │    输出结果     │                                        │
│                  └────────┬───────┘                                        │
│                           │                                                │
│         ┌─────────────────┼─────────────────┐                              │
│         │                 │                 │                              │
│         ▼                 ▼                 ▼                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                        │
│  │   数据库     │ │   集成层     │ │   GUI/API   │                        │
│  │   持久化     │ │   IRS/PAS   │ │   展示层    │                        │
│  └──────────────┘ └──────────────┘ └──────────────┘                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 数据流阶段

### 2.1 Step 1：数据采集

```
输入：TuShare API + 本地缓存
输出：原始行情数据

处理流程：
1. 检查交易日历，确认是交易日
2. 优先从本地缓存读取（Parquet文件）
3. 缓存未命中则调用TuShare API
4. 数据校验：字段完整性、数值范围
5. 缓存数据供后续使用

数据格式：
- raw_daily: 全市场日线行情 DataFrame
- raw_limit_list: 涨跌停明细 DataFrame
- raw_trade_cal: 交易日历 DataFrame
```

### 2.2 Step 2：数据聚合

```
输入：原始行情数据
输出：MssMarketSnapshot（市场日快照）

处理流程：
1. 计算涨跌家数：rise_count, fall_count, flat_count
2. 统计涨跌停：limit_up_count, limit_down_count, touched_limit_up
3. 统计新高新低：new_100d_high_count, new_100d_low_count
4. 统计大涨大跌：strong_up_count, strong_down_count
5. 计算连续性：continuous_limit_up_2d, continuous_limit_up_3d_plus, continuous_new_high_2d_plus
6. 统计极端行为：high_open_low_close_count, low_open_high_close_count
7. 计算波动率：pct_chg_std, amount_volatility

依赖组件：MarketSnapshotAggregator
```

### 2.3 Step 3：因子计算

```
输入：MssMarketSnapshot
输出：6个因子原始值（ratio/continuous）

处理流程（与 mss-algorithm.md §3 验收口径一致）：
1. market_coefficient_raw = rise_count / total_stocks
2. profit_effect_raw = 0.4×(limit_up_count/total) + 0.3×(new_100d_high_count/total) + 0.3×(strong_up_count/total)
3. loss_effect_raw = 0.3×broken_rate + 0.2×(limit_down_count/total) + 0.3×(strong_down_count/total) + 0.2×(new_100d_low_count/total)
   - broken_rate = (touched_limit_up - limit_up_count) / max(touched_limit_up, 1)
4. continuity_factor_raw = 0.5×((continuous_limit_up_2d + 2×continuous_limit_up_3d_plus)/max(limit_up_count,1))
                        + 0.5×(continuous_new_high_2d_plus/max(new_100d_high_count,1))
5. extreme_factor_raw = (high_open_low_close_count/total) + (low_open_high_close_count/total)
6. volatility_factor_raw = 0.5×pct_chg_std + 0.5×amount_volatility

依赖组件：MssFactorCalculator
```

### 2.4 Step 4：归一化

```
输入：6个因子原始值
输出：6个因子标准化得分（0-100）

处理流程：
1. 读取历史因子值（基于2015-2025历史样本）
2. 计算 Z-Score: z = (x - mean) / std
3. 映射到 0-100 分数: score = (z + 3) / 6 × 100  【与 mss-algorithm.md 统一】
4. 边界裁剪: score = clip(score, 0, 100)

依赖组件：MssNormalizer
```

### 2.5 Step 5：加权求和

```
输入：6个因子标准化得分
输出：市场温度（0-100）

公式（与 mss-algorithm.md 统一）：
# 基础温度（85%权重）
base_temperature = market_coefficient × 0.2 
                 + profit_effect × 0.4 
                 + (100 - loss_effect) × 0.4

# 完整温度（含增强因子15%）
temperature = base_temperature × 0.85 
            + continuity_factor × 0.05 
            + extreme_factor × 0.05 
            + volatility_factor × 0.05

依赖组件：MssAggregator
```

### 2.6 Step 6：辅助分析

```
输入：当前温度 + 历史温度序列
输出：周期、趋势、中性度

处理流程：
1. 周期识别
   - 使用 temperature + trend 按优先级匹配（见 mss-algorithm.md）
   - 若 trend 不可判定，默认 sideways

2. 趋势判断（需至少3日历史）
   - 读取最近3日温度
   - 严格递增（T-2 < T-1 < T）→ up
   - 严格递减（T-2 > T-1 > T）→ down
   - 其他 → sideways

3. 中性度计算
   - neutrality = 1 - |temperature - 50| / 50
   - 说明：越接近1越中性，越接近0信号越极端

依赖组件：MssCycleDetector, MssTrendAnalyzer
```

### 2.7 Step 7：输出与持久化

```
输入：完整计算结果
输出：MssPanorama + 数据库记录

处理流程：
1. 组装 MssPanorama 对象
2. 写入 mss_panorama 表
3. 写入 mss_factor_intermediate 表（因子中间结果）
4. 检查预警条件，必要时写入 mss_alert_log
5. 返回 API 响应

依赖组件：MssRepository, MssAlertService
```

---

## 3. 组件依赖关系

```
┌─────────────────────────────────────────────────────────────────┐
│                       组件依赖图                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  MssController (API层)                                           │
│       │                                                          │
│       ▼                                                          │
│  MssService (服务层)                                              │
│       │                                                          │
│       ├───────────────────┬───────────────────┐                  │
│       ▼                   ▼                   ▼                  │
│  MssEngine           MssRepository      MssAlertService          │
│  (计算引擎)          (数据仓库)         (预警服务)                 │
│       │                   │                   │                  │
│       │                   ▼                   ▼                  │
│       │              Database           AlertQueue               │
│       │                                                          │
│       ├───────────────────────────────────────┐                  │
│       ▼                                       ▼                  │
│  MssFactorCalculator                   MarketSnapshotAggregator  │
│  (因子计算器)                          (市场快照聚合器)            │
│       │                                       │                  │
│       ├───────────────────┐                   │                  │
│       ▼                   ▼                   ▼                  │
│  MssNormalizer       MssCycleDetector    DataRepository         │
│  (归一化器)          (周期检测器)        (数据仓库)              │
│                           │                   │                  │
│                           ▼                   ▼                  │
│                      MssTrendAnalyzer    TuShareClient           │
│                      (趋势分析器)        (API客户端)             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. 数据流转示例

### 4.1 单日计算流程

```
Timeline: T=15:30 (收盘后)

T+0min:  调度器触发 MssService.calculate("20260131")
T+0.1min: DataRepository.get_daily_data() -> 从缓存/API获取数据
T+0.3min: MarketSnapshotAggregator.aggregate() -> MssMarketSnapshot
T+0.5min: MssEngine.calculate(snapshot)
         ├─ MssFactorCalculator.calc_market_coefficient()
         ├─ MssFactorCalculator.calc_profit_effect()
         ├─ MssFactorCalculator.calc_loss_effect()
         ├─ MssFactorCalculator.calc_continuity_factor()
         ├─ MssFactorCalculator.calc_extreme_factor()
         └─ MssFactorCalculator.calc_volatility_factor()
T+0.8min: MssNormalizer.normalize(factors) -> [0-100] scores
T+0.9min: MssAggregator.weighted_sum(scores) -> temperature
T+1.0min: MssCycleDetector.detect(history) -> cycle
T+1.1min: MssTrendAnalyzer.analyze(history) -> trend
T+1.2min: MssRepository.save(panorama) -> 持久化
T+1.3min: MssAlertService.check_and_alert() -> 检查预警
T+1.5min: 返回 MssPanorama
```

### 4.2 数据流转格式

```
Step 1 -> Step 2:
  raw_daily DataFrame (5000+ rows)
      trade_date | ts_code | open | high | low | close | pct_chg | vol | amount
  
Step 2 -> Step 3:
  MssMarketSnapshot (单条记录)
      trade_date: "20260131"
      total_stocks: 5123
      rise_count: 3456
      fall_count: 1234
      ...

Step 3 -> Step 4:
  dict (6个因子原始值)
      {
        "market_coefficient_raw": 0.675,
        "profit_effect_raw": 0.156,
        "loss_effect_raw": 0.089,
        "continuity_factor_raw": 0.234,
        "extreme_factor_raw": 0.045,
        "volatility_factor_raw": 1.25
      }

Step 4 -> Step 5:
  dict (6个因子标准化得分)
      {
        "market_coefficient": 72.5,
        "profit_effect": 68.2,
        "loss_effect": 45.8,
        "continuity_factor": 70.1,
        "extreme_factor": 55.0,
        "volatility_factor": 60.3
      }

Step 5 -> Step 6:
  float (市场温度)
      temperature: 63.21

Step 6 -> Step 7:
  MssPanorama (完整结果)
      trade_date: "20260131"
      temperature: 63.21
      cycle: "divergence"
      trend: "up"
      ...
```

---

## 5. 与其他模块交互

### 5.1 与 IRS 模块

```
MSS -> Integration（非 IRS 直接输入）:
  - MssPanorama.temperature (当前市场温度)
  - MssPanorama.cycle (当前情绪周期)
  - MssPanorama.trend (当前趋势方向)

用途：Integration 在协同约束层使用 MSS 结果调节综合信号与仓位；
IRS 算法本身不直接消费 MSS 字段做因子计算
```

### 5.2 与 PAS 模块

```
MSS -> Integration（非 PAS 直接输入）:
  - MssPanorama.temperature (市场温度)
  - MssPanorama.trend (市场趋势)
  - MssPanorama.cycle (情绪周期)

用途：Integration 在协同约束层使用 MSS 结果调节综合信号与仓位；
PAS 算法本身不直接消费 MSS 字段做评分/分级
```

### 5.3 与 Integration 模块

```
MSS -> Integration:
  - MssPanorama (完整结果)

Integration 汇总 MSS + IRS + PAS，生成三三制集成信号
```

---

## 6. 异常处理

### 6.1 数据异常

| 异常情况 | 检测方式 | 处理策略 |
|----------|----------|----------|
| 数据缺失 | total_stocks < 1000 | 使用前一日数据 |
| 涨跌停异常 | limit_up > 500 | 人工确认后计算 |
| API超时 | TuShare 返回超时 | 重试3次，使用缓存 |

### 6.2 计算异常

| 异常情况 | 检测方式 | 处理策略 |
|----------|----------|----------|
| 除零错误 | 分母为0 | 返回默认值 |
| 超出范围 | temperature > 100 | 裁剪到边界值 |
| 历史不足 | 历史数据<3日 | trend=sideways，周期按温度+trend判定 |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.1.6 | 2026-02-08 | 修复 R19：§5.1/§5.2 跨模块交互改为 `MSS -> Integration（非 IRS/PAS 直接输入）`，与 IRS/PAS info-flow 对齐 |
| v3.1.5 | 2026-02-08 | 修复 R17：§4.2 示例中 `temperature=63.21 + trend=up` 的周期改为 `divergence`（与周期判定伪代码一致） |
| v3.1.4 | 2026-02-08 | 修复 R13：趋势判定语义显式为严格递增/递减，相等归入 sideways |
| v3.1.3 | 2026-02-07 | 修复 R7：架构图“因子计算层”补齐极端因子/波动因子，图文口径统一为 6 因子 |
| v3.1.2 | 2026-02-06 | Step 1 输入源命名统一为 Data Layer raw_* 表口径 |
| v3.1.1 | 2026-02-05 | 周期识别口径与算法文档对齐（去除5日历史要求） |
| v3.1.0 | 2026-02-04 | 同步 MSS v3.1.0：补齐 Step2/3 字段与口径（ratio 化 + broken_rate 等），示例温度与公式对齐 |
| v3.0.0 | 2026-01-31 | 重构版：统一信息流架构、明确阶段划分、补充组件依赖 |

---

**关联文档**：
- 算法设计：[mss-algorithm.md](./mss-algorithm.md)
- 数据模型：[mss-data-models.md](./mss-data-models.md)
- API接口：[mss-api.md](./mss-api.md)

