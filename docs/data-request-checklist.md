# RQQ 数据请求清单

用途：给人或外部 LLM 逐条检查当前 CLI 能请求哪些米筐数据。

约定：

- 所有命令都从项目根目录执行。
- 默认输出 JSON，方便程序读取。
- 样例股票：`000001.XSHE`、`600000.XSHG`。
- 样例指数：`000300.XSHG`。
- 样例基金/ETF：`000003`、`510300.XSHG`。如果某个代码在账号权限或日期上无数据，换成你实际使用的基金/ETF 代码即可。
- 这里写的是实际请求样例，不代表每个样例日期一定有返回行；无数据时也应返回空表或空数组，而不是 CLI 参数错误。

## 1. 需要的数据场景

| 场景 | 目标 | 优先请求 |
| --- | --- | --- |
| 基础股票池 | 证券主数据、行业、股本、ST/停牌 | `base-universe`、`instruments`、`instrument-industry` |
| 行情与交易状态 | 日线、分钟、tick、快照、换手 | `price`、`current-snapshot`、`current-minute`、`ticks`、`turnover-rate` |
| 财务与公司质量 | PIT 财务、快报、预告、披露日、股东 | `company-quality`、`company-quality-snapshot` |
| 机构关注 | 公告、投资者问答、投资者关系活动、一致预期 | `institution-attention`、`consensus-attention-snapshot` |
| 资金确认 | 资金流、北向、两融、龙虎榜、大宗交易 | `capital-confirmation`、`capital-confirmation-snapshot` |
| 基金/ETF | ETF 份额、申赎清单、基金持仓、配置、净值 | `fund-position-snapshot`、`etf-*`、`fund-*` |
| 指数与相对强弱输入 | 指数成分、权重、指标、因子暴露 | `index-relative-strength-snapshot`、`index-*` |
| 新闻事件输入 | 当前新闻流 | `event-news-snapshot`、`current-news` |
| 每日监控 | 公告、调研、行情、资金、风险输入 | `daily-monitor`、`research-monitor-snapshot` |
| 风险拥挤输入 | 涨幅、换手、两融、北向、资金背离、龙虎榜 | `risk-crowding` |

## 2. 元数据和健康检查

```bash
uv run rqq data info --format json
uv run rqq data quota --format json
uv run rqq data list --format json
uv run rqq data list --category market --format json
uv run rqq data describe price --format json
uv run rqq data scenario list --format json
uv run rqq data scenario describe company-quality --format json
uv run rqq data scenario plan company-quality --ids 000001.XSHE --start 2024-01-01 --end 2024-01-31 --start-quarter 2023q1 --end-quarter 2023q4 --format json
uv run rqq data business list --format json
uv run rqq data business describe research-monitor-snapshot --format json
uv run rqq data business plan research-monitor-snapshot --ids 000001.XSHE --start 2024-01-01 --end 2024-01-31 --format json
```

## 3. 快捷命令请求

```bash
uv run rqq data instruments --type CS --market cn --date 2024-01-02 --format json
uv run rqq data id-convert 000001.SZ 600000.SH --format json
uv run rqq data price 000001.XSHE --start 2024-01-02 --end 2024-01-05 --fields open,close,volume --format json
uv run rqq data trading-dates --start 2024-01-01 --end 2024-01-10 --format json
uv run rqq data call get_price --kwargs '{"order_book_ids":"000001.XSHE","start_date":"2024-01-02","end_date":"2024-01-05","fields":["open","close"],"expect_df":true}' --format json
uv run rqq data call user.get_quota --format json
```

## 4. 原子数据工具请求

### Master

```bash
uv run rqq data get instruments --type CS --date 2024-01-02 --format json
uv run rqq data get instrument --ids 000001.XSHE 600000.XSHG --format json
uv run rqq data get id-convert --ids 000001.SZ 600000.SH --format json
```

### Calendar

```bash
uv run rqq data get trading-dates --start 2024-01-01 --end 2024-01-10 --format json
uv run rqq data get previous-trading-date --date 2024-01-08 --n 1 --format json
uv run rqq data get next-trading-date --date 2024-01-08 --n 1 --format json
```

### Market

```bash
uv run rqq data get price --ids 000001.XSHE --start 2024-01-02 --end 2024-01-05 --fields open,high,low,close,volume,total_turnover --format json
uv run rqq data get current-snapshot --ids 000001.XSHE --format json
uv run rqq data get current-minute --ids 000001.XSHE --fields open,close,volume --format json
uv run rqq data get ticks --ids 000001.XSHE --start 2024-01-02 --end 2024-01-02 --format json
```

### Factor

```bash
uv run rqq data get factor-names --format json
uv run rqq data get factor --ids 000001.XSHE --factor gross_profit_margin_ttm,net_profit_margin_ttm,market_cap_3 --start 2024-01-02 --end 2024-01-05 --format json
```

