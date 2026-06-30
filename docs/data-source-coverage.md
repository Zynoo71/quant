# 设计数据源与当前 API 覆盖检查

检查日期：2026-06-29

检查对象：

- 原始设计的数据需求（内部设计文档，未随仓库发布）
- 当前 SDK：`rqdatac==3.5.3.1`，`rqdatac-fund==1.0.43`
- 当前 CLI：本仓库 `rqq data fetch/generate/business`
- 官方文档入口：
  - RQData A 股模块：https://www.ricequant.com/doc/rqdata/python/stock-mod
  - RQData 基金/ETF模块：https://www.ricequant.com/doc/rqdata/python/fund-mod
  - RQData 通用 Python 文档：https://www.ricequant.com/doc/rqdata/python

## 总结

按原 PDF 的数据需求看，当前 RQData/RQSDK 可以覆盖大部分“市场结构化数据”，包括 A 股行情、股票基础、财务、业绩预告、公告、投资者问答/关系活动、北上/陆股通、资金流、ETF 份额、两融、龙虎榜、大宗交易、基金持仓、指数成分和指数权重。

当前不能只靠 RQData 完整覆盖的是“产业认知证据层”：政策、招标、专利、产业链上下游关系、卡脖子环节、核心产品、收入暴露度、研报全文、产业新闻的深度语义抽取。这些需要外部数据源、文档抓取、人工维护或 LLM/知识库处理。

当前 CLI 已补齐主要 RQData/RQSDK 结构化能力，包括此前缺口里的 4 类接口：

1. `rqdatac.fund.*` 基金持仓/资产配置/份额/净值，已封装为 `fund-*`。
2. `rqdatac.get_consensus_*` 一致预期、评级、目标价，已封装为 `consensus-*`。
3. `rqdatac.index_*` 指数成分、权重、指标，已封装为 `index-*`。
4. `rqdatac.get_current_news` 当前新闻流，已封装为 `current-news`。

## 覆盖状态口径

- `可直接拿`：SDK 有对应结构化接口，当前 CLI 也已封装。
- `SDK 可拿，CLI 已封装`：本地 SDK 有接口，小样本可调用，当前 `rqq data list` 已封装。
- `可拼装`：不是一个接口直接返回，需要用多个已封装数据集组合。
- `外部补充`：RQData 当前接口不能完整覆盖，需要其他数据源或人工/LLM处理。

## PDF 数据资源清单逐项检查

| PDF 数据类型 | PDF 用途 | RQData/RQSDK 覆盖 | 当前 CLI 覆盖 | 检查结论 |
| --- | --- | --- | --- | --- |
| A 股行情 | 价格趋势、成交额、相对强弱 | `get_price`、`current_snapshot`、`current_minute`、`get_ticks` | `price`、`current-snapshot`、`current-minute`、`ticks` | 可直接拿。小样本 `000001.XSHE` 日线返回 2 行。 |
| 财务数据 | 三高分、业绩加速度 | `get_pit_financials_ex`、`current_performance`、`performance_forecast`、`get_factor` | `financials-pit`、`current-performance`、`performance-forecast`、`factor` | 可直接拿和拼装。PIT 财务、质量因子小样本成功；某些快报/预告会因股票和日期无披露而为空。 |
| 北上资金 | 外资增持/减持趋势 | `get_stock_connect` | `stock-connect` | 可直接拿。小样本返回 2 行。 |
| 机构调研 | 机构关注度 | `get_investor_ra`、`get_investor_qa`、`get_announcement` | `investor-ra`、`investor-qa`、`announcement` | 可直接拿，但是否有数据取决于股票和日期。投资者问答、公告小样本成功；投资者关系活动在样本区间为空。 |
| 两融数据 | 交易热度与拥挤度 | `get_securities_margin` | `securities-margin` | 可直接拿。小样本返回 2 行。 |
| ETF 规模份额 | 行业资金流 | `rqdatac.etf.get_daily_units`、`etf.get_components`、`etf.get_cash_components` | `etf-daily-units`、`etf-components`、`etf-cash-components` | 可直接拿。ETF 份额和申赎成分小样本成功。 |
| 龙虎榜 | 短中期机构确认 | `get_abnormal_stocks`、`get_abnormal_stocks_detail` | `abnormal-stocks`、`abnormal-stocks-detail` | 可直接拿。列表小样本成功；个股明细会因股票未上榜而为空。 |
| 政策 | 产业证据验证 | 当前 SDK 无结构化政策库接口 | 无 | 外部补充。建议接政府网站、政策库、新闻源或文档库。 |
| 招标 | 产业证据验证 | 当前 SDK 无招标接口 | 无 | 外部补充。建议接招标平台/企业公告/政府采购数据。 |
| 专利 | 产业证据验证 | 当前 SDK 无专利接口 | 无 | 外部补充。建议接国家知识产权局、企查查/智慧芽等专利源。 |

