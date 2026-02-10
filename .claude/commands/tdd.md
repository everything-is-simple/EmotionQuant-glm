# TDD 提醒（A5 实现阶段）

在 A5 实现阶段开始前，提醒 TDD（测试驱动开发）原则和零容忍规则。

## TDD 核心流程

```text
1. RED（红灯）: 先写失败的测试
   pytest tests/unit/xxx_test.py -v  # 应该 FAIL

2. GREEN（绿灯）: 写最小代码让测试通过
   pytest tests/unit/xxx_test.py -v  # 应该 PASS

3. REFACTOR（重构）: 改进代码质量
   black src/ && flake8 src/
   pytest tests/ -v  # 所有测试仍然 PASS
```

## 零容忍规则

### 1. 路径硬编码（最严重）

```python
# ❌ 绝对禁止
db_path = "G:/EmotionQuant_data/database/emotionquant.db"
cache_dir = "data/cache/"

# ✅ 必须这样
config = Config.from_env()
db_path = config.database_path
cache_dir = config.cache_dir
```

### 2. 数据契约违规

```python
# ❌ 禁止自创字段名
@dataclass
class Bar:
    date: str  # 错误！应该是 trade_date
    symbol: str  # 错误！应该是 ts_code

# ✅ 必须严格按照 {module}-data-models.md
@dataclass
class Bar:
    ts_code: str
    trade_date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
```

### 3. TDD 违规

```text
❌ 先实现后测试
❌ 批量实现后补测试
✅ 每个 Step：红灯 → 绿灯 → 重构
```

### 4. 技术指标使用

```python
# ❌ 严格禁止
import talib
ma = talib.MA(close, timeperiod=20)
rsi = talib.RSI(close, timeperiod=14)

# ✅ 只能使用基础市场数据
up_count = (df['close'] > df['open']).sum()
limit_up_count = (df['close'] >= df['limit_up']).sum()
```

## 权威文档参考

- 数据模型：`docs/design/{module}/{module}-data-models.md`

- API 规范：`docs/design/{module}/{module}-api.md`

- 信息流：`docs/design/{module}/{module}-information-flow.md`

## 遇到问题时

1. **不确定数据模型定义**：立即查阅 `docs/design/{module}/{module}-data-models.md`

2. **Gate 检查失败**：立即停止，修复后重跑

3. **测试无法通过**：先分析根因，必要时调整测试数据

## 成功标准

- [ ] 所有测试用例通过（绿灯）

- [ ] Gate 检查全部通过

- [ ] 代码符合 Black + Flake8 规范

- [ ] 无路径硬编码

- [ ] 数据模型与权威定义一致
