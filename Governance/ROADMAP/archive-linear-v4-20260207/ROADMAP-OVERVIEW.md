# EmotionQuant ROADMAP 总览

**版本**: v4.0.9（量化版）
**创建日期**: 2026-01-31
**最后更新**: 2026-02-06
**状态**: 文档/规格（Spec）量化版 - 输入输出可量化、验收标准明确、错误处理完备（**不代表代码实现已完成**）
**实现状态**: Skeleton（截至 2026-02-06：`src/` 已有少量占位与基础配置/数据层骨架实现，核心业务逻辑未落地）

---

## 文档对齐声明

> ⚠️ **本 ROADMAP 与以下重构设计文档保持严格一致（规格/设计一致性）**：
>
> - 系统总览：`docs/system-overview.md`
> - 模块索引：`docs/module-index.md`
> - 核心算法：`docs/design/core-algorithms/`（MSS/IRS/PAS/Integration）
> - 基础设施：`docs/design/`（data-layer/backtest/trading/gui/analysis）
>
> **四位一体文档规范**：每个模块包含 algorithm + data-models + api + information-flow
>
> **重要**：本文中的 “✅/v4.0” 仅代表文档规格完成度，不代表代码实现完成度；实现进度以 `src/` 与实际可运行命令为准。

---

## 1. 总体路线图

### 1.1 Phase 概览

| Phase | 名称 | 核心交付 | 预估工期 | 依赖 | 文档位置 |
|-------|------|----------|----------|------|----------|
| 01 | Data Layer | L1-L4数据架构、Repository模式 | 4周 | 无 | `docs/design/data-layer/` |
| 02 | MSS | 市场情绪全景算法 | 4周 | Phase 01 | `docs/design/core-algorithms/mss/` |
| 03 | IRS | 行业轮动追踪算法 | 4周 | Phase 01 | `docs/design/core-algorithms/irs/` |
| 04 | PAS | 个股精准分析算法 | 4周 | Phase 01 | `docs/design/core-algorithms/pas/` |
| 05 | Integration | 三三制集成算法 | 4周 | Phase 02-04 | `docs/design/core-algorithms/integration/` |
| 06 | Backtest | 回测引擎 | 4周 | Phase 05 | `docs/design/backtest/` |
| 07 | Trading | 交易与风控 | 4周 | Phase 05 | `docs/design/trading/` |
| 08 | GUI | 图形界面 | 4周 | Phase 01-07 | `docs/design/gui/` |
| 09 | Analysis | 分析报告 | 4周 | Phase 01-07 | `docs/design/analysis/` |

### 1.2 依赖关系图

```
Phase 01 (Data Layer) ─────────────────────────────────────────────────
    │                                                                   
    ├──────────────────┬──────────────────┬──────────────────┐         
    │                  │                  │                  │         
    ▼                  ▼                  ▼                  │         
Phase 02 (MSS)    Phase 03 (IRS)    Phase 04 (PAS)          │         
    │                  │                  │                  │         
    └──────────────────┼──────────────────┘                  │         
                       │                                     │         
                       ▼                                     │         
               Phase 05 (Integration)                        │         
                       │                                     │         
           ┌───────────┼───────────┐                        │         
           │           │           │                        │         
           ▼           ▼           ▼                        ▼         
    Phase 06      Phase 07      Phase 08 ◄──────────────────┘         
    (Backtest)    (Trading)     (GUI)                                 
           │           │           │                                   
           └───────────┼───────────┘                                   
                       │                                               
                       ▼                                               
               Phase 09 (Analysis)                                     
```

### 1.3 关键里程碑

