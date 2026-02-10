# IRS 信息流

**版本**: v3.2.7（重构版）
**最后更新**: 2026-02-08
**状态**: 设计完成（验收口径补齐；代码未落地）

---

## 实现状态（仓库现状）

- 当前仓库 `src/algorithms/irs/` 仅有骨架（`__init__.py`），DataRepository/IrsRepository 等为规划接口。
- 本文档为信息流设计规格，具体实现以 CP-03 落地为准（兼容文件名 Phase 03）。

---

## 1. 数据流总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           IRS 信息流架构图                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │   TuShare    │    │   本地缓存    │    │   行业分类    │                   │
│  │   API        │    │   Parquet    │    │   DuckDB     │                   │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                   │
│         │                   │                   │                            │
│         └───────────────────┼───────────────────┘                            │
│                             │                                                │
│                             ▼                                                │
│                    ┌────────────────┐                                        │
│                    │  数据预处理层   │                                        │
│                    │ IndustrySnapshot│                                        │
│                    │   Aggregator   │                                        │
│                    └────────┬───────┘                                        │
│                             │                                                │
│                             ▼                                                │
│         ┌─────────────────────────────────────────┐                          │
│         │              IRS 计算引擎                │                          │
│         │  ┌─────────────────────────────────┐    │                          │
│         │  │       基础因子计算层             │    │                          │
│         │  │ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐│    │                          │
│         │  │ │相对 │ │连续 │ │资金 │ │估值 ││    │                          │
│         │  │ │强度 │ │因子 │ │流向 │ │因子 ││    │                          │
│         │  │ └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘│    │                          │
│         │  └────┼───────┼───────┼───────┼───┘    │                          │
│         │       │       │       │       │        │                          │
│         │  ┌────┼───────┼───────┼───────┼───┐    │                          │
│         │  │    └───────┴───────┴───────┘   │    │                          │
│         │  │       增强因子计算层             │    │                          │
│         │  │    ┌──────────┐ ┌──────────┐   │    │                          │
│         │  │    │  龙头    │ │ 行业基因 │   │    │                          │
│         │  │    │  因子    │ │   库     │   │    │                          │
│         │  │    └────┬─────┘ └────┬─────┘   │    │                          │
│         │  │         └──────┬─────┘         │    │                          │
│         │  └────────────────┼───────────────┘    │                          │
│         │                   ▼                    │                          │
│         │          ┌────────────────┐            │                          │
│         │          │  加权求和      │            │                          │
│         │          │  行业评分      │            │                          │
│         │          └────────┬───────┘            │                          │
│         │                   │                    │                          │
│         │                   ▼                    │                          │
│         │          ┌────────────────┐            │                          │
│         │          │  排名与轮动    │            │                          │
│         │          │  状态识别      │            │                          │
│         │          └────────┬───────┘            │                          │
│         └───────────────────┼────────────────────┘                          │
│                             │                                                │
│                             ▼                                                │
│                    ┌────────────────┐                                        │
│                    │ IrsIndustryDaily│                                        │
│                    │   (31个行业)    │                                        │
│                    └────────┬───────┘                                        │
│                             │                                                │
│         ┌───────────────────┼───────────────────┐                            │
│         │                   │                   │                            │
│         ▼                   ▼                   ▼                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                        │
│  │   数据库     │  │   Integration│  │   GUI/API   │                        │
│  │   持久化     │  │   MSS+IRS+PAS│  │   展示层    │                        │
│  └──────────────┘  └──────────────┘  └──────────────┘                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 数据流阶段

### 2.1 Step 1：数据采集

```
输入：TuShare API + 本地缓存
输出：原始行情数据（按行业分组）

处理流程：
1. 获取申万一级行业分类（raw_index_classify）
2. 获取各行业成分股列表（raw_index_member）
3. 获取成分股日线数据（raw_daily + raw_daily_basic）
4. 获取涨跌停数据（raw_limit_list）
5. 获取基准指数数据（raw_index_daily）
6. 读取 IRS Z-Score baseline（mean/std）

数据格式：
- industry_stocks: Dict[industry_code, List[stock_code]]
- daily_data: DataFrame (全市场日线)
- limit_data: DataFrame (涨跌停明细)
- benchmark_data: DataFrame (基准指数)
```

### 2.2 Step 2：行业聚合

```
输入：原始行情数据
输出：31个 IrsIndustrySnapshot

处理流程（对每个行业）：
1. 筛选行业成分股（得到 stock_count）
2. 计算行业涨跌幅（成分股加权平均）
3. 统计涨跌家数、涨跌停家数
4. 统计新高/新低家数（new_100d_high_count / new_100d_low_count）
5. 计算行业成交额、换手率
6. 计算行业估值（PE/PB 中位数）
7. 识别龙头股（成交额 Top5）
8. 统计龙头股涨跌幅、涨停数量

依赖组件：IndustrySnapshotAggregator
```

