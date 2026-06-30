from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from . import __version__
from .business import describe_business_dataset, list_business_datasets, plan_business_dataset
from .datasets import describe_dataset, list_datasets
from .errors import CliError
from .output import write_output
from .scenarios import describe_scenario, list_scenarios, plan_scenario


def _force_utf8_io() -> None:
    # On Windows the console / a redirected pipe defaults to the locale encoding
    # (cp936/cp1252), which garbles the CLI's Chinese output (dataset descriptions,
    # help text, JSON). Force UTF-8 so output is consistent on every platform and
    # whether or not it is piped (e.g. captured by an automation tool).
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass


def main(argv: list[str] | None = None) -> None:
    _force_utf8_io()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "handler"):
        parser.print_help()
        return
    try:
        result = args.handler(args)
        if result is not None:
            write_output(result, output=getattr(args, "output", None), fmt=getattr(args, "format", "markdown"))
    except CliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    except BrokenPipeError:
        raise SystemExit(0)
    except Exception as exc:
        if os.getenv("RQQ_DEBUG"):
            raise
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


_TOP_EPILOG = """\
Quick start:
  rqq license -l '<license_key>'    configure the license (paste your key; account:password also works)
  rqq help                          one-shot reference: every command, parameter, required field, default
  rqq data list                    list all datasets (filter with --category)
  rqq data describe price          show one dataset's params / required / defaults
  rqq data get price --ids 000001.XSHE --start 2024-01-02 --end 2024-01-03
  rqq data build research-monitor-snapshot --ids 000001.XSHE --start 2024-01-01 --end 2024-01-31

Output defaults to markdown (human/LLM friendly); add --format json for machine parsing,
or -o FILE to write a file. Run `rqq help` for the full reference of every dataset,
scenario and business table (with params, required fields and defaults).
"""

