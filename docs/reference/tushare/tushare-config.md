# TuShare Pro API 配置指南 - 索引页

**版本**: v3.1
**最后更新**: 2026-02-04
**适用范围**: EmotionQuant项目 - 5000积分 + 10000积分双配置

---
> 安全提示：本文档中的 Token 与网关地址均为占位符，请在 `.env` 中配置真实值（参考 `.env.example`）。

## 📋 配置文件索引

EmotionQuant项目支持两套TuShare Pro API配置，请根据您的使用场景选择对应的配置文档：

### 🔹 [5000积分标准版配置](./tushare-config-5000-官方.md)

**适用场景**：

- ✅ 单IP开发环境

- ✅ 成本优先（5000积分价格更低）

- ✅ 不需要10000积分专属接口

- ✅ 官方API稳定性保障

**核心特性**：

- Token: `{{TUSHARE_TOKEN_5000}}`

- 频率限制: 500次/分钟

- IP限制: **有**（同一账号在2个以上IP同时调用会被拦截）

- 配置方式: 官方API，直接配置token即可

**查看详细配置** → [tushare-config-5000-官方.md](./tushare-config-5000-官方.md)

---

### 🔸 [10000积分网关版配置](./tushare-config-10000.md)

**适用场景**：

- ✅ 多IP并发环境（网关解决IP限制）

- ✅ 需要10000积分专属接口（如 `limit_list_ths`）

- ✅ 高频调用需求（上游支持1000次/分钟）

- ✅ 需要更高的数据访问权限

**核心特性**：

- Token: `{{TUSHARE_TOKEN_10000}}`

- 网关URL: `{{TUSHARE_GATEWAY_URL}}`

- 频率限制: ≈400次/分钟（网关）, 1000次/分钟（上游）

- IP限制: **无**（通过网关解决）

- 配置方式: 需要额外配置网关URL

- **首次使用**: 需要运行激活脚本

**查看详细配置** → [tushare-config-10000.md](./tushare-config-10000.md)

---

## 📚 专题数据索引

- [tushare-topic-index.md](./tushare-topic-index.md)

## 🔍 快速对比

| 对比项 | 5000积分（官方） | 10000积分（网关） |
| -------- | ----------------- | ------------------ |
| **Token** | `{{TUSHARE_TOKEN_5000}}` | `{{TUSHARE_TOKEN_10000}}` |
| **API源** | TuShare官方 | 第三方网关（轻知量化） |
| **网关URL** | 无 | `{{TUSHARE_GATEWAY_URL}}` |
| **频率限制** | 500次/分钟 | ≈400次/分钟（网关）<br>1000次/分钟（上游） |
| **IP并发限制** | 有（IP>2拦截） | **无** |
| **配置复杂度** | 简单 | 中等（需配置网关） |
| **首次激活** | 不需要 | **需要** |
| **专属接口** | 无 | `limit_list_ths` 等 |
| **延迟** | 直连 | +6ms（网关延迟） |
| **稳定性** | 官方保障 | 第三方网关 |
| **适用场景** | 单IP开发 | 多IP并发 |

---

## 🚀 快速开始

### 1️⃣ 如果您使用5000积分（官方API）

```python
from utils.config import Config
import tushare as ts

# 配置.env文件
# TUSHARE_TOKEN={{TUSHARE_TOKEN_5000}}

# 加载配置
config = Config.from_env()

# 初始化（官方API，无需额外配置）
pro = ts.pro_api(config.tushare_token)

# 正常使用
df = pro.daily(trade_date='20180810')
```

**详细说明** → [tushare-config-5000-官方.md](./tushare-config-5000-官方.md)

---

### 2️⃣ 如果您使用10000积分（网关API）

```python
from utils.config import Config
import tushare as ts

# 配置.env文件
# TUSHARE_TOKEN={{TUSHARE_TOKEN_10000}}

# 加载配置
config = Config.from_env()

# 初始化
pro = ts.pro_api()

# ✅ 配置第三方网关（关键步骤）
pro._DataApi__token = config.tushare_token
pro._DataApi__http_url = '{{TUSHARE_GATEWAY_URL}}'

# 正常使用
df = pro.daily(trade_date='20180810')
```

**⚠️ 首次使用需要激活Token**

运行激活脚本：
```bash
python scripts/utils/activate_tushare_token_10000.py
```

**详细说明** → [tushare-config-10000.md](./tushare-config-10000.md)

