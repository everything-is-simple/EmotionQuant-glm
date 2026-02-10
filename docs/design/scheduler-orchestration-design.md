# 调度与编排设计

**版本**: v0.3
**最后更新**: 2026-02-09
**状态**: 可执行草案（Spiral Lite）

## 目标

- 任务编排与依赖
- 失败重试策略
- 运行时间窗口

## DAG 任务依赖（主流程）

```text
Data Layer
  ├─ raw_daily / raw_daily_basic / raw_limit_list / trade_calendar
  └─ stock_info / index_classify
        ↓
MSS / IRS / PAS
        ↓
Validation Gate（因子验证 + 权重验证）
        ↓
Integration
        ↓
Trading
        ↓
Analysis / GUI 刷新
```

执行约束：
- `Data Layer` 未完成则禁止 MSS/IRS/PAS 启动
- 三个子系统全部成功后才允许 Validation Gate
- Validation Gate 必须 `PASS` 或 `WARN`；若 `FAIL` 则阻断 Integration
- Integration 失败时禁止 Trading 下发

## 数据就绪检查点与超时

| 检查点 | 条件 | 超时 |
|--------|------|------|
| `trade_calendar` | 当日为交易日且日历可读 | 2 分钟 |
| `raw_daily` | 覆盖当日目标股票池 | 10 分钟 |
| `raw_index_daily` | 指数数据可用 | 5 分钟 |
| `index_classify(SW2021)` | 31 行业映射齐全 | 5 分钟 |
| `validation_gate_decision` | `final_gate ∈ {PASS, WARN}` 且 `selected_weight_plan` 非空 | 2 分钟 |
| `integrated_recommendation` | 推荐结果生成成功 | 3 分钟 |

超时处理：
- 首次超时：触发一次即时重试
- 连续超时：进入指数退避重试并触发 `P1` 告警

## 调度窗口（A股口径）

- 盘后主计算窗口：`15:30 - 18:30`
  - `15:30 - 16:30`：Data Layer（采集 + L2 聚合）
  - `16:30 - 17:00`：MSS / IRS / PAS
  - `17:00 - 17:15`：算法输出收敛与就绪校验
  - `17:15 - 17:20`：Validation Gate
  - `17:20 - 17:40`：Integration + Trading 准备
  - `17:40 - 18:30`：Analysis + GUI 刷新
- 夜间补算窗口：`19:00 - 22:00`
- 盘前准备窗口：`08:30 - 09:20`
- 交易执行窗口：`09:30 - 11:30`、`13:00 - 15:00`

## 重试与补偿策略

- 默认重试：最多 5 次，指数退避（30s, 60s, 120s, 240s, 480s）
- 失败补偿：下游任务自动跳过，标记 `blocked_by_dependency`
- 人工恢复：允许基于 `trade_date + module` 手动重跑单节点

## 约束

- 不违反系统铁律
- 路径硬编码绝对禁止

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v0.3 | 2026-02-09 | 修复 R25：DAG 补齐 Validation Gate 节点；执行约束新增 Gate 阻断规则；就绪检查点新增 `validation_gate_decision`；盘后窗口细化到 Validation 时段 |
| v0.2 | 2026-02-08 | 修复 R10：补齐 DAG、就绪检查点、超时阈值与失败重试/补偿策略 |
| v0.1 | 2026-02-02 | 初始占位草案 |
