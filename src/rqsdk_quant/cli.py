from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from . import __version__
from .datasets import PARAM_INFO, describe_dataset, list_datasets, param_description
from .errors import CliError
from .output import write_output


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
  rqq license -l '<key>'    set license (once)       rqq help                full reference
  rqq data list             list datasets            rqq data describe <ds>  params + example
  rqq data get price --ids 000001.XSHE --start 2024-01-02 --end 2024-01-03

One atomic RQData call per dataset. Output is markdown by default (--format json for machines).
"""

_DATA_EPILOG = """\
Tips:
  list datasets in one module?      rqq data list --category fund-mod
  not sure which params a dataset takes?   rqq data describe <dataset>
  want the whole catalog in one call?      rqq help
  need a one-off rqdatac kwarg?            --param KEY=VALUE   (or --params '<json>')
  function not wrapped yet?                rqq data call <dotted.fn> --kwargs '<json>'
Output defaults to markdown; add --format json for machine parsing.
"""

_FETCH_EPILOG = (
    "Params are dataset-specific. Run `rqq data describe <dataset>` for that dataset's "
    "params (with descriptions), required fields and a runnable example; or `rqq help` "
    "for the whole catalog. Any rqdatac kwarg without a flag: --param KEY=VALUE / --params '<json>'."
)


class _HintingParser(argparse.ArgumentParser):
    """Appends a recovery hint when argparse rejects an unrecognized flag, so an
    LLM knows to check `describe` or use the --param escape hatch. Subparsers
    inherit this class (argparse's parser_class defaults to type(self))."""

    def error(self, message: str):  # noqa: D401
        if "unrecognized arguments" in message:
            message += (
                "\n参数随数据集而定：用 `rqq data describe <dataset>` 查该数据集支持的参数；"
                "\n未列出的 rqdatac 参数用 --param KEY=VALUE（或 --params '<json>'）传入。"
            )
        super().error(message)


def build_parser() -> argparse.ArgumentParser:
    parser = _HintingParser(
        prog="rqq",
        description="A CLI over Ricequant RQData: one command per atomic rqdatac data call.",
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
        help="Output a full reference of all datasets, parameters and required fields.",
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


def _add_data_parser(subparsers: Any) -> None:
    data = subparsers.add_parser(
        "data",
        help="Fetch data from RQData.",
        description="Fetch atomic datasets from RQData. Run `rqq help` for the full reference.",
        epilog=_DATA_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    data_sub = data.add_subparsers(dest="data_command")

    data_help = data_sub.add_parser("help", help="Alias for top-level `help`; output the full reference.")
    _add_common_output(data_help)
    data_help.set_defaults(handler=_handle_help)

    list_parser = data_sub.add_parser("list", help="List supported datasets (filter with --category <module>).")
    list_parser.add_argument("--category", help="Filter by official module slug, e.g. fund-mod, futures-mod.")
    _add_common_output(list_parser)
    list_parser.set_defaults(handler=_handle_data_list)

    describe = data_sub.add_parser("describe", help="Describe a dataset: params, required fields, rqdatac function.")
    describe.add_argument("dataset", help="Dataset name from `rqq data list`.")
    _add_common_output(describe)
    describe.set_defaults(handler=_handle_data_describe)

    fetch = data_sub.add_parser("fetch", help="Fetch a dataset.", epilog=_FETCH_EPILOG)
    fetch.add_argument("dataset", help="Dataset name from `rqq data list`.")
    _add_fetch_options(fetch)
    _add_common_output(fetch)
    fetch.set_defaults(handler=_handle_data_fetch)

    get = data_sub.add_parser("get", help="Alias for `fetch`.", epilog=_FETCH_EPILOG)
    get.add_argument("dataset", help="Dataset name from `rqq data list`.")
    _add_fetch_options(get)
    _add_common_output(get)
    get.set_defaults(handler=_handle_data_fetch)

    info = data_sub.add_parser("info", help="Show rqdatac connection and account information.")
    _add_common_output(info)
    info.set_defaults(handler=_handle_data_info)

    quota = data_sub.add_parser("quota", help="Show rqdatac user quota.")
    _add_common_output(quota)
    quota.set_defaults(handler=_handle_data_quota)

    call = data_sub.add_parser("call", help="Call any rqdatac function by dotted name (escape hatch).")
    call.add_argument("function", help="Function name, for example get_price or fund.get_nav.")
    call.add_argument("--args", help="JSON array of positional arguments.")
    call.add_argument("--kwargs", help="JSON object of keyword arguments.")
    _add_common_output(call)
    call.set_defaults(handler=_handle_data_call)


# Common flags surfaced for every fetch. The long tail of per-function params
# rides --param KEY=VALUE / --params '<json>'. Each entry: (dest, nargs, type).
_STR_FLAGS = [
    ("ids", "+", None),       # also accepts comma-separated
    ("start", None, None),
    ("end", None, None),
    ("date", None, None),
    ("market", None, None),
    ("type", None, None),
    ("fields", None, None),
    ("frequency", None, None),
    ("adjust_type", None, None),
    ("factor", None, None),
    ("factors", None, None),
    ("universe", None, None),
    ("industry", None, None),
    ("industries", None, None),
    ("indexes", None, None),
    ("source", None, None),
    ("to", None, None),
    ("types", None, None),
    ("sides", None, None),
    ("statements", None, None),
    ("interval", None, None),
    ("start_quarter", None, None),
    ("end_quarter", None, None),
    ("quarter", None, None),
    ("info_date", None, None),
    ("date_rule", None, None),
    ("underlying", None, None),
    ("start_time", None, None),
    ("end_time", None, None),
    ("channels", None, None),
]
_INT_FLAGS = ["level", "n", "fiscal_year", "report_range", "start_rank", "end_rank"]
_BOOL_FLAGS = ["skip_suspended", "adjusted", "is_total", "return_create_tm"]
KNOWN_FLAG_DESTS = (
    [name for name, _, _ in _STR_FLAGS] + _INT_FLAGS + _BOOL_FLAGS + ["expect_df"]
)

def _flag_help(dest: str) -> str:
    """Flag help = the shared param description (+ an example value when one exists).

    Sourced from datasets.PARAM_INFO so flags, `describe` and `help` never disagree.
    """
    desc = param_description(dest)
    sample = PARAM_INFO.get(dest, (None, None))[1]
    return f"{desc}（例：{sample}）" if sample else desc


def _add_fetch_options(parser: argparse.ArgumentParser) -> None:
    for dest, nargs, _ in _STR_FLAGS:
        flag = "--" + dest.replace("_", "-")
        kwargs: dict[str, Any] = {"dest": dest, "help": _flag_help(dest)}
        if nargs:
            kwargs["nargs"] = nargs
        parser.add_argument(flag, **kwargs)
    for dest in _INT_FLAGS:
        parser.add_argument("--" + dest.replace("_", "-"), dest=dest, type=int, help=_flag_help(dest))
    for dest in _BOOL_FLAGS:
        parser.add_argument("--" + dest.replace("_", "-"), dest=dest, action="store_true", default=None, help=_flag_help(dest))
    parser.add_argument("--expect-df", dest="expect_df", action="store_true", default=None, help="Force DataFrame output (default on where supported).")
    parser.add_argument("--no-expect-df", dest="expect_df", action="store_false", help="Return the raw rqdatac structure instead of a DataFrame.")
    parser.add_argument("--params", help="Extra rqdatac kwargs as a JSON object, e.g. --params '{\"market\": \"hk\"}'.")
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Extra rqdatac kwarg; repeatable. VALUE is JSON-decoded when possible, e.g. --param rule=0.",
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

    try:
        return rq_fetch_dataset(args.dataset, _fetch_params_from_args(args))
    except CliError:
        raise  # already actionable: unknown dataset / missing required / license
    except Exception as exc:
        if os.getenv("RQQ_DEBUG"):
            raise
        raise CliError(
            f"`{args.dataset}` 调用失败: {type(exc).__name__}: {exc}\n"
            f"  多为 id/字段/日期格式问题，核对: rqq data describe {args.dataset}；"
            f"RQQ_DEBUG=1 可看完整 traceback。"
        ) from exc


def _handle_data_quota(args: argparse.Namespace) -> Any:
    from .rqdata_client import rq_quota

    return rq_quota()


def _handle_data_call(args: argparse.Namespace) -> Any:
    from .rqdata_client import rq_call

    return rq_call(args.function, args.args, args.kwargs)


def _fetch_params_from_args(args: argparse.Namespace) -> dict[str, Any]:
    params = {dest: getattr(args, dest, None) for dest in KNOWN_FLAG_DESTS}
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
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return key, raw
    if isinstance(parsed, (int, float)) and not isinstance(parsed, bool):
        return key, raw  # keep numeric ids (e.g. manager_id) as strings; int params coerced downstream
    return key, parsed
