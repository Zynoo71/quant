#!/usr/bin/env python
"""Generate src/rqsdk_quant/catalog.py from the installed rqdatac's signatures.

Dev-only tool. The committed `catalog.py` is stdlib-only so metadata commands
(`rqq data list/describe`, `rqq help`) work without rqdatac installed; this script
keeps it in sync with the SDK.

    uv run --no-sync python scripts/gen_catalog.py          # regenerate catalog.py
    uv run --no-sync python scripts/gen_catalog.py --check  # fail if out of date

`CURATED` is the ONLY hand-maintained data: function dotted path -> (module slug,
public dataset name, one-line description). Param structure (required / list /
bool) is read from the live signature, never hand-written. The generator asserts
every callable data function is curated and every public name is unique, so a new
rqdatac release surfaces as an explicit "uncurated function" failure.
"""
from __future__ import annotations

import inspect
import sys
import types
from pathlib import Path

import rqdatac
import rqdatac_fund  # noqa: F401  (registers the `fund` namespace on rqdatac)

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "src" / "rqsdk_quant" / "catalog.py"

# Namespaces to mirror (top-level handled separately).
NAMESPACES = ("fund", "etf", "econ", "options", "convertible", "futures")

# Infrastructure / non-data functions that are never wrapped as datasets.
EXCLUDE = {
    "info", "init", "initialized", "is_data_ready", "reset", "version",
    "get_update_status", "get_temporary_code",
    "concept",  # *concepts varargs — use get_concept / concept_names instead
    # deprecated since 2021 AND broken upstream (raises `fields: got invalided
    # value cn` even called directly); its replacement get_auction_info is
    # already wrapped as `auction-info`.
    "get_ksh_auction_info",
}

