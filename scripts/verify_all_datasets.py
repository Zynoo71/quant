"""Exhaustively verify every dataset against live RQData via the real CLI path.

Calls all ~211 datasets through `build_dataset_kwargs` + the dotted-name resolver
(the exact code path `rqq data get` uses), with realistic sample params and a few
IDs discovered live (futures/option/convertible contract, fund manager/amc,
concept, option maturity). Classifies each as OK / EMPTY (valid call, no rows) /
ERROR / SKIP. Exits non-zero if any *unexpected* ERROR occurs.

Needs a live license + burns a little quota (one call per dataset).

    uv run --no-sync python scripts/verify_all_datasets.py
"""
from __future__ import annotations

import sys

from rqsdk_quant.datasets import DATASETS, build_dataset_kwargs, sample_value
from rqsdk_quant.rqdata_client import _resolve_attr, init_rqdatac

STOCK, INDEX, ETF, FUND = "000001.XSHE", "000300.XSHG", "510300.XSHG", "000003"
OPT_UNDERLYING, SPOT = "510050.XSHG", "AG999.SGEX"
START, END, DATE = "2024-01-02", "2024-01-31", "2024-01-03"

# Datasets whose rqdatac implementation is broken upstream (verified by calling
# rqdatac directly, bypassing rqq). Our wrapper forwards params correctly; the
# error originates inside rqdatac. Not counted as a failure. (Empty now that the
# deprecated+broken get_ksh_auction_info is excluded from the catalog.)
KNOWN_UPSTREAM_BROKEN: dict[str, str] = {}


def _first(value, *cols):
    try:
        if hasattr(value, "reset_index"):
            df = value.reset_index()
            for c in cols:
                if c in df.columns and len(df):
                    return str(df[c].iloc[0])
            for c in df.columns:
                if "order_book_id" in str(c).lower() and len(df):
                    return str(df[c].iloc[0])
            if len(df):
                return str(df.iloc[0, -1])
    except Exception:
        pass
    if isinstance(value, dict) and value:
        return str(next(iter(value)))
    if isinstance(value, (list, tuple)) and value:
        first = value[0]
        return str(first[cols[0]]) if isinstance(first, dict) and cols and cols[0] in first else str(first)
    return str(value) if isinstance(value, str) else None


def discover(rq) -> dict:
    d = {}
    probes = {
        "FUT": lambda: _first(rq.get_dominant_future("AG", start_date=START, end_date=START), "dominant", "value", 0),
        "OPT": lambda: _first(rq.options.get_contracts(OPT_UNDERLYING), "order_book_id"),
        "CONV": lambda: _first(rq.convertible.all_instruments(), "order_book_id"),
        "MANAGER": lambda: _first(rq.fund.get_manager(FUND), "manager_id", "id"),
        "AMC": lambda: _first(rq.fund.get_amc(), "amc_id", "id"),
        "CONCEPT": lambda: _first(rq.concept_list(), "concept", 0),
    }
    for k, fn in probes.items():
        try:
            d[k] = fn()
        except Exception as exc:
            d[k] = None
            print(f"  discover {k}: {type(exc).__name__}: {exc}")
    try:
        opt = d.get("OPT")
        d["MATURITY"] = str(getattr(rq.instruments(opt), "maturity_date", None)) if opt else None
    except Exception:
        d["MATURITY"] = None
    print("discovered:", d)
    return d


def value_for(spec, param, d):
    name, cat = spec.name, spec.category
    if param == "ids":
        if cat == "fund-mod":
            return FUND
        if name.startswith("etf-"):
            return ETF
        if cat == "indices-mod":
            return INDEX
        if cat == "convertible-mod":
            return d.get("CONV")
        if cat == "options-mod":
            return d.get("OPT")
        if cat == "futures-mod":
            return d.get("FUT")
        if name == "spot-benchmark-price":
            return SPOT
        return STOCK
    simple = {
        "underlying": OPT_UNDERLYING if cat == "options-mod" else "AG",
        "obj": d.get("FUT"), "start": START, "end": END, "date": DATE, "trading_date": DATE,
        "start_time": "2024-01-02 09:30:00", "end_time": "2024-01-02 15:00:00",
        "start_quarter": "2023q1", "end_quarter": "2023q4", "quarter": "2023q4", "fiscal_year": 2024,
        "industries": "银行", "industry": "银行", "indexes": INDEX, "factor": "pe_ratio_ttm",
        "factors": "beta,momentum", "concepts": d.get("CONCEPT"), "amc_ids": d.get("AMC"),
        "manager_id": d.get("MANAGER"), "manager_ids": d.get("MANAGER"), "managers": d.get("MANAGER"),
        "n": 5, "offset": 5, "index_name": "银行", "industry_name": "银行",
        "maturity": d.get("MATURITY"), "names": "M2",
        "code": "Financials" if name == "sector" else "A01",
        "category": {"concept": "人工智能"},
    }
    if param in simple:
        return simple[param]
    s = sample_value(param)
    return None if s.startswith("<") else s


# Datasets whose rqdatac function requires a param at runtime that its signature
# marks optional (so it isn't auto-supplied as "required").
EXTRA_PARAMS = {"options-greeks": {"start": START, "end": END}}


def resolve(spec, d):
    params = {}
    for p in spec.required:
        v = value_for(spec, p, d)
        if v is None:
            return None, p
        params[p] = v
    params.update(EXTRA_PARAMS.get(spec.name, {}))
    return params, None


def classify(v):
    if v is None:
        return "EMPTY", 0
    if hasattr(v, "empty"):
        return ("EMPTY" if v.empty else "OK"), int(v.shape[0])
    if isinstance(v, (list, tuple, dict, str)):
        return ("EMPTY" if len(v) == 0 else "OK"), len(v)
    return "OK", 1


def main() -> int:
    rq = init_rqdatac()
    d = discover(rq)
    rows = []
    for name, spec in DATASETS.items():
        params, missing = resolve(spec, d)
        if params is None:
            rows.append((name, spec.category, "SKIP", f"unresolved required param: {missing}"))
            continue
        try:
            value = _resolve_attr(rq, spec.function)(**build_dataset_kwargs(spec, params))
            status, n = classify(value)
            rows.append((name, spec.category, status, f"rows={n}"))
        except Exception as exc:
            tag = "KNOWN" if name in KNOWN_UPSTREAM_BROKEN else "ERROR"
            rows.append((name, spec.category, tag, f"{type(exc).__name__}: {exc}"))

    counts: dict[str, int] = {}
    for _, _, status, _ in rows:
        counts[status] = counts.get(status, 0) + 1
    print("\n==== SUMMARY ====", counts, "total", len(rows))
    for tag in ("ERROR", "KNOWN", "SKIP"):
        items = [(n, c, det) for n, c, s, det in rows if s == tag]
        if items:
            print(f"\n==== {tag} ====")
            for n, c, det in items:
                print(f"[{c}] {n}: {det}")

    unexpected = counts.get("ERROR", 0)
    print(f"\n{'PASS' if not unexpected else 'FAIL'}: {unexpected} unexpected error(s).")
    return 1 if unexpected else 0


if __name__ == "__main__":
    raise SystemExit(main())