## PDF 核心数据表逐项检查

| PDF 核心表 | 字段示例 | RQData/RQSDK 覆盖 | 当前 CLI/业务表 | 检查结论 |
| --- | --- | --- | --- | --- |
| 股票基础表 | stock_code, stock_name, industry, market_cap, listing_date | `all_instruments`、`instruments`、`get_instrument_industry`、`get_factor(market_cap_3)` | `instruments`、`instrument-industry`、`factor`、`base-universe` | 可直接拿和拼装。 |
| 产业链表 | industry_id, chain_segment, bottleneck_level, policy_support_level | 只有行业分类，不含产业链/卡点语义 | 无 | 外部补充。需要维护产业链、卡点、政策支持等业务知识表。 |
| 公司产业映射表 | stock_code, industry_id, chain_segment, revenue_exposure, core_product | 可拿行业归属，但不能拿核心产品和收入暴露 | `instrument-industry` | 部分可拿。公司-行业归属可拿；公司-产业链映射、核心产品、收入暴露需外部补充。 |
| 财务表 | revenue, net_profit, gross_margin, net_margin, roe, operating_cashflow, rd_expense_ratio | PIT 财务、快报、因子均可提供一部分 | `company-quality-snapshot` | 可拼装。原始收入利润和研发字段走 PIT；毛利率、净利率、估值/成长因子走 `get_factor` 或快报字段。 |
| 北上资金表 | holding_shares, holding_value, holding_ratio, daily_change | `get_stock_connect` | `stock-connect`、`capital-confirmation-snapshot` | 可直接拿和拼装。 |
| 机构调研表 | date, institution_count, institution_names, research_topic, question_summary | `get_investor_ra`、`get_investor_qa`、公告 | `institution-attention`、`research-monitor-snapshot` | 部分可拿。调研/问答文本可拿；机构名单和主题摘要需要字段清洗或 LLM 提取。 |
| ETF 资金表 | etf_code, fund_share, fund_size, tracking_index, related_industry | ETF 份额、申赎清单、基金接口、指数基准 | `etf-daily-units`、`etf-components`、`fund-*`、`index-*`、`fund-position-snapshot` | SDK 可拿，CLI 已封装。ETF、基金持仓、基金配置、指数基准/权重均可获取。 |
| 两融表 | financing_balance, financing_buy_amount, margin_balance_ratio | `get_securities_margin` | `securities-margin`、`capital-confirmation-snapshot` | 可直接拿。 |
| 龙虎榜表 | reason, institution_buy, institution_sell, northbound_buy, hot_money_seats | `get_abnormal_stocks`、`get_abnormal_stocks_detail` | `abnormal-stocks`、`abnormal-stocks-detail` | 可直接拿。 |
| 价格趋势表 | close, volume, turnover, ma20, ma60, relative_strength_hs300 | `get_price`、`get_turnover_rate`、指数接口 | `price-trend`、`research-monitor-snapshot`、`index-relative-strength-snapshot` | 可拼装。收盘价、成交量、换手率、指数成分/权重/指标可直接拿；MA、相对强弱需要本地计算。 |
| AI 摘要表 | event_type, summary, sentiment_score, impact_score, source_url | RQData 只提供部分原文/新闻/公告源 | 当前 CLI 不内置 LLM 调用；可提供公告/问答/新闻输入表 | 需要应用层或外部模型生成。公告/问答/新闻可作为输入，摘要、情绪、影响分需外部处理并入库。 |

## PDF Agent 数据需求逐项检查

| Agent | 数据需求 | API 覆盖 | 当前缺口 |
| --- | --- | --- | --- |
| 产业链 Agent | 政策、招标、新闻、研报、公告、产业链变化 | 公告可拿；当前新闻有 `current-news`；研报全文、政策、招标、产业链无完整结构化接口 | 需要研报/政策/招标外部源和产业链知识库；新闻与证券/产业匹配需要 LLM 或规则层。 |
| 基本面 Agent | 财报、公告、业绩预告、收入、利润、毛利率、订单、产能 | 财报、公告、预告、财务因子可拿 | 订单、产能需要公告/研报/招标文本抽取或外部源。 |
| 机构关注 Agent | 调研、研报、机构名单、盈利预测变化 | 调研/问答、一致预期、目标价可拿 | 研报全文不足；观点摘要和主题命中需要外部研报源或 LLM。 |
| 资金流 Agent | 北上、ETF、两融、龙虎榜、基金持仓 | 北上、ETF、两融、龙虎榜、基金持仓、基金配置均已封装 | 基金持仓解释和行业资金归因需要业务拼装/计算。 |
| 价格趋势 Agent | 行业突破、龙头强弱、成交额变化、高位滞涨 | 个股行情、换手率、指数成分/权重/指标均已封装 | MA、突破、相对强弱、高位滞涨需要本地计算。 |
| 组合风控 Agent | 仓位、集中度、回撤、估值分位、事件风险 | 回撤、估值分位可基于行情/因子计算；事件源来自公告/新闻 | 仓位和组合交易记录是内部数据；事件风险需要 LLM/规则层。 |