# function dotted path -> (module slug, public name, description)
CURATED: dict[str, tuple[str, str, str]] = {
    # ---- 跨品种通用 API (generic-api) ----
    "all_instruments": ("generic-api", "instruments", "全市场证券基础信息列表"),
    "instruments": ("generic-api", "instrument", "单个/多个证券详细信息"),
    "id_convert": ("generic-api", "id-convert", "证券代码转换为 order_book_id"),
    "get_basic_info": ("generic-api", "basic-info", "证券基础信息字段查询"),
    "get_price": ("generic-api", "price", "历史行情（日/分钟/tick）"),
    "get_price_change_rate": ("generic-api", "price-change-rate", "区间涨跌幅"),
    "get_vwap": ("generic-api", "vwap", "成交量加权平均价"),
    "current_snapshot": ("generic-api", "current-snapshot", "当前行情快照"),
    "current_minute": ("generic-api", "current-minute", "当前分钟行情快照"),
    "get_ticks": ("generic-api", "ticks", "历史 tick 行情"),
    "get_live_ticks": ("generic-api", "live-ticks", "实时 tick 行情"),
    "get_live_minute_price_change_rate": ("generic-api", "live-minute-price-change-rate", "实时分钟涨跌幅"),
    "get_auction_info": ("generic-api", "auction-info", "竞价行情信息"),
    "get_open_auction_info": ("generic-api", "open-auction-info", "开盘集合竞价信息"),
    "get_close_auction_info": ("generic-api", "close-auction-info", "收盘集合竞价信息"),
    "get_tick_size": ("generic-api", "tick-size", "最小变动价位"),
    "get_trading_dates": ("generic-api", "trading-dates", "交易日历"),
    "get_previous_trading_date": ("generic-api", "previous-trading-date", "向前第 n 个交易日"),
    "get_next_trading_date": ("generic-api", "next-trading-date", "向后第 n 个交易日"),
    "get_latest_trading_date": ("generic-api", "latest-trading-date", "最新交易日"),
    "is_trading_date": ("generic-api", "is-trading-date", "是否交易日"),
    "trading_date_offset": ("generic-api", "trading-date-offset", "交易日偏移"),
    "get_trading_hours": ("generic-api", "trading-hours", "交易时段"),
    "get_trading_periods": ("generic-api", "trading-periods", "交易小节时段"),
    "get_yield_curve": ("generic-api", "yield-curve", "国债收益率曲线"),
    "get_future_latest_trading_date": ("generic-api", "future-latest-trading-date", "期货最新交易日"),

    # ---- A股 (stock-mod) ----
    "get_pit_financials_ex": ("stock-mod", "financials-pit", "PIT 季度财务数据"),
    "current_performance": ("stock-mod", "current-performance", "财务快报"),
    "performance_forecast": ("stock-mod", "performance-forecast", "业绩预告"),
    "get_forecast_report_date": ("stock-mod", "forecast-report-date", "定期报告预约披露日"),
    "get_audit_opinion": ("stock-mod", "audit-opinion", "财务报表审计意见"),
    "get_shares": ("stock-mod", "shares", "股本结构"),
    "get_ex_factor": ("stock-mod", "ex-factor", "复权因子"),
    "get_dividend": ("stock-mod", "dividend", "分红"),
    "get_dividend_amount": ("stock-mod", "dividend-amount", "分红总额"),
    "get_dividend_info": ("stock-mod", "dividend-info", "分红预案明细"),
    "get_split": ("stock-mod", "split", "拆股"),
    "get_allotment": ("stock-mod", "allotment", "配股"),
    "get_buy_back": ("stock-mod", "buy-back", "股份回购"),
    "get_incentive_plan": ("stock-mod", "incentive-plan", "股权激励计划"),
    "get_private_placement": ("stock-mod", "private-placement", "定向增发"),
    "get_restricted_shares": ("stock-mod", "restricted-shares", "限售股解禁"),
    "get_share_transformation": ("stock-mod", "share-transformation", "股权分置/股份变更"),
    "get_turnover_rate": ("stock-mod", "turnover-rate", "换手率"),
    "current_freefloat_turnover": ("stock-mod", "current-freefloat-turnover", "当日自由流通换手率"),
    "is_st_stock": ("stock-mod", "st", "是否 ST"),
    "st_warning": ("stock-mod", "st-warning", "ST 风险警示预告"),
    "get_special_treatment_info": ("stock-mod", "special-treatment-info", "ST 特别处理信息"),
    "is_suspended": ("stock-mod", "suspended", "是否停牌"),
    "get_symbol_change_info": ("stock-mod", "symbol-change-info", "证券简称变更"),
    "get_holder_number": ("stock-mod", "holder-number", "股东户数"),
    "get_main_shareholder": ("stock-mod", "main-shareholder", "主要股东"),
    "get_leader_shares_change": ("stock-mod", "leader-shares-change", "董监高持股变动"),
    "get_staff_count": ("stock-mod", "staff-count", "员工人数"),
    "get_capital_flow": ("stock-mod", "capital-flow", "资金流向"),
    "current_capital_flow_minute": ("stock-mod", "current-capital-flow-minute", "当日分钟资金流"),
    "get_stock_connect": ("stock-mod", "stock-connect", "陆股通持股"),
    "get_stock_connect_holding_details": ("stock-mod", "stock-connect-holding-details", "陆股通持股明细"),
    "get_stock_connect_quota": ("stock-mod", "stock-connect-quota", "陆股通额度历史"),
    "current_stock_connect_quota": ("stock-mod", "current-stock-connect-quota", "当前陆股通额度"),
    "get_securities_margin": ("stock-mod", "securities-margin", "融资融券"),
    "get_margin_stocks": ("stock-mod", "margin-stocks", "融资融券标的列表"),
    "get_margin_haircut": ("stock-mod", "margin-haircut", "融资融券折算率"),
    "get_eligible_securities_margin": ("stock-mod", "eligible-securities-margin", "融资融券标的资格"),
    "get_block_trade": ("stock-mod", "block-trade", "大宗交易"),
    "get_abnormal_stocks": ("stock-mod", "abnormal-stocks", "龙虎榜/异动股票列表"),
    "get_abnormal_stocks_detail": ("stock-mod", "abnormal-stocks-detail", "龙虎榜/异动明细"),
    "get_announcement": ("stock-mod", "announcement", "公司公告"),
    "get_investor_qa": ("stock-mod", "investor-qa", "投资者问答"),
    "get_investor_ra": ("stock-mod", "investor-ra", "投资者关系活动/调研"),
    "get_instrument_industry": ("stock-mod", "instrument-industry", "证券所属行业"),
    "get_industry": ("stock-mod", "industry", "行业成分股"),
    "get_industry_mapping": ("stock-mod", "industry-mapping", "行业分类映射"),
    "get_industry_change": ("stock-mod", "industry-change", "行业成分变更"),
    "industry": ("stock-mod", "industry-by-code", "按行业代码取成分股"),
    "sector": ("stock-mod", "sector", "板块成分股"),
    "shenwan_industry": ("stock-mod", "shenwan-industry", "申万行业成分"),
    "shenwan_instrument_industry": ("stock-mod", "shenwan-instrument-industry", "证券申万行业分类"),
    "zx_industry": ("stock-mod", "zx-industry", "中信行业成分"),
    "zx_instrument_industry": ("stock-mod", "zx-instrument-industry", "证券中信行业分类"),
    "jy_instrument_industry": ("stock-mod", "jy-instrument-industry", "证券聚源行业分类"),

    # ---- 风险因子 / 因子 (risk-factors-mod) ----
    "get_all_factor_names": ("risk-factors-mod", "factor-names", "全部因子名称"),
    "get_factor": ("risk-factors-mod", "factor", "因子值"),
    "get_factor_exposure": ("risk-factors-mod", "factor-exposure", "风险模型因子暴露"),
    "get_style_factor_exposure": ("risk-factors-mod", "style-factor-exposure", "风格因子暴露"),
    "get_descriptor_exposure": ("risk-factors-mod", "descriptor-exposure", "风险模型细分描述因子暴露"),
    "get_index_factor_exposure": ("risk-factors-mod", "index-factor-exposure", "指数因子暴露"),
    "get_factor_return": ("risk-factors-mod", "factor-return", "因子收益率"),
    "get_live_factor_return": ("risk-factors-mod", "live-factor-return", "实时因子收益率"),
    "get_factor_covariance": ("risk-factors-mod", "factor-covariance", "因子协方差矩阵"),
    "get_specific_return": ("risk-factors-mod", "specific-return", "个股特异收益率"),
    "get_specific_risk": ("risk-factors-mod", "specific-risk", "个股特异风险"),
    "get_stock_beta": ("risk-factors-mod", "stock-beta", "个股 Beta"),

    # ---- 指数、场内基金 (indices-mod) ----
    "index_components": ("indices-mod", "index-components", "指数成分股"),
    "index_weights": ("indices-mod", "index-weights", "指数成分权重"),
    "index_weights_ex": ("indices-mod", "index-weights-ex", "指数成分权重（扩展）"),
    "index_indicator": ("indices-mod", "index-indicator", "指数估值指标"),
    "etf.get_components": ("indices-mod", "etf-components", "ETF 申赎成分清单"),
    "etf.get_cash_components": ("indices-mod", "etf-cash-components", "ETF 申赎现金差额"),
    "etf.get_daily_units": ("indices-mod", "etf-daily-units", "ETF 每日份额"),

    # ---- 另类数据 (alternative-data) ----
    "get_consensus_price": ("alternative-data", "consensus-price", "一致预期目标价（按机构逐条）"),
    "get_consensus_comp_indicators": ("alternative-data", "consensus-comp-indicators", "公司一致预期综合指标"),
    "get_consensus_indicator": ("alternative-data", "consensus-indicator", "一致预期财务指标（每行含研报标题/分析师/机构/摘要）"),
    "get_consensus_market_estimate": ("alternative-data", "consensus-market-estimate", "市场一致预期"),
    "get_consensus_industry_rating": ("alternative-data", "consensus-industry-rating", "行业一致预期评级"),
    "all_consensus_industries": ("alternative-data", "consensus-industries", "一致预期行业列表"),
    "get_current_news": ("alternative-data", "current-news", "实时新闻流"),
    "concept_list": ("alternative-data", "concept-list", "概念板块列表"),
    "concept_names": ("alternative-data", "concept-names", "证券所属概念板块名称"),
    "get_concept": ("alternative-data", "concept", "概念板块成分股"),
    "get_concept_list": ("alternative-data", "concept-list-range", "区间概念板块列表"),
    "get_stock_concept": ("alternative-data", "stock-concept", "个股所属概念"),

    # ---- 现货 (spot-goods) ----
    "get_spot_benchmark_price": ("spot-goods", "spot-benchmark-price", "现货基准价"),

    # ---- 货币市场 (repo) ----
    "get_interbank_offered_rate": ("repo", "interbank-offered-rate", "银行间同业拆借利率 (Shibor)"),
    "econ.get_fixing_repo_rate": ("repo", "econ-fixing-repo-rate", "回购定盘利率"),
    "econ.get_interbank_pledged_repo_rate": ("repo", "econ-interbank-pledged-repo-rate", "银行间质押式回购利率"),

    # ---- 宏观经济 (macro-economy) ----
    "get_exchange_rate": ("macro-economy", "exchange-rate", "人民币汇率"),
    "econ.get_money_supply": ("macro-economy", "econ-money-supply", "货币供应量"),
    "econ.get_reserve_ratio": ("macro-economy", "econ-reserve-ratio", "存款准备金率"),
    "econ.get_factors": ("macro-economy", "econ-factors", "宏观经济指标因子"),
    "econ.get_index": ("macro-economy", "econ-index", "宏观经济指数"),
    "econ.get_gold_reserves": ("macro-economy", "econ-gold-reserves", "黄金储备"),
    "econ.get_oil_price": ("macro-economy", "econ-oil-price", "成品油价格"),
    "econ.get_us_treasury_yield": ("macro-economy", "econ-us-treasury-yield", "美国国债收益率"),
    "econ.get_cny_reference_rate": ("macro-economy", "econ-cny-reference-rate", "人民币汇率中间价"),

    # ---- 期货 (futures-mod) ----
    "get_dominant_future": ("futures-mod", "dominant-future", "期货主力合约"),
    "get_future_contracts": ("futures-mod", "future-contracts", "期货可交易合约列表"),
    "future_commission_margin": ("futures-mod", "future-commission-margin", "期货手续费及保证金率"),
    "get_future_member_rank": ("futures-mod", "future-member-rank", "期货会员持仓排名"),
    "has_night_trading": ("futures-mod", "has-night-trading", "是否有夜盘交易"),
    "futures.get_dominant": ("futures-mod", "futures-dominant", "期货主力/次主力合约"),
    "futures.get_dominant_price": ("futures-mod", "futures-dominant-price", "期货主力连续行情"),
    "futures.get_ex_factor": ("futures-mod", "futures-ex-factor", "期货主力连续复权因子"),
    "futures.get_contracts": ("futures-mod", "futures-contracts", "期货合约列表"),
    "futures.get_continuous_contracts": ("futures-mod", "futures-continuous-contracts", "期货连续合约"),
    "futures.get_contract_multiplier": ("futures-mod", "futures-contract-multiplier", "期货合约乘数"),
    "futures.get_basis": ("futures-mod", "futures-basis", "期货基差"),
    "futures.get_current_basis": ("futures-mod", "futures-current-basis", "期货实时基差"),
    "futures.get_exchange_daily": ("futures-mod", "futures-exchange-daily", "期货交易所日行情"),
    "futures.get_member_rank": ("futures-mod", "futures-member-rank", "期货会员成交持仓排名"),
    "futures.get_warehouse_stocks": ("futures-mod", "futures-warehouse-stocks", "期货仓单库存"),
    "futures.get_roll_yield": ("futures-mod", "futures-roll-yield", "期货展期收益率"),
    "futures.get_trading_parameters": ("futures-mod", "futures-trading-parameters", "期货交易参数"),
    "futures.get_commission_margin": ("futures-mod", "futures-commission-margin", "期货手续费及保证金"),
    "futures.get_predicted_dividend_point": ("futures-mod", "futures-predicted-dividend-point", "股指期货预测分红点位"),

    # ---- 期权 (options-mod) ----
    "options.get_contracts": ("options-mod", "options-contracts", "期权合约筛选"),
    "options.get_contract_property": ("options-mod", "options-contract-property", "期权合约属性"),
    "options.get_atm_option": ("options-mod", "options-atm-option", "平值期权合约"),
    "options.get_dominant_month": ("options-mod", "options-dominant-month", "期权主力月份"),
    "options.get_greeks": ("options-mod", "options-greeks", "期权希腊字母"),
    "options.get_indicators": ("options-mod", "options-indicators", "期权指标"),
    "options.get_commission": ("options-mod", "options-commission", "期权手续费"),

    # ---- 可转债 (convertible-mod) ----
    "convertible.all_instruments": ("convertible-mod", "convertible-instruments", "可转债基础信息列表"),
    "convertible.instruments": ("convertible-mod", "convertible-instrument", "可转债详细信息"),
    "convertible.get_close_price": ("convertible-mod", "convertible-close-price", "可转债收盘价"),
    "convertible.get_indicators": ("convertible-mod", "convertible-indicators", "可转债估值指标"),
    "convertible.get_conversion_price": ("convertible-mod", "convertible-conversion-price", "可转债转股价"),
    "convertible.get_conversion_info": ("convertible-mod", "convertible-conversion-info", "可转债转股信息"),
    "convertible.get_call_info": ("convertible-mod", "convertible-call-info", "可转债赎回信息"),
    "convertible.get_call_announcement": ("convertible-mod", "convertible-call-announcement", "可转债赎回公告"),
    "convertible.get_put_info": ("convertible-mod", "convertible-put-info", "可转债回售信息"),
    "convertible.get_cash_flow": ("convertible-mod", "convertible-cash-flow", "可转债现金流"),
    "convertible.get_coupon_rate_table": ("convertible-mod", "convertible-coupon-rate", "可转债票面利率表"),
    "convertible.get_accrued_interest_eod": ("convertible-mod", "convertible-accrued-interest", "可转债应计利息"),
    "convertible.get_credit_rating": ("convertible-mod", "convertible-credit-rating", "可转债信用评级"),
    "convertible.get_latest_rating": ("convertible-mod", "convertible-latest-rating", "可转债最新评级"),
    "convertible.rating": ("convertible-mod", "convertible-rating", "可转债评级列表"),
    "convertible.get_std_discount": ("convertible-mod", "convertible-std-discount", "可转债标准券折算率"),
    "convertible.get_industry": ("convertible-mod", "convertible-industry", "可转债行业成分"),
    "convertible.get_instrument_industry": ("convertible-mod", "convertible-instrument-industry", "可转债所属行业"),
    "convertible.is_suspended": ("convertible-mod", "convertible-suspended", "可转债是否停牌"),

    # ---- 基金 (fund-mod) ----
    "fund.all_instruments": ("fund-mod", "fund-instruments", "基金基础信息列表"),
    "fund.instruments": ("fund-mod", "fund-instrument", "基金详细信息"),
    "fund.get_nav": ("fund-mod", "fund-nav", "基金净值"),
    "fund.get_benchmark": ("fund-mod", "fund-benchmark", "基金业绩比较基准"),
    "fund.get_benchmark_price": ("fund-mod", "fund-benchmark-price", "基金基准指数价格"),
    "fund.get_indicators": ("fund-mod", "fund-indicators", "基金业绩指标"),
    "fund.get_snapshot": ("fund-mod", "fund-snapshot", "基金指标快照"),
    "fund.get_ratings": ("fund-mod", "fund-ratings", "基金评级"),
    "fund.get_holdings": ("fund-mod", "fund-holdings", "基金持仓明细"),
    "fund.get_stock_change": ("fund-mod", "fund-stock-change", "基金重大持仓变动"),
    "fund.get_asset_allocation": ("fund-mod", "fund-asset-allocation", "基金资产配置"),
    "fund.get_industry_allocation": ("fund-mod", "fund-industry-allocation", "基金行业配置"),
    "fund.get_holder_structure": ("fund-mod", "fund-holder-structure", "基金持有人结构"),
    "fund.get_daily_units": ("fund-mod", "fund-daily-units", "基金每日份额"),
    "fund.get_units_change": ("fund-mod", "fund-units-change", "基金份额变动"),
    "fund.get_dividend": ("fund-mod", "fund-dividend", "基金分红"),
    "fund.get_split": ("fund-mod", "fund-split", "基金拆分"),
    "fund.get_ex_factor": ("fund-mod", "fund-ex-factor", "基金复权因子"),
    "fund.get_financials": ("fund-mod", "fund-financials", "基金财务数据"),
    "fund.get_manager": ("fund-mod", "fund-manager", "基金经理信息"),
    "fund.get_manager_info": ("fund-mod", "fund-manager-info", "基金经理档案"),
    "fund.get_manager_indicators": ("fund-mod", "fund-manager-indicators", "基金经理业绩指标"),
    "fund.get_manager_weight_info": ("fund-mod", "fund-manager-weight-info", "基金经理任职权重"),
    "fund.get_amc": ("fund-mod", "fund-amc", "基金管理人信息"),
    "fund.get_amc_rank": ("fund-mod", "fund-amc-rank", "基金管理人规模排名"),
    "fund.get_category": ("fund-mod", "fund-category", "基金分类成分"),
    "fund.get_category_mapping": ("fund-mod", "fund-category-mapping", "基金分类映射"),
    "fund.get_instrument_category": ("fund-mod", "fund-instrument-category", "基金所属分类"),
    "fund.get_fee": ("fund-mod", "fund-fee", "基金费率"),
    "fund.get_transaction_status": ("fund-mod", "fund-transaction-status", "基金申赎状态"),
    "fund.get_related_code": ("fund-mod", "fund-related-code", "基金关联代码（场内外）"),
    "fund.get_transition_info": ("fund-mod", "fund-transition-info", "基金转型信息"),
    "fund.get_etf_components": ("fund-mod", "fund-etf-components", "ETF 申赎成分清单（基金口径）"),
    "fund.get_etf_cash_components": ("fund-mod", "fund-etf-cash-components", "ETF 申赎现金差额（基金口径）"),
    "fund.get_credit_quality": ("fund-mod", "fund-credit-quality", "基金信用质量分布"),
    "fund.get_bond_stru": ("fund-mod", "fund-bond-stru", "基金债券类属配置"),
    "fund.get_bond_structure": ("fund-mod", "fund-bond-structure", "基金债券持仓结构"),
    "fund.get_term_to_maturity": ("fund-mod", "fund-term-to-maturity", "基金持仓剩余期限"),
    "fund.get_irr_sensitivity": ("fund-mod", "fund-irr-sensitivity", "基金利率敏感性"),
    "fund.get_qdii_scope": ("fund-mod", "fund-qdii-scope", "QDII 投资范围"),
}