### Equity

```bash
uv run rqq data get shares --ids 000001.XSHE --start 2024-01-01 --end 2024-03-31 --format json
uv run rqq data get dividend --ids 000001.XSHE --start 2023-01-01 --end 2024-12-31 --format json
uv run rqq data get split --ids 000001.XSHE --start 2020-01-01 --end 2024-12-31 --format json
uv run rqq data get turnover-rate --ids 000001.XSHE --start 2024-01-02 --end 2024-01-05 --format json
uv run rqq data get st --ids 000001.XSHE --start 2024-01-02 --end 2024-01-05 --format json
uv run rqq data get suspended --ids 000001.XSHE --start 2024-01-02 --end 2024-01-05 --format json
uv run rqq data get holder-number --ids 000001.XSHE --start 2023-01-01 --end 2024-12-31 --format json
uv run rqq data get main-shareholder --ids 000001.XSHE --start 2023-01-01 --end 2024-12-31 --start-rank 1 --end-rank 10 --format json
```

### Financial

```bash
uv run rqq data get financials-pit --ids 000001.XSHE --fields revenue,net_profit,cash_flow_from_operating_activities,total_rnd --start-quarter 2023q1 --end-quarter 2023q4 --format json
uv run rqq data get current-performance --ids 000001.XSHE --quarter 2023q4 --interval 1q --format json
uv run rqq data get performance-forecast --ids 000001.XSHE --info-date 2024-01-31 --format json
uv run rqq data get forecast-report-date --ids 000001.XSHE --start-quarter 2023q1 --end-quarter 2024q4 --format json
```

### Industry

```bash
uv run rqq data get instrument-industry --ids 000001.XSHE --source citics_2019 --level 1 --date 2024-01-02 --format json
uv run rqq data get industry --industry b10 --source citics_2019 --date 2024-01-02 --format json
uv run rqq data get industry-mapping --source citics_2019 --date 2024-01-02 --format json
```

### Event

```bash
uv run rqq data get announcement --ids 000001.XSHE --start 2024-01-01 --end 2024-03-31 --format json
uv run rqq data get investor-qa --ids 000001.XSHE --start 2024-01-01 --end 2024-03-31 --format json
uv run rqq data get investor-ra --ids 000001.XSHE --start 2024-01-01 --end 2024-03-31 --format json
```

### Money Flow

```bash
uv run rqq data get capital-flow --ids 000001.XSHE --start 2024-01-02 --end 2024-01-05 --frequency 1d --format json
uv run rqq data get stock-connect --ids 000001.XSHE --start 2024-01-02 --end 2024-01-05 --format json
uv run rqq data get securities-margin --ids 000001.XSHE --start 2024-01-02 --end 2024-01-05 --format json
uv run rqq data get block-trade --ids 000001.XSHE --start 2024-01-01 --end 2024-03-31 --format json
uv run rqq data get abnormal-stocks --start 2024-01-02 --end 2024-01-05 --format json
uv run rqq data get abnormal-stocks-detail --ids 000001.XSHE --start 2024-01-02 --end 2024-01-05 --format json
```

### ETF

```bash
uv run rqq data get etf-daily-units --ids 510300.XSHG --start 2024-01-02 --end 2024-01-05 --format json
uv run rqq data get etf-components --ids 510300.XSHG --date 2024-01-02 --format json
uv run rqq data get etf-cash-components --ids 510300.XSHG --start 2024-01-02 --end 2024-01-05 --format json
```

### Fund

```bash
uv run rqq data get fund-instruments --date 2024-01-02 --format json
uv run rqq data get fund-daily-units --ids 000003 --start 2024-01-02 --end 2024-01-05 --format json
uv run rqq data get fund-holdings --ids 000003 --date 2023-12-31 --format json
uv run rqq data get fund-stock-change --ids 000003 --start 2023-01-01 --end 2024-12-31 --format json
uv run rqq data get fund-asset-allocation --ids 000003 --date 2023-12-31 --format json
uv run rqq data get fund-industry-allocation --ids 000003 --date 2023-12-31 --format json
uv run rqq data get fund-nav --ids 000003 --start 2024-01-02 --end 2024-01-05 --format json
uv run rqq data get fund-benchmark --ids 000003 --format json
```

### Consensus

```bash
uv run rqq data get consensus-price --ids 000001.XSHE --start 2024-01-01 --end 2024-03-31 --format json
uv run rqq data get consensus-comp-indicators --ids 000001.XSHE --start 2024-01-01 --end 2024-03-31 --format json
uv run rqq data get consensus-indicator --ids 000001.XSHE --fiscal-year 2024 --format json
uv run rqq data get consensus-market-estimate --indexes 000300.XSHG --fiscal-year 2024 --format json
uv run rqq data get consensus-industry-rating --industries 银行 --start 2024-01-01 --end 2024-03-31 --format json
uv run rqq data get consensus-industries --format json
```

