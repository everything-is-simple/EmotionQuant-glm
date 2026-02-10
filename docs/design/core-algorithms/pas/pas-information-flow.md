# PAS 信息流

**版本**: v3.1.11（重构版）
**最后更新**: 2026-02-08
**状态**: 设计完成（验收口径补齐；代码未落地）

---

## 实现状态（仓库现状）

- 当前仓库 `src/algorithms/pas/` 仅有骨架（`__init__.py`），DataRepository/PasRepository 等为规划接口。
- 本文档为信息流设计规格，具体实现以 CP-04 落地为准（兼容文件名 Phase 04）。

---

## 1. 数据流总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PAS 信息流架构图                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │   TuShare    │    │   本地缓存    │    │  IRS行业池   │                   │
│  │   API        │    │   Parquet    │    │  (超配行业)  │                   │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                   │
│         │                   │                   │                            │
│         └───────────────────┼───────────────────┘                            │
│                             │                                                │
│                             ▼                                                │
│                    ┌────────────────┐                                        │
│                    │  数据预处理层   │                                        │
│                    │ StockSnapshot  │                                        │
│                    │   Aggregator   │                                        │
│                    └────────┬───────┘                                        │
│                             │                                                │
│                             ▼                                                │
│         ┌─────────────────────────────────────────┐                          │
│         │              PAS 计算引擎                │                          │
│         │  ┌─────────────────────────────────┐    │                          │
│         │  │         因子计算层               │    │                          │
│         │  │ ┌─────────┐ ┌─────────┐ ┌─────┐│    │                          │
│         │  │ │牛股基因 │ │结构位置 │ │行为 ││    │                          │
│         │  │ │ 20%    │ │ 50%    │ │确认 ││    │                          │
│         │  │ │        │ │(无MA)  │ │30% ││    │                          │
│         │  │ └────┬───┘ └────┬───┘ └──┬──┘│    │                          │
│         │  │      └──────────┼────────┘   │    │                          │
│         │  └─────────────────┼────────────┘    │                          │
│         │                    │                  │                          │
│         │                    ▼                  │                          │
│         │           ┌────────────────┐          │                          │
│         │           │  加权求和      │          │                          │
│         │           │  机会评分      │          │                          │
│         │           └────────┬───────┘          │                          │
│         │                    │                  │                          │
│         │                    ▼                  │                          │
│         │           ┌────────────────┐          │                          │
│         │           │  等级划分      │          │                          │
│         │           │  S/A/B/C/D    │          │                          │
│         │           └────────┬───────┘          │                          │
│         │                    │                  │                          │
│         │                    ▼                  │                          │
│         │           ┌────────────────┐          │                          │
│         │           │  风险收益比    │          │                          │
│         │           │  止损止盈      │          │                          │
│         │           └────────┬───────┘          │                          │
│         └────────────────────┼──────────────────┘                          │
│                              │                                              │
│                              ▼                                              │
│                     ┌────────────────┐                                      │
│                     │  StockPasDaily │                                      │
│                     │   (N只个股)    │                                      │
│                     └────────┬───────┘                                      │
│                              │                                              │
│          ┌───────────────────┼───────────────────┐                          │
│          │                   │                   │                          │
│          ▼                   ▼                   ▼                          │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                      │
│   │   数据库     │  │   Integration│  │   GUI/API   │                      │
│   │   持久化     │  │   MSS+IRS+PAS│  │   展示层    │                      │
│   └──────────────┘  └──────────────┘  └──────────────┘                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 数据流阶段

### 2.1 Step 1：数据采集

```
输入：TuShare API + 本地缓存 + IRS超配行业
输出：候选股票池的原始行情数据

处理流程：
1. 从IRS获取超配行业列表（优先处理）
2. 获取候选股票列表（排除ST、停牌）
3. 获取个股日线数据（raw_daily）
4. 获取换手率、市值（raw_daily_basic）
5. 获取涨跌停状态（raw_limit_list）
6. 读取 PAS Z-Score baseline（mean/std）
7. 计算历史统计（近120日涨停、近60日新高等）

数据格式：
- stock_list: List[str] (候选股票代码)
- daily_data: DataFrame (个股日线)
- limit_data: DataFrame (涨跌停明细)
- history_stats: Dict (历史统计)
```