## 已补齐的接口

这些接口已经补进 `datasets.py`，并提供 `rqq data fetch` 入口。

### 基金持仓与基金配置

本地验证 `rqdatac.fund` 可用，基金代码使用不带交易所后缀的基金代码，例如 `000003`：

- `fund-instruments` -> `fund.all_instruments`
- `fund-daily-units` -> `fund.get_daily_units`
- `fund-holdings` -> `fund.get_holdings`
- `fund-stock-change` -> `fund.get_stock_change`
- `fund-asset-allocation` -> `fund.get_asset_allocation`
- `fund-industry-allocation` -> `fund.get_industry_allocation`
- `fund-nav` -> `fund.get_nav`
- `fund-benchmark` -> `fund.get_benchmark`

小样本验证：

- `fund.get_holdings('000003', date='2023-12-31')` 返回 69 行。
- `fund.get_stock_change('000003', '2023-01-01', '2024-01-03')` 返回 80 行。
- `fund.get_asset_allocation('000003', date='2023-12-31')` 返回 1 行。

### 一致预期与目标价

SDK 有以下接口：

- `consensus-indicator` -> `get_consensus_indicator`
- `consensus-price` -> `get_consensus_price`
- `consensus-comp-indicators` -> `get_consensus_comp_indicators`
- `consensus-market-estimate` -> `get_consensus_market_estimate`
- `consensus-industry-rating` -> `get_consensus_industry_rating`
- `consensus-industries` -> `all_consensus_industries`

小样本验证：

- `get_consensus_price('000001.XSHE', '2024-01-02', '2024-01-03')` 返回 1 行。
- `get_consensus_comp_indicators('000001.XSHE', '2024-01-02', '2024-01-31')` 返回 22 行。

### 指数和相对强弱

SDK 有以下接口：

- `index-components` -> `index_components`
- `index-weights` -> `index_weights`
- `index-indicator` -> `index_indicator`
- `index-weights-ex` -> `index_weights_ex`
- `index-factor-exposure` -> `get_index_factor_exposure`

小样本验证：

- `index_components('000300.XSHG', date='2024-01-03')` 返回 300 个成分。
- `index_weights('000300.XSHG', date='2024-01-03')` 返回 300 个权重。
- `index_indicator('000300.XSHG', '2024-01-02', '2024-01-03')` 返回 2 行。

### 新闻流

SDK 有 `get_current_news(n=None, start_time=None, end_time=None, channels=None)`，已封装为 `current-news`。

小样本验证：

- `get_current_news(n=3)` 返回 DataFrame，但不是按股票代码查询，需要下游做关键词/证券匹配。

## 当前已封装业务表与覆盖关系

| 业务表 | 覆盖 PDF 模块 | 已覆盖 | 主要缺口 |
| --- | --- | --- | --- |
| `company-quality-snapshot` | 公司基本面层 | PIT 财务、质量因子、财务快报、业绩预告、预约披露日、股东数据 | 订单、产能、客户认证、专利、核心产品、收入暴露度。 |
| `capital-confirmation-snapshot` | 资金流层 | 资金流、陆股通、两融、龙虎榜、大宗交易 | 基金持仓归因由 `fund-position-snapshot` 补充。 |
| `research-monitor-snapshot` | 每日监控/AI 决策层 | 行情、换手、ST/停牌、公告、投资者问答/关系、资金流、陆股通、两融 | AI 摘要待补。 |
| `fund-position-snapshot` | 资金流层 / 基金持仓 | 基金份额、持仓、持仓变化、资产配置、行业配置、净值、基准 | 持仓明细进一步聚合需要下游计算。 |
| `consensus-attention-snapshot` | 机构关注层 / 一致预期 | 目标价、一致预期综合指标、财务预测指标 | 研报全文和观点摘要需外部源/LLM。 |
| `index-relative-strength-snapshot` | 价格趋势层 / 指数相对强弱 | 指数指标、成分、权重 | 相对强弱、MA、突破信号需下游计算。 |
| `event-news-snapshot` | AI 决策层 / 新闻事件 | 当前新闻流 | 新闻与证券/产业匹配、摘要和影响分需下游处理。 |

## 建议补齐顺序

1. 建立外部证据表：
   - `industry_chain`
   - `company_industry_mapping`
   - `policy_event`
   - `tender_event`
   - `patent_event`
   - `research_report_document`
2. 增加本地特征计算：MA20/MA60、相对强弱、突破、高位滞涨、基金持仓聚合、新闻证券匹配。
3. 再进入评分层：产业卡点分、公司三高分、机构关注分、资金确认分、趋势分、拥挤风险分。