def _is_data_fn(obj: object) -> bool:
    return callable(obj) and not inspect.isclass(obj) and not isinstance(obj, types.ModuleType)


def iter_callables() -> dict[str, object]:
    """Return {dotted_path: callable} for every rqdatac data function."""
    found: dict[str, object] = {}
    for name in dir(rqdatac):
        if name.startswith("_") or name in EXCLUDE:
            continue
        obj = getattr(rqdatac, name)
        if _is_data_fn(obj):
            found[name] = obj
    for ns in NAMESPACES:
        nsobj = getattr(rqdatac, ns, None)
        if nsobj is None:
            continue
        for name in dir(nsobj):
            if name.startswith("_"):
                continue
            obj = getattr(nsobj, name)
            if _is_data_fn(obj):
                found[f"{ns}.{name}"] = obj
    return found


def params_spec(fn: object) -> str:
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return ""
    tokens = []
    for param in sig.parameters.values():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        required = param.default is inspect.Parameter.empty
        is_bool = (not required) and isinstance(param.default, bool)
        token = ("!" if required else "") + param.name + (":bool" if is_bool else "")
        tokens.append(token)
    return " ".join(tokens)


def build_rows() -> list[tuple[str, str, str, str, str]]:
    callables = iter_callables()

    uncurated = sorted(set(callables) - set(CURATED))
    if uncurated:
        raise SystemExit(
            "Uncurated rqdatac functions (add to CURATED or EXCLUDE in gen_catalog.py):\n  "
            + "\n  ".join(uncurated)
        )
    stale = sorted(set(CURATED) - set(callables))
    if stale:
        raise SystemExit("CURATED entries not found in rqdatac (stale):\n  " + "\n  ".join(stale))

    rows: list[tuple[str, str, str, str, str]] = []
    seen_names: dict[str, str] = {}
    for path, fn in callables.items():
        module, name, desc = CURATED[path]
        if name in seen_names:
            raise SystemExit(f"Duplicate dataset name `{name}` from {path} and {seen_names[name]}")
        seen_names[name] = path
        rows.append((name, path, module, desc, params_spec(fn)))
    return rows