### 2.2 Step 2：个股快照聚合

```
输入：原始行情数据 + 历史统计
输出：List[PasStockSnapshot]

处理流程（对每只股票）：
1. 聚合基础行情（OHLCV、涨跌幅）
2. 计算牛股基因数据：
   - 近120日涨停次数
   - 近60日新高次数
   - 历史最大涨幅
3. 计算结构位置数据（铁律合规）：
   - 60日高低点
   - 20日方向/止损窗口（high_20d_prev, low_20d_prev, low_20d）
   - 价格位置（0-1）
   - 连续上涨/下跌天数
4. 计算行为确认数据：
   - 量比（当日/20日均量）
   - 涨跌停状态

依赖组件：StockSnapshotAggregator
```

### 2.3 Step 3：因子计算

```
输入：PasStockSnapshot
输出：3个因子得分

处理流程：
1. 牛股基因因子（20%）
   limit_up_120d_ratio = limit_up_count_120d / 120
   new_high_60d_ratio = new_high_count_60d / 60
   max_pct_chg_history_ratio = max_pct_chg_history / 100  # 15 表示 15%
   bull_gene_raw = 0.4×limit_up_120d_ratio + 0.3×new_high_60d_ratio + 0.3×max_pct_chg_history_ratio
   bull_gene = normalize_zscore(bull_gene_raw)

2. 结构位置因子（50%）【铁律合规】
   price_position = (close - low_60d) / max(high_60d - low_60d, ε)
   trend_continuity_ratio = consecutive_up_days / trend_window
   breakout_strength = (close - high_60d_prev) / max(high_60d_prev, ε)
   structure_raw = 0.4×price_position + 0.3×trend_continuity_ratio + 0.3×breakout_strength
   structure = normalize_zscore(structure_raw)

3. 行为确认因子（30%）
   volume_ratio = vol / max(volume_avg_20d, ε)
   limit_up_flag = is_limit_up ? 1.0 : (is_touched_limit_up ? 0.7 : 0.0)
   volume_ratio_norm = clip(volume_ratio / 3.0, 0, 1)
   pct_chg_norm = clip((pct_chg + 20) / 40, 0, 1)
   behavior_raw = 0.4×volume_ratio_norm + 0.3×pct_chg_norm + 0.3×limit_up_flag
   behavior = normalize_zscore(behavior_raw)

依赖组件：PasFactorCalculator
```

### 2.4 Step 4：综合评分与分级

```
输入：3个因子得分
输出：机会评分 + 机会等级

公式：
opportunity_score = bull_gene × 0.20
                  + structure × 0.50
                  + behavior × 0.30

等级划分：
- S: score ≥ 85
- A: 70 ≤ score < 85
- B: 55 ≤ score < 70
- C: 40 ≤ score < 55
- D: score < 40

方向判断：
- bullish: close > high_20d_prev 且 consecutive_up_days ≥ 3
- bearish: close < low_20d_prev 且 consecutive_down_days ≥ 3
- neutral: 其他

依赖组件：PasAggregator, PasGrader
```

### 2.5 Step 5：风险收益比计算

```
输入：机会评分 + 价格数据
输出：止损止盈 + risk_reward_ratio

公式：
entry = close
stop_loss_pct = 0.08
stop = min(low_20d, close × (1 - stop_loss_pct))
target_ref = max(high_20d_prev, high_60d_prev)
risk = max(entry - stop, ε)
breakout_floor = entry + risk
if close > target_ref:
    target = max(target_ref, breakout_floor, entry × (1 + stop_loss_pct))
else:
    target = max(target_ref, entry × 1.03)
reward = max(target - entry, 0)
risk_reward_ratio = reward / risk

过滤规则（可选）：
- risk_reward_ratio < 1 的机会可降级为 D 级（由策略层决定）

依赖组件：PasRiskCalculator
```

### 2.6 Step 6：输出与持久化

