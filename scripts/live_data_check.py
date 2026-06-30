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
SCENARIO_DIR = ROOT / "outputs" / "live-data-check" / "scenario"
BUSINESS_DIR = ROOT / "outputs" / "live-data-check" / "business"
REPORT_PATH = ROOT / "docs" / "data-live-sample-results.md"


@dataclass(frozen=True)
class Case:
    case_id: str
    group: str
    title: str
    args: tuple[str, ...]
    note: str = ""

    @property
    def output_path(self) -> Path:
        return RAW_DIR / f"{self.case_id}.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run live RQData CLI sample requests and write a markdown report.")
    parser.add_argument("--limit", type=int, help="Run only the first N cases.")
    parser.add_argument("--from-existing", action="store_true", help="Rebuild the markdown report from existing output files.")
    parsed = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    SCENARIO_DIR.mkdir(parents=True, exist_ok=True)
    BUSINESS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    cases = build_cases()
    if parsed.limit:
        cases = cases[: parsed.limit]

    results = [existing_case(case) if parsed.from_existing else run_case(case) for case in cases]
    REPORT_PATH.write_text(render_report(results), encoding="utf-8")
    print(f"wrote {REPORT_PATH}")
    print(f"cases={len(results)} ok={sum(1 for item in results if item['ok'])} failed={sum(1 for item in results if not item['ok'])}")


