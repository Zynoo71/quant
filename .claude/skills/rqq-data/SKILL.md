---
name: rqq-data
description: >-
  Fetch and assemble Chinese A-share / fund / index quant data through the `rqq`
  CLI (a stable wrapper over Ricequant RQData). Covers daily & minute prices,
  ticks, PIT financials, shares/dividends/splits, ST/suspension, capital flows
  (北上资金/陆股通, 两融, 龙虎榜, 大宗交易, ETF 份额), factor values, consensus
  estimates (一致预期), index components/weights/indicators, fund holdings &
  allocations, announcements/调研, news, plus composed multi-source research
  snapshots. Use this skill whenever the user wants Chinese-market data — stock
  prices, financial statements, fund flows, factor exposures, index constituents,
  fund positions, 龙虎榜, 北上资金, ETF 规模, 一致预期, 公告/调研 — or wants to
  build research tables from RQData, even if they never say "rqq" or "RQData"
  (e.g. "取一下 600519 的行情", "看看贵州茅台的 PIT 财务", "沪深300 的成分股权重",
  "最近北上资金流向"). Do NOT use for non-Chinese markets, for backtesting /
  factor-strategy / live trading (not built yet), or when the user only wants
  analysis on data they already have.
---

# rqq — Ricequant RQData CLI

`rqq` is a single, stable command entry point over Ricequant's RQData for A-share
quant research. It wraps ~60 RQData functions ("datasets"), bundles them into
module "scenarios", and composes multi-source "business tables" — all as plain
CLI calls that return readable output. This skill is the data layer: fetch and
assemble data. It does not do factors-as-strategy, backtesting, or trading.

## How to invoke

Use `rqq …` if it is installed as a global tool (`uv tool install`), or
`uv run rqq …` from inside the `rqsdk_quant` repo. The examples below write `rqq`;
substitute `uv run rqq` if a bare `rqq` is not found.

## Step 1 — discover the catalog before guessing

Always start a data task by running **`rqq help`** once. It prints, in one shot,
every command plus all datasets / scenarios / business tables with their
parameters, required fields and defaults. This is the source of truth — do not
guess dataset or parameter names from memory.

```
rqq help                 # full reference, markdown (best for reading)
rqq help --format json   # same content, machine-parseable
```

If you need the precise schema for one thing right before calling it:

```
rqq data describe <dataset>           # one dataset's function/required/defaults
rqq data scenario plan <name> --ids …  # preview a scenario; marks missing params
rqq data business plan <name> --ids …  # preview a business table's components
```

`plan` is especially useful: it tells you which steps are ready and which lack
required parameters *without* spending any quota.

## Choosing a command

Pick by what the user wants, then confirm params via `describe`/`plan`:

| User wants | Command |
| --- | --- |
| Know what data exists | `rqq data list` (filter `--category market\|financial\|fund\|...`) |
| One atomic dataset (price, financials, factor, capital-flow, …) | `rqq data get <dataset> …` |
| A ready-made multi-source table (company quality, capital confirmation, research monitor, fund position, consensus, index strength, news) | `rqq data build <business-dataset> …` |
| All raw tables for one research module, written to files | `rqq data generate <scenario> …` |
| An rqdatac function not yet wrapped | `rqq data call <fn> --args '[…]' --kwargs '{…}'` |
| Connection / account info, remaining quota | `rqq data info`, `rqq data quota` |

`data get` is an alias of `data fetch`; `data build` is an alias of
`data business build`. Dataset categories: master, calendar, market, factor,
financial, equity, industry, event, money-flow, etf, fund, consensus, index, news.

## Output conventions

- **Default output is markdown** — tabular results render as GFM tables, nested
  metadata as sectioned key-value blocks. This is what you should read.
- Add **`--format json`** only when you need to parse the result programmatically;
  `--format csv` for spreadsheet-style data.
