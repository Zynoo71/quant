# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A CLI (`rqq`) over Ricequant's RQSDK/RQData for quant research. The goal is a single, stable command entry point that humans and external LLMs/automation can call to fetch market data, aggregate it, and produce business tables. Factors, backtesting, and trading are future work. The scenario/business modules map onto the layers of the project's original (internal) design.

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

`scripts/live_data_check.py` runs a large suite of real RQData requests and regenerates a local sample-results report (`docs/data-live-sample-results.md`, gitignored — real RQData output is not committed/redistributed) plus files under `outputs/live-data-check/`. It needs a live license.

## Architecture

The CLI is a thin argparse layer over four declarative registries. The key design choice: **datasets, scenarios, and business datasets are all data, not code** — adding a new wrapper means adding a dataclass entry, not writing a function.

- `cli.py` — argparse tree. `main()` calls the matched `handler`, then pipes the return value through `write_output`. All RQData-touching handlers import `rqdata_client` lazily so the CLI's metadata commands (`list`/`describe`/`plan`) work without rqdatac installed.
- `datasets.py` — `DATASETS: dict[str, DatasetSpec]`, the catalog of ~60 single-API wrappers. A `DatasetSpec` maps public CLI param names → rqdatac kwarg names (`param_map`), with `defaults`, `required`, `list_params` (comma-split into lists), `bool_params`. `build_dataset_kwargs()` is the one place that resolves CLI args into a real rqdatac call. This is the layer to edit when wrapping a new RQData function.
- `scenarios.py` — `SCENARIOS: dict[str, ScenarioSpec]`. A scenario is an ordered list of `ScenarioStep`s (each pointing at a dataset) that maps to one module of the design doc. `generate_scenario()` runs every step and writes one file per step plus a `manifest.json`; steps missing required params are recorded under `skipped` (or raise if `--strict`).
- `business.py` — `BUSINESS_DATASETS: dict[str, BusinessDatasetSpec]`. A business dataset fetches several component datasets and **merges them into one wide table** keyed on `order_book_id`. `_latest_frame()` does the heavy lifting: normalize any rqdatac return (DataFrame/Series/list/dict/wide-by-stock) to a frame, find the id column (`id_candidates`), take the latest row per id, and prefix every value column with `<component>__`. `_merge_frames()` left-joins all components onto the requested ids.
- `rqdata_client.py` — the only module that imports rqdatac. `init_rqdatac()` initializes the session; `_resolve_attr()` resolves dotted names like `etf.get_daily_units` or `user.get_quota`; warnings about license expiry/deprecation are suppressed and license strings are redacted from `info` output.
- `output.py` — renders any value (DataFrame, Series, list-of-dicts, dict, scalar) as `markdown` (default), `table`, `json`, or `csv`, to stdout or a file (see Conventions). Scenario/business generators call `write_output` directly per file.
- `reference.py` — `build_help_reference()` assembles the one-shot data-layer reference (commands + every dataset/scenario/business dataset with params, required fields, defaults) by reading the three registries. Backs `rqq help` / `rqq data help`; the verb list in `COMMANDS` is hand-curated for copy-pasteable examples, everything else is derived from the registries. No rqdatac import, so it works offline.
- `errors.py` — `CliError` is the one expected-error type; `main()` prints it cleanly and exits 2.

### Command surface

`rqq help` (alias `rqq data help`) dumps the whole data-layer reference in one call — use it (or point an LLM at it) before anything else. `rqq data ...` has these groups: `list`/`describe`/`fetch` (alias `get`) for datasets; `scenario list`/`describe`/`plan`/`generate` (generate also aliased as top-level `data generate`); `business list`/`describe`/`plan`/`build` (build also aliased as top-level `data build`). Plus thin convenience commands (`info`, `quota`, `instruments`, `id-convert`, `price`, `trading-dates`) and the escape hatch `data call <dotted.fn> --args/--kwargs` for any rqdatac function not yet wrapped. Top-level `rqq license [-l <key|account:password>]` (also `info`/`clear`) validates the credential via `rqdatac.init(uri=...)` and stores the connection uri under `~/.rqq/credentials`; `init_rqdatac()` reads it and passes it to `rqdatac.init(uri=...)`, falling back to the `RQDATAC2_CONF` env var. No rqsdk needed.

`--param KEY=VALUE` (repeatable, JSON-decoded when possible) and `--params '<json>'` inject extra params into any fetch/scenario/business call — use these for one-off rqdatac kwargs without editing a spec.

### Conventions

- Public param names are uniform across the whole CLI (`--ids`, `--start`, `--end`, `--date`, `--start-quarter`, …); `param_map` translates them per dataset. When adding a dataset, reuse existing public names so scenarios/business specs can share params.
- `output.py` renders any value as `markdown` (default — GFM tables for tabular results, sectioned key-value blocks for nested metadata; best for human/LLM reading), `table`, `json`, or `csv`. The CLI defaults to `markdown`; reserve `json`/`csv` for machine parsing or file output. Scenario/business data files are still written as csv/json (`--file-format`); markdown is a display-only format.
- Generated artifacts go under `outputs/` (gitignored region); every generator emits a `manifest.json` recording parameters, written files, and `skipped`/`external_inputs`. `external_inputs` flags data the design doc needs but RQData's A-share SDK does not provide (patents, orders, supply-chain maps, research-report text).
- `QUALITY_FIELDS`, `QUALITY_FACTOR_NAMES`, `PRICE_FIELDS` are defined in `scenarios.py` and reused by `business.py` — keep field lists there, not duplicated.

## Dependencies

Never edit `pyproject.toml` by hand — use `uv add` / `uv remove` (e.g. `uv add --optional <extra> <pkg>`). Two dependency tiers: core (no runtime deps) and the `data` extra (rqdatac + rqdatac-fund + pandas, all wheels — installs cleanly). License handling is native (`rqq license`, stored under `~/.rqq`), so rqsdk is no longer a dependency. Modules guard their imports so the core CLI runs without the `data` extra.
