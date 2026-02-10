# TuShare 专题数据索引（结构化）

**版本**: v1.0
**最后更新**: 2026-02-04
**来源**: `EmotionQuant_alpha可用tushare专题数据.txt`（原始清单）
**定位**: 参考索引（以 TuShare 官方文档为准）

---

## 1. 打板专题

| 接口 | 说明 | 备注 |
| --- | --- | --- |
| limit_list_ths | 同花顺涨跌停榜单 | 历史数据自 20231101 |
| limit_list_d | 涨跌停/炸板列表 | 不含 ST 统计 |
| limit_step | 连板天梯 | 连板晋级结构 |
| limit_cpt_list | 最强板块统计 | 概念轮动 |
| stk_auction | 当日集合竞价 | 9:25~9:29 可获取当日 |
| kpl_list | 开盘啦榜单 | 次日 8:30 更新 |
| kpl_concept | 题材库 | 源站改版后暂无新增 |
| kpl_concept_cons | 题材成分 | 与题材库配套 |

---

## 2. 资金流向

| 接口 | 说明 | 备注 |
| --- | --- | --- |
| moneyflow_hsgt | 沪深港通资金流向 | 官方不再发布，仅历史 |
| moneyflow | 个股资金流向 | 大单/小单 |
| moneyflow_ths | 同花顺资金流向 | 盘后更新 |
| moneyflow_cnt_ths | 概念板块资金流向 | 同花顺 |
| moneyflow_ind_ths | 行业资金流向 | 同花顺 |

---

## 3. 融资融券

| 接口 | 说明 |
| --- | --- |
| margin | 融资融券交易汇总 |
| margin_detail | 融资融券交易明细 |

---

## 4. 行情数据（常用）

| 接口 | 说明 |
| --- | --- |
| daily | A股日线行情 |

---

## 5. 使用说明

- 本索引仅做功能归类与快速检索，具体字段与权限以 TuShare 官方文档为准。
- 需要完整原始记录请查阅：`EmotionQuant_alpha可用tushare专题数据.txt`。

---

## 6. 关联文档

- [tushare-config.md](./tushare-config.md)
- [tushare-config-5000-官方.md](./tushare-config-5000-官方.md)
- [tushare-config-10000.md](./tushare-config-10000.md)
