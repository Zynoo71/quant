from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .datasets import build_dataset_kwargs, describe_dataset, get_dataset
from .errors import CliError
from .output import write_output


@dataclass(frozen=True)
class ScenarioStep:
    name: str
    dataset: str
    description: str
    params: dict[str, Any] = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ScenarioSpec:
    name: str
    module: str
    description: str
    doc_basis: str
    steps: tuple[ScenarioStep, ...]
    external_inputs: tuple[str, ...] = ()


QUALITY_FIELDS = [
    "revenue",
    "operating_revenue",
    "net_profit",
    "net_profit_parent_company",
    "gross_profit",
    "cash_flow_from_operating_activities",
    "total_rnd",
    "r_n_d",
    "return_on_equity_weighted_average",
]

QUALITY_FACTOR_NAMES = [
    "gross_profit_margin_ttm",
    "net_profit_margin_ttm",
    "operating_revenue_growth_ratio_ttm",
    "net_profit_growth_ratio_ttm",
    "operating_cash_flow_per_share_ttm",
    "market_cap_3",
    "pe_ratio_ttm",
    "pb_ratio_lf",
]

PRICE_FIELDS = ["open", "high", "low", "close", "volume", "total_turnover"]


SCENARIOS: dict[str, ScenarioSpec] = {
    "base-universe": ScenarioSpec(
        name="base-universe",
        module="数据层 / 公司产业映射",
        description="生成股票基础信息、行业映射、股本和交易状态数据，用于构建研究股票池。",
        doc_basis="对应原始文档的数据层、股票基础表、公司产业映射表。",
        steps=(
            ScenarioStep("instruments", "instruments", "A 股基础证券列表。"),
            ScenarioStep("industry-mapping", "industry-mapping", "行业分类映射表。"),
            ScenarioStep("instrument-industry", "instrument-industry", "个股所属行业。"),
            ScenarioStep("shares", "shares", "股本结构数据。"),
            ScenarioStep("st", "st", "ST 状态过滤。"),
            ScenarioStep("suspended", "suspended", "停牌状态过滤。"),
        ),
        external_inputs=("产业链-公司映射、核心产品、收入暴露度需要人工或外部产业数据补充。",),
    ),
    "company-quality": ScenarioSpec(
        name="company-quality",
        module="公司基本面层",
        description="生成三高筛选和业绩加速度需要的财务、业绩预告、披露日、股东结构数据。",
        doc_basis="对应原始文档的公司三高分、业绩验证、财务表。",
        steps=(
            ScenarioStep("financials-pit", "financials-pit", "PIT 财务字段快照。", params={"fields": QUALITY_FIELDS}),
            ScenarioStep("quality-factor", "factor", "毛利率、净利率、成长、现金流、估值等公共因子。", params={"factor": QUALITY_FACTOR_NAMES}),
            ScenarioStep("current-performance", "current-performance", "财务快报。"),
            ScenarioStep("performance-forecast", "performance-forecast", "业绩预告。"),
            ScenarioStep("forecast-report-date", "forecast-report-date", "定期报告预约披露日。"),
            ScenarioStep("holder-number", "holder-number", "股东户数变化。"),
            ScenarioStep("main-shareholder", "main-shareholder", "主要股东结构。"),
        ),
        external_inputs=("专利、客户认证、产能壁垒、订单和下游景气度不在 RQData 标准行情财务接口内。",),
    ),
    "institution-attention": ScenarioSpec(
        name="institution-attention",
        module="机构关注层",
        description="生成公告、投资者问答、投资者关系活动数据，用于跟踪机构关注升温。",
        doc_basis="对应原始文档的机构调研、研报覆盖、盈利预测上修。",
        steps=(
            ScenarioStep("announcement", "announcement", "公告数据。"),
            ScenarioStep("investor-qa", "investor-qa", "投资者问答。"),
            ScenarioStep("investor-ra", "investor-ra", "投资者关系活动。"),
            ScenarioStep("performance-forecast", "performance-forecast", "业绩预告变化。"),
        ),
        external_inputs=("研报正文、盈利预测一致预期通常需要 Choice/iFinD/Wind 等数据源补充。",),
    ),
    "capital-confirmation": ScenarioSpec(
        name="capital-confirmation",
        module="资金流层",
        description="生成北上/资金流、ETF 份额、两融、龙虎榜和大宗交易数据，用于判断资金确认。",
        doc_basis="对应原始文档的资金确认分、北上、ETF、两融、龙虎榜。",
        steps=(
            ScenarioStep("capital-flow", "capital-flow", "个股资金流。"),
            ScenarioStep("stock-connect", "stock-connect", "陆股通持股/交易相关数据。"),
            ScenarioStep("securities-margin", "securities-margin", "融资融券数据。"),
            ScenarioStep("block-trade", "block-trade", "大宗交易。"),
            ScenarioStep("abnormal-stocks", "abnormal-stocks", "龙虎榜/异动列表。"),
            ScenarioStep("abnormal-stocks-detail", "abnormal-stocks-detail", "龙虎榜/异动明细。"),
            ScenarioStep("etf-daily-units", "etf-daily-units", "ETF 份额变化。", aliases={"ids": "etf_ids"}),
            ScenarioStep("etf-cash-components", "etf-cash-components", "ETF 现金差额。", aliases={"ids": "etf_ids"}),
        ),
    ),
    "price-trend": ScenarioSpec(
        name="price-trend",
        module="价格趋势层",
        description="生成个股行情、换手率和交易状态数据，用于趋势确认和相对强弱计算。",
        doc_basis="对应原始文档的价格趋势表、行业突破、龙头强弱、成交额变化。",
        steps=(
            ScenarioStep("price", "price", "日线行情。", params={"fields": PRICE_FIELDS}),
            ScenarioStep("turnover-rate", "turnover-rate", "换手率。"),
            ScenarioStep("st", "st", "ST 状态。"),
            ScenarioStep("suspended", "suspended", "停牌状态。"),
        ),
        external_inputs=("行业指数相对强弱需要传入指数代码或另行维护行业指数映射。",),
    ),
    "risk-crowding": ScenarioSpec(
        name="risk-crowding",
        module="组合风控 / 拥挤撤退识别",
        description="生成高位拥挤、分歧和撤退风险判断所需的数据。",
        doc_basis="对应原始文档的一致预期期、撤退期、风险扣分和关键预警规则。",
        steps=(
            ScenarioStep("price", "price", "价格和成交额。", params={"fields": PRICE_FIELDS}),
            ScenarioStep("turnover-rate", "turnover-rate", "换手率。"),
            ScenarioStep("securities-margin", "securities-margin", "融资融券拥挤度。"),
            ScenarioStep("stock-connect", "stock-connect", "北上分歧。"),
            ScenarioStep("capital-flow", "capital-flow", "资金净流入/流出。"),
            ScenarioStep("abnormal-stocks", "abnormal-stocks", "异动列表。"),
            ScenarioStep("abnormal-stocks-detail", "abnormal-stocks-detail", "异动明细。"),
        ),
    ),
    "daily-monitor": ScenarioSpec(
        name="daily-monitor",
        module="每日运行流程",
        description="生成盘前/盘中/盘后监控需要的公告、调研、行情、资金和风险数据。",
        doc_basis="对应原始文档的每日运行流程与预警规则。",
        steps=(
            ScenarioStep("announcement", "announcement", "公告更新。"),
            ScenarioStep("investor-qa", "investor-qa", "投资者问答更新。"),
            ScenarioStep("investor-ra", "investor-ra", "投资者关系活动更新。"),
            ScenarioStep("price", "price", "行情更新。", params={"fields": PRICE_FIELDS}),
            ScenarioStep("capital-flow", "capital-flow", "资金流更新。"),
            ScenarioStep("securities-margin", "securities-margin", "两融更新。"),
            ScenarioStep("stock-connect", "stock-connect", "陆股通更新。"),
            ScenarioStep("abnormal-stocks", "abnormal-stocks", "龙虎榜/异动列表更新。"),
            ScenarioStep("etf-daily-units", "etf-daily-units", "ETF 份额更新。", aliases={"ids": "etf_ids"}),
        ),
    ),
}


