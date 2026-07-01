# AGENT.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A CLI (`rqq`) over Ricequant's RQData for quant research. The goal is a single, stable command entry point that humans and external LLMs/automation can call to fetch market data. **Every command is one atomic rqdatac call** — one CLI dataset maps to exactly one RQData function — organized by RQData's official module taxonomy. There is deliberately **no aggregation/composition layer** (an earlier scenario/business-table layer was removed). Factors-as-strategy, backtesting, and trading are future work.

## Commands

```bash
uv sync --group dev                     # install dev deps (no rqdatac)
uv run pytest -q                        # run all tests
uv run pytest tests/test_cli.py::test_data_fetch_uses_dataset_registry  # single test
uv run rqq --help                       # run the CLI
```

The `data` extra (rqdatac + rqdatac-fund + pandas) installs cleanly from wheels — no build hacks:

```bash
uv sync --extra data                    # everything needed to fetch data
uv run rqq license -l "<license_key>"   # validate + store the license under ~/.rqq
```

The CLI does not use `rqsdk` at all (license handling is native). There is a leftover empty `rqsdk = []` extra that `uv` can't delete on its own; it is harmless.

There is no linter/formatter configured. Set `RQQ_DEBUG=1` to make the CLI re-raise full tracebacks instead of printing a one-line error.

Verification (need a live license; burn a little quota):

```bash
uv run --no-sync python scripts/gen_catalog.py --check       # catalog.py is in sync with rqdatac (offline)
uv run --no-sync python scripts/verify_all_datasets.py       # call EVERY dataset live; PASS = 0 unexpected errors
uv run --no-sync python scripts/live_data_check.py           # representative per-module smoke + sample report
```

`verify_all_datasets.py` exercises all ~211 wrappers through the real `build_dataset_kwargs` path and classifies OK / EMPTY (valid call, no rows) / ERROR / SKIP. `KNOWN_UPSTREAM_BROKEN` there lists datasets whose rqdatac function is broken upstream (verified by calling rqdatac directly) — currently empty (the deprecated + upstream-broken `get_ksh_auction_info` was dropped from the catalog; its replacement `get_auction_info` is wrapped as `auction-info`).

## Architecture

The CLI is a thin argparse layer over **one declarative catalog**. The key design choice: **the catalog is data, not code, and is generated from rqdatac's own signatures** — adding a wrapper means adding one row to a curated table and regenerating, not writing a function.

- `cli.py` — argparse tree. `main()` calls the matched `handler`, then pipes the return value through `write_output`. RQData-touching handlers import `rqdata_client` lazily so metadata commands (`list`/`describe`/`help`) work without rqdatac installed. `_add_fetch_options` exposes ~40 curated common flags (`--ids`, `--start`, …); the long tail of per-function params rides `--param KEY=VALUE` / `--params '<json>'`.
- `datasets.py` — the **model**. `DatasetSpec(name, function, category, description, params_spec)` where `params_spec` is a signature snapshot string (`"!order_book_ids start_date … expect_df:bool market"`; `!`=required, `:bool`=bool default). `param_map`/`required`/`list_params`/`bool_params`/`accepts_expect_df` are **derived** in `__post_init__` from `params_spec` + two module-level tables: `STD_PUBLIC` (the single rqdatac-name→public-name authority, e.g. `order_book_ids→ids`, `start_date→start`) and `LIST_PARAMS` (comma/space-splittable params). `build_dataset_kwargs()` is the one place that resolves CLI args into a real rqdatac call (single-id unwrap for singular `order_book_id` funcs, list splitting, bool coercion, `expect_df=True` injection). `MODULES` is the official slug→display-name map.
- `catalog.py` — **auto-generated, committed, stdlib-only.** `DATASETS: dict[str, DatasetSpec]`, ~200 entries, one literal `DatasetSpec(...)` per rqdatac data function. Never hand-edit; regenerate with the script below.
- `scripts/gen_catalog.py` — dev-only generator. Introspects the installed rqdatac + rqdatac-fund, merges the hand-curated `CURATED = {dotted_fn: (module_slug, public_name, description)}` table (**the only hand-written data**), and emits `catalog.py`. Asserts every non-excluded rqdatac function is curated (so a new SDK release surfaces as an explicit failure) and every public name is unique. `--check` mode fails if `catalog.py` is stale — run it after upgrading rqdatac.
- `rqdata_client.py` — the only module that imports rqdatac. `init_rqdatac()` initializes the session; `_resolve_attr()` resolves dotted names like `fund.get_nav` or `futures.get_dominant`; warnings about license expiry/deprecation are suppressed and license strings redacted from `info` output. Exposes `rq_info`, `rq_quota`, `rq_fetch_dataset`, `rq_call` + native license management.
- `output.py` — renders any value (DataFrame, Series, list-of-dicts, dict, scalar) as `markdown` (default), `table`, `json`, or `csv`, to stdout or a file.
- `reference.py` — `build_help_reference()` assembles the one-shot reference (curated `COMMANDS` + every dataset grouped by official module, with required/optional params and a synthesized example) by reading `DATASETS`. Backs `rqq help` / `rqq data help`. No rqdatac import, so it works offline. Per-param 中文说明 + example samples live in `datasets.PARAM_INFO` (the single source for `describe`, the `rqq help` reference and the CLI flag help); `describe`/`help` build a runnable example via `datasets.build_example`.
- `errors.py` — `CliError` is the one expected-error type; `main()` prints it cleanly and exits 2.