_DATA_EPILOG = """\
Tips:
  not sure which params a dataset takes?   rqq data describe <dataset>
  want the whole catalog in one call?      rqq help
  preview a scenario/business before run?  rqq data scenario plan <name> / rqq data business plan <name>
  need a one-off rqdatac kwarg?            --param KEY=VALUE   (or --params '<json>')
Output defaults to markdown; add --format json for machine parsing.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rqq",
        description="A CLI over Ricequant RQData for quant research: fetch market data, aggregate it, build business tables.",
        epilog=_TOP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    _add_data_parser(subparsers)
    _add_help_parser(subparsers)
    _add_license_parser(subparsers)
    return parser


def _add_license_parser(subparsers: Any) -> None:
    license_parser = subparsers.add_parser(
        "license",
        help="Configure the Ricequant license; stored under ~/.rqq and used automatically.",
    )
    license_parser.add_argument(
        "action",
        nargs="?",
        choices=["set", "info", "clear"],
        default="set",
        help="set (default), info (show current), or clear.",
    )
    license_parser.add_argument(
        "-l",
        "--license",
        dest="license",
        help="License key, or account:password. Omit for an interactive paste prompt.",
    )
    _add_common_output(license_parser)
    license_parser.set_defaults(handler=_handle_license)


def _handle_license(args: argparse.Namespace) -> Any:
    from .rqdata_client import clear_license, license_info, set_license

    if args.action == "info":
        return license_info()
    if args.action == "clear":
        return clear_license()
    cred = args.license or _prompt_license()
    return set_license(cred)


def _prompt_license() -> str:
    try:
        cred = input("Paste your Ricequant license key (or account:password): ").strip()
    except EOFError:
        cred = ""
    if not cred:
        raise CliError("No license provided.")
    return cred


def _add_help_parser(subparsers: Any) -> None:
    help_parser = subparsers.add_parser(
        "help",
        help="Output a full reference of all data commands, parameters, required fields and defaults.",
    )
    _add_common_output(help_parser)
    help_parser.set_defaults(handler=_handle_help)


def _handle_help(args: argparse.Namespace) -> Any:
    from .reference import build_help_reference

    return build_help_reference()


def _add_common_output(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", "-o", help="Write output to a file.")
    parser.add_argument(
        "--format",
        choices=["markdown", "table", "json", "csv"],
        default="markdown",
        help="Output format. Defaults to markdown, which is the most readable for humans and LLMs.",
    )


_FETCH_EPILOG = (
    "The parameters a dataset accepts depend on the dataset. Run "
    "`rqq data describe <dataset>` for one dataset's required fields and defaults, or "
    "`rqq help` for the whole catalog. Any unwrapped rqdatac kwarg can be passed with "
    "--param KEY=VALUE or --params '<json>'."
)
_SCENARIO_EPILOG = (
    "The parameters a scenario needs depend on its steps. Run "
    "`rqq data scenario plan <scenario> ...` to preview which steps are ready and which "
    "lack required params, or `rqq help` for the full reference."
)
_BUSINESS_EPILOG = (
    "The parameters a business dataset needs depend on its components. Run "
    "`rqq data business plan <dataset> ...` to preview components and missing params, or "
    "`rqq help` for the full reference."
)


def _add_data_parser(subparsers: Any) -> None:
    data = subparsers.add_parser(
        "data",
        help="Fetch data from RQData/RQSDK.",
        description="Fetch data from RQData/RQSDK. Run `rqq help` for the full data-layer reference.",
        epilog=_DATA_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    data_sub = data.add_subparsers(dest="data_command")

    data_help = data_sub.add_parser(
        "help",
        help="Alias for top-level `help`; output the full data-layer reference.",
    )
    _add_common_output(data_help)
    data_help.set_defaults(handler=_handle_help)

    list_parser = data_sub.add_parser("list", help="List supported dataset wrappers.")
    list_parser.add_argument("--category", help="Filter by dataset category.")
    _add_common_output(list_parser)
    list_parser.set_defaults(handler=_handle_data_list)

    describe = data_sub.add_parser("describe", help="Describe a dataset wrapper.")
    describe.add_argument("dataset", help="Dataset name from `rqq data list`.")
    _add_common_output(describe)
    describe.set_defaults(handler=_handle_data_describe)

    fetch = data_sub.add_parser("fetch", help="Fetch a registered dataset.", epilog=_FETCH_EPILOG)
    fetch.add_argument("dataset", help="Dataset name from `rqq data list`.")
    _add_fetch_options(fetch)
    _add_common_output(fetch)
    fetch.set_defaults(handler=_handle_data_fetch)

    get = data_sub.add_parser("get", help="Alias for `fetch`; fetch a registered dataset.", epilog=_FETCH_EPILOG)
    get.add_argument("dataset", help="Dataset name from `rqq data list`.")
    _add_fetch_options(get)
    _add_common_output(get)
    get.set_defaults(handler=_handle_data_fetch)

    scenario = data_sub.add_parser("scenario", help="List and inspect module-oriented data scenarios.")
    scenario_sub = scenario.add_subparsers(dest="scenario_command")

    scenario_list = scenario_sub.add_parser("list", help="List supported data generation scenarios.")
    _add_common_output(scenario_list)
    scenario_list.set_defaults(handler=_handle_scenario_list)

    scenario_describe = scenario_sub.add_parser("describe", help="Describe one data generation scenario.")
    scenario_describe.add_argument("scenario", help="Scenario name from `rqq data scenario list`.")
    _add_common_output(scenario_describe)
    scenario_describe.set_defaults(handler=_handle_scenario_describe)

    scenario_plan = scenario_sub.add_parser("plan", help="Preview the datasets that a scenario would generate.", epilog=_SCENARIO_EPILOG)
    scenario_plan.add_argument("scenario", help="Scenario name from `rqq data scenario list`.")
    _add_scenario_options(scenario_plan)
    _add_common_output(scenario_plan)
    scenario_plan.set_defaults(handler=_handle_scenario_plan)

    generate = data_sub.add_parser("generate", help="Generate files for a module-oriented data scenario.", epilog=_SCENARIO_EPILOG)
    generate.add_argument("scenario", help="Scenario name from `rqq data scenario list`.")
    generate.add_argument("--output-dir", "-d", default="outputs/data", help="Directory for generated scenario files.")
    generate.add_argument("--file-format", choices=["csv", "json"], default="csv", help="Format for generated dataset files.")
    generate.add_argument("--strict", action="store_true", help="Fail if a scenario step lacks required parameters.")
    _add_scenario_options(generate)
    _add_common_output(generate)
    generate.set_defaults(handler=_handle_data_generate)

    build = data_sub.add_parser("build", help="Alias for `business build`; build a composed business dataset.", epilog=_BUSINESS_EPILOG)
    build.add_argument("dataset", help="Business dataset name from `rqq data business list`.")
    build.add_argument("--output-dir", "-d", default="outputs/business", help="Directory for generated business tables.")
    build.add_argument("--file-format", choices=["csv", "json"], default="csv", help="Format for generated business table.")
    build.add_argument("--strict", action="store_true", help="Fail if a component lacks required parameters.")
    build.add_argument("--write-components", action="store_true", help="Also write normalized latest component tables.")
    _add_scenario_options(build)
    _add_common_output(build)
    build.set_defaults(handler=_handle_business_build)

    business = data_sub.add_parser("business", help="Build composed business datasets from multiple raw datasets.")
    business_sub = business.add_subparsers(dest="business_command")

    business_list = business_sub.add_parser("list", help="List supported composed business datasets.")
    _add_common_output(business_list)
    business_list.set_defaults(handler=_handle_business_list)

    business_describe = business_sub.add_parser("describe", help="Describe one composed business dataset.")
    business_describe.add_argument("dataset", help="Business dataset name from `rqq data business list`.")
    _add_common_output(business_describe)
    business_describe.set_defaults(handler=_handle_business_describe)

    business_plan = business_sub.add_parser("plan", help="Preview component datasets for a composed business dataset.", epilog=_BUSINESS_EPILOG)
    business_plan.add_argument("dataset", help="Business dataset name from `rqq data business list`.")
    _add_scenario_options(business_plan)
    _add_common_output(business_plan)
    business_plan.set_defaults(handler=_handle_business_plan)

    business_build = business_sub.add_parser("build", help="Build a composed business dataset.", epilog=_BUSINESS_EPILOG)
    business_build.add_argument("dataset", help="Business dataset name from `rqq data business list`.")
    business_build.add_argument("--output-dir", "-d", default="outputs/business", help="Directory for generated business tables.")
    business_build.add_argument("--file-format", choices=["csv", "json"], default="csv", help="Format for generated business table.")
    business_build.add_argument("--strict", action="store_true", help="Fail if a component lacks required parameters.")
    business_build.add_argument("--write-components", action="store_true", help="Also write normalized latest component tables.")
    _add_scenario_options(business_build)
    _add_common_output(business_build)
    business_build.set_defaults(handler=_handle_business_build)

    info = data_sub.add_parser("info", help="Show rqdatac connection and account information.")
    _add_common_output(info)
    info.set_defaults(handler=_handle_data_info)

    quota = data_sub.add_parser("quota", help="Show rqdatac user quota.")
    _add_common_output(quota)
    quota.set_defaults(handler=_handle_data_quota)

    instruments = data_sub.add_parser("instruments", help="Fetch instrument master data.")
    instruments.add_argument("--type", default="CS", dest="instrument_type", help="Instrument type, for example CS.")
    instruments.add_argument("--market", default="cn", help="Market code.")
    instruments.add_argument("--date", help="Effective date.")
    _add_common_output(instruments)
    instruments.set_defaults(handler=_handle_data_instruments)

    id_convert = data_sub.add_parser("id-convert", help="Convert exchange symbols to rqdatac order_book_id.")
    id_convert.add_argument("ids", nargs="+", help="Symbols to convert, for example 000001.SZ.")
    _add_common_output(id_convert)
    id_convert.set_defaults(handler=_handle_data_id_convert)

    price = data_sub.add_parser("price", help="Fetch price data with rqdatac.get_price.")
    price.add_argument("ids", nargs="+", help="Order book ids, for example 000001.XSHE.")
    price.add_argument("--start", help="Start date.")
    price.add_argument("--end", help="End date.")
    price.add_argument("--frequency", default="1d", help="Frequency, for example 1d, 1m, 5m, tick.")
    price.add_argument("--fields", help="Comma-separated fields, for example open,close,volume.")
    price.add_argument("--adjust-type", default="pre", help="Adjust type: pre, post, none.")
    price.add_argument("--skip-suspended", action="store_true", help="Skip suspended trading days.")
    _add_common_output(price)
    price.set_defaults(handler=_handle_data_price)

    trading_dates = data_sub.add_parser("trading-dates", help="Fetch trading dates.")
    trading_dates.add_argument("--start", required=True, help="Start date.")
    trading_dates.add_argument("--end", required=True, help="End date.")
    trading_dates.add_argument("--market", default="cn", help="Market code.")
    _add_common_output(trading_dates)
    trading_dates.set_defaults(handler=_handle_data_trading_dates)

    call = data_sub.add_parser("call", help="Call any rqdatac function by dotted name.")
    call.add_argument("function", help="Function name, for example get_price or user.get_quota.")
    call.add_argument("--args", help="JSON array of positional arguments.")
    call.add_argument("--kwargs", help="JSON object of keyword arguments.")
    _add_common_output(call)
    call.set_defaults(handler=_handle_data_call)


def _add_fetch_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ids", nargs="+", help="Security order_book_id(s); space- or comma-separated. Stocks/indexes carry the exchange suffix (000001.XSHE, 600000.XSHG, 000300.XSHG); fund-plugin codes are bare (000003).")
    parser.add_argument("--start", help="Start date, ISO format YYYY-MM-DD, e.g. 2024-01-02.")
    parser.add_argument("--end", help="End date, ISO format YYYY-MM-DD, e.g. 2024-01-31.")
    parser.add_argument("--date", help="Single date, YYYY-MM-DD, e.g. 2024-01-03 (point-in-time datasets such as holdings/components/industry).")
    parser.add_argument("--market", default=None, help="Market code; defaults to cn for most datasets.")
    parser.add_argument("--type", dest="instrument_type", help="Instrument type for `instruments`, e.g. CS (A-share stock), ETF, INDX, Future.")
    parser.add_argument("--fields", help="Field list, comma-separated, e.g. open,close,volume. Valid fields are dataset-specific; see `rqq data describe <dataset>`.")
    parser.add_argument("--frequency", help="Bar frequency, e.g. 1d (default), 1m, 5m, tick.")
    parser.add_argument("--adjust-type", dest="adjust_type", help="Price adjustment: pre (default), post, or none.")
    parser.add_argument("--skip-suspended", action="store_true", default=None, help="Drop suspended trading days from price output.")
    parser.add_argument("--expect-df", dest="expect_df", action="store_true", default=None, help="Force DataFrame output where the dataset supports both (default on).")
    parser.add_argument("--no-expect-df", dest="expect_df", action="store_false", help="Return the raw rqdatac structure instead of a DataFrame.")
    parser.add_argument("--factor", help="Factor name(s) for `factor`, comma-separated, e.g. pe_ratio_ttm,pb_ratio_lf. List all via `rqq data fetch factor-names`.")
    parser.add_argument("--factor-type", dest="factor_type", help="Name-type filter for the `factor-names` catalog API.")
    parser.add_argument("--universe", help="Universe filter for `factor`, e.g. an index order_book_id like 000300.XSHG.")
    parser.add_argument("--industry", help="Industry code or name for `industry` (members of one industry), e.g. a citics_2019 code/name.")
    parser.add_argument("--source", help="Industry classification source, e.g. citics_2019 (default), sws.")
    parser.add_argument("--level", type=int, help="Industry level, 1-3 (default 1).")
    parser.add_argument("--n", type=int, help="Count/offset: trading-day offset for calendar datasets, or item count for current-news.")
    parser.add_argument("--to", help="Target code system for `id-convert`, e.g. normal.")
    parser.add_argument("--adjusted", action="store_true", default=None, help="Return adjusted values for `dividend` when supported.")
    parser.add_argument("--types", help="Type filters, comma-separated, for abnormal-stocks / abnormal-stocks-detail.")
    parser.add_argument("--sides", help="Side filters, comma-separated, for abnormal-stocks-detail.")
    parser.add_argument("--start-quarter", dest="start_quarter", help="Start financial quarter, format YYYYqN, e.g. 2023q1.")
    parser.add_argument("--end-quarter", dest="end_quarter", help="End financial quarter, format YYYYqN, e.g. 2023q4.")
    parser.add_argument("--quarter", help="Single financial quarter, format YYYYqN, e.g. 2023q4.")
    parser.add_argument("--info-date", dest="info_date", help="Announcement/info date filter, YYYY-MM-DD (performance-forecast / current-performance).")
    parser.add_argument("--statements", help="PIT statement mode for financials-pit: latest (default) or all.")
    parser.add_argument("--interval", help="Reporting interval for current-performance, e.g. 1q (default) or 5y.")
    parser.add_argument("--is-total", dest="is_total", action="store_true", default=None, help="Use the total A-share base for main-shareholder data.")
    parser.add_argument("--start-rank", dest="start_rank", type=int, help="Start rank (1-based) for main-shareholder data.")
    parser.add_argument("--end-rank", dest="end_rank", type=int, help="End rank for main-shareholder data.")
    parser.add_argument("--fiscal-year", dest="fiscal_year", type=int, help="Fiscal year (int) for consensus APIs, e.g. 2024.")
    parser.add_argument("--date-rule", dest="date_rule", help="Date rule for consensus-indicator.")
    parser.add_argument("--report-range", dest="report_range", type=int, help="Report range for consensus-comp-indicators (default 0).")
    parser.add_argument("--indexes", help="Index code(s), comma-separated, for consensus-market-estimate, e.g. 000300.XSHG.")
    parser.add_argument("--industries", help="Industry name(s)/code(s), comma-separated, for consensus-industry-rating.")
    parser.add_argument("--factors", help="Factor name(s), comma-separated, for index-factor-exposure.")
    parser.add_argument("--return-create-tm", dest="return_create_tm", action="store_true", default=None, help="Include the record create-time column for index-components.")
    parser.add_argument("--start-time", dest="start_time", help="Start timestamp for current-news, e.g. '2024-01-02 09:30:00'.")
    parser.add_argument("--end-time", dest="end_time", help="End timestamp for current-news, e.g. '2024-01-02 15:00:00'.")
    parser.add_argument("--channels", help="News channel(s), comma-separated, for current-news, e.g. a-stock,global.")
    parser.add_argument("--params", help="Extra rqdatac kwargs as a JSON object merged into the call, e.g. --params '{\"adjust_type\": \"post\"}'.")
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Extra rqdatac kwarg; repeatable. VALUE is JSON-decoded when possible, e.g. --param expect_df=false.",
    )


def _add_scenario_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ids", nargs="+", help="Stock order_book_id(s), space- or comma-separated, e.g. 000001.XSHE 600000.XSHG.")
    parser.add_argument("--etf-ids", nargs="+", help="ETF order_book_id(s) for ETF steps, e.g. 510300.XSHG (steps that need ETF codes, e.g. etf-daily-units).")
    parser.add_argument("--start", help="Start date, ISO format YYYY-MM-DD, e.g. 2024-01-02.")
    parser.add_argument("--end", help="End date, ISO format YYYY-MM-DD, e.g. 2024-01-31.")
    parser.add_argument("--date", help="Single date, YYYY-MM-DD, e.g. 2024-01-03.")
    parser.add_argument("--market", default=None, help="Market code; defaults to cn for most datasets.")
    parser.add_argument("--source", help="Industry classification source, e.g. citics_2019 (default), sws.")
    parser.add_argument("--level", type=int, help="Industry level, 1-3 (default 1).")
    parser.add_argument("--frequency", help="Bar frequency, e.g. 1d (default).")
    parser.add_argument("--adjust-type", dest="adjust_type", help="Price adjustment: pre (default), post, or none.")
    parser.add_argument("--start-quarter", dest="start_quarter", help="Start financial quarter, format YYYYqN, e.g. 2023q1.")
    parser.add_argument("--end-quarter", dest="end_quarter", help="End financial quarter, format YYYYqN, e.g. 2023q4.")
    parser.add_argument("--quarter", help="Single financial quarter, format YYYYqN, e.g. 2023q4.")
    parser.add_argument("--info-date", dest="info_date", help="Announcement/info date filter, YYYY-MM-DD.")
    parser.add_argument("--statements", help="PIT statement mode for financials-pit: latest (default) or all.")
    parser.add_argument("--interval", help="Reporting interval for current-performance, e.g. 1q (default) or 5y.")
    parser.add_argument("--n", type=int, help="Count/offset: trading-day offset, or item count for current-news.")
    parser.add_argument("--fiscal-year", dest="fiscal_year", type=int, help="Fiscal year (int) for consensus APIs, e.g. 2024.")
    parser.add_argument("--date-rule", dest="date_rule", help="Date rule for consensus-indicator.")
    parser.add_argument("--report-range", dest="report_range", type=int, help="Report range for consensus-comp-indicators (default 0).")
    parser.add_argument("--indexes", help="Index code(s), comma-separated, for consensus-market-estimate, e.g. 000300.XSHG.")
    parser.add_argument("--industries", help="Industry name(s)/code(s), comma-separated, for consensus-industry-rating.")
    parser.add_argument("--factors", help="Factor name(s), comma-separated, for index-factor-exposure.")
    parser.add_argument("--return-create-tm", dest="return_create_tm", action="store_true", default=None, help="Include the record create-time column for index-components.")
    parser.add_argument("--start-time", dest="start_time", help="Start timestamp for current-news, e.g. '2024-01-02 09:30:00'.")
    parser.add_argument("--end-time", dest="end_time", help="End timestamp for current-news, e.g. '2024-01-02 15:00:00'.")
    parser.add_argument("--channels", help="News channel(s), comma-separated, for current-news, e.g. a-stock,global.")
    parser.add_argument("--params", help="Extra rqdatac kwargs as a JSON object merged into every step, e.g. --params '{\"market\": \"cn\"}'.")
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Extra parameter; repeatable. VALUE is JSON-decoded when possible, e.g. --param level=2.",
    )


def _handle_data_info(args: argparse.Namespace) -> Any:
    from .rqdata_client import rq_info

    return rq_info()


def _handle_data_list(args: argparse.Namespace) -> Any:
    return list_datasets(args.category)


def _handle_data_describe(args: argparse.Namespace) -> Any:
    return describe_dataset(args.dataset)


def _handle_data_fetch(args: argparse.Namespace) -> Any:
    from .rqdata_client import rq_fetch_dataset

    return rq_fetch_dataset(args.dataset, _fetch_params_from_args(args))


def _handle_scenario_list(args: argparse.Namespace) -> Any:
    return list_scenarios()


def _handle_scenario_describe(args: argparse.Namespace) -> Any:
    return describe_scenario(args.scenario)


def _handle_scenario_plan(args: argparse.Namespace) -> Any:
    return plan_scenario(args.scenario, _scenario_params_from_args(args))


def _handle_data_generate(args: argparse.Namespace) -> Any:
    from .rqdata_client import rq_generate_scenario

    return rq_generate_scenario(
        name=args.scenario,
        params=_scenario_params_from_args(args),
        output_dir=args.output_dir,
        file_format=args.file_format,
        strict=args.strict,
    )


def _handle_business_list(args: argparse.Namespace) -> Any:
    return list_business_datasets()


def _handle_business_describe(args: argparse.Namespace) -> Any:
    return describe_business_dataset(args.dataset)


def _handle_business_plan(args: argparse.Namespace) -> Any:
    return plan_business_dataset(args.dataset, _scenario_params_from_args(args))


def _handle_business_build(args: argparse.Namespace) -> Any:
    from .rqdata_client import rq_build_business_dataset

    return rq_build_business_dataset(
        name=args.dataset,
        params=_scenario_params_from_args(args),
        output_dir=args.output_dir,
        file_format=args.file_format,
        strict=args.strict,
        write_components=args.write_components,
    )


def _handle_data_quota(args: argparse.Namespace) -> Any:
    from .rqdata_client import rq_quota

    return rq_quota()


def _handle_data_instruments(args: argparse.Namespace) -> Any:
    from .rqdata_client import rq_instruments

    return rq_instruments(args.instrument_type, args.market, args.date)


def _handle_data_id_convert(args: argparse.Namespace) -> Any:
    from .rqdata_client import rq_id_convert

    return rq_id_convert(args.ids)


def _handle_data_price(args: argparse.Namespace) -> Any:
    from .rqdata_client import rq_price

    fields = [field.strip() for field in args.fields.split(",") if field.strip()] if args.fields else None
    return rq_price(
        ids=args.ids,
        start=args.start,
        end=args.end,
        frequency=args.frequency,
        fields=fields,
        adjust_type=args.adjust_type,
        skip_suspended=args.skip_suspended,
    )


def _handle_data_trading_dates(args: argparse.Namespace) -> Any:
    from .rqdata_client import rq_trading_dates

    return rq_trading_dates(args.start, args.end, args.market)


def _handle_data_call(args: argparse.Namespace) -> Any:
    from .rqdata_client import rq_call

    return rq_call(args.function, args.args, args.kwargs)


def _fetch_params_from_args(args: argparse.Namespace) -> dict[str, Any]:
    params = {
        "ids": args.ids,
        "start": args.start,
        "end": args.end,
        "date": args.date,
        "market": args.market,
        "instrument_type": args.instrument_type,
        "fields": args.fields,
        "frequency": args.frequency,
        "adjust_type": args.adjust_type,
        "skip_suspended": args.skip_suspended,
        "expect_df": args.expect_df,
        "factor": args.factor,
        "factor_type": args.factor_type,
        "universe": args.universe,
        "industry": args.industry,
        "source": args.source,
        "level": args.level,
        "n": args.n,
        "to": args.to,
        "adjusted": args.adjusted,
        "types": args.types,
        "sides": args.sides,
        "start_quarter": args.start_quarter,
        "end_quarter": args.end_quarter,
        "quarter": args.quarter,
        "info_date": args.info_date,
        "statements": args.statements,
        "interval": args.interval,
        "is_total": args.is_total,
        "start_rank": args.start_rank,
        "end_rank": args.end_rank,
        "fiscal_year": args.fiscal_year,
        "date_rule": args.date_rule,
        "report_range": args.report_range,
        "indexes": args.indexes,
        "industries": args.industries,
        "factors": args.factors,
        "return_create_tm": args.return_create_tm,
        "start_time": args.start_time,
        "end_time": args.end_time,
        "channels": args.channels,
    }
    params.update(_json_object_arg(args.params, "--params"))
    for item in args.param:
        key, value = _key_value_arg(item)
        params[key] = value
    return params


def _scenario_params_from_args(args: argparse.Namespace) -> dict[str, Any]:
    params = {
        "ids": args.ids,
        "etf_ids": args.etf_ids,
        "start": args.start,
        "end": args.end,
        "date": args.date,
        "market": args.market,
        "source": args.source,
        "level": args.level,
        "frequency": args.frequency,
        "adjust_type": args.adjust_type,
        "start_quarter": args.start_quarter,
        "end_quarter": args.end_quarter,
        "quarter": args.quarter,
        "info_date": args.info_date,
        "statements": args.statements,
        "interval": args.interval,
        "n": args.n,
        "fiscal_year": args.fiscal_year,
        "date_rule": args.date_rule,
        "report_range": args.report_range,
        "indexes": args.indexes,
        "industries": args.industries,
        "factors": args.factors,
        "return_create_tm": args.return_create_tm,
        "start_time": args.start_time,
        "end_time": args.end_time,
        "channels": args.channels,
    }
    params.update(_json_object_arg(args.params, "--params"))
    for item in args.param:
        key, value = _key_value_arg(item)
        params[key] = value
    return params


def _json_object_arg(value: str | None, name: str) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise CliError(f"{name} must be a JSON object: {exc}") from exc
    if not isinstance(parsed, dict):
        raise CliError(f"{name} must be a JSON object.")
    return parsed


def _key_value_arg(value: str) -> tuple[str, Any]:
    if "=" not in value:
        raise CliError("--param must use KEY=VALUE syntax.")
    key, raw = value.split("=", 1)
    if not key:
        raise CliError("--param key cannot be empty.")
    try:
        return key, json.loads(raw)
    except json.JSONDecodeError:
        return key, raw
