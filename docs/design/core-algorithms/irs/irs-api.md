# IRS API 接口

**版本**: v3.2.2（重构版）
**最后更新**: 2026-02-09
**状态**: 设计完成（模块接口；当前仓库无 Web API）

---

## 实现状态（仓库现状）

- 当前仓库 `src/algorithms/irs/` 仅有骨架（`__init__.py`），IrsCalculator/IrsRepository 为规划接口。
- 本文档为设计规格，接口实现以 CP-03 落地为准（兼容文件名 Phase 03）。

---

## 1. 接口定位

当前仓库不包含 Web 后端。IRS 以 **Python 模块接口/CLI** 形式对外提供能力；
如需 HTTP 服务，由 GUI/服务层另行封装。

---

## 2. 模块接口（Python）

### 2.1 计算器接口

```python
class IrsCalculator:
    """IRS 计算器接口"""
    
    def calculate(self, trade_date: str) -> List[IrsIndustryDaily]:
        """
        计算指定日期的所有行业评分
        
        Args:
            trade_date: 交易日期 YYYYMMDD
        Returns:
            31个行业的评分列表（按排名升序；每条记录包含 quality_flag/sample_days）
            - quality_flag: normal/cold_start/stale
            - sample_days: 有效样本天数（>= 0）
        Raises:
            ValueError: 非交易日或数据缺失
        Note:
            - 当 sample_days < 60 时，应输出 quality_flag="cold_start"（合法降级，不抛异常）
        """
        pass
    
    def batch_calculate(self, start_date: str, end_date: str) -> Dict[str, List[IrsIndustryDaily]]:
        """批量计算日期范围内的行业评分"""
        pass
    
    def get_factor_scores(self, trade_date: str, industry_code: str) -> dict:
        """获取指定行业的六因子得分"""
        pass
    
    def get_top_industries(self, trade_date: str, top_n: int = 10) -> List[str]:
        """获取评分前N的行业代码"""
        pass
    
    def get_rotation_status(self, trade_date: str, industry_code: str) -> str:
        """获取指定行业的轮动状态"""
        pass
```

### 2.2 数据仓库接口

```python
class IrsRepository:
    """IRS 数据仓库接口"""
    
    def save(self, industry_daily: IrsIndustryDaily) -> None:
        """保存单条记录（幂等）"""
        pass
    
    def save_batch(self, industry_dailies: List[IrsIndustryDaily]) -> int:
        """批量保存"""
        pass
    
    def get_by_date(self, trade_date: str) -> List[IrsIndustryDaily]:
        """按日期查询所有行业"""
        pass
    
    def get_by_industry(self, industry_code: str, limit: int = 30) -> List[IrsIndustryDaily]:
        """按行业查询历史"""
        pass

    def get_cold_start_industries(self, trade_date: str) -> List[IrsIndustryDaily]:
        """查询当日 quality_flag='cold_start' 的行业记录（可选实现）"""
        pass
```

---

## 3. 错误处理

- 非交易日或数据缺失：抛出 `ValueError`。
- 冷启动降级：当 `sample_days < 60` 时，输出 `quality_flag="cold_start"` 与对应 `sample_days`（合法输出，不抛异常）。
- 陈旧数据降级：当可用样本不足但可沿用前值时，输出 `quality_flag="stale"`（合法输出，不抛异常）。
- 详细错误码与处理策略见：
  - `docs/design/core-algorithms/irs/irs-algorithm.md`
  - `Governance/ROADMAP/ROADMAP-PHASE-03-irs.md`

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.2.2 | 2026-02-09 | 修复 R27：`calculate()` 返回契约补充 `quality_flag/sample_days`；错误处理补充 `cold_start/stale` 降级语义；`IrsRepository` 增加可选查询 `get_cold_start_industries()` |
| v3.2.1 | 2026-02-05 | 移除 HTTP 接口示例，改为模块接口定义；与路线图/仓库架构对齐 |
| v3.2.0 | 2026-02-04 | 同步 IRS v3.2.0：动量斜率改为连续性因子；示例口径对齐 |
| v3.0.0 | 2026-01-31 | 重构版：统一API风格、添加枚举映射、完善错误处理 |

---

**关联文档**：
- 算法设计：[irs-algorithm.md](./irs-algorithm.md)
- 数据模型：[irs-data-models.md](./irs-data-models.md)
- 信息流：[irs-information-flow.md](./irs-information-flow.md)
