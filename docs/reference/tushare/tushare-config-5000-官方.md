# TuShare Pro API 配置指南 - 5000积分标准版

**版本**: v1.3
**最后更新**: 2026-02-07
**适用范围**: EmotionQuant项目 - 5000积分官方API
**API类型**: TuShare官方API（https://tushare.pro）
**安全提示**: 文档内 Token 为占位符，请在 `.env` 中配置真实值（参考 `.env.example`）

---

## 一、配置总览

### 1.1 Token信息（安全口径）

- **Token存放位置**: 仅 `.env` 文件中的 `TUSHARE_TOKEN`

- **积分额度**: 5000积分

- **有效期**: 1年（2025-06-23 至 2026-06-23）

- **购买日期**: 2025-01-15

### 1.2 权限详情

根据 [TuShare Pro 官方文档](https://tushare.pro/document/1?doc_id=290)：

| 权限项 | 限制 |
| -------- | ------ |
| **每分钟频次** | **500 次** |
| **每天总量** | **常规数据无上限** |
| **可访问 API** | tushare.pro 90% 的 API |
| **IP限制** | 有（IP>2会被拦截） |

---

## 二、配置方法

### 2.1 环境变量配置（推荐）

**1. 编辑项目根目录下的 `.env` 文件**

```bash
# TuShare Pro Token（只在本机 .env 存放真实值）
TUSHARE_TOKEN=<YOUR_REAL_TOKEN>

# 数据路径配置（示例占位符）
DATA_PATH=${DATA_PATH}
DUCKDB_DIR=${DUCKDB_DIR}
CACHE_PATH=${CACHE_PATH}
LOG_PATH=${LOG_PATH}
```

**2. 在代码中使用Config类加载**

```python
from src.config.config import Config
import tushare as ts

# 加载配置
config = Config.from_env()

# 初始化TuShare Pro API（官方API，无需额外配置）
pro = ts.pro_api(config.tushare_token)

# 正常使用
df = pro.daily(trade_date='20180810')
```

### 2.2 直接配置（禁用）

生产环境与日常开发均禁用 `ts.pro_api('明文token')` 写法。

- 原因：违反“密钥禁止硬编码”铁律。
- 要求：统一通过 `.env` + `Config.from_env()` 注入。

---

## 三、Token智能适配与切换 ⭐ 新增功能

> **版本**: v1.1 (2026-01-11)
> **新增**: `TuShareClient`现支持智能识别5000积分和10000积分token

### 3.1 智能适配原理

项目中的`TuShareClient`类现在可以自动识别token类型：

| Token类型 | 长度特征 | 使用模式 | 说明 |
| ----------- | ---------- | ---------- | ------ |
| **5000积分官方** | >30字符 | 官方API | 直接连接TuShare官方API |
| **10000积分网关** | ≤30字符 | 第三方网关 | 通过第三方网关连接 |

**代码实现说明**（[docs/design/data-layer/data-layer-api.md](../../design/data-layer/data-layer-api.md)）：

```python
from src.data.downloaders.tushare_client import TuShareClient
from src.config.config import Config

config = Config.from_env()
client = TuShareClient(config)  # ✅ 自动识别token类型

# 无需关心使用哪种API，客户端会自动适配
df = client.fetch_daily('20250110')
```

### 3.2 切换Token方法

您可以随时在两种token之间切换，**无需修改任何代码**：

**方法1: 使用5000积分官方token（当前）**

编辑`.env`文件：
```bash
TUSHARE_TOKEN=<YOUR_5000_TOKEN>
```

- ✅ 优点：官方直连，无中间商，稳定性高

- ⚠️ 限制：IP并发限制（同一账号不能在2个以上IP同时调用）

**方法2: 使用10000积分网关token**

编辑`.env`文件：
```bash
TUSHARE_TOKEN=<YOUR_10000_TOKEN>
```

- ✅ 优点：无IP并发限制，支持多设备同时使用

- ✅ 优点：10000积分权限，可访问更多专属接口

- ⚠️ 限制：依赖第三方网关服务稳定性

### 3.3 验证Token切换

切换token后，运行验证脚本确认：

```bash
python scripts/utils/test_tushare_token.py
```

**预期输出**：
```text
✅ 连接测试: 通过
✅ 基础API测试: 通过
✅ daily接口测试: 通过
✅ limit_list_d接口测试: 通过

🎉 Token验证成功！所有核心接口可用。
```

### 3.4 使用建议

| 场景 | 推荐Token | 理由 |
| ------ | ---------- | ------ |
| **单机开发** | 5000积分官方 | 直连稳定，无额外依赖 |
| **多设备协作** | 10000积分网关 | 无IP限制，灵活部署 |
| **需要专属接口** | 10000积分网关 | 更多数据接口权限 |
| **生产环境** | 5000积分官方 | 官方保障，长期稳定 |

---

## 四、系统集成

### 3.1 标准使用模式

```python
# src/data/repositories/daily_bar_repository.py
from src.config.config import Config
import tushare as ts

class DailyBarRepository:
    def __init__(self, config: Config):
        self.config = config

        # 初始化TuShare Pro API（官方API）
        self.pro = ts.pro_api(config.tushare_token)

    def fetch_daily_bars(self, trade_date: str) -> pd.DataFrame:
        """获取指定日期的日线数据"""
        try:
            df = self.pro.daily(
                trade_date=trade_date,
                fields='ts_code,trade_date,open,high,low,close,vol,amount'
            )
            return df
        except Exception as e:
            logger.error(f"获取日线数据失败: {e}")
            raise
```

### 3.2 测试环境配置

在单元测试中，可以使用真实token或mock：

```python
# tests/unit/data/test_daily_bar_repository.py
import pytest
from src.config.config import Config

@pytest.fixture
def config():
    return Config.from_env()

@pytest.fixture
def repository(config):
    return DailyBarRepository(config)

def test_fetch_daily_bars(repository):
    # 使用真实API测试（需要网络连接）
    df = repository.fetch_daily_bars('20180810')
    assert not df.empty
    assert 'ts_code' in df.columns
```

---

## 四、频率控制与限制

### 4.1 频率限制

| 频率类型 | 限制 |
| --------- | ------ |
| **每分钟** | 500次 |
| **每日** | 常规接口无上限 |

### 4.2 系统配置

- **限流器设置**: **400 次/分钟**（留 20% 余量）

- **配置位置**: `src/data/tushare_client.py`

- **自适应模式**: 禁用（使用固定速率）

### 4.3 EmotionQuant项目调用频率

根据项目需求，以下是典型场景的调用频率：

| 场景 | 调用频率 | 5000积分 |
| ------ | --------- | --------- |
| 全市场日线数据（5000+股票） | 约10-20次/分钟 | ✅ 充足 |
| 实时涨跌停监控 | 约5-10次/分钟 | ✅ 充足 |
| 行业轮动数据更新 | 约5次/分钟 | ✅ 充足 |
| 历史数据回测（批量） | 约50-100次/分钟 | ✅ 充足 |

**结论**：5000积分权限完全满足EmotionQuant项目的所有数据需求，无需担心频率限制。

### 4.4 频率控制配置

```python
# 系统配置
RATE_LIMITS = {
    'daily': 400,           # 留20%余量
    'limit_list_d': 150,    # 留25%余量
    'kpl_list': 150,        # 留25%余量
    'sw_daily': 500,        # 无限制，但建议控制
    'default': 400,         # 默认频率
}
```

---

## 五、EmotionQuant数据需求支持

### 5.1 核心接口支持

5000积分足够支持EmotionQuant项目的数据需求：

- **MSS系统**: 获取市场广度数据、涨跌家数统计

- **IRS系统**: 获取申万31个行业分类和行业指数数据（2021版）

- **PAS系统**: 获取个股价格行为数据

### 5.2 关键接口清单

| 接口 | 积分要求 | 频率限制 | 系统用途 |
| ------ | --------- | --------- | ---------- |
| `stock_basic` | 免费 | 100次/分 | 股票池、ST标记 |
| `trade_cal` | 免费 | 500次/分 | 交易日判断 |
| `daily` | 5000 | 500次/分 | Bar数据、涨跌统计 |
| `limit_list_d` | 5000 | 200次/分 | **MSS/IRS核心** |
| `sw_daily` | 5000 | 无限制 | IRS行业温度 |
| `index_classify` | 2000 | 无限制 | IRS行业列表 |
| `index_member` | 2000 | 无限制 | 股票-行业映射 |
| `moneyflow_hsgt` | 2000 | 300条/次 | 辅助情绪指标 |
| `kpl_list` | 5000 | 200次/分 | 涨停原因、题材 |

---

## 六、常见问题

### 6.1 为什么获取不到数据？

**可能原因**：

1. 日期不是交易日

2. TuShare维护中

3. 网络问题

4. Token错误或未激活

**解决方案**：
```python
# 先检查是否为交易日
cal_df = pro.trade_cal(start_date='20251219', end_date='20251219')
if cal_df['is_open'].iloc[0] != 1:
    print("不是交易日")

# 测试连接
try:
    df = pro.daily(trade_date='20241219')  # 用过去日期测试
    print("连接正常")
except Exception as e:
    print(f"连接失败: {e}")
```

### 6.2 如何避免频率限制？

**最佳实践**：

1. 使用批量接口（如trade_cal可以一次性获取一个月）

2. 合理设置调用间隔

3. 使用缓存机制

4. 错峰调用（避开交易时间）

```python
# 错误示例：循环调用单只股票
for code in stock_list:
    df = pro.daily(ts_code=code)  # ❌ 会导致频率限制

# 正确示例：一次获取所有股票
df = pro.daily(trade_date='20251219')  # ✅ 推荐方式
```

### 6.3 Token需要定期重置吗？

**A**: 不需要。有效期内固定使用，到期续费即可。

### 6.4 多人使用同一Token会被清退吗？

**A**: 会。Token限个人使用，发现多人调用将进行清退。

### 6.5 遇到IP并发限制怎么办？

**A**: 5000积分官方API有IP并发限制（同一账号在2个以上IP同时调用会被拦截）。

**解决方案**：

1. 单IP开发（推荐）

2. 升级到10000积分网关版（无IP限制）

---

## 七、安全与最佳实践

### 7.1 安全警告 ⚠️

1. **禁止硬编码Token**: 生产环境必须通过 `.env` 文件和 `Config.from_env()` 加载

2. **禁止提交Token到Git**: `.env` 文件已加入 `.gitignore`，确保不提交敏感信息

3. **禁止多人共享Token**: Token限个人使用，发现多人调用将被清退

### 7.3 Token泄露应急处理（立即执行）

1. 立刻在 TuShare 控制台重置/轮换 Token。
2. 仅在本机 `.env` 更新 `TUSHARE_TOKEN`，不要写入任何文档或代码。
3. 检查最近提交与报告文件，确认无明文 Token 残留。
4. 重新运行最小连接验证脚本，确认新 Token 可用。

### 7.2 最佳实践 ✅

1. **使用Config类**: 统一通过 `Config.from_env()` 加载配置

2. **仓库层封装**: 数据获取逻辑封装在Repository层

3. **错误处理**: 捕获并记录TuShare API调用异常

4. **频率控制**: 合理安排批量数据更新任务，避免不必要的高频调用

5. **数据缓存**: 利用Parquet存储减少重复API调用

---

## 八、技术支持

### 官方资源

- **官方文档**: [https://tushare.pro/document/2](https://tushare.pro/document/2)

- **积分与频次权限对应表**: [https://tushare.pro/document/1?doc_id=290](https://tushare.pro/document/1?doc_id=290)

- **API 积分要求说明**: [https://tushare.pro/document/1?doc_id=108](https://tushare.pro/document/1?doc_id=108)

### 项目文档

- [EmotionQuant项目指南](../../../CLAUDE.md)

- [A股规则与TuShare映射](../astock-rules-handbook.md)

- [数据模型规范](../../design/data-layer/data-layer-data-models.md)

- [API接口规范](../../design/data-layer/data-layer-api.md)

---

**声明**：本站提供的相应接口服务，所有数据产权归属于其互联网最原始出处，数据仅作为分析、研究与学习之用。任何您私自基于该数据的商业应用或决策遭受的损失，本网站不负任何责任！使用即代表您同意本声明！
