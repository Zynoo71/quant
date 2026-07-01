---
name: rqq-data
description: >-
  Fetch Chinese-market quant data through the `rqq` CLI (a stable wrapper over
  Ricequant RQData). Every command is one atomic RQData call, organized by
  RQData's official modules: A股 (prices, ticks, PIT financials, shares/dividends,
  ST/suspension, capital flows 北上资金/陆股通, 两融, 龙虎榜, 大宗交易, 公告/调研),
  指数/场内基金 (index components/weights/indicators, ETF 份额/申赎),
  基金 (holdings, allocations, NAV, managers), 可转债 (转股/赎回/回售/评级),
  期货 (主力合约, 基差, 会员排名, 仓单), 期权 (greeks, contracts), 风险因子
  (factor values, 风格暴露, beta), 一致预期, 宏观/货币市场, 另类数据 (概念, 新闻).
  Use this skill whenever the user wants Chinese-market data — stock/futures/option/
  convertible/fund/index prices or fundamentals, fund flows, factor exposures,
  index constituents, fund positions, 龙虎榜, 北上资金, ETF 规模, 一致预期, 公告/调研,
  期货主力, 可转债 — or RQData data generally, even if they never say "rqq" or
  "RQData" (e.g. "取一下 600519 的行情", "看看贵州茅台的 PIT 财务", "沪深300 的成分股权重",
  "螺纹钢主力合约", "最近北上资金流向"). Do NOT use for non-Chinese markets, for
  backtesting / factor-strategy / live trading (not built yet), or when the user
  only wants analysis on data they already have.
---

# rqq — Ricequant RQData CLI

`rqq` is a single, stable command entry point over Ricequant's RQData. **Every
command is one atomic RQData call** — one CLI dataset maps to exactly one rqdatac
function — and the ~200 datasets are organized by RQData's official module
taxonomy. There is no aggregation/composition layer: this skill fetches atomic
data. It does not do factors-as-strategy, backtesting, or trading.

## How to invoke

Use `rqq …` if it is installed as a global tool (`uv tool install`), or
`uv run rqq …` from inside the `rqsdk_quant` repo. The examples below write `rqq`;
substitute `uv run rqq` if a bare `rqq` is not found.

## Step 1 — discover the catalog before guessing

Always start a data task by running **`rqq help`** once. It prints, in one shot,
every command plus all datasets (grouped by module) with their parameters and
required fields. This is the source of truth — do not guess dataset or parameter
names from memory.

```
rqq help                          # full reference, markdown (best for reading)
rqq help --format json            # same content, machine-parseable
rqq data list --category <module> # datasets in one module (slug below)
rqq data describe <dataset>       # a dataset's params (with 说明), required fields + a runnable example
```

Module slugs: `generic-api` (跨品种通用), `stock-mod` (A股), `stock-hk` (港股),
`futures-mod` (期货), `options-mod` (期权), `indices-mod` (指数/场内基金),
`fund-mod` (基金), `convertible-mod` (可转债), `risk-factors-mod` (风险因子),
`spot-goods` (现货), `repo` (货币市场), `macro-economy` (宏观经济),
`alternative-data` (另类数据：一致预期/新闻/概念).

## Choosing a command

| User wants | Command |
| --- | --- |
| Know what data exists | `rqq data list` (filter `--category <module-slug>`) |
| One dataset (price, financials, factor, fund-nav, futures-dominant, …) | `rqq data get <dataset> …` |
| The exact params a dataset needs | `rqq data describe <dataset>` |
| An rqdatac function not yet wrapped | `rqq data call <fn> --args '[…]' --kwargs '{…}'` |
| Connection / account info, remaining quota | `rqq data info`, `rqq data quota` |

`data get` is an alias of `data fetch`.

## Output conventions

- **Default output is markdown** — tabular results render as GFM tables, nested
  metadata as sectioned key-value blocks. This is what you should read.
- Add **`--format json`** only when you need to parse the result programmatically;
  `--format csv` for spreadsheet-style data. Add **`-o PATH`** to write a file.
- Parameter names are uniform across every command: `--ids` (space- or
  comma-separated order_book_ids), `--start`/`--end`/`--date` in `YYYY-MM-DD`,
  `--start-quarter`/`--end-quarter`/`--quarter` in `YYYYqN` (e.g. `2023q4`),
  `--fields`/`--factor`/`--factors` comma-separated, `--fiscal-year` an int,
  `--underlying` for futures/options (e.g. `AG`, `IF`, `510050.XSHG`). A-share &
  index codes carry the exchange suffix (`000001.XSHE`, `600519.XSHG`,
  `000300.XSHG`); fund codes are bare (`000003`). **Quote values** in the shell.
