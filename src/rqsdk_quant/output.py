from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any, Iterable


def write_output(value: Any, output: str | None = None, fmt: str = "markdown") -> None:
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() == ".csv" or fmt == "csv":
            _write_csv_file(value, path)
        elif fmt == "markdown" or path.suffix.lower() in {".md", ".markdown"}:
            path.write_text(_to_markdown_text(value), encoding="utf-8")
        else:
            path.write_text(_to_json_text(value), encoding="utf-8")
        return

    if fmt == "json":
        print(_to_json_text(value))
    elif fmt == "csv":
        _write_csv_stream(value, sys.stdout)
    elif fmt == "table":
        print(_to_table_text(value))
    else:
        print(_to_markdown_text(value))


def _to_json_text(value: Any) -> str:
    normalized = _normalize(value)
    return json.dumps(normalized, ensure_ascii=False, indent=2, default=str)


# --- markdown -------------------------------------------------------------


def _to_markdown_text(value: Any) -> str:
    if _is_dataframe(value) or _is_series(value):
        return _md_value(_normalize(value))
    if isinstance(value, str):
        return value
    return _md_value(_normalize(value))


def _md_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return _md_document(value)
    if isinstance(value, list):
        if not value:
            return "_(empty)_"
        if all(isinstance(item, dict) for item in value):
            return _records_to_md_table(value)
        return "\n".join(f"- {_md_scalar(item)}" for item in value)
    return _md_scalar(value)


def _md_document(mapping: dict[str, Any]) -> str:
    scalar_lines: list[str] = []
    sections: list[tuple[str, str]] = []
    for key, val in mapping.items():
        if isinstance(val, list) and val and all(isinstance(item, dict) for item in val):
            sections.append((key, _records_to_md_table(val)))
        elif isinstance(val, dict) and val:
            sections.append((key, _md_dict_kv(val)))
        else:
            scalar_lines.append(f"- **{key}**: {_md_scalar(val)}")

    parts: list[str] = []
    if scalar_lines:
        parts.append("\n".join(scalar_lines))
    for key, body in sections:
        parts.append(f"### {key}\n\n{body}")
    return "\n\n".join(parts) if parts else "_(empty)_"


def _md_dict_kv(mapping: dict[str, Any]) -> str:
    records = [{"key": key, "value": _md_scalar(val)} for key, val in mapping.items()]
    return _records_to_md_table(records)


def _records_to_md_table(records: list[dict[str, Any]]) -> str:
    if not records:
        return "_(empty)_"
    fields = _fieldnames(records)
    header = "| " + " | ".join(fields) + " |"
    sep = "| " + " | ".join("---" for _ in fields) + " |"
    body = [
        "| " + " | ".join(_md_cell(row.get(field, "")) for field in fields) + " |"
        for row in records
    ]
    return "\n".join([header, sep, *body])


def _md_cell(value: Any) -> str:
    return _md_scalar(value).replace("|", "\\|").replace("\n", " ")


def _md_scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return "; ".join(f"{key}={_md_scalar(val)}" for key, val in value.items())
    if isinstance(value, (list, tuple)):
        return ", ".join(_md_scalar(item) for item in value)
    return str(value)


# --- table ----------------------------------------------------------------


def _to_table_text(value: Any) -> str:
    if _is_dataframe(value):
        return value.to_string()
    if _is_series(value):
        return value.to_string()
    normalized = _normalize(value)
    if isinstance(normalized, list) and normalized and isinstance(normalized[0], dict):
        return _records_to_table(normalized)
    if isinstance(normalized, dict):
        rows = [{"key": key, "value": _stringify(val)} for key, val in normalized.items()]
        return _records_to_table(rows)
    return _stringify(normalized)


def _records_to_table(records: list[dict[str, Any]]) -> str:
    if not records:
        return ""
    fields = _fieldnames(records)
    widths = {
        field: max(len(field), *(len(_stringify(row.get(field, ""))) for row in records))
        for field in fields
    }
    header = "  ".join(field.ljust(widths[field]) for field in fields)
    sep = "  ".join("-" * widths[field] for field in fields)
    body = [
        "  ".join(_stringify(row.get(field, "")).ljust(widths[field]) for field in fields)
        for row in records
    ]
    return "\n".join([header, sep, *body])


# --- csv ------------------------------------------------------------------


def _write_csv_file(value: Any, path: Path) -> None:
    if _is_dataframe(value):
        value.to_csv(path)
        return
    if _is_series(value):
        value.to_csv(path)
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        _write_csv_stream(value, handle)


def _write_csv_stream(value: Any, stream: Any) -> None:
    records = _as_records(value)
    writer = csv.DictWriter(stream, fieldnames=_fieldnames(records))
    writer.writeheader()
    writer.writerows(records)


def _as_records(value: Any) -> list[dict[str, Any]]:
    if _is_dataframe(value):
        return value.reset_index().to_dict(orient="records")
    if _is_series(value):
        return value.reset_index().to_dict(orient="records")
    normalized = _normalize(value)
    if isinstance(normalized, list):
        if not normalized:
            return []
        if isinstance(normalized[0], dict):
            return normalized
        return [{"value": item} for item in normalized]
    if isinstance(normalized, dict):
        return [{"key": key, "value": _stringify(val)} for key, val in normalized.items()]
    return [{"value": normalized}]


# --- shared helpers -------------------------------------------------------


def _fieldnames(records: Iterable[dict[str, Any]]) -> list[str]:
    fields: list[str] = []
    for record in records:
        for key in record:
            if key not in fields:
                fields.append(key)
    return fields or ["value"]


def _normalize(value: Any) -> Any:
    if _is_dataframe(value):
        return value.reset_index().to_dict(orient="records")
    if _is_series(value):
        return value.reset_index().to_dict(orient="records")
    if hasattr(value, "to_dict"):
        try:
            return value.to_dict()
        except TypeError:
            pass
    if isinstance(value, tuple):
        return list(value)
    return value


def _is_dataframe(value: Any) -> bool:
    return value.__class__.__name__ == "DataFrame" and hasattr(value, "to_csv")


def _is_series(value: Any) -> bool:
    return value.__class__.__name__ == "Series" and hasattr(value, "to_csv")


def _stringify(value: Any) -> str:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return "" if value is None else str(value)