### Command surface

`rqq help` (alias `rqq data help`) dumps the whole reference in one call — use it (or point an LLM at it) before anything else. `rqq data ...` has: `list` (`--category <module>`), `describe` (a dataset's params with 说明, required fields and a runnable example), `fetch` (alias `get`), `info`, `quota`, and the escape hatch `data call <dotted.fn> --args/--kwargs` for any rqdatac function. Top-level `rqq license [-l <key|account:password>]` (also `info`/`clear`) validates the credential via `rqdatac.init(uri=...)` and stores the connection uri under `~/.rqq/credentials`; `init_rqdatac()` reads it, falling back to the `RQDATAC2_CONF` env var.

### Official modules (the `category` of every dataset)

`generic-api` 跨品种通用 · `stock-mod` A股 · `stock-hk` 港股 · `futures-mod` 期货 · `options-mod` 期权 · `indices-mod` 指数/场内基金 · `fund-mod` 基金 · `convertible-mod` 可转债 · `risk-factors-mod` 风险因子 · `spot-goods` 现货 · `repo` 货币市场 · `macro-economy` 宏观经济 · `alternative-data` 另类数据 · `ricequant-index` 米筐特色指数. (港股/米筐特色指数 are reached via `--market hk` / special index codes on existing datasets, so they currently have no dedicated entries.)

### Conventions

- Public param names are uniform across the whole CLI (`--ids`, `--start`, `--end`, `--date`, `--start-quarter`, …); `STD_PUBLIC` + the signature snapshot translate them per dataset. To add/rename a public name, edit `STD_PUBLIC` and regenerate.
- **Adding a new wrapper = add a row to `CURATED` in `gen_catalog.py` and run it.** Do not hand-edit `catalog.py`. After an rqdatac upgrade, run `gen_catalog.py --check`; if it fails, regenerate and review the diff.
- `output.py` renders any value as `markdown` (default — GFM tables for tabular results, sectioned key-value blocks for nested metadata; best for human/LLM reading), `table`, `json`, or `csv`. Reserve `json`/`csv` for machine parsing or file output.

## Dependencies

Never edit `pyproject.toml` by hand — use `uv add` / `uv remove` (e.g. `uv add --optional <extra> <pkg>`). Two dependency tiers: core (no runtime deps) and the `data` extra (rqdatac + rqdatac-fund + pandas, all wheels — installs cleanly). License handling is native (`rqq license`, stored under `~/.rqq`), so rqsdk is no longer a dependency. The metadata commands (`list`/`describe`/`help`) run on the core install because `catalog.py` is stdlib-only.