### Index

```bash
uv run rqq data get index-components --ids 000300.XSHG --date 2024-01-02 --format json
uv run rqq data get index-weights --ids 000300.XSHG --date 2024-01-02 --format json
uv run rqq data get index-weights-ex --ids 000300.XSHG --date 2024-01-02 --format json
uv run rqq data get index-indicator --ids 000300.XSHG --start 2024-01-02 --end 2024-01-05 --format json
uv run rqq data get index-factor-exposure --ids 000300.XSHG --start 2024-01-02 --end 2024-01-05 --factors beta,momentum --format json
```

### News

```bash
uv run rqq data get current-news --n 20 --channels a-stock --format json
uv run rqq data get current-news --n 20 --start-time "2024-01-02 09:00:00" --end-time "2024-01-02 15:30:00" --format json
```

## 5. 场景生成请求

```bash
uv run rqq data generate base-universe --ids 000001.XSHE 600000.XSHG --date 2024-01-02 --output-dir outputs/check/scenario --file-format json --format json

uv run rqq data generate company-quality --ids 000001.XSHE --start 2024-01-01 --end 2024-03-31 --start-quarter 2023q1 --end-quarter 2023q4 --quarter 2023q4 --output-dir outputs/check/scenario --file-format json --format json

uv run rqq data generate institution-attention --ids 000001.XSHE --start 2024-01-01 --end 2024-03-31 --output-dir outputs/check/scenario --file-format json --format json

uv run rqq data generate capital-confirmation --ids 000001.XSHE --etf-ids 510300.XSHG --start 2024-01-02 --end 2024-01-05 --output-dir outputs/check/scenario --file-format json --format json

uv run rqq data generate price-trend --ids 000001.XSHE --start 2024-01-02 --end 2024-01-05 --output-dir outputs/check/scenario --file-format json --format json

uv run rqq data generate risk-crowding --ids 000001.XSHE --start 2024-01-02 --end 2024-01-05 --output-dir outputs/check/scenario --file-format json --format json

uv run rqq data generate daily-monitor --ids 000001.XSHE --etf-ids 510300.XSHG --start 2024-01-02 --end 2024-01-05 --output-dir outputs/check/scenario --file-format json --format json
```

## 6. 业务表拼装请求

```bash
uv run rqq data build company-quality-snapshot --ids 000001.XSHE --start 2024-01-01 --end 2024-03-31 --start-quarter 2023q1 --end-quarter 2023q4 --quarter 2023q4 --output-dir outputs/check/business --file-format json --write-components --format json

uv run rqq data build capital-confirmation-snapshot --ids 000001.XSHE --start 2024-01-02 --end 2024-01-05 --output-dir outputs/check/business --file-format json --write-components --format json

uv run rqq data build research-monitor-snapshot --ids 000001.XSHE --start 2024-01-01 --end 2024-03-31 --output-dir outputs/check/business --file-format json --write-components --format json

uv run rqq data build fund-position-snapshot --ids 000003 --date 2023-12-31 --start 2024-01-02 --end 2024-01-05 --output-dir outputs/check/business --file-format json --write-components --format json

uv run rqq data build consensus-attention-snapshot --ids 000001.XSHE --start 2024-01-01 --end 2024-03-31 --fiscal-year 2024 --output-dir outputs/check/business --file-format json --write-components --format json

uv run rqq data build index-relative-strength-snapshot --ids 000300.XSHG --date 2024-01-02 --start 2024-01-02 --end 2024-01-05 --output-dir outputs/check/business --file-format json --write-components --format json

uv run rqq data build event-news-snapshot --n 20 --channels a-stock --output-dir outputs/check/business --file-format json --write-components --format json
```

## 7. 最小全量检查顺序

如果你想从少到多检查，建议按这个顺序跑：

```bash
uv run rqq data info --format json
uv run rqq data quota --format json
uv run rqq data list --format json
uv run rqq data get price --ids 000001.XSHE --start 2024-01-02 --end 2024-01-05 --fields open,close,volume --format json
uv run rqq data get financials-pit --ids 000001.XSHE --fields revenue,net_profit --start-quarter 2023q1 --end-quarter 2023q4 --format json
uv run rqq data get stock-connect --ids 000001.XSHE --start 2024-01-02 --end 2024-01-05 --format json
uv run rqq data build research-monitor-snapshot --ids 000001.XSHE --start 2024-01-01 --end 2024-03-31 --output-dir outputs/check/business --file-format json --write-components --format json
```
