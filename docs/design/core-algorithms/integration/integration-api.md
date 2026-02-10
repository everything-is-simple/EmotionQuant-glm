# Integration API 接口

**版本**: v3.4.4（重构版）
**最后更新**: 2026-02-09
**状态**: 设计完成（模块接口；当前仓库无 Web API）

---

## 实现状态（仓库现状）

- 当前仓库 `src/integration/` 仅有骨架（`__init__.py`），IntegrationEngine/IntegrationRepository 为规划接口。
- 本文档为设计规格，接口实现以 CP-05 落地为准（兼容文件名 Phase 05）。

---

## 1. 接口定位

当前仓库不包含 Web 后端。Integration 以 **Python 模块接口/CLI** 形式对外提供能力；
如需 HTTP 服务，由 GUI/服务层另行封装。

---

## 2. 模块接口（Python）

### 2.1 集成引擎接口

```python
class IntegrationEngine:
    """Integration"""
    MAX_MODULE_WEIGHT = 0.60
    
    def calculate(
        self,
        mss_input: MssInput,
        irs_inputs: List[IrsInput],
        pas_inputs: List[PasInput],
        weight_plan: WeightPlan,
        validation_gate_decision: ValidationGateDecision
    ) -> List[IntegratedRecommendation]:
        """
        计算集成推荐
        
        Args:
            mss_input: 当日MSS数据（全市场唯一）
            irs_inputs: 当日各行业IRS数据（读取 quality_flag/sample_days；当 quality_flag ∈ {cold_start, stale} 时强制回退 baseline 权重并提升 Gate 状态为 WARN）
            pas_inputs: 当日各股票PAS数据
            weight_plan: 已通过验证的权重方案（含 plan_id 与 w_mss/w_irs/w_pas；需由 Validation `resolve_weight_plan(trade_date, gate.selected_weight_plan)` 解析）
            validation_gate_decision: 验证门禁决策（建议从 Validation `validation_gate_decision` 表读取）
        Returns:
            集成推荐列表（按final_score降序）
        Raises:
            ValueError: 输入数据无效
            WeightViolationError: 权重方案违反约束
            ValidationGateError: validation_gate_decision.final_gate=FAIL，不允许进入集成
        """
        pass
    
    def generate_recommendations(
        self,
        signals: List[IntegratedRecommendation],
        top_n: int = 20
    ) -> List[IntegratedRecommendation]:
        """
        筛选并生成最终推荐列表
        
        Args:
            signals: 全部集成信号
            top_n: 最大推荐数量
        Returns:
            筛选后的推荐列表（按等级+评分排序）
        """
        pass
    
    def get_latest_recommendations(self, trade_date: str = None) -> List[IntegratedRecommendation]:
        """获取最新推荐列表"""
        pass
    
    def verify_weight_plan(self, weight_plan: WeightPlan) -> bool:
        """验证权重约束：非负、和为1、单模块上限"""
        weights = [weight_plan.w_mss, weight_plan.w_irs, weight_plan.w_pas]
        return (
            all(v >= 0 for v in weights) and
            abs(sum(weights) - 1.0) < 1e-8 and
            all(v <= self.MAX_MODULE_WEIGHT for v in weights)
        )
```

### 2.3 Validation 桥接调用约定

```python
# 约定：Integration 不直接解析 selected_weight_plan 字符串
gate, weight_plan = validation_orchestrator.build_integration_inputs(trade_date)
signals = integration_engine.calculate(
    mss_input=mss,
    irs_inputs=irs,
    pas_inputs=pas,
    weight_plan=weight_plan,
    validation_gate_decision=gate,
)
```

说明：`selected_weight_plan` -> `WeightPlan` 的桥接责任在 Validation Orchestrator，避免 Integration 侧重复实现解析逻辑。

### 2.2 数据仓库接口

```python
class IntegrationRepository:
    """Integration 数据仓库"""
    
    def save(self, recommendation: IntegratedRecommendation) -> None:
        """保存单条记录（幂等）"""
        pass
    
    def save_batch(self, recommendations: List[IntegratedRecommendation]) -> int:
        """批量保存"""
        pass
    
    def get_by_date(self, trade_date: str) -> List[IntegratedRecommendation]:
        """按日期查询"""
        pass
    
    def get_by_stock(self, stock_code: str, limit: int = 30) -> List[IntegratedRecommendation]:
        """按股票查询历史"""
        pass
```

---

## 3. 错误处理

- 权重违规：抛出 `WeightViolationError`。
- 输入数据缺失：抛出 `ValueError` 或记录降级标记。
- Gate=FAIL：抛出 `ValidationGateError` 并阻断集成输出。
- 若 IRS 输入全部为 `quality_flag="cold_start"`：不抛异常，强制回退 baseline 权重并按 WARN 继续输出（用于下游识别低置信度）。
- 详细错误码与处理策略见：
  - `docs/design/core-algorithms/integration/integration-algorithm.md`
  - `Governance/ROADMAP/ROADMAP-PHASE-05-integration.md`

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.4.4 | 2026-02-09 | 修复 R29：补充 Validation -> Integration 权重桥接调用约定（通过 Validation Orchestrator 解析 `selected_weight_plan` 为 `WeightPlan`） |
| v3.4.3 | 2026-02-09 | 修复 R27：`calculate()` 参数说明补充 IRS `quality_flag/sample_days` 对 Gate 与权重回退的影响；错误处理补充 `Gate=FAIL` 与“全行业 cold_start”行为 |
| v3.4.2 | 2026-02-08 | 修复 R17：`weight_plan` 参数类型由 `dict` 收敛为 `WeightPlan`，保留 `plan_id` 追溯并增强类型约束 |
| v3.4.1 | 2026-02-08 | 修复 R11：显式定义 `MAX_MODULE_WEIGHT = 0.60`，与 Validation 权重上限口径一致 |
| v3.4.0 | 2026-02-07 | 接入 Validation Gate 与 weight_plan；权重校验由固定1/3改为约束校验 |
| v3.3.1 | 2026-02-05 | 移除 HTTP 接口示例，改为模块接口定义；与路线图/仓库架构对齐 |
| v3.3.0 | 2026-02-04 | 同步 Integration v3.3.0：示例评分与协同约束口径对齐 |
| v3.0.0 | 2026-01-31 | 重构版：统一API风格、完善错误处理 |

---

**关联文档**：
- 算法设计：[integration-algorithm.md](./integration-algorithm.md)
- 数据模型：[integration-data-models.md](./integration-data-models.md)
- 信息流：[integration-information-flow.md](./integration-information-flow.md)