def list_scenarios() -> list[dict[str, Any]]:
    return [
        {
            "name": spec.name,
            "module": spec.module,
            "description": spec.description,
        }
        for spec in SCENARIOS.values()
    ]


def describe_scenario(name: str) -> dict[str, Any]:
    spec = get_scenario(name)
    return {
        "name": spec.name,
        "module": spec.module,
        "description": spec.description,
        "doc_basis": spec.doc_basis,
        "external_inputs": list(spec.external_inputs),
        "steps": [_describe_step(step) for step in spec.steps],
    }


def plan_scenario(name: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = get_scenario(name)
    params = params or {}
    return {
        "scenario": spec.name,
        "module": spec.module,
        "description": spec.description,
        "doc_basis": spec.doc_basis,
        "external_inputs": list(spec.external_inputs),
        "steps": [_plan_step(step, params) for step in spec.steps],
    }


def generate_scenario(
    name: str,
    params: dict[str, Any],
    output_dir: str | Path,
    file_format: str,
    resolver: Callable[[str], Any],
    *,
    strict: bool = False,
) -> dict[str, Any]:
    if file_format not in {"csv", "json"}:
        raise CliError("--file-format must be csv or json.")

    spec = get_scenario(name)
    base_dir = Path(output_dir) / spec.name
    base_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "scenario": spec.name,
        "module": spec.module,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(base_dir),
        "file_format": file_format,
        "parameters": _compact_params(params),
        "external_inputs": list(spec.external_inputs),
        "files": [],
        "skipped": [],
    }

    for index, step in enumerate(spec.steps, start=1):
        step_params = _step_params(step, params)
        missing = _missing_required(step.dataset, step_params)
        if missing:
            item = {
                "step": step.name,
                "dataset": step.dataset,
                "reason": f"missing required parameters: {', '.join(missing)}",
            }
            if strict:
                raise CliError(f"Scenario `{spec.name}` step `{step.name}` {item['reason']}.")
            manifest["skipped"].append(item)
            continue

        target = resolver(get_dataset(step.dataset).function)
        result = target(**build_dataset_kwargs(get_dataset(step.dataset), step_params))
        output_path = base_dir / f"{index:02d}-{step.name}.{file_format}"
        write_output(result, output=str(output_path), fmt=file_format)
        manifest["files"].append(
            {
                "step": step.name,
                "dataset": step.dataset,
                "description": step.description,
                "path": str(output_path),
            }
        )

    manifest_path = base_dir / "manifest.json"
    write_output(manifest, output=str(manifest_path), fmt="json")
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def get_scenario(name: str) -> ScenarioSpec:
    try:
        return SCENARIOS[name]
    except KeyError as exc:
        raise CliError(f"Unknown scenario `{name}`. Run `rqq data scenario list` to see supported scenarios.") from exc


