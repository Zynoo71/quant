from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .datasets import build_dataset_kwargs, get_dataset
from .errors import CliError
from .output import write_output
from .scenarios import PRICE_FIELDS, QUALITY_FACTOR_NAMES, QUALITY_FIELDS


@dataclass(frozen=True)
class BusinessComponent:
    name: str
    dataset: str
    description: str
    params: dict[str, Any] = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)
    id_candidates: tuple[str, ...] = ()
    drop_params: tuple[str, ...] = ()


@dataclass(frozen=True)
class BusinessDatasetSpec:
    name: str
    module: str
    description: str
    output_table: str
    components: tuple[BusinessComponent, ...]
    external_inputs: tuple[str, ...] = ()


BUSINESS_DATASETS: dict[str, BusinessDatasetSpec] = {
    "company-quality-snapshot": BusinessDatasetSpec(
        name="company-quality-snapshot",
        module="公司基本面层",
        description="把 PIT 财务、质量因子、快报、预告、股东数据拼装为公司质量快照。",
        output_table="company_quality_snapshot",
        components=(
            BusinessComponent("financials", "financials-pit", "PIT 财务字段。", params={"fields": QUALITY_FIELDS}),
            BusinessComponent("quality_factor", "factor", "质量和估值因子。", params={"factor": QUALITY_FACTOR_NAMES}),
            BusinessComponent("current_performance", "current-performance", "财务快报。"),
            BusinessComponent("performance_forecast", "performance-forecast", "业绩预告。"),
            BusinessComponent("forecast_report_date", "forecast-report-date", "预约披露日。"),
            BusinessComponent("holder_number", "holder-number", "股东户数。"),
            BusinessComponent("main_shareholder", "main-shareholder", "主要股东。"),
        ),
        external_inputs=("专利、订单、客户认证、产能壁垒和产业暴露度需要外部产业数据补充。",),
    ),
    "capital-confirmation-snapshot": BusinessDatasetSpec(
        name="capital-confirmation-snapshot",
        module="资金流层",
        description="把资金流、陆股通、两融、龙虎榜、大宗交易拼装为资金确认快照。",
        output_table="capital_confirmation_snapshot",
        components=(
            BusinessComponent("capital_flow", "capital-flow", "个股资金流。"),
            BusinessComponent("stock_connect", "stock-connect", "陆股通持股/交易。"),
            BusinessComponent("securities_margin", "securities-margin", "融资融券。"),
            BusinessComponent("block_trade", "block-trade", "大宗交易。"),
            BusinessComponent("abnormal_detail", "abnormal-stocks-detail", "龙虎榜/异动明细。"),
        ),
    ),
    "research-monitor-snapshot": BusinessDatasetSpec(
        name="research-monitor-snapshot",
        module="每日运行流程 / AI 决策层",
        description="把行情、趋势、事件、资金和风险状态拼装为每日研究监控快照。",
        output_table="research_monitor_snapshot",
        components=(
            BusinessComponent("price", "price", "日线行情。", params={"fields": PRICE_FIELDS}),
            BusinessComponent("turnover", "turnover-rate", "换手率。"),
            BusinessComponent("st", "st", "ST 状态。"),
            BusinessComponent("suspended", "suspended", "停牌状态。"),
            BusinessComponent("announcement", "announcement", "公告。"),
            BusinessComponent("investor_qa", "investor-qa", "投资者问答。"),
            BusinessComponent("investor_ra", "investor-ra", "投资者关系活动。"),
            BusinessComponent("capital_flow", "capital-flow", "资金流。"),
            BusinessComponent("stock_connect", "stock-connect", "陆股通。"),
            BusinessComponent("securities_margin", "securities-margin", "两融。"),
        ),
        external_inputs=("AI 摘要、产业卡点分、组合仓位和人工研究结论应在下游评分层补充。",),
    ),
    "fund-position-snapshot": BusinessDatasetSpec(
        name="fund-position-snapshot",
        module="资金流层 / 基金持仓",
        description="把基金份额、持仓、持仓变化、资产配置、行业配置、净值和基准拼装为基金持仓快照。",
        output_table="fund_position_snapshot",
        components=(
            BusinessComponent("fund_units", "fund-daily-units", "基金份额。"),
            BusinessComponent("fund_holdings", "fund-holdings", "基金持仓。", id_candidates=("fund_id", "order_book_id")),
            BusinessComponent("fund_stock_change", "fund-stock-change", "基金重大持仓变动。", id_candidates=("fund_id", "order_book_id")),
            BusinessComponent("fund_asset_allocation", "fund-asset-allocation", "基金资产配置。"),
            BusinessComponent("fund_industry_allocation", "fund-industry-allocation", "基金行业配置。"),
            BusinessComponent("fund_nav", "fund-nav", "基金净值。"),
            BusinessComponent("fund_benchmark", "fund-benchmark", "基金业绩基准。"),
        ),
    ),
    "consensus-attention-snapshot": BusinessDatasetSpec(
        name="consensus-attention-snapshot",
        module="机构关注层 / 一致预期",
        description="把目标价、一致预期综合指标和财务预测指标拼装为一致预期关注快照。",
        output_table="consensus_attention_snapshot",
        components=(
            BusinessComponent("consensus_price", "consensus-price", "一致预期目标价。"),
            BusinessComponent("consensus_comp", "consensus-comp-indicators", "公司一致预期综合指标。"),
            BusinessComponent("consensus_indicator", "consensus-indicator", "一致预期指标。", drop_params=("start", "end")),
        ),
        external_inputs=("研报全文、分析师观点摘要和观点命中产业卡点需要外部研报源或模型/规则层抽取。",),
    ),
    "index-relative-strength-snapshot": BusinessDatasetSpec(
        name="index-relative-strength-snapshot",
        module="价格趋势层 / 指数相对强弱",
        description="把指数指标、成分和权重拼装为指数相对强弱输入表。",
        output_table="index_relative_strength_snapshot",
        components=(
            BusinessComponent("index_indicator", "index-indicator", "指数指标。", drop_params=("date",)),
            BusinessComponent("index_components", "index-components", "指数成分。", id_candidates=("index_id",), drop_params=("start", "end")),
            BusinessComponent("index_weights", "index-weights", "指数权重。", id_candidates=("index_id",), drop_params=("start", "end")),
        ),
        external_inputs=("相对强弱、MA20/MA60、突破和高位滞涨信号需要下游特征计算。",),
    ),
    "event-news-snapshot": BusinessDatasetSpec(
        name="event-news-snapshot",
        module="AI 决策层 / 新闻事件",
        description="生成当前新闻流快照，供后续证券匹配、摘要和事件打分使用。",
        output_table="event_news_snapshot",
        components=(
            BusinessComponent("current_news", "current-news", "当前新闻流。", id_candidates=("channel",)),
        ),
        external_inputs=("新闻与证券/产业的匹配、摘要、情绪和影响分需要外部模型或规则层处理。",),
    ),
}


ID_COLUMNS = ("order_book_id", "order_book_ids", "symbol", "stock_code", "code")
DATE_COLUMNS = ("datetime", "date", "trading_date", "info_date", "announcement_date", "end_date", "quarter")


def list_business_datasets() -> list[dict[str, Any]]:
    return [
        {
            "name": spec.name,
            "module": spec.module,
            "output_table": spec.output_table,
            "description": spec.description,
        }
        for spec in BUSINESS_DATASETS.values()
    ]


def describe_business_dataset(name: str) -> dict[str, Any]:
    spec = get_business_dataset(name)
    return {
        "name": spec.name,
        "module": spec.module,
        "description": spec.description,
        "output_table": spec.output_table,
        "external_inputs": list(spec.external_inputs),
        "components": [
            {
                "name": component.name,
                "dataset": component.dataset,
                "function": get_dataset(component.dataset).function,
                "description": component.description,
                "params": component.params,
                "aliases": component.aliases,
                "id_candidates": list(component.id_candidates),
                "drop_params": list(component.drop_params),
                "required": list(get_dataset(component.dataset).required),
            }
            for component in spec.components
        ],
    }


def plan_business_dataset(name: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = get_business_dataset(name)
    params = params or {}
    return {
        "business_dataset": spec.name,
        "module": spec.module,
        "description": spec.description,
        "output_table": spec.output_table,
        "external_inputs": list(spec.external_inputs),
        "components": [_plan_component(component, params) for component in spec.components],
    }


def build_business_dataset(
    name: str,
    params: dict[str, Any],
    output_dir: str | Path,
    file_format: str,
    resolver: Callable[[str], Any],
    *,
    strict: bool = False,
    write_components: bool = False,
) -> dict[str, Any]:
    if file_format not in {"csv", "json"}:
        raise CliError("--file-format must be csv or json.")

    spec = get_business_dataset(name)
    output_path = Path(output_dir) / spec.name
    output_path.mkdir(parents=True, exist_ok=True)

    frames: list[Any] = []
    manifest: dict[str, Any] = {
        "business_dataset": spec.name,
        "module": spec.module,
        "output_table": spec.output_table,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(output_path),
        "file_format": file_format,
        "parameters": _compact_params(params),
        "external_inputs": list(spec.external_inputs),
        "components": [],
        "skipped": [],
    }

    for component in spec.components:
        component_params = _component_params(component, params)
        missing = _missing_required(component.dataset, component_params)
        if missing:
            item = {
                "component": component.name,
                "dataset": component.dataset,
                "reason": f"missing required parameters: {', '.join(missing)}",
            }
            if strict:
                raise CliError(f"Business dataset `{spec.name}` component `{component.name}` {item['reason']}.")
            manifest["skipped"].append(item)
            continue

        result = _fetch_component(component.dataset, component_params, resolver)
        frame = _latest_frame(component.name, result, params.get("ids"), component.id_candidates)
        if frame is None:
            manifest["skipped"].append(
                {
                    "component": component.name,
                    "dataset": component.dataset,
                    "reason": "empty or non-tabular result",
                }
            )
            continue

        frames.append(frame)
        component_item: dict[str, Any] = {
            "component": component.name,
            "dataset": component.dataset,
            "rows": int(len(frame)),
            "columns": list(frame.columns),
        }
        if write_components:
            component_path = output_path / f"component-{component.name}.{file_format}"
            write_output(frame, output=str(component_path), fmt=file_format)
            component_item["path"] = str(component_path)
        manifest["components"].append(component_item)

    table = _merge_frames(params.get("ids"), frames)
    table_path = output_path / f"{spec.output_table}.{file_format}"
    write_output(table, output=str(table_path), fmt=file_format)
    manifest["table_path"] = str(table_path)
    manifest["rows"] = int(len(table))
    manifest["columns"] = list(table.columns)

    manifest_path = output_path / "manifest.json"
    write_output(manifest, output=str(manifest_path), fmt="json")
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def get_business_dataset(name: str) -> BusinessDatasetSpec:
    try:
        return BUSINESS_DATASETS[name]
    except KeyError as exc:
        raise CliError(f"Unknown business dataset `{name}`. Run `rqq data business list` to see supported datasets.") from exc


def _fetch_component(dataset_name: str, params: dict[str, Any], resolver: Callable[[str], Any]) -> Any:
    spec = get_dataset(dataset_name)
    target = resolver(spec.function)
    return target(**build_dataset_kwargs(spec, params))


def _latest_frame(component_name: str, value: Any, ids: list[str] | None, id_candidates: tuple[str, ...] = ()) -> Any | None:
    pd = _load_pandas()
    frame = _to_frame(value)
    if frame is None or frame.empty:
        return None

    candidates = id_candidates or ID_COLUMNS
    id_column = _find_column(frame, candidates)
    if id_column is None:
        frame = _melt_wide_id_columns(frame, ids)
        id_column = _find_column(frame, candidates)

    if id_column is None:
        if ids and len(ids) == 1:
            if "order_book_id" in frame.columns:
                frame = frame.rename(columns={"order_book_id": "source_order_book_id"})
            frame["order_book_id"] = ids[0]
            id_column = "order_book_id"
        else:
            return None

    if id_column != "order_book_id" and "order_book_id" in frame.columns:
        frame = frame.rename(columns={"order_book_id": "source_order_book_id"})
    if id_column != "order_book_id":
        frame = frame.rename(columns={id_column: "order_book_id"})

    date_column = _find_column(frame, DATE_COLUMNS)
    if date_column:
        frame = frame.sort_values([date_column])
    latest = frame.groupby("order_book_id", dropna=False, as_index=False).tail(1)

    keep_columns = ["order_book_id"]
    if date_column and date_column in latest.columns:
        keep_columns.append(date_column)
    keep_columns.extend(column for column in latest.columns if column not in keep_columns)
    latest = latest[keep_columns]

    renamed = {}
    for column in latest.columns:
        if column == "order_book_id":
            continue
        renamed[column] = f"{component_name}__{column}"
    latest = latest.rename(columns=renamed)
    return pd.DataFrame(latest)


def _melt_wide_id_columns(frame: Any, ids: list[str] | None) -> Any:
    if not ids:
        return frame
    value_columns = [column for column in frame.columns if str(column) in set(ids)]
    if not value_columns:
        return frame
    id_vars = [column for column in frame.columns if column not in value_columns]
    return frame.melt(id_vars=id_vars, value_vars=value_columns, var_name="order_book_id", value_name="value")


def _merge_frames(ids: list[str] | None, frames: list[Any]) -> Any:
    pd = _load_pandas()
    if ids:
        merged = pd.DataFrame({"order_book_id": ids})
    elif frames:
        merged = pd.DataFrame({"order_book_id": sorted(set().union(*(set(frame["order_book_id"]) for frame in frames)))})
    else:
        merged = pd.DataFrame(columns=["order_book_id"])

    for frame in frames:
        merged = merged.merge(frame, on="order_book_id", how="left")
    return merged


def _to_frame(value: Any) -> Any | None:
    pd = _load_pandas()
    if value is None:
        return None
    if value.__class__.__name__ == "DataFrame":
        return value.reset_index()
    if value.__class__.__name__ == "Series":
        return value.reset_index()
    if isinstance(value, list):
        if not value:
            return pd.DataFrame()
        if isinstance(value[0], dict):
            return pd.DataFrame(value)
        return pd.DataFrame({"value": value})
    if isinstance(value, dict):
        if value and all(isinstance(item, dict) for item in value.values()):
            frame = pd.DataFrame.from_dict(value, orient="index").reset_index()
            return frame.rename(columns={"index": "order_book_id"})
        return pd.DataFrame([value])
    if hasattr(value, "to_dict"):
        try:
            return pd.DataFrame(value.to_dict()).reset_index()
        except Exception:
            return None
    return None


def _plan_component(component: BusinessComponent, params: dict[str, Any]) -> dict[str, Any]:
    component_params = _component_params(component, params)
    missing = _missing_required(component.dataset, component_params)
    return {
        "name": component.name,
        "dataset": component.dataset,
        "description": component.description,
        "status": "ready" if not missing else "skipped",
        "missing": missing,
        "params": _compact_params(component_params),
    }


def _component_params(component: BusinessComponent, params: dict[str, Any]) -> dict[str, Any]:
    merged = dict(params)
    for public_name, source_name in component.aliases.items():
        if params.get(source_name) is not None:
            merged[public_name] = params[source_name]
    for name in component.drop_params:
        merged.pop(name, None)
    merged.update(component.params)
    return merged


def _missing_required(dataset_name: str, params: dict[str, Any]) -> list[str]:
    spec = get_dataset(dataset_name)
    merged = {**spec.defaults, **{key: value for key, value in params.items() if value is not None}}
    return [name for name in spec.required if _is_empty(merged.get(name))]


def _find_column(frame: Any, candidates: tuple[str, ...]) -> str | None:
    columns = {str(column).lower(): column for column in frame.columns}
    for candidate in candidates:
        if candidate in columns:
            return columns[candidate]
    return None


def _compact_params(params: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in params.items() if not _is_empty(value)}


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == []


def _load_pandas() -> Any:
    try:
        import pandas as pd
    except ImportError as exc:
        raise CliError("Business dataset composition requires pandas. Install data extras with `uv sync --extra data --group dev`.") from exc
    return pd