- Add **`-o PATH`** (`--output`) to write to a file instead of stdout.
- Parameter names are uniform across every command: `--ids` (space- or
  comma-separated order_book_ids), `--start`/`--end`/`--date` in `YYYY-MM-DD`,
  `--start-quarter`/`--end-quarter`/`--quarter` in `YYYYqN` (e.g. `2023q4`),
  `--fields`/`--factor` comma-separated, `--fiscal-year` an int. A-share & index
  codes carry the exchange suffix (`000001.XSHE`, `600519.XSHG`, `000300.XSHG`);
  fund-plugin codes are bare (`000003`). **Quote values** in the shell, single
  quotes are safest.
- One-off rqdatac kwargs that have no flag: `--param key=value` (repeatable) or
  `--params '<json>'`.

## The license is the human's job — never handle the secret

`rqq` needs a Ricequant license, configured **once by the human** and stored at
`~/.rqq/credentials` (or via the `RQDATAC2_CONF` env var). You must not ask for,
paste, log, or commit a license key.

- Check status (redacted): `rqq license info`.
- If a data call fails with *"no valid Ricequant license is configured"*, **stop
  and tell the user** to run `rqq license -l '<their_license_key>'` themselves
  (or set `RQDATAC2_CONF`). Do not attempt to set it yourself with a guessed or
  user-pasted secret inside your command.

## Respect the data quota

RQData is metered. Keep requests narrow so you don't burn the user's quota:
specific `--ids`, short date ranges, only the `--fields` you need. Before a large
pull, you can check `rqq data quota`. Don't fetch a whole market or multi-year
minute data unless the user explicitly asks and accepts the cost.

## What rqq can and can't do

- **Can**: fetch/aggregate/compose A-share, fund and index data — prices,
  financials, equity actions, fund flows, factors, consensus, index data, fund
  holdings, events/news; and write module datasets or composed snapshots.
- **Can't (yet)**: factor-strategy scoring, backtesting, live trading, and
  non-Chinese markets. If asked, say it's out of scope for this tool.
- **Not in RQData** (flagged as `external_inputs` in generated manifests):
  patents, supply-chain / 产业链 maps, customer-certification, orders/招标, and
  full research-report text. These need an external source — don't fabricate them.

## When something fails — recovery playbook

- **Exit code 2** = an expected error you can fix yourself:
  - `Unknown dataset/scenario/business dataset …` → you used a wrong name; run
    `rqq data list` / `rqq data scenario list` / `rqq data business list` (or
    `rqq help`) and retry with a valid name.
  - `Dataset \`X\` requires: …` → add the missing parameters (see
    `rqq data describe X`).
  - `--param must use KEY=VALUE` / `--params must be a JSON object` → fix syntax.
  - `no valid Ricequant license …` → license issue; hand back to the user (above).
- **Exit code 1** = an unexpected error. Re-run with `RQQ_DEBUG=1` prefixed to get
  a full traceback before deciding what's wrong.
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

**Factor values**
```
rqq data get factor --ids 000001.XSHE --factor pe_ratio_ttm,pb_ratio_lf --start 2024-01-02 --end 2024-01-03
```

**Capital flows / 北上 / 两融**
```
rqq data get capital-flow    --ids 000001.XSHE --start 2024-01-02 --end 2024-01-03
rqq data get stock-connect   --ids 000001.XSHE --start 2024-01-02 --end 2024-01-03
rqq data get securities-margin --ids 000001.XSHE --start 2024-01-02 --end 2024-01-03
```

**Index components & weights**
```
rqq data get index-components --ids 000300.XSHG --date 2024-01-03
rqq data get index-weights    --ids 000300.XSHG --date 2024-01-03
```

**A ready-made research snapshot (multi-source wide table)**
```
rqq data build research-monitor-snapshot --ids 000001.XSHE 600519.XSHG --start 2024-01-01 --end 2024-01-31
```

**Need it as JSON to post-process**
```
rqq data get price --ids 600519.XSHG --start 2024-01-02 --end 2024-01-03 --format json
```

When unsure which dataset or which parameters, the fastest path is always:
`rqq help` → `rqq data describe <dataset>` (or `… plan <name>`) → the real call.
