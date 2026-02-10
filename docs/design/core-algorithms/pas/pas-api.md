# PAS API 接口

**版本**: v3.1.3（重构版）
**最后更新**: 2026-02-08
**状态**: 设计完成（模块接口；当前仓库无 Web API）

---

## 实现状态（仓库现状）

- 当前仓库 `src/algorithms/pas/` 仅有骨架（`__init__.py`），PasCalculator/PasRepository 为规划接口。
- 本文档为设计规格，接口实现以 CP-04 落地为准（兼容文件名 Phase 04）。

---

## 1. 接口定位

当前仓库不包含 Web 后端。PAS 以 **Python 模块接口/CLI** 形式对外提供能力；
如需 HTTP 服务，由 GUI/服务层另行封装。

---

## 2. 模块接口（Python）

### 2.1 计算器接口

```python
class PasCalculator:
    """PAS 计算器接口"""
    
    def calculate(self, trade_date: str, stock_code: str) -> StockPasDaily:
        """
        计算单只股票的 PAS 评分
        
        Args:
            trade_date: 交易日期 YYYYMMDD
            stock_code: 股票代码
        Returns:
            StockPasDaily 对象
        Raises:
            ValueError: 非交易日或数据缺失
        """
        pass
    
    def batch_calculate(self, trade_date: str, stock_codes: List[str] = None) -> List[StockPasDaily]:
        """
        批量计算股票 PAS 评分
        
        Args:
            trade_date: 交易日期
            stock_codes: 股票代码列表，None表示全市场
        Returns:
            StockPasDaily 列表（按评分降序）
        """
        pass
    
    def get_top_opportunities(self, trade_date: str, top_n: int = 100, min_grade: str = "B") -> List[StockPasDaily]:
        """获取评分前N的机会"""
        pass
    
```

### 2.2 数据仓库接口

```python
class PasRepository:
    """PAS 数据仓库接口"""
    
    def save(self, pas_daily: StockPasDaily) -> None:
        """保存单条记录（幂等）"""
        pass
    
    def save_batch(self, pas_dailies: List[StockPasDaily]) -> int:
        """批量保存"""
        pass
    
    def get_by_date(self, trade_date: str) -> List[StockPasDaily]:
        """按日期查询所有股票"""
        pass
    
    def get_by_stock(self, stock_code: str, limit: int = 30) -> List[StockPasDaily]:
        """按股票查询历史"""
        pass

    def get_by_industry(self, trade_date: str, industry_code: str) -> List[StockPasDaily]:
        """按日期+行业查询股票评分"""
        pass

    def get_by_grade(self, trade_date: str, grades: List[str]) -> List[StockPasDaily]:
        """按日期+等级批量查询股票评分"""
        pass
```

---

## 3. 错误处理

- 非交易日或数据缺失：抛出 `ValueError`。
- 详细错误码与处理策略见：
  - `docs/design/core-algorithms/pas/pas-algorithm.md`
  - `Governance/ROADMAP/ROADMAP-PHASE-04-pas.md`

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.1.3 | 2026-02-08 | 修复 R19：`PasRepository` 补充 `get_by_grade(trade_date, grades)`，与 Integration info-flow 调用链对齐 |
| v3.1.2 | 2026-02-08 | 修复 R17：`get_by_industry` 从 `PasCalculator` 迁移到 `PasRepository`，与查询职责分层及 IRS 口径一致 |
| v3.1.1 | 2026-02-05 | 移除 HTTP 接口示例，改为模块接口定义；与路线图/仓库架构对齐 |
| v3.1.0 | 2026-02-04 | 同步 PAS v3.1.0：验收口径补齐（ratio→zscore），示例字段对齐 |
| v3.0.0 | 2026-01-31 | 重构版：统一API风格、完善错误处理 |

---

**关联文档**：
- 算法设计：[pas-algorithm.md](./pas-algorithm.md)
- 数据模型：[pas-data-models.md](./pas-data-models.md)
- 信息流：[pas-information-flow.md](./pas-information-flow.md)