def _describe_step(step: ScenarioStep) -> dict[str, Any]:
    dataset = describe_dataset(step.dataset)
    return {
        "name": step.name,
        "dataset": step.dataset,
        "description": step.description,
        "function": dataset["function"],
        "required": dataset["required"],
        "defaults": dataset["defaults"],
        "params": step.params,
        "aliases": step.aliases,
    }


def _plan_step(step: ScenarioStep, params: dict[str, Any]) -> dict[str, Any]:
    step_params = _step_params(step, params)
    missing = _missing_required(step.dataset, step_params)
    return {
        "name": step.name,
        "dataset": step.dataset,
        "description": step.description,
        "status": "ready" if not missing else "skipped",
        "missing": missing,
        "params": _compact_params(step_params),
    }


def _step_params(step: ScenarioStep, params: dict[str, Any]) -> dict[str, Any]:
    merged = dict(params)
    for public_name, source_name in step.aliases.items():
        if params.get(source_name) is not None:
            merged[public_name] = params[source_name]
    merged.update(step.params)
    return merged


def _missing_required(dataset_name: str, params: dict[str, Any]) -> list[str]:
    spec = get_dataset(dataset_name)
    merged = {**spec.defaults, **{key: value for key, value in params.items() if value is not None}}
    return [name for name in spec.required if _is_empty(merged.get(name))]


def _compact_params(params: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in params.items() if not _is_empty(value)}


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == []
