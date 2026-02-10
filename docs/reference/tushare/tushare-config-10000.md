# TuShare 10000积分网关版配置

**版本**: v1.1
**最后更新**: 2026-02-04
**适用场景**: 多 IP 并发 / 网关访问
**定位**: 5000 积分配置的增强入口（数据口径保持一致）

---

## 1. 适用场景

- 多 IP 并发调用导致 IP 限制
- 需要通过网关访问 TuShare API
- 需要 10000 积分专属接口（如 `limit_list_ths`）

---

## 2. 配置项

| 配置项 | 说明 | 示例 |
| --- | --- | --- |
| TUSHARE_TOKEN | 10000 积分 Token | `{{TUSHARE_TOKEN_10000}}` |
| TUSHARE_GATEWAY_URL | 网关地址 | `{{TUSHARE_GATEWAY_URL}}` |
| TUSHARE_RATE_LIMIT | 调用频率 | `1000/分钟` |

---

## 3. 环境变量配置

```bash
TUSHARE_TOKEN={{TUSHARE_TOKEN_10000}}
TUSHARE_GATEWAY_URL={{TUSHARE_GATEWAY_URL}}
```

> 建议将真实 Token 写入 `.env`（参考 `.env.example`），避免出现在文档与仓库中。

---

## 4. 初始化示例（网关）

```python
import tushare as ts
from utils.config import Config

config = Config.from_env()
pro = ts.pro_api()

pro._DataApi__token = config.tushare_token
pro._DataApi__http_url = config.tushare_gateway_url
```

---

## 5. 验证方式

- 调用 `trade_cal` 或 `daily` 拉取样例数据
- 检查返回字段与 5000 积分口径一致

---

## 6. 注意事项

- 网关不可用时建议回退到 5000 积分配置
- 仅作为访问入口差异，数据口径保持一致

---

## 7. 关联文档

- [tushare-config.md](./tushare-config.md)
- [tushare-config-5000-官方.md](./tushare-config-5000-官方.md)
- [../astock-rules-handbook.md](../astock-rules-handbook.md)
