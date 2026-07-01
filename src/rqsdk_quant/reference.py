from __future__ import annotations

from typing import Any

from . import __version__
from .datasets import DATASETS, MODULES, build_example


# Curated list of the data-layer verbs. Kept here (not auto-extracted from
# argparse) so the one-shot reference can carry copy-pasteable examples, which
# are the most useful thing for an LLM driving the CLI.
COMMANDS: list[dict[str, str]] = [
    {
        "command": "data list [--category <module>]",
        "purpose": "列出所有数据集；--category 按官方模块过滤（如 fund-mod、futures-mod）。",
        "example": "rqq data list --category fund-mod",
    },
    {
        "command": "data describe <dataset>",
        "purpose": "查看单个数据集的底层 rqdatac 函数、必填和可选参数。",
        "example": "rqq data describe price",
    },
    {
        "command": "data fetch <dataset> [params]",
        "purpose": "统一取数入口（别名 data get）；一个数据集对应一次原子 rqdatac 调用。",
        "example": "rqq data fetch price --ids 000001.XSHE --start 2024-01-02 --end 2024-01-03",
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
        "purpose": "输出本参考：所有数据集的用途、参数和必填字段。",
        "example": "rqq help --format json",
    },
]

NOTES = (
    "每个数据集 = 一次原子 rqdatac 调用，按 RQData 官方模块组织。"
    "默认输出 markdown，加 --format json 取机器可解析结构，--format csv 取表格，"
    "-o/--output 写文件。日期用 YYYY-MM-DD。多值参数（--ids/--fields/--factor 等）"
    "用空格或逗号分隔。未暴露为命令行参数的 rqdatac kwarg 可用 --param KEY=VALUE "
    "或 --params '<json>' 传入。"
)


def build_help_reference() -> dict[str, Any]:
    """Assemble the one-shot data reference for humans and LLMs."""
    return {
        "cli": "rqq",
        "version": __version__,
        "default_format": "markdown",
        "notes": NOTES,
        "commands": COMMANDS,
        "modules": [
            {
                "module": MODULES[slug],
                "slug": slug,
                "datasets": [_dataset_row(name) for name in names],
            }
            for slug, names in _datasets_by_module().items()
        ],
    }


def _datasets_by_module() -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {slug: [] for slug in MODULES}
    for name in sorted(DATASETS):
        grouped.setdefault(DATASETS[name].category, []).append(name)
    return {slug: names for slug, names in grouped.items() if names}


def _dataset_row(name: str) -> dict[str, Any]:
    spec = DATASETS[name]
    optional = [param for param in spec.public_params() if param not in spec.required]
    return {
        "name": spec.name,
        "function": spec.function,
        "required": list(spec.required),
        "optional": optional,
        "description": spec.description,
        "example": build_example(spec),
    }