---

## 📊 EmotionQuant项目数据需求

两套配置均完全满足EmotionQuant项目的所有数据需求：

| 系统 | 数据需求 | 5000积分 | 10000积分 |
| ------ | --------- | --------- | ---------- |
| **MSS** | 市场广度数据、涨跌停统计 | ✅ 充足 | ✅ 充足 |
| **IRS** | 申万31行业分类、行业日线 | ✅ 充足 | ✅ 充足 |
| **PAS** | 个股价格行为数据 | ✅ 充足 | ✅ 充足 |
| **回测** | 历史数据、交易日历 | ✅ 充足 | ✅ 充足 |

**调用频率统计**：

- 全市场日线数据（5000+股票）：约10-20次/分钟

- 实时涨跌停监控：约5-10次/分钟

- 行业轮动数据更新：约5次/分钟

- 历史数据回测（批量）：约50-100次/分钟

**结论**：两套配置的频率限制均远超项目需求，无需担心频率不足。

---

## 🎯 如何选择配置？

### 选择5000积分的情况：

- ✅ 您在单IP环境开发（如单台电脑、单台服务器）

- ✅ 您不需要10000积分专属接口（如 `limit_list_ths`）

- ✅ 您希望使用官方API，稳定性有保障

- ✅ 您希望降低成本（5000积分价格更低）

### 选择10000积分的情况：

- ✅ 您需要多IP并发访问（如多台服务器、云服务）

- ✅ 您遇到了IP并发限制问题（IP>2拦截）

- ✅ 您需要10000积分专属接口（如 `limit_list_ths`）

- ✅ 您需要更高的频率限制（上游支持1000次/分钟）

---

## ⚠️ 重要说明

### 关于IP并发限制

**5000积分官方API限制**：

- 同一账号在**2个以上IP**同时调用会被**拦截**

- 这是TuShare官方的风控策略，无法绕过

**10000积分网关解决方案**：

- 通过第三方网关统一调用，**无IP并发限制**

- 网关到上游延迟仅6ms，数据实时同步

- 适合多IP并发场景

### 关于数据质量

两套配置的数据均来自TuShare官方数据源：

- 5000积分：直连TuShare官方API

- 10000积分：通过网关访问TuShare官方API，数据实时同步

**数据质量完全一致，无差异。**

---

## 📚 相关文档

### 配置文档

- [5000积分配置详解](./tushare-config-5000-官方.md) - 官方API配置指南

- [10000积分配置详解](./tushare-config-10000.md) - 网关版配置说明

### 项目文档

- [EmotionQuant项目指南](../../../CLAUDE.md) - 项目总览

- [A股规则与TuShare映射](../astock-rules-handbook.md) - MSS/IRS/PAS数据映射

- [数据模型规范](../../design/data-layer/data-layer-data-models.md) - 数据模型定义

- [API接口规范](../../design/data-layer/data-layer-api.md) - API接口定义

### TuShare官方

- [TuShare Pro 官方文档](https://tushare.pro/document/2)

- [积分与频次权限对应表](https://tushare.pro/document/1?doc_id=290)

- [API 积分要求说明](https://tushare.pro/document/1?doc_id=108)

### 网关服务（10000积分）

- [轻知量化网关文档](https://www.yuque.com/soku/nzpwx7/ua8axq0qpbqvrhg2)

- [网关在线率监控](https://status.xiximiao.com/status/year01)

---

## 🔧 故障排除

### 遇到IP并发限制错误？

**错误信息示例**：
```text
抱歉，您的账号在多个IP同时调用，已被系统拦截。
```

**解决方案**：

1. 确认是否在多个IP同时调用（如多台服务器、云服务）

2. 如果是，切换到 [10000积分网关配置](./tushare-config-10000.md)

3. 如果不是，检查是否有其他程序在使用同一Token

### 配置网关后仍无法访问？

**可能原因**：

1. Token未激活（10000积分首次使用需激活）

2. 网关URL配置错误

3. 网关服务暂时不可用

**解决步骤**：

1. 运行激活脚本：`python scripts/utils/activate_tushare_token_10000.py`

2. 检查网关在线率：https://status.xiximiao.com/status/year01

3. 查看详细排查步骤：[tushare-config-10000.md § 常见问题](./tushare-config-10000.md#八常见问题)

---

**最后更新**: 2026-01-09
**文档版本**: v3.0
**维护者**: EmotionQuant Team