### 2.3 Step 3：基础因子计算

```
输入：IrsIndustrySnapshot + 历史数据
输出：4个基础因子得分

处理流程：
1. 相对强度 = industry_pct_chg - benchmark_pct_chg
   → normalize_zscore → relative_strength_score

2. 连续性因子 = 0.6×Σ(net_breadth,5d) + 0.4×Σ(net_new_high,5d)
   → normalize_zscore → continuity_score

3. 资金流向 = Σ(amount_delta, 10d)
   → normalize_zscore → capital_flow_score

4. 估值因子：valuation_raw = -pe_ttm（PE 越低越优）
   → normalize_zscore(valuation_raw, 3y) → valuation_score

注：
- 若任一因子缺 baseline mean/std，则该因子得分回退为 50（中性）

依赖组件：IrsFactorCalculator
```

### 2.4 Step 4：增强因子计算

```
输入：IrsIndustrySnapshot + 历史数据
输出：2个增强因子得分

处理流程：
1. 龙头因子
   leader_avg_pct = Mean(top5_pct_chg)
   leader_limit_ratio = top5_limit_up / 5
   leader_score = 0.6 × normalize(leader_avg_pct) + 0.4 × scale(leader_limit_ratio)

2. 行业基因库
   gene_score = 0.6 × time_decay(history_limit_up)
              + 0.4 × time_decay(history_new_high)

依赖组件：IrsFactorCalculator
```

### 2.5 Step 5：加权求和

```
输入：6个因子得分
输出：行业综合评分（0-100）

公式：
industry_score = 0.25 × relative_strength
               + 0.20 × continuity_factor
               + 0.20 × capital_flow
               + 0.15 × valuation
               + 0.12 × leader_score
               + 0.08 × gene_score

依赖组件：IrsAggregator
```

### 2.6 Step 6：排名与轮动识别

```
输入：31个行业评分 + 历史评分
输出：排名、轮动状态、配置建议

处理流程：
1. 按 industry_score 降序排名
2. 根据排名映射配置建议
   - 前3名 → 超配
   - 4-10名 → 标配
   - 11-26名 → 减配
   - 后5名（27-31）→ 回避
3. 检测轮动状态（需至少3日历史）
   - industry_score 连续3日上升 → IN
   - industry_score 连续3日下降 → OUT
   - 其他 → HOLD
4. 识别轮动详情（强势领涨/轮动加速/趋势反转...）

依赖组件：IrsRanker, IrsRotationDetector
```

### 2.7 Step 7：输出与持久化

```
输入：31个 IrsIndustryDaily
输出：数据库记录 + API响应

处理流程：
1. 批量写入 irs_industry_daily 表
2. 写入 irs_factor_intermediate 表
3. 生成配置调整日志（若有变动）
4. 返回 API 响应

依赖组件：IrsRepository
```

---

## 3. 组件依赖关系

```
┌─────────────────────────────────────────────────────────────────┐
│                       组件依赖图                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  IrsController (API层)                                           │
│       │                                                          │
│       ▼                                                          │
│  IrsService (服务层)                                              │
│       │                                                          │
│       ├───────────────────┬───────────────────┐                  │
│       ▼                   ▼                   ▼                  │
│  IrsEngine           IrsRepository       IrsRanker               │
│  (计算引擎)          (数据仓库)         (排名器)                  │
│       │                   │                   │                  │
│       │                   ▼                   │                  │
│       │              Database                 │                  │
│       │                                       │                  │
│       ├───────────────────────────────────────┤                  │
│       ▼                                       ▼                  │
│  IrsFactorCalculator                   IndustrySnapshotAggregator│
│  (因子计算器)                          (行业快照聚合器)           │
│       │                                       │                  │
│       ├───────────────────┐                   │                  │
│       ▼                   ▼                   ▼                  │
│  IrsNormalizer       IrsRotationDetector DataRepository         │
│  (归一化器)          (轮动检测器)        (数据仓库)              │
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

T+0min:  调度器触发 IrsService.calculate("20260131")
T+0.1min: IndustryClassifier.get_sw_industries() -> 31个行业
T+0.5min: DataRepository.get_industry_stocks() -> 行业成分股
T+1.0min: DataRepository.get_daily_data() -> 全市场日线
T+1.5min: IndustrySnapshotAggregator.aggregate() -> 31个 IrsIndustrySnapshot
T+2.0min: IrsEngine.calculate(snapshots)
         ├─ 计算31个行业的6个因子
         ├─ 归一化因子得分
         └─ 加权求和
T+3.0min: IrsRanker.rank() -> 排名
T+3.2min: IrsRotationDetector.detect() -> 轮动状态
T+3.5min: IrsRepository.save_batch() -> 持久化
T+4.0min: 返回结果
```

### 4.2 数据流转格式

```
Step 1 -> Step 2:
  raw_daily DataFrame (5000+ rows per industry)
  raw_limit_list DataFrame
  benchmark DataFrame

Step 2 -> Step 3:
  List[IrsIndustrySnapshot] (31个)
      industry_code: "801750"
      industry_name: "计算机"
      industry_pct_chg: 2.15
      top5_codes: ["000001", "000002", ...]
      ...

Step 3-4 -> Step 5:
  Dict[industry_code, Dict[factor_name, float]]
      {
        "801750": {
          "relative_strength": 82.3,
          "continuity_factor": 76.8,
          "capital_flow": 80.5,
          "valuation": 65.2,
          "leader_score": 85.0,
          "gene_score": 70.5
        },
        ...
      }

Step 5 -> Step 6:
  Dict[industry_code, float]
      {
        "801750": 78.5,
        "801080": 75.2,
        ...
      }

Step 6 -> Step 7:
  List[IrsIndustryDaily] (31个)
```

---

## 5. 与其他模块交互

### 5.1 与 MSS 模块

```
MSS -> Integration（非 IRS 直接输入）:
  - MssPanorama.temperature (当前市场温度)
  - MssPanorama.cycle (当前情绪周期)

用途：
- Integration 在协同约束中根据 temperature 调整仓位与风险暴露
- IRS 算法本身不直接消费 MSS 字段做因子计算
```

### 5.2 与 PAS 模块

```
IRS -> PAS:
  - 超配行业列表（前3名）
  - 行业权重建议

用途：
- PAS 在超配行业内进行个股精选
- PAS 评分 ≥ 85（S级）的个股优先从超配行业选择
```

### 5.3 与 Integration 模块

```
IRS -> Integration:
  - List[IrsIndustryDaily] (31个行业完整结果)

Integration 汇总 MSS + IRS + PAS，生成三三制集成信号：
- 市场层面（MSS）
- 行业层面（IRS）
- 个股层面（PAS）
```

---

## 6. 异常处理

### 6.1 数据异常

| 异常情况 | 检测方式 | 处理策略 |
|----------|----------|----------|
| 行业成分股缺失 | stock_count < 10 | 使用前一日数据 |
| 涨跌停数据异常 | limit_up > stock_count/3 | 人工确认后计算 |
| 估值数据缺失 | pe_ttm is None | 使用行业历史均值 |

### 6.2 计算异常

| 异常情况 | 检测方式 | 处理策略 |
|----------|----------|----------|
| 因子计算失败 | Exception | 使用中性值50 |
| 行业数不足31 | count < 31 | 记录告警，继续计算 |
| 历史数据不足 | history < 20d | 跳过连续性因子 |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.2.7 | 2026-02-08 | 修复 R17：§5.2 IRS→PAS 协同阈值由 `PAS≥80` 对齐为 `PAS≥85（S级）` |
| v3.2.6 | 2026-02-08 | 修复 R14：§5.1 明确 MSS 温度由 Integration 消费（非 IRS 直接输入） |
| v3.2.5 | 2026-02-08 | 修复 R13：轮动状态判定字段显式为 `industry_score`（连续3日） |
| v3.2.4 | 2026-02-07 | 修复 R5：Step 1 补充 IRS baseline 读取；Step 3 明确 baseline 缺失时回退 50 |
| v3.2.3 | 2026-02-07 | 修复 P1：Step 3 估值因子口径统一为 normalize_zscore（由 -pe_ttm 输入） |
| v3.2.2 | 2026-02-07 | 修复 P0：Step 6 排名映射覆盖 31 行业（11-26 减配，27-31 回避） |
| v3.2.1 | 2026-02-06 | Step 1 输入源命名统一为 Data Layer raw_* 表口径 |
| v3.2.0 | 2026-02-04 | 同步 IRS v3.2.0：连续性因子替换动量斜率；示例与异常处理口径对齐 |
| v3.0.0 | 2026-01-31 | 重构版：统一信息流架构、明确阶段划分、补充组件依赖 |

---

**关联文档**：
- 算法设计：[irs-algorithm.md](./irs-algorithm.md)
- 数据模型：[irs-data-models.md](./irs-data-models.md)
- API接口：[irs-api.md](./irs-api.md)