def build_cases() -> list[Case]:
    stock = "000001.XSHE"
    stock2 = "600000.XSHG"
    index = "000300.XSHG"
    etf = "510300.XSHG"
    fund = "000003"
    start = "2024-01-02"
    end = "2024-01-05"
    q_start = "2023q1"
    q_end = "2023q4"

    cases: list[Case] = [
        Case("meta-list", "metadata", "dataset list", ("data", "list")),
        Case("meta-business-list", "metadata", "business list", ("data", "business", "list")),
        Case("meta-scenario-list", "metadata", "scenario list", ("data", "scenario", "list")),
        Case("meta-quota", "metadata", "quota", ("data", "quota")),
        Case("quick-instruments", "shortcut", "shortcut instruments", ("data", "instruments", "--type", "CS", "--date", start)),
        Case("quick-id-convert", "shortcut", "shortcut id convert", ("data", "id-convert", "000001.SZ", "600000.SH")),
        Case("quick-price", "shortcut", "shortcut price", ("data", "price", stock, "--start", start, "--end", end, "--fields", "open,close,volume")),
        Case("quick-trading-dates", "shortcut", "shortcut trading dates", ("data", "trading-dates", "--start", "2024-01-01", "--end", "2024-01-10")),
        Case("quick-call", "shortcut", "generic rqdatac call", ("data", "call", "get_price", "--kwargs", json.dumps({"order_book_ids": stock, "start_date": start, "end_date": end, "fields": ["open", "close"], "expect_df": True}))),
        Case("master-instruments", "master", "instruments", ("data", "get", "instruments", "--type", "CS", "--date", start)),
        Case("master-instrument", "master", "instrument", ("data", "get", "instrument", "--ids", stock, stock2)),
        Case("master-id-convert", "master", "id-convert", ("data", "get", "id-convert", "--ids", "000001.SZ", "600000.SH")),
        Case("calendar-trading-dates", "calendar", "trading-dates", ("data", "get", "trading-dates", "--start", "2024-01-01", "--end", "2024-01-10")),
        Case("calendar-prev", "calendar", "previous-trading-date", ("data", "get", "previous-trading-date", "--date", "2024-01-08", "--n", "1")),
        Case("calendar-next", "calendar", "next-trading-date", ("data", "get", "next-trading-date", "--date", "2024-01-08", "--n", "1")),
        Case("market-price", "market", "price", ("data", "get", "price", "--ids", stock, "--start", start, "--end", end, "--fields", "open,high,low,close,volume,total_turnover")),
        Case("market-current-snapshot", "market", "current-snapshot", ("data", "get", "current-snapshot", "--ids", stock)),
        Case("market-current-minute", "market", "current-minute", ("data", "get", "current-minute", "--ids", stock, "--fields", "open,close,volume")),
        Case("market-ticks", "market", "ticks", ("data", "get", "ticks", "--ids", stock, "--start", start, "--end", start)),
        Case("factor-names", "factor", "factor-names", ("data", "get", "factor-names")),
        Case("factor-factor", "factor", "factor", ("data", "get", "factor", "--ids", stock, "--factor", "gross_profit_margin_ttm,net_profit_margin_ttm,market_cap_3", "--start", start, "--end", end)),
        Case("equity-shares", "equity", "shares", ("data", "get", "shares", "--ids", stock, "--start", "2024-01-01", "--end", "2024-03-31")),
        Case("equity-dividend", "equity", "dividend", ("data", "get", "dividend", "--ids", stock, "--start", "2023-01-01", "--end", "2024-12-31")),
        Case("equity-split", "equity", "split", ("data", "get", "split", "--ids", stock, "--start", "2020-01-01", "--end", "2024-12-31")),
        Case("equity-turnover-rate", "equity", "turnover-rate", ("data", "get", "turnover-rate", "--ids", stock, "--start", start, "--end", end)),
        Case("equity-st", "equity", "st", ("data", "get", "st", "--ids", stock, "--start", start, "--end", end)),
        Case("equity-suspended", "equity", "suspended", ("data", "get", "suspended", "--ids", stock, "--start", start, "--end", end)),
        Case("equity-holder-number", "equity", "holder-number", ("data", "get", "holder-number", "--ids", stock, "--start", "2023-01-01", "--end", "2024-12-31")),
        Case("equity-main-shareholder", "equity", "main-shareholder", ("data", "get", "main-shareholder", "--ids", stock, "--start", "2023-01-01", "--end", "2024-12-31", "--start-rank", "1", "--end-rank", "10")),
        Case("financial-pit", "financial", "financials-pit", ("data", "get", "financials-pit", "--ids", stock, "--fields", "revenue,net_profit,cash_flow_from_operating_activities,total_rnd", "--start-quarter", q_start, "--end-quarter", q_end)),
        Case("financial-current-performance", "financial", "current-performance", ("data", "get", "current-performance", "--ids", stock, "--quarter", "2023q4", "--interval", "1q")),
        Case("financial-performance-forecast", "financial", "performance-forecast", ("data", "get", "performance-forecast", "--ids", stock, "--info-date", "2024-01-31")),
        Case("financial-forecast-report-date", "financial", "forecast-report-date", ("data", "get", "forecast-report-date", "--ids", stock, "--start-quarter", q_start, "--end-quarter", "2024q4")),
        Case("industry-instrument", "industry", "instrument-industry", ("data", "get", "instrument-industry", "--ids", stock, "--source", "citics_2019", "--level", "1", "--date", start)),
        Case("industry-industry", "industry", "industry", ("data", "get", "industry", "--industry", "b10", "--source", "citics_2019", "--date", start)),
        Case("industry-mapping", "industry", "industry-mapping", ("data", "get", "industry-mapping", "--source", "citics_2019", "--date", start)),
        Case("event-announcement", "event", "announcement", ("data", "get", "announcement", "--ids", stock, "--start", "2024-01-01", "--end", "2024-03-31")),
        Case("event-investor-qa", "event", "investor-qa", ("data", "get", "investor-qa", "--ids", stock, "--start", "2024-01-01", "--end", "2024-03-31")),
        Case("event-investor-ra", "event", "investor-ra", ("data", "get", "investor-ra", "--ids", stock, "--start", "2024-01-01", "--end", "2024-03-31")),
        Case("money-capital-flow", "money-flow", "capital-flow", ("data", "get", "capital-flow", "--ids", stock, "--start", start, "--end", end, "--frequency", "1d")),
        Case("money-stock-connect", "money-flow", "stock-connect", ("data", "get", "stock-connect", "--ids", stock, "--start", start, "--end", end)),
        Case("money-securities-margin", "money-flow", "securities-margin", ("data", "get", "securities-margin", "--ids", stock, "--start", start, "--end", end)),
        Case("money-block-trade", "money-flow", "block-trade", ("data", "get", "block-trade", "--ids", stock, "--start", "2024-01-01", "--end", "2024-03-31")),
        Case("money-abnormal-stocks", "money-flow", "abnormal-stocks", ("data", "get", "abnormal-stocks", "--start", start, "--end", end)),
        Case("money-abnormal-detail", "money-flow", "abnormal-stocks-detail", ("data", "get", "abnormal-stocks-detail", "--ids", stock, "--start", start, "--end", end)),
        Case("etf-daily-units", "etf", "etf-daily-units", ("data", "get", "etf-daily-units", "--ids", etf, "--start", start, "--end", end)),
        Case("etf-components", "etf", "etf-components", ("data", "get", "etf-components", "--ids", etf, "--date", start)),
        Case("etf-cash-components", "etf", "etf-cash-components", ("data", "get", "etf-cash-components", "--ids", etf, "--start", start, "--end", end)),
        Case("fund-instruments", "fund", "fund-instruments", ("data", "get", "fund-instruments", "--date", start)),
        Case("fund-daily-units", "fund", "fund-daily-units", ("data", "get", "fund-daily-units", "--ids", fund, "--start", start, "--end", end)),
        Case("fund-holdings", "fund", "fund-holdings", ("data", "get", "fund-holdings", "--ids", fund, "--date", "2023-12-31")),
        Case("fund-stock-change", "fund", "fund-stock-change", ("data", "get", "fund-stock-change", "--ids", fund, "--start", "2023-01-01", "--end", "2024-12-31")),
        Case("fund-asset-allocation", "fund", "fund-asset-allocation", ("data", "get", "fund-asset-allocation", "--ids", fund, "--date", "2023-12-31")),
        Case("fund-industry-allocation", "fund", "fund-industry-allocation", ("data", "get", "fund-industry-allocation", "--ids", fund, "--date", "2023-12-31")),
        Case("fund-nav", "fund", "fund-nav", ("data", "get", "fund-nav", "--ids", fund, "--start", start, "--end", end)),
        Case("fund-benchmark", "fund", "fund-benchmark", ("data", "get", "fund-benchmark", "--ids", fund)),
        Case("consensus-price", "consensus", "consensus-price", ("data", "get", "consensus-price", "--ids", stock, "--start", "2024-01-01", "--end", "2024-03-31")),
        Case("consensus-comp", "consensus", "consensus-comp-indicators", ("data", "get", "consensus-comp-indicators", "--ids", stock, "--start", "2024-01-01", "--end", "2024-03-31")),
        Case("consensus-indicator", "consensus", "consensus-indicator", ("data", "get", "consensus-indicator", "--ids", stock, "--fiscal-year", "2024")),
        Case("consensus-market-estimate", "consensus", "consensus-market-estimate", ("data", "get", "consensus-market-estimate", "--indexes", index, "--fiscal-year", "2024")),
        Case("consensus-industry-rating", "consensus", "consensus-industry-rating", ("data", "get", "consensus-industry-rating", "--industries", "银行", "--start", "2024-01-01", "--end", "2024-03-31")),
        Case("consensus-industries", "consensus", "consensus-industries", ("data", "get", "consensus-industries")),
        Case("index-components", "index", "index-components", ("data", "get", "index-components", "--ids", index, "--date", start)),
        Case("index-weights", "index", "index-weights", ("data", "get", "index-weights", "--ids", index, "--date", start)),
        Case("index-weights-ex", "index", "index-weights-ex", ("data", "get", "index-weights-ex", "--ids", index, "--date", start)),
        Case("index-indicator", "index", "index-indicator", ("data", "get", "index-indicator", "--ids", index, "--start", start, "--end", end)),
        Case("index-factor-exposure", "index", "index-factor-exposure", ("data", "get", "index-factor-exposure", "--ids", index, "--start", start, "--end", end, "--factors", "beta,momentum")),
        Case("news-current", "news", "current-news", ("data", "get", "current-news", "--n", "20", "--channels", "a-stock")),
    ]

    scenario_common = ("--output-dir", str(SCENARIO_DIR), "--file-format", "json")
    cases.extend(
        [
            Case("scenario-base-universe", "scenario", "base-universe", ("data", "generate", "base-universe", "--ids", stock, stock2, "--date", start, *scenario_common)),
            Case("scenario-company-quality", "scenario", "company-quality", ("data", "generate", "company-quality", "--ids", stock, "--start", "2024-01-01", "--end", "2024-03-31", "--start-quarter", q_start, "--end-quarter", q_end, "--quarter", "2023q4", *scenario_common)),
            Case("scenario-institution-attention", "scenario", "institution-attention", ("data", "generate", "institution-attention", "--ids", stock, "--start", "2024-01-01", "--end", "2024-03-31", *scenario_common)),
            Case("scenario-capital-confirmation", "scenario", "capital-confirmation", ("data", "generate", "capital-confirmation", "--ids", stock, "--etf-ids", etf, "--start", start, "--end", end, *scenario_common)),
            Case("scenario-price-trend", "scenario", "price-trend", ("data", "generate", "price-trend", "--ids", stock, "--start", start, "--end", end, *scenario_common)),
            Case("scenario-risk-crowding", "scenario", "risk-crowding", ("data", "generate", "risk-crowding", "--ids", stock, "--start", start, "--end", end, *scenario_common)),
            Case("scenario-daily-monitor", "scenario", "daily-monitor", ("data", "generate", "daily-monitor", "--ids", stock, "--etf-ids", etf, "--start", start, "--end", end, *scenario_common)),
        ]
    )

    business_common = ("--output-dir", str(BUSINESS_DIR), "--file-format", "json", "--write-components")
    cases.extend(
        [
            Case("business-company-quality", "business", "company-quality-snapshot", ("data", "build", "company-quality-snapshot", "--ids", stock, "--start", "2024-01-01", "--end", "2024-03-31", "--start-quarter", q_start, "--end-quarter", q_end, "--quarter", "2023q4", *business_common)),
            Case("business-capital-confirmation", "business", "capital-confirmation-snapshot", ("data", "build", "capital-confirmation-snapshot", "--ids", stock, "--start", start, "--end", end, *business_common)),
            Case("business-research-monitor", "business", "research-monitor-snapshot", ("data", "build", "research-monitor-snapshot", "--ids", stock, "--start", "2024-01-01", "--end", "2024-03-31", *business_common)),
            Case("business-fund-position", "business", "fund-position-snapshot", ("data", "build", "fund-position-snapshot", "--ids", fund, "--date", "2023-12-31", "--start", start, "--end", end, *business_common)),
            Case("business-consensus-attention", "business", "consensus-attention-snapshot", ("data", "build", "consensus-attention-snapshot", "--ids", stock, "--start", "2024-01-01", "--end", "2024-03-31", "--fiscal-year", "2024", *business_common)),
            Case("business-index-relative-strength", "business", "index-relative-strength-snapshot", ("data", "build", "index-relative-strength-snapshot", "--ids", index, "--date", start, "--start", start, "--end", end, *business_common)),
            Case("business-event-news", "business", "event-news-snapshot", ("data", "build", "event-news-snapshot", "--n", "20", "--channels", "a-stock", *business_common)),
        ]
    )
    return cases


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
        "cmd": "uv run rqq " + " ".join(shell_quote(part) for part in case.args) + f" --format json --output {case.output_path.relative_to(ROOT)}",
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "summary": summary,
    }


