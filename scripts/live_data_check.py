"""Run a representative set of live RQData CLI requests and write a markdown report.

Dev-only smoke test against a real license. Covers every populated module with a
few real, parametrized `rqq data get` calls. Full returns are saved under
outputs/live-data-check/raw/ (gitignored); a summary report is written next to
them. Some sample params legitimately return empty rows — that is recorded as OK,
not a failure.

    uv run --no-sync python scripts/live_data_check.py            # run all cases
    uv run --no-sync python scripts/live_data_check.py --limit 10 # first N
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "outputs" / "live-data-check" / "raw"
REPORT_PATH = ROOT / "outputs" / "live-data-check" / "sample-results.md"


@dataclass(frozen=True)
class Case:
    case_id: str
    group: str          # module slug
    title: str          # dataset name
    args: tuple[str, ...]

    @property
    def output_path(self) -> Path:
        return RAW_DIR / f"{self.case_id}.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run live RQData CLI sample requests and write a markdown report.")
    parser.add_argument("--limit", type=int, help="Run only the first N cases.")
    parser.add_argument("--from-existing", action="store_true", help="Rebuild the report from existing output files.")
    parsed = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    cases = build_cases()
    if parsed.limit:
        cases = cases[: parsed.limit]

    results = [existing_case(case) if parsed.from_existing else run_case(case) for case in cases]
    REPORT_PATH.write_text(render_report(results), encoding="utf-8")
    print(f"wrote {REPORT_PATH}")
    print(f"cases={len(results)} ok={sum(1 for r in results if r['ok'])} failed={sum(1 for r in results if not r['ok'])}")


def build_cases() -> list[Case]:
    stock, stock2 = "000001.XSHE", "600000.XSHG"
    index, etf, fund = "000300.XSHG", "510300.XSHG", "000003"
    start, end = "2024-01-02", "2024-01-05"
    q_start, q_end = "2023q1", "2023q4"

    def get(name: str, group: str, *args: str) -> Case:
        return Case(name, group, name, ("data", "get", name, *args))

    return [
        # generic-api
        get("instruments", "generic-api", "--type", "CS", "--date", start),
        get("instrument", "generic-api", "--ids", stock, stock2),
        get("id-convert", "generic-api", "--ids", "000001.SZ", "600000.SH"),
        get("price", "generic-api", "--ids", stock, "--start", start, "--end", end, "--fields", "open,high,low,close,volume,total_turnover"),
        get("current-snapshot", "generic-api", "--ids", stock),
        get("ticks", "generic-api", "--ids", stock, "--start", start, "--end", start),
        get("trading-dates", "generic-api", "--start", "2024-01-01", "--end", "2024-01-10"),
        get("vwap", "generic-api", "--ids", stock, "--start", start, "--end", end),
        get("yield-curve", "generic-api", "--start", start, "--end", end),
        # stock-mod
        get("financials-pit", "stock-mod", "--ids", stock, "--fields", "revenue,net_profit,cash_flow_from_operating_activities", "--start-quarter", q_start, "--end-quarter", q_end),
        get("current-performance", "stock-mod", "--ids", stock, "--quarter", "2023q4", "--interval", "1q"),
        get("performance-forecast", "stock-mod", "--ids", stock, "--info-date", "2024-01-31"),
        get("shares", "stock-mod", "--ids", stock, "--start", "2024-01-01", "--end", "2024-03-31"),
        get("dividend", "stock-mod", "--ids", stock, "--start", "2023-01-01", "--end", "2024-12-31"),
        get("turnover-rate", "stock-mod", "--ids", stock, "--start", start, "--end", end),
        get("st", "stock-mod", "--ids", stock, "--start", start, "--end", end),
        get("suspended", "stock-mod", "--ids", stock, "--start", start, "--end", end),
        get("holder-number", "stock-mod", "--ids", stock, "--start", "2023-01-01", "--end", "2024-12-31"),
        get("main-shareholder", "stock-mod", "--ids", stock, "--start", "2023-01-01", "--end", "2024-12-31", "--start-rank", "1", "--end-rank", "10"),
        get("capital-flow", "stock-mod", "--ids", stock, "--start", start, "--end", end),
        get("stock-connect", "stock-mod", "--ids", stock, "--start", start, "--end", end),
        get("securities-margin", "stock-mod", "--ids", stock, "--start", start, "--end", end),
        get("block-trade", "stock-mod", "--ids", stock, "--start", "2024-01-01", "--end", "2024-03-31"),
        get("abnormal-stocks", "stock-mod", "--start", start, "--end", end),
        get("announcement", "stock-mod", "--ids", stock, "--start", "2024-01-01", "--end", "2024-03-31"),
        get("investor-ra", "stock-mod", "--ids", stock, "--start", "2024-01-01", "--end", "2024-03-31"),
        get("instrument-industry", "stock-mod", "--ids", stock, "--source", "citics_2019", "--level", "1", "--date", start),
        get("industry-mapping", "stock-mod", "--source", "citics_2019", "--date", start),
        # risk-factors-mod
        get("factor-names", "risk-factors-mod"),
        get("factor", "risk-factors-mod", "--ids", stock, "--factor", "pe_ratio_ttm,pb_ratio_lf", "--start", start, "--end", end),
        get("style-factor-exposure", "risk-factors-mod", "--ids", stock, "--start", start, "--end", end),
        get("stock-beta", "risk-factors-mod", "--ids", stock, "--start", start, "--end", end),
        # indices-mod
        get("index-components", "indices-mod", "--ids", index, "--date", start),
        get("index-weights", "indices-mod", "--ids", index, "--date", start),
        get("index-indicator", "indices-mod", "--ids", index, "--start", start, "--end", end),
        get("etf-daily-units", "indices-mod", "--ids", etf, "--start", start, "--end", end),
        get("etf-components", "indices-mod", "--ids", etf, "--date", start),
        # fund-mod
        get("fund-instruments", "fund-mod", "--date", start),
        get("fund-nav", "fund-mod", "--ids", fund, "--start", start, "--end", end),
        get("fund-holdings", "fund-mod", "--ids", fund, "--date", "2023-12-31"),
        get("fund-asset-allocation", "fund-mod", "--ids", fund, "--date", "2023-12-31"),
        get("fund-manager", "fund-mod", "--ids", fund),
        # futures-mod
        get("dominant-future", "futures-mod", "--underlying", "AG", "--start", start, "--end", end),
        get("futures-dominant", "futures-mod", "--underlying", "AG", "--start", start, "--end", end),
        get("futures-contracts", "futures-mod", "--underlying", "AG", "--date", start),
        # options-mod
        get("options-contracts", "options-mod", "--underlying", "510050.XSHG"),
        # convertible-mod
        get("convertible-instruments", "convertible-mod", "--date", start),
        # repo / macro-economy
        get("interbank-offered-rate", "repo", "--start", start, "--end", end),
        get("econ-money-supply", "macro-economy", "--start", "2023-01-01", "--end", "2024-01-31"),
        get("exchange-rate", "macro-economy", "--start", start, "--end", end),
        # alternative-data
        get("consensus-price", "alternative-data", "--ids", stock, "--start", "2024-01-01", "--end", "2024-03-31"),
        get("consensus-indicator", "alternative-data", "--ids", stock, "--fiscal-year", "2024"),
        get("current-news", "alternative-data", "--n", "20", "--channels", "a-stock"),
        get("stock-concept", "alternative-data", "--ids", stock),
    ]


def run_case(case: Case) -> dict[str, Any]:
    if case.output_path.exists():
        case.output_path.unlink()
    cmd = [sys.executable, "-m", "rqsdk_quant", *case.args, "--format", "json", "--output", str(case.output_path)]
    completed = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=90)
    summary = summarize_output(case.output_path) if completed.returncode == 0 and case.output_path.exists() else {"type": "no-output"}
    return {
        "case": case,
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "cmd": "uv run rqq " + " ".join(shell_quote(part) for part in case.args) + " --format json",
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "summary": summary,
    }


def existing_case(case: Case) -> dict[str, Any]:
    summary = summarize_output(case.output_path) if case.output_path.exists() else {"type": "no-output"}
    return {"case": case, "ok": True, "returncode": 0,
            "cmd": "uv run rqq " + " ".join(shell_quote(part) for part in case.args) + " --format json",
            "stdout": "", "stderr": "", "summary": summary}


def summarize_output(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"type": "unreadable", "error": str(exc), "path": str(path.relative_to(ROOT))}
    summary = describe_value(data)
    summary["path"] = str(path.relative_to(ROOT))
    return summary


def describe_value(value: Any) -> dict[str, Any]:
    if isinstance(value, list):
        sample = value[:3]
        columns = list(sample[0].keys()) if sample and isinstance(sample[0], dict) else []
        return {"type": "list", "rows": len(value), "columns": columns[:30], "sample": sample}
    if isinstance(value, dict):
        return {"type": "dict", "keys": list(value.keys())[:30], "sample": trim_sample(value)}
    return {"type": type(value).__name__, "sample": value}


def trim_sample(value: Any) -> Any:
    text = json.dumps(value, ensure_ascii=False, default=str)
    if len(text) <= 1200:
        return value
    if isinstance(value, dict):
        return {key: value[key] for key in list(value)[:10]}
    return text[:1200]


def render_report(results: list[dict[str, Any]]) -> str:
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "# 米筐数据真实请求结果",
        "",
        f"生成时间：{now}",
        "",
        "说明：本文件由 `scripts/live_data_check.py` 真实调用当前 CLI 生成。完整返回保存在 `outputs/live-data-check/raw/`。空表表示该样本参数下无数据，不算失败。",
        "",
        f"总请求数：{len(results)}",
        f"成功：{sum(1 for r in results if r['ok'])}",
        f"失败：{sum(1 for r in results if not r['ok'])}",
        "",
        "## 汇总",
        "",
        "| 模块 | 数据集 | 状态 | 行数/类型 |",
        "| --- | --- | --- | --- |",
    ]
    for item in results:
        case: Case = item["case"]
        status = "OK" if item["ok"] else "FAILED"
        shape = shape_text(item["summary"]) if item["ok"] else f"exit {item['returncode']}"
        lines.append(f"| {case.group} | `{case.title}` | {status} | {escape_md(shape)} |")

    for item in results:
        case = item["case"]
        lines.extend(["", f"## {case.group} / {case.title}", "", f"命令：`{item['cmd']}`", ""])
        if not item["ok"]:
            lines.extend(["状态：失败", "", "```text", item["stderr"] or item["stdout"] or "(empty)", "```"])
            continue
        summary = item["summary"]
        if summary.get("type") == "no-output":
            lines.append("状态：成功，但无输出（SDK 在该样本参数下返回空）。")
            continue
        lines.append(f"返回形态：{shape_text(summary)}")
        if summary.get("columns"):
            lines.extend(["", "字段：", "", "```text", ", ".join(summary["columns"]), "```"])
        if "sample" in summary:
            lines.extend(["", "样例：", "", "```json", json.dumps(summary["sample"], ensure_ascii=False, indent=2, default=str), "```"])
    lines.append("")
    return "\n".join(lines)


def shape_text(summary: dict[str, Any]) -> str:
    if summary.get("type") == "list":
        return f"list rows={summary.get('rows', 0)} columns={len(summary.get('columns', []))}"
    if summary.get("type") == "dict":
        return f"dict keys={len(summary.get('keys', []))}"
    return str(summary.get("type", "unknown"))


def shell_quote(value: str) -> str:
    if not value:
        return "''"
    if all(ch.isalnum() or ch in "-_./:=,[]" for ch in value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


def escape_md(value: str) -> str:
    return value.replace("|", "\\|")


if __name__ == "__main__":
    main()