MODULE_ORDER = [
    "generic-api", "stock-mod", "stock-hk", "futures-mod", "options-mod",
    "indices-mod", "fund-mod", "convertible-mod", "risk-factors-mod",
    "spot-goods", "repo", "macro-economy", "alternative-data", "ricequant-index",
]


def render(rows: list[tuple[str, str, str, str, str]]) -> str:
    rows = sorted(rows, key=lambda r: (MODULE_ORDER.index(r[2]) if r[2] in MODULE_ORDER else 99, r[0]))
    lines = [
        '"""Auto-generated by scripts/gen_catalog.py — DO NOT EDIT BY HAND.',
        "",
        "Regenerate after upgrading rqdatac:",
        "    uv run --no-sync python scripts/gen_catalog.py",
        '"""',
        "from .datasets import DatasetSpec",
        "",
        "DATASETS = {",
        "    spec.name: spec",
        "    for spec in (",
    ]
    for name, path, module, desc, pspec in rows:
        lines.append(
            f'        DatasetSpec("{name}", "{path}", "{module}", "{desc}", "{pspec}"),'
        )
    lines.append("    )")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    rows = build_rows()
    rendered = render(rows)
    if "--check" in argv:
        current = CATALOG_PATH.read_text(encoding="utf-8") if CATALOG_PATH.exists() else ""
        if current != rendered:
            print("catalog.py is out of date — run: uv run --no-sync python scripts/gen_catalog.py")
            return 1
        print(f"catalog.py up to date ({len(rows)} datasets).")
        return 0
    CATALOG_PATH.write_text(rendered, encoding="utf-8")
    print(f"Wrote {CATALOG_PATH.relative_to(REPO_ROOT)} ({len(rows)} datasets).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