def existing_case(case: Case) -> dict[str, Any]:
    summary = summarize_output(case.output_path) if case.output_path.exists() else {"type": "no-output"}
    return {
        "case": case,
        "ok": True,
        "returncode": 0,
        "cmd": "uv run rqq " + " ".join(shell_quote(part) for part in case.args) + f" --format json --output {case.output_path.relative_to(ROOT)}",
        "stdout": "",
        "stderr": "",
        "summary": summary,
    }


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
        out: dict[str, Any] = {"type": "dict", "keys": list(value.keys())[:30]}
        if "files" in value:
            out["files"] = value.get("files", [])
        if "components" in value:
            out["components"] = value.get("components", [])
        if "skipped" in value:
            out["skipped"] = value.get("skipped", [])
        if "rows" in value:
            out["rows"] = value.get("rows")
        out["sample"] = trim_sample(value)
        return out
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
        "说明：本文件由 `scripts/live_data_check.py` 真实调用当前 CLI 生成。完整返回保存在 `outputs/live-data-check/raw/`；场景和业务表的组件文件保存在 `outputs/live-data-check/scenario/` 与 `outputs/live-data-check/business/`。",
        "",
        f"总请求数：{len(results)}",
        f"成功：{sum(1 for item in results if item['ok'])}",
        f"失败：{sum(1 for item in results if not item['ok'])}",
        "",
        "## 汇总",
        "",
        "| 分组 | 数据/场景 | 状态 | 行数/类型 | 输出 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in results:
        case: Case = item["case"]
        status = "OK" if item["ok"] else "FAILED"
        summary = item["summary"]
        shape = shape_text(summary) if item["ok"] else f"exit {item['returncode']}"
        output = summary.get("path", "-") if item["ok"] and summary.get("type") != "no-output" else "-"
        lines.append(f"| {case.group} | `{case.title}` | {status} | {escape_md(shape)} | `{output}` |")

    for item in results:
        case: Case = item["case"]
        lines.extend(["", f"## {case.group} / {case.title}", "", f"命令：`{item['cmd']}`", ""])
        if not item["ok"]:
            lines.extend(["状态：失败", "", "错误输出：", "", "```text", item["stderr"] or item["stdout"] or "(empty)", "```"])
            continue
        summary = item["summary"]
        if summary.get("type") == "no-output":
            lines.extend(["状态：成功，但接口没有写出结果。通常表示该样本参数下 SDK 返回 `None` 或空对象，CLI 没有生成输出文件。"])
            continue
        lines.append(f"输出文件：`{summary.get('path')}`")
        lines.append("")
        lines.append(f"返回形态：{shape_text(summary)}")
        if summary.get("columns"):
            lines.append("")
            lines.append("字段：")
            lines.append("")
            lines.append("```text")
            lines.append(", ".join(summary["columns"]))
            lines.append("```")
        if summary.get("files"):
            lines.append("")
            lines.append("场景文件：")
            lines.append("")
            for file_item in summary["files"]:
                lines.append(f"- `{file_item.get('dataset')}` -> `{file_item.get('path')}`")
        if summary.get("components"):
            lines.append("")
            lines.append("业务组件：")
            lines.append("")
            for component in summary["components"]:
                path = component.get("path", "")
                lines.append(f"- `{component.get('dataset')}` rows={component.get('rows')} columns={len(component.get('columns', []))} `{path}`")
        if summary.get("skipped"):
            lines.append("")
            lines.append("跳过项：")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(summary["skipped"], ensure_ascii=False, indent=2, default=str))
            lines.append("```")
        if "sample" in summary:
            lines.append("")
            lines.append("样例：")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(summary["sample"], ensure_ascii=False, indent=2, default=str))
            lines.append("```")
    lines.append("")
    return "\n".join(lines)


def shape_text(summary: dict[str, Any]) -> str:
    if summary.get("type") == "list":
        return f"list rows={summary.get('rows', 0)} columns={len(summary.get('columns', []))}"
    if summary.get("type") == "dict":
        rows = summary.get("rows")
        if rows is not None:
            return f"dict rows={rows} keys={len(summary.get('keys', []))}"
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
