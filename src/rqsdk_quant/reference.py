from __future__ import annotations

from typing import Any

from . import __version__
from .business import BUSINESS_DATASETS
from .datasets import DATASETS
from .scenarios import SCENARIOS


# Curated list of the data-layer verbs. Kept here (not auto-extracted from
# argparse) so the one-shot reference can carry copy-pasteable examples, which
# are the most useful thing for an LLM driving the CLI.
COMMANDS: list[dict[str, str]] = [
    {
        "command": "data list [--category C]",
        "purpose": "列出所有已封装的数据集。",
        "example": "rqq data list --category market",
    },
    {
        "command": "data describe <dataset>",
        "purpose": "查看单个数据集的底层函数、必填参数和默认值。",
        "example": "rqq data describe price",
    },
    {
        "command": "data fetch <dataset> [params]",
        "purpose": "统一取数入口（别名 data get）。可用参数见 datasets 小节。",
        "example": "rqq data fetch price --ids 000001.XSHE --start 2024-01-02 --end 2024-01-03",
    },
    {
        "command": "data scenario list|describe|plan <name>",
        "purpose": "查看模块化数据场景；plan 会标出缺失的必填参数。",
        "example": "rqq data scenario plan company-quality --ids 000001.XSHE",
    },
    {
        "command": "data generate <scenario> [params]",
        "purpose": "生成一个场景的多份数据文件 + manifest.json。",
        "example": "rqq data generate price-trend --ids 000001.XSHE --start 2024-01-01 --end 2024-01-31",
    },
    {
        "command": "data business list|describe|plan <name>",
        "purpose": "查看业务拼装表；plan 会标出缺失的必填参数。",
        "example": "rqq data business plan research-monitor-snapshot --ids 000001.XSHE",
    },
    {
        "command": "data build <business> [params]",
        "purpose": "生成一个业务拼装宽表（data business build 的短别名）。",
        "example": "rqq data build research-monitor-snapshot --ids 000001.XSHE --start 2024-01-01 --end 2024-01-31",
    },
    {
        "command": "data info | data quota",
        "purpose": "查看 rqdatac 连接信息和账号配额。",
        "example": "rqq data info",
    },
    {
        "command": "data call <fn> [--args JSON] [--kwargs JSON]",
        "purpose": "直接调用任意 rqdatac 函数（数据集未封装时的兜底入口）。",
        "example": "rqq data call user.get_quota",
    },
    {
        "command": 'license [-l "<license_key>"|"<account>:<password>"]',
        "purpose": "配置 Ricequant license（验证后存到 ~/.rqq，取数时自动用）；不带 -l 进入粘贴式输入。`license info` 查看，`license clear` 清除。",
        "example": 'rqq license -l "<your_license_key>"',
    },
    {
        "command": "help",
        "purpose": "输出本参考：所有数据命令的用途、参数、必填和默认值。",
        "example": "rqq help --format json",
    },
]

NOTES = (
    "默认输出 markdown，加 --format json 取机器可解析结构，--format csv 取表格，"
    "-o/--output 写文件。日期用 YYYY-MM-DD。多值参数（--ids/--fields/--factor 等）"
    "用空格或逗号分隔。每个数据集可接受的参数 = required + optional。"
)


def build_help_reference() -> dict[str, Any]:
    """Assemble the one-shot data-layer reference for humans and LLMs."""
    dataset_names = sorted(DATASETS, key=lambda name: (DATASETS[name].category, name))
    return {
        "cli": "rqq",
        "version": __version__,
        "default_format": "markdown",
        "notes": NOTES,
        "commands": COMMANDS,
        "datasets": [_dataset_row(name) for name in dataset_names],
        "scenarios": [_scenario_row(name) for name in SCENARIOS],
        "business_datasets": [_business_row(name) for name in BUSINESS_DATASETS],
    }


def _dataset_row(name: str) -> dict[str, Any]:
    spec = DATASETS[name]
    optional = [param for param in spec.public_params() if param not in spec.required]
    return {
        "name": spec.name,
        "category": spec.category,
        "function": spec.function,
        "required": list(spec.required),
        "optional": optional,
        "defaults": spec.defaults,
        "description": spec.description,
    }


def _scenario_row(name: str) -> dict[str, Any]:
    spec = SCENARIOS[name]
    return {
        "name": spec.name,
        "module": spec.module,
        "datasets": [step.dataset for step in spec.steps],
        "description": spec.description,
        "external_inputs": list(spec.external_inputs),
    }


def _business_row(name: str) -> dict[str, Any]:
    spec = BUSINESS_DATASETS[name]
    return {
        "name": spec.name,
        "output_table": spec.output_table,
        "module": spec.module,
        "components": [component.dataset for component in spec.components],
        "description": spec.description,
        "external_inputs": list(spec.external_inputs),
    }