| 里程碑 | 完成Phase | 核心能力 | 验收标准 |
|--------|-----------|----------|----------|
| **M0: MVP-01 闭环就绪** | Phase 01-05 | L1→L2→L3 跑通（含 TD/BU 双模式集成输出） | L1/L2 覆盖率达标；MSS/IRS/PAS/Integration 输出范围合法且可被回测引擎消费 |
| **M1: 数据基础就绪** | Phase 01 | 数据采集、存储、访问 | L1数据8类完整率≥99%，L2快照生成成功率≥95% |
| **M2: 三维分析就绪** | Phase 02-04 | MSS+IRS+PAS独立运行 | 各算法输出覆盖率≥95%，评分范围[0-100] |
| **M3: 信号生成就绪** | Phase 05 | 三三制集成推荐 | 权重严格1:1:1；TD 为默认主流程；BU 不突破 TD 上限 |
| **M4: 策略验证就绪** | Phase 06-07 | 回测+风控 | 回测引擎优先 backtrader（qlib为规划项）；风控规则100%生效 |
| **M5: 系统上线就绪** | Phase 08-09 | GUI+报告 | 界面响应<3s，日报自动生成 |

---

## 2. 系统铁律（全Phase强制）

### 2.1 铁律清单

| 铁律 | 内容 | 检查方式 | 违反后果 |
|------|------|----------|----------|
| **零技术指标** | 禁止MA/MACD/RSI/KDJ/BOLL等 | pre-commit hook + 代码审查 | 立即回滚，阻断合并 |
| **情绪优先** | 所有算法基于情绪因子 | 设计评审 | 设计返工 |
| **本地数据优先** | 本地数据库/存储/读取为主 | 配置检查 + 代码审查 | 阻断合并 |
| **路径硬编码绝对禁止** | 路径/密钥/配置必须注入 | 路径扫描 + 代码审查 | 阻断合并 |
| **A 股专属** | 严格遵守中国 A 股规则 | 设计评审 + 数据校验 | 阻断合并 |

### 2.2 铁律检测脚本

> 注：以下为**规范示例脚本**；仓库当前未内置 `.pre-commit-config.yaml` 或 hooks 安装脚本，需在实现阶段落地。

```bash
# pre-commit hook 检测技术指标关键词
FORBIDDEN_KEYWORDS="talib|ta-lib|TA_Lib|MA\(|EMA\(|SMA\(|RSI\(|MACD\(|KDJ\(|BOLL\(|ATR\(|DMI\(|ADX\("
if grep -rE "$FORBIDDEN_KEYWORDS" src/; then
    echo "❌ 检测到禁止的技术指标！"
    exit 1
fi
```

```bash
# pre-commit hook 检测路径硬编码（示例）
FORBIDDEN_PATHS="[A-Za-z]:\\\\|[A-Za-z]:/|/home/|/Users/|\"(data|cache|logs)/|\\\\"
if grep -rE "$FORBIDDEN_PATHS" src/; then
    echo "❌ 检测到硬编码路径！"
    exit 1
fi
```

---

## 3. 全局验收标准

### 3.1 代码质量标准

| 指标 | 阈值 | 检测工具 |
|------|------|----------|
| 测试覆盖率 | ≥80% | pytest-cov |
| 代码规范 | 0 error | flake8/black |
| 类型检查 | 0 error | mypy |
| 文档覆盖率 | 100% public API | pydoc |

### 3.2 数据质量标准

| 指标 | 阈值 | 检测方法 |
|------|------|----------|
| 数据完整率 | ≥99% | COUNT(NOT NULL) / COUNT(*) |
| 数据及时性 | ≤30min延迟 | 采集时间戳检查 |
| 数据一致性 | 0重复 | DISTINCT检查 |
| 评分范围 | [0,100] | MIN/MAX检查 |

### 3.3 性能标准

| 指标 | 阈值 | 适用Phase |
|------|------|-----------|
| 日度处理时间 | ≤3小时 | Phase 01-05 |
| 单股计算时间 | ≤100ms | Phase 02-04 |
| 回测速度 | ≥50日/秒 | Phase 06 |
| GUI响应时间 | ≤3秒 | Phase 08 |

---

## 4. 错误处理策略

### 4.1 错误分级

| 级别 | 描述 | 处理策略 | 示例 |
|------|------|----------|------|
| **P0-致命** | 系统无法运行 | 立即停止，人工介入 | 数据库连接失败、API限流 |
| **P1-严重** | 核心功能异常 | 降级处理，告警通知 | 部分数据缺失、计算超时 |
| **P2-一般** | 非核心功能异常 | 自动重试，记录日志 | 单股计算失败、网络抖动 |
| **P3-轻微** | 体验问题 | 静默处理，定期修复 | 报告格式问题、缓存失效 |

### 4.2 通用错误处理模式

```python
def execute_with_retry(func, max_retries=3, backoff=2):
    """
    通用重试模式
    
    参数:
        func: 待执行函数
        max_retries: 最大重试次数
        backoff: 退避系数（指数退避）
    
    返回:
        函数执行结果或None（失败时）
    """
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            wait_time = backoff ** attempt
            logger.warning(f"Attempt {attempt+1} failed: {e}, retry in {wait_time}s")
            time.sleep(wait_time)
    logger.error(f"All {max_retries} attempts failed")
    return None
```

### 4.3 Phase级错误处理

| Phase | 常见错误 | 处理策略 | 降级方案 |
|-------|----------|----------|----------|
| 01 | TuShare限流 | 指数退避重试 | 使用缓存数据 |
| 02 | 快照数据缺失 | 使用前一日数据 | 跳过该日计算 |
| 03 | 行业成分变更 | 动态更新映射 | 使用历史映射 |
| 04 | 个股停牌 | 跳过该股 | 无影响 |
| 05 | 子系统超时 | 使用缓存结果 | 降级推荐 |
| 06 | 回测数据不足 | 调整窗口 | 跳过该标的 |
| 07 | 风控规则冲突 | 优先严格规则 | 拒绝交易 |
| 08 | 数据加载慢 | 分页加载 | 减少展示量 |
| 09 | 报告生成失败 | 重新生成 | 简化报告 |

---

## 5. 数据层架构（全Phase基础）

### 5.1 四层架构

| 层级 | 名称 | 内容 | 存储格式 | Phase责任 |
|------|------|------|----------|------------|
| L1 | 原始数据层 | 外部数据源采集 | Parquet | Phase 01 |
| L2 | 特征层 | 情绪因子计算 | DuckDB（按年分库） | Phase 01 |
| L3 | 算法输出层 | MSS/IRS/PAS/Integration 结果 | DuckDB（按年分库） | Phase 02-05 |
| L4 | 分析层 | 绩效/报告 | DuckDB（按年分库） + MD | Phase 09 |

> 补充：交易与回测运行表（`trade_records` / `positions` / `t1_frozen` / `backtest_trade_records` / `backtest_results`）统一归类为 **Business Tables（非 L1-L4）**。

### 5.2 核心数据表（输入输出矩阵）

| 数据表 | 层级 | 写入Phase | 读取Phase | 记录数/日 | 关键字段 |
|--------|------|-----------|-----------|-----------|----------|
| raw_daily | L1 | 01 | All | ~5000 | ts_code, trade_date, OHLCV |
| raw_daily_basic | L1 | 01 | All | ~5000 | turnover_rate, pe, pb |
| raw_limit_list | L1 | 01 | 01-04 | ~50-300 | limit (U/D/Z) |
| raw_index_daily | L1 | 01 | 03 | ~100 | 指数行情 |
| market_snapshot | L2 | 01 | 02 | 1 | rise_count, limit_up_count等 |
| industry_snapshot | L2 | 01 | 03 | 31 | 行业聚合指标 |
| mss_panorama | L3 | 02 | 05,08,09 | 1 | temperature, cycle, trend |
| irs_industry_daily | L3 | 03 | 05,08,09 | 31 | industry_score, rotation_status |
| stock_pas_daily | L3 | 04 | 05,08,09 | ~5000 | opportunity_score, grade |
| integrated_recommendation | L3 | 05 | 06-09 | ~20 | final_score, recommendation |
| backtest_trade_records | Business Tables | 06 | 09 | n/回测 | signal_date, execute_date, pnl |
| backtest_results | Business Tables | 06 | 09 | 1/回测 | sharpe, max_drawdown |
| daily_report | L4 | 09 | 08 | 1 | 日报内容 |

---

## 6. Phase级验收标准汇总

### 6.1 量化验收指标

| Phase | 验收指标 | 阈值 | 验证方法 |
|-------|----------|------|----------|
| 01 | L1数据完整率 | ≥99% | `COUNT(*) vs 预期记录数` |
| 01 | L2快照生成率 | ≥95% | `生成天数/交易日数` |
| 01 | 数据延迟 | ≤30min | `采集时间-收盘时间` |
| 02 | 温度范围 | [0,100] | `MIN/MAX检查` |
| 02 | 周期覆盖 | 7种 | `DISTINCT(cycle)` |
| 02 | 日均输出 | 1条 | `COUNT(DISTINCT trade_date)` |
| 03 | 六因子完整性 | 100% | `NOT NULL检查` |
| 03 | 行业覆盖 | 31个 | `COUNT(DISTINCT industry_code)` |
| 03 | 排名连续性 | 1-31 | `rank序列检查` |
| 04 | 评分范围 | [0,100] | `MIN/MAX检查` |
| 04 | 技术指标关键词 | 0处 | `grep检查` |
| 04 | 日均输出 | ≥4000只 | `COUNT(*)` |
| 05 | 权重等分 | 1/3:1/3:1/3 | `单元测试` |
| 05 | 推荐等级 | 5种 | `DISTINCT(recommendation)` |
| 05 | 日均推荐 | ≥10只 | `COUNT(*)` |
| 06 | 夏普比率 | ≥1.0 | `绩效计算` |
| 06 | T+1规则 | 100%生效 | `交易记录检查` |
| 06 | 回测速度 | ≥50日/秒 | `性能测试` |
| 07 | 风控规则 | 100%生效 | `规则触发检查` |
| 07 | 订单状态 | 5种 | `状态机测试` |
| 08 | 页面响应 | ≤3秒 | `性能测试` |
| 08 | 数据正确性 | 100% | `前后端一致性` |
| 09 | 绩效指标 | 5+项 | `指标完整性` |
| 09 | 日报生成 | 100% | `自动化检查` |

### 6.2 验收检查清单模板

```markdown
## Phase XX 验收检查清单

### 功能验收
- [ ] 核心功能1: 描述 | 预期结果 | 实际结果 | ✅/❌
- [ ] 核心功能2: 描述 | 预期结果 | 实际结果 | ✅/❌

### 数据验收
- [ ] 输出记录数: 预期≥N | 实际=M | ✅/❌
- [ ] 字段完整性: 预期100% | 实际=X% | ✅/❌
- [ ] 评分范围: 预期[0,100] | 实际=[min,max] | ✅/❌

### 性能验收
- [ ] 处理时间: 预期≤T | 实际=X | ✅/❌
- [ ] 内存占用: 预期≤M | 实际=X | ✅/❌

### 质量验收
- [ ] 测试覆盖率: 预期≥80% | 实际=X% | ✅/❌
- [ ] 代码规范: 预期0 error | 实际=X | ✅/❌
```

---

## 7. 关键约定

### 7.1 周期命名（中英文映射）

| 英文 | 中文 | 温度区间 | 仓位建议 |
|------|------|----------|----------|
| emergence | 萌芽期 | <30°C + up | 80%-100% |
| fermentation | 发酵期 | 30-45°C + up | 60%-80% |
| acceleration | 加速期 | 45-60°C + up | 50%-70% |
| divergence | 分歧期 | 60-75°C + up/sideways | 40%-60% |
| climax | 高潮期 | ≥75°C | 20%-40% |
| diffusion | 扩散期 | 60-75°C + down | 30%-50% |
| recession | 退潮期 | <60°C + down | 0%-20% |

### 7.2 趋势命名

| 英文 | 中文 | 判定条件 |
|------|------|----------|
| up | 上行 | 温度连续3日上升 |
| down | 下行 | 温度连续3日下降 |
| sideways | 横盘 | 其他情况 |

### 7.3 轮动状态

| 状态 | 描述 | 判定条件 |
|------|------|----------|
| IN | 进入轮动 | 评分连续3日上升 |
| OUT | 退出轮动 | 评分连续3日下降 |
| HOLD | 维持观望 | 其他情况 |

### 7.4 推荐等级

| 等级 | 条件 | 操作建议 |
|------|------|----------|
| STRONG_BUY | final_score≥80 且 周期∈{emergence,fermentation} | 强烈买入 |
| BUY | 70-79 或 ≥80且其他周期 | 买入 |
| HOLD | 50-69 | 持有 |
| SELL | 30-49 | 卖出 |
| AVOID | <30 | 回避 |

### 7.5 机会等级（PAS）

| 等级 | 评分区间 | 操作建议 |
|------|----------|----------|
| S | ≥85 | 重仓买入 |
| A | 70-84 | 标准仓位 |
| B | 55-69 | 轻仓试探 |
| C | 40-54 | 不操作 |
| D | <40 | 减仓/清仓 |

---

## 8. ROADMAP文件索引

> 说明：下表仅描述**文档规格**状态（Spec），不代表实现完成度。

|| 文件 | 内容 | 文档状态（Spec） |
||------|------|------------------|
|| ROADMAP-OVERVIEW.md | 总览（本文档） | Spec v4.0.9 |
|| ROADMAP-PHASE-01-data-layer.md | Phase 01 数据层 | Spec v4.0.2 |
|| ROADMAP-PHASE-02-mss.md | Phase 02 MSS | Spec v4.0.2 |
|| ROADMAP-PHASE-03-irs.md | Phase 03 IRS | Spec v4.0.3 |
|| ROADMAP-PHASE-04-pas.md | Phase 04 PAS | Spec v4.0.2 |
|| ROADMAP-PHASE-05-integration.md | Phase 05 集成 | Spec v4.0.3 |
|| ROADMAP-PHASE-06-backtest.md | Phase 06 回测 | Spec v4.1.4 |
|| ROADMAP-PHASE-07-trading.md | Phase 07 交易 | Spec v4.1.0 |
|| ROADMAP-PHASE-08-gui.md | Phase 08 GUI | Spec v4.0.1 |
|| ROADMAP-PHASE-09-analysis.md | Phase 09 分析 | Spec v4.0.1 |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v4.0.9 | 2026-02-06 | 对齐核心算法与 Phase 02-05 输入依赖命名（raw_*）并同步规格版本索引 |
| v4.0.8 | 2026-02-06 | 对齐 Business Tables 口径：补充回测/交易业务表为非L1-L4；更新 Phase 06/07 规格版本引用 |
| v4.0.7 | 2026-02-06 | 更新实现状态口径与回测引擎表述 |
| v4.0.6 | 2026-02-05 | Phase 06 验收清单对齐测试用例清单 |
| v4.0.5 | 2026-02-05 | Phase 06 回测规范补充执行细节 |
| v4.0.4 | 2026-02-05 | Phase 06 回测规范升级（signal_date/execute_date 对齐） |
| v4.0.3 | 2026-02-05 | 系统铁律更新：新增路径硬编码禁令与 A 股专属 |
| v4.0.2 | 2026-02-05 | 系统铁律更新：新增本地数据优先，移除铁律三/四 |
| v4.0.1 | 2026-02-04 | 修正存储口径与术语：L4表命名、技术指标检测表述更新 |
| v4.0.0 | 2026-02-02 | 量化版：添加完整验收标准、错误处理、里程碑、输入输出矩阵 |
| v3.0.0 | 2026-01-31 | 重构版：与 docs/ 设计文档完全对齐 |
| v2.0.0 | 2026-01-23 | 6A工作流对齐 |
| v1.0.0 | 2025-12-20 | 初始版本 |

---

**关联文档**：
- 系统总览：`docs/system-overview.md`
- 核心原则：`Governance/steering/CORE-PRINCIPLES.md`
- 系统铁律：`Governance/steering/系统铁律.md`