```
输入：完整计算结果
输出：StockPasDaily + 数据库记录

处理流程：
1. 组装 StockPasDaily 对象
2. 批量写入 stock_pas_daily 表
3. 写入 pas_factor_intermediate 表
4. 记录等级变化到 pas_opportunity_log
5. 返回 API 响应（按评分排序）

依赖组件：PasRepository
```

---

## 3. 组件依赖关系

```
┌─────────────────────────────────────────────────────────────────┐
│                       组件依赖图                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PasController (API层)                                           │
│       │                                                          │
│       ▼                                                          │
│  PasService (服务层)                                              │
│       │                                                          │
│       ├───────────────────┬───────────────────┐                  │
│       ▼                   ▼                   ▼                  │
│  PasEngine           PasRepository       PasGrader               │
│  (计算引擎)          (数据仓库)         (分级器)                  │
│       │                   │                   │                  │
│       │                   ▼                   │                  │
│       │              Database                 │                  │
│       │                                       │                  │
│       ├───────────────────────────────────────┤                  │
│       ▼                                       ▼                  │
│  PasFactorCalculator                   StockSnapshotAggregator   │
│  (因子计算器)                          (个股快照聚合器)           │
│       │                                       │                  │
│       ├───────────────────┐                   │                  │
│       ▼                   ▼                   ▼                  │
│  PasNormalizer       PasRiskCalculator   DataRepository         │
│  (归一化器)          (风险计算器)        (数据仓库)              │
│                                               │                  │
│                                               ▼                  │
│                                          TuShareClient           │
│                                          (API客户端)             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. 数据流转示例

### 4.1 单日计算流程

```
Timeline: T=15:30 (收盘后)

T+0min:  调度器触发 PasService.calculate("20260131")
T+0.2min: IrsService.get_overweight_industries() -> 超配行业列表
T+0.5min: DataRepository.get_stock_list() -> 候选股票（~5000只）
T+2.0min: DataRepository.get_daily_data() -> 个股日线
T+3.0min: StockSnapshotAggregator.aggregate() -> List[PasStockSnapshot]
T+5.0min: PasEngine.calculate(snapshots)
         ├─ 计算牛股基因因子
         ├─ 计算结构位置因子（无MA）
         └─ 计算行为确认因子
T+8.0min: PasGrader.grade() -> S/A/B/C/D 分级
T+8.5min: PasRiskCalculator.calculate_risk_reward_ratio() -> 风险收益比
T+9.0min: PasRepository.save_batch() -> 持久化
T+10.0min: 返回结果（S级15只，A级120只）
```

### 4.2 数据流转格式

```
Step 1 -> Step 2:
  raw_daily DataFrame (5000 stocks × 120 days)
  raw_limit_list DataFrame

Step 2 -> Step 3:
  List[PasStockSnapshot] (5000个)
      stock_code: "000001"
      stock_name: "平安银行"
      close: 12.50
      limit_up_count_120d: 3
      high_60d: 13.00
      low_60d: 10.50
      high_20d_prev: 12.80
      low_20d_prev: 11.90
      low_20d: 11.80
      consecutive_up_days: 5
      ...

Step 3 -> Step 4:
  Dict[stock_code, Dict[factor_name, float]]
      {
        "000001": {
          "bull_gene": 75.2,
          "structure": 92.1,
          "behavior": 85.3
        },
        ...
      }

Step 4 -> Step 5:
  Dict[stock_code, Tuple[score, grade]]
      {
        "000001": (88.5, "S"),
        "600000": (72.3, "A"),
        ...
      }

Step 5 -> Step 6:
  List[StockPasDaily] (5000个)
```

---

## 5. 与其他模块交互

### 5.1 与 MSS 模块

```
MSS -> Integration（非 PAS 直接输入）:
  - MssPanorama.temperature (市场温度)

用途：
- Integration 在协同约束中根据 temperature 调整仓位与风险暴露
- PAS 算法本身不直接消费 MSS 字段做评分/分级
```

### 5.2 与 IRS 模块

```
IRS -> PAS:
  - 超配行业列表（前3名）
  - 行业龙头因子得分

用途：
- PAS 优先计算超配行业内个股
- 超配行业 + S级机会 = 最优组合
```

### 5.3 与 Integration 模块

```
PAS -> Integration:
  - List[StockPasDaily] (S/A/B/C/D全量)
  - 行业内机会分布统计

Integration 汇总 MSS + IRS + PAS，生成三三制集成信号：
- 市场允许（MSS温度适中）
- 行业优选（IRS超配）
- 个股评分（PAS S/A/B/C/D）
```

---

## 6. 铁律合规检查点

### 6.1 单指标不得独立决策合规

| 检查点 | 合规状态 | 说明 |
|--------|----------|------|
| 单指标不独立触发交易 | ✅ | 至少与情绪/结构/行为因子联合 |
| MA/EMA/SMA 不作独立信号 | ✅ | 如使用仅作辅助特征 |
| MACD/RSI/KDJ 不作独立信号 | ✅ | 如使用仅作对照或特征 |

### 6.2 数据来源合规

| 因子 | 数据来源 | 合规状态 |
|------|----------|----------|
| 牛股基因 | raw_daily + raw_limit_list | ✅ 基础行情 |
| 结构位置 | raw_daily (OHLC) | ✅ 基础行情 |
| 行为确认 | raw_daily + raw_limit_list | ✅ 基础行情 |

---

## 7. 异常处理

### 7.1 数据异常

| 异常情况 | 检测方式 | 处理策略 |
|----------|----------|----------|
| 个股停牌 | vol = 0 | 跳过计算 |
| 数据缺失 | close is None | 使用前一日数据 |
| 涨跌停数据缺失 | raw_limit_list 为空 | 基于 pct_chg 推断 |

### 7.2 计算异常

| 异常情况 | 检测方式 | 处理策略 |
|----------|----------|----------|
| 除零错误 | high_60d = low_60d | 返回中性值 0.5 |
| 历史数据不足 | history < 60d | 跳过牛股基因因子 |
| 评分超界 | score > 100 | 裁剪到边界值 |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.1.11 | 2026-02-08 | 修复 R18：§5.3 PAS→Integration 传递范围改为 `S/A/B/C/D全量`，与 Integration 读取口径一致 |
| v3.1.10 | 2026-02-08 | 修复 R14：§5.1 明确 MSS 温度调整职责位于 Integration（非 PAS 直接输入） |
| v3.1.9 | 2026-02-08 | 修复 R13：Step 3 锁定牛股基因窗口口径（120/60）；方向判断显式引用 `consecutive_down_days`；Step 5 增加突破场景目标价下限（RR≥1） |
| v3.1.8 | 2026-02-08 | 修复 R10：Step 3 `pct_chg_norm` 映射扩展为 ±20%，与创业板/科创板涨跌幅区间更匹配 |
| v3.1.7 | 2026-02-07 | 修复 R8 P1：与算法文档统一冷/热市场行为为“下调”而非“暂停” |
| v3.1.6 | 2026-02-07 | 修复 R8 P0：Step 5 风险收益比改为阻力位目标价口径，移除恒等式 `RR=2` |
| v3.1.5 | 2026-02-07 | 修复 R5：Step 1 补充 PAS baseline 读取；Step 3 行为因子加入量纲映射后再组合 |
| v3.1.4 | 2026-02-07 | 修复 P1：Step 3 补充 max_pct_chg_history 百分数→ratio 转换，消除 bull_gene 子因子量纲歧义 |
| v3.1.3 | 2026-02-07 | 修复 P0：Step 2 补充 20 日方向/止损窗口字段，示例快照与算法输入口径对齐 |
| v3.1.2 | 2026-02-06 | Step 1 输入源命名统一为 Data Layer raw_* 表口径 |
| v3.1.1 | 2026-02-05 | 字段命名与路线图对齐（limit_up_count_120d 等） |
| v3.1.0 | 2026-02-04 | 同步 PAS v3.1.0：ratio→zscore 口径对齐，示例与因子定义一致 |
| v3.0.0 | 2026-01-31 | 重构版：统一信息流架构、明确阶段划分、补充组件依赖 |

---

**关联文档**：
- 算法设计：[pas-algorithm.md](./pas-algorithm.md)
- 数据模型：[pas-data-models.md](./pas-data-models.md)
- API接口：[pas-api.md](./pas-api.md)