- Use `--market hk` on shared datasets for 港股 where supported.
- Any rqdatac kwarg without a dedicated flag: `--param key=value` (repeatable) or
  `--params '<json>'`.

## The license is the human's job — never handle the secret

`rqq` needs a Ricequant license, configured **once by the human** and stored at
`~/.rqq/credentials` (or via the `RQDATAC2_CONF` env var). You must not ask for,
paste, log, or commit a license key.

- Check status (redacted): `rqq license info`.
- If a data call fails with *"no valid Ricequant license is configured"*, **stop
  and tell the user** to run `rqq license -l '<their_license_key>'` themselves.
  Do not attempt to set it yourself with a guessed or user-pasted secret.

## Respect the data quota

RQData is metered. Keep requests narrow so you don't burn the user's quota:
specific `--ids`, short date ranges, only the `--fields` you need. Before a large
pull, you can check `rqq data quota`. Don't fetch a whole market or multi-year
minute data unless the user explicitly asks and accepts the cost.

## What rqq can and can't do

- **Can**: fetch atomic data across all RQData modules — A股/港股 prices & ticks,
  financials, equity actions, fund flows (北上/两融/龙虎榜/大宗), factors & risk
  exposures, index components/weights, ETF & fund holdings/NAV, 可转债, 期货, 期权,
  一致预期, 宏观/货币市场, 概念/新闻.
- **Can't (yet)**: factor-strategy scoring, backtesting, live trading, and
  multi-source aggregation/composition (removed by design). If asked, say it's
  out of scope for this tool.
- **Not in RQData**: patents, supply-chain / 产业链 maps, customer-certification,
  orders/招标, and full research-report text. These need an external source —
  don't fabricate them.

## When something fails — recovery playbook

**Read the error message — it is written to tell you the next command.** Errors are
self-describing, so usually you just do what the message says:

- **Exit code 2** = an expected input error you can fix yourself:
  - `未知数据集 \`X\`。你是不是想输: …` → wrong/typo'd name; use the suggested
    close match, or run `rqq data list` / `rqq help`.
  - `\`X\` 缺少必填参数: --a, --b` → the message also prints `rqq data describe X`
    and a **可运行示例** (runnable example); copy the example and substitute your ids.
  - `\`X\` 调用失败: <rqdatac error>` → the raw rqdatac message is kept (usually a bad
    id/field/date format); fix it against `rqq data describe X`.
  - `unrecognized arguments: --foo` → that flag isn't a dedicated one; check
    `rqq data describe X` for real params, or pass it as `--param foo=bar`.
  - `no valid Ricequant license …` → license issue; hand back to the user (above).
- **Exit code 1** = an unexpected error. Re-run with `RQQ_DEBUG=1` prefixed to get
  a full traceback (also works to see the traceback behind a `调用失败` message).
- **Empty result** is not an error — check the date range, market, and that the
  ids trade in that window. Some datasets are point-in-time (`--date`) not range.

## Worked examples

**Daily prices**
```
rqq data get price --ids 600519.XSHG --start 2024-01-02 --end 2024-01-31 --fields open,close,volume
```

**PIT financials for several quarters**
```
rqq data get financials-pit --ids 000001.XSHE --start-quarter 2023q1 --end-quarter 2023q4 --fields revenue,net_profit,gross_profit
```

**Factor values / risk exposure**
```
rqq data get factor --ids 000001.XSHE --factor pe_ratio_ttm,pb_ratio_lf --start 2024-01-02 --end 2024-01-03
rqq data get style-factor-exposure --ids 000001.XSHE --start 2024-01-02 --end 2024-01-03
```

**Capital flows / 北上 / 两融**
```
rqq data get capital-flow      --ids 000001.XSHE --start 2024-01-02 --end 2024-01-03
rqq data get stock-connect     --ids 000001.XSHE --start 2024-01-02 --end 2024-01-03
rqq data get securities-margin --ids 000001.XSHE --start 2024-01-02 --end 2024-01-03
```

**Index components & weights**
```
rqq data get index-components --ids 000300.XSHG --date 2024-01-03
rqq data get index-weights    --ids 000300.XSHG --date 2024-01-03
```

**Fund holdings & NAV** (bare fund codes)
```
rqq data get fund-holdings --ids 000003 --date 2023-12-31
rqq data get fund-nav      --ids 000003 --start 2024-01-02 --end 2024-01-05
```

**Futures main contract / 可转债**
```
rqq data get futures-dominant        --underlying AG --start 2024-01-02 --end 2024-01-31
rqq data get convertible-instruments --date 2024-01-02
```

**Need it as JSON to post-process**
```
rqq data get price --ids 600519.XSHG --start 2024-01-02 --end 2024-01-03 --format json
```

When unsure which dataset or which parameters, the fastest path is always:
`rqq help` → `rqq data describe <dataset>` → the real call.
