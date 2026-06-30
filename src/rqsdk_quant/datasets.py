from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .errors import CliError


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    function: str
    category: str
    description: str
    param_map: dict[str, str] = field(default_factory=dict)
    defaults: dict[str, Any] = field(default_factory=dict)
    required: tuple[str, ...] = ()
    list_params: tuple[str, ...] = ()
    bool_params: tuple[str, ...] = ()
    positional: tuple[str, ...] = ()

    def public_params(self) -> list[str]:
        params = set(self.param_map)
        params.update(self.defaults)
        params.update(self.required)
        params.update(self.list_params)
        params.update(self.bool_params)
        return sorted(params)


DATASETS: dict[str, DatasetSpec] = {
    "instruments": DatasetSpec(
        name="instruments",
        function="all_instruments",
        category="master",
        description="证券基础信息列表，对应 rqdatac.all_instruments。",
        param_map={"instrument_type": "type", "date": "date", "market": "market"},
        defaults={"instrument_type": "CS", "market": "cn"},
    ),
    "instrument": DatasetSpec(
        name="instrument",
        function="instruments",
        category="master",
        description="单个或多个证券详细信息，对应 rqdatac.instruments。",
        param_map={"ids": "order_book_ids", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        defaults={"market": "cn"},
    ),
    "id-convert": DatasetSpec(
        name="id-convert",
        function="id_convert",
        category="master",
        description="证券代码转换为米筐 order_book_id，对应 rqdatac.id_convert。",
        param_map={"ids": "order_book_ids", "to": "to"},
        required=("ids",),
        list_params=("ids",),
    ),
    "trading-dates": DatasetSpec(
        name="trading-dates",
        function="get_trading_dates",
        category="calendar",
        description="交易日历，对应 rqdatac.get_trading_dates。",
        param_map={"start": "start_date", "end": "end_date", "market": "market"},
        required=("start", "end"),
        defaults={"market": "cn"},
    ),
    "previous-trading-date": DatasetSpec(
        name="previous-trading-date",
        function="get_previous_trading_date",
        category="calendar",
        description="向前第 n 个交易日，对应 rqdatac.get_previous_trading_date。",
        param_map={"date": "date", "n": "n", "market": "market"},
        required=("date",),
        defaults={"n": 1, "market": "cn"},
    ),
    "next-trading-date": DatasetSpec(
        name="next-trading-date",
        function="get_next_trading_date",
        category="calendar",
        description="向后第 n 个交易日，对应 rqdatac.get_next_trading_date。",
        param_map={"date": "date", "n": "n", "market": "market"},
        required=("date",),
        defaults={"n": 1, "market": "cn"},
    ),
    "price": DatasetSpec(
        name="price",
        function="get_price",
        category="market",
        description="历史行情，对应 rqdatac.get_price。",
        param_map={
            "ids": "order_book_ids",
            "start": "start_date",
            "end": "end_date",
            "frequency": "frequency",
            "fields": "fields",
            "adjust_type": "adjust_type",
            "skip_suspended": "skip_suspended",
            "expect_df": "expect_df",
            "market": "market",
        },
        required=("ids",),
        list_params=("ids", "fields"),
        bool_params=("skip_suspended", "expect_df"),
        defaults={"frequency": "1d", "adjust_type": "pre", "skip_suspended": False, "expect_df": True, "market": "cn"},
    ),
    "current-snapshot": DatasetSpec(
        name="current-snapshot",
        function="current_snapshot",
        category="market",
        description="当前快照行情，对应 rqdatac.current_snapshot。",
        param_map={"ids": "order_book_ids", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        defaults={"market": "cn"},
    ),
    "current-minute": DatasetSpec(
        name="current-minute",
        function="current_minute",
        category="market",
        description="当前分钟行情，对应 rqdatac.current_minute。",
        param_map={"ids": "order_book_ids", "fields": "fields", "skip_suspended": "skip_suspended", "market": "market"},
        required=("ids",),
        list_params=("ids", "fields"),
        bool_params=("skip_suspended",),
        defaults={"skip_suspended": False, "market": "cn"},
    ),
    "ticks": DatasetSpec(
        name="ticks",
        function="get_ticks",
        category="market",
        description="历史 tick 数据，对应 rqdatac.get_ticks。",
        param_map={"ids": "order_book_id", "start": "start_date", "end": "end_date", "expect_df": "expect_df", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        bool_params=("expect_df",),
        defaults={"expect_df": True, "market": "cn"},
    ),
    "factor-names": DatasetSpec(
        name="factor-names",
        function="get_all_factor_names",
        category="factor",
        description="全部因子名称，对应 rqdatac.get_all_factor_names。",
        param_map={"factor_type": "type", "market": "market"},
        defaults={"market": "cn"},
    ),
    "factor": DatasetSpec(
        name="factor",
        function="get_factor",
        category="factor",
        description="因子值，对应 rqdatac.get_factor。",
        param_map={"ids": "order_book_ids", "factor": "factor", "start": "start_date", "end": "end_date", "universe": "universe", "expect_df": "expect_df", "market": "market"},
        required=("ids", "factor"),
        list_params=("ids", "factor"),
        bool_params=("expect_df",),
        defaults={"expect_df": True, "market": "cn"},
    ),
    "shares": DatasetSpec(
        name="shares",
        function="get_shares",
        category="equity",
        description="股本数据，对应 rqdatac.get_shares。",
        param_map={"ids": "order_book_ids", "start": "start_date", "end": "end_date", "fields": "fields", "expect_df": "expect_df", "market": "market"},
        required=("ids",),
        list_params=("ids", "fields"),
        bool_params=("expect_df",),
        defaults={"expect_df": True, "market": "cn"},
    ),
    "dividend": DatasetSpec(
        name="dividend",
        function="get_dividend",
        category="equity",
        description="分红数据，对应 rqdatac.get_dividend。",
        param_map={"ids": "order_book_ids", "start": "start_date", "end": "end_date", "adjusted": "adjusted", "expect_df": "expect_df", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        bool_params=("adjusted", "expect_df"),
        defaults={"adjusted": False, "expect_df": True, "market": "cn"},
    ),
    "split": DatasetSpec(
        name="split",
        function="get_split",
        category="equity",
        description="拆股数据，对应 rqdatac.get_split。",
        param_map={"ids": "order_book_ids", "start": "start_date", "end": "end_date", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        defaults={"market": "cn"},
    ),
    "turnover-rate": DatasetSpec(
        name="turnover-rate",
        function="get_turnover_rate",
        category="equity",
        description="换手率，对应 rqdatac.get_turnover_rate。",
        param_map={"ids": "order_book_ids", "start": "start_date", "end": "end_date", "fields": "fields", "expect_df": "expect_df", "market": "market"},
        required=("ids",),
        list_params=("ids", "fields"),
        bool_params=("expect_df",),
        defaults={"expect_df": True, "market": "cn"},
    ),
    "st": DatasetSpec(
        name="st",
        function="is_st_stock",
        category="equity",
        description="ST 状态，对应 rqdatac.is_st_stock。",
        param_map={"ids": "order_book_ids", "start": "start_date", "end": "end_date", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        defaults={"market": "cn"},
    ),
    "suspended": DatasetSpec(
        name="suspended",
        function="is_suspended",
        category="equity",
        description="停牌状态，对应 rqdatac.is_suspended。",
        param_map={"ids": "order_book_ids", "start": "start_date", "end": "end_date", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        defaults={"market": "cn"},
    ),
    "financials-pit": DatasetSpec(
        name="financials-pit",
        function="get_pit_financials_ex",
        category="financial",
        description="PIT 季度财务数据，对应 rqdatac.get_pit_financials_ex。",
        param_map={
            "ids": "order_book_ids",
            "fields": "fields",
            "start_quarter": "start_quarter",
            "end_quarter": "end_quarter",
            "date": "date",
            "statements": "statements",
            "market": "market",
        },
        required=("ids", "fields", "start_quarter", "end_quarter"),
        list_params=("ids", "fields"),
        defaults={"statements": "latest", "market": "cn"},
    ),
    "performance-forecast": DatasetSpec(
        name="performance-forecast",
        function="performance_forecast",
        category="financial",
        description="业绩预告数据，对应 rqdatac.performance_forecast。",
        param_map={
            "ids": "order_book_ids",
            "info_date": "info_date",
            "end": "end_date",
            "fields": "fields",
            "market": "market",
        },
        required=("ids",),
        list_params=("ids", "fields"),
        defaults={"market": "cn"},
    ),
    "current-performance": DatasetSpec(
        name="current-performance",
        function="current_performance",
        category="financial",
        description="财务快报数据，对应 rqdatac.current_performance。",
        param_map={
            "ids": "order_book_ids",
            "info_date": "info_date",
            "quarter": "quarter",
            "interval": "interval",
            "fields": "fields",
            "market": "market",
        },
        required=("ids",),
        list_params=("ids", "fields"),
        defaults={"interval": "1q", "market": "cn"},
    ),
    "forecast-report-date": DatasetSpec(
        name="forecast-report-date",
        function="get_forecast_report_date",
        category="financial",
        description="定期报告预约披露日，对应 rqdatac.get_forecast_report_date。",
        param_map={
            "ids": "order_book_ids",
            "start_quarter": "start_quarter",
            "end_quarter": "end_quarter",
            "market": "market",
        },
        required=("ids", "start_quarter", "end_quarter"),
        list_params=("ids",),
        defaults={"market": "cn"},
    ),
    "holder-number": DatasetSpec(
        name="holder-number",
        function="get_holder_number",
        category="equity",
        description="股东户数，对应 rqdatac.get_holder_number。",
        param_map={"ids": "order_book_ids", "start": "start_date", "end": "end_date", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        defaults={"market": "cn"},
    ),
    "main-shareholder": DatasetSpec(
        name="main-shareholder",
        function="get_main_shareholder",
        category="equity",
        description="主要股东构成，对应 rqdatac.get_main_shareholder。",
        param_map={
            "ids": "order_book_ids",
            "start": "start_date",
            "end": "end_date",
            "is_total": "is_total",
            "start_rank": "start_rank",
            "end_rank": "end_rank",
            "market": "market",
        },
        required=("ids",),
        list_params=("ids",),
        bool_params=("is_total",),
        defaults={"is_total": False, "market": "cn"},
    ),
    "instrument-industry": DatasetSpec(
        name="instrument-industry",
        function="get_instrument_industry",
        category="industry",
        description="证券所属行业，对应 rqdatac.get_instrument_industry。",
        param_map={"ids": "order_book_ids", "source": "source", "level": "level", "date": "date", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        defaults={"source": "citics_2019", "level": 1, "market": "cn"},
    ),
    "industry": DatasetSpec(
        name="industry",
        function="get_industry",
        category="industry",
        description="行业成分，对应 rqdatac.get_industry。",
        param_map={"industry": "industry", "source": "source", "date": "date", "market": "market"},
        required=("industry",),
        defaults={"source": "citics_2019", "market": "cn"},
    ),
    "industry-mapping": DatasetSpec(
        name="industry-mapping",
        function="get_industry_mapping",
        category="industry",
        description="行业映射，对应 rqdatac.get_industry_mapping。",
        param_map={"source": "source", "date": "date", "market": "market"},
        defaults={"source": "citics_2019", "market": "cn"},
    ),
    "announcement": DatasetSpec(
        name="announcement",
        function="get_announcement",
        category="event",
        description="公告数据，对应 rqdatac.get_announcement。",
        param_map={"ids": "order_book_ids", "start": "start_date", "end": "end_date", "fields": "fields", "market": "market"},
        required=("ids",),
        list_params=("ids", "fields"),
        defaults={"market": "cn"},
    ),
    "investor-qa": DatasetSpec(
        name="investor-qa",
        function="get_investor_qa",
        category="event",
        description="投资者问答，对应 rqdatac.get_investor_qa。",
        param_map={"ids": "order_book_ids", "start": "start_date", "end": "end_date", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        defaults={"market": "cn"},
    ),
    "investor-ra": DatasetSpec(
        name="investor-ra",
        function="get_investor_ra",
        category="event",
        description="投资者关系活动，对应 rqdatac.get_investor_ra。",
        param_map={"ids": "order_book_ids", "start": "start_date", "end": "end_date", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        defaults={"market": "cn"},
    ),
    "capital-flow": DatasetSpec(
        name="capital-flow",
        function="get_capital_flow",
        category="money-flow",
        description="资金流，对应 rqdatac.get_capital_flow。",
        param_map={"ids": "order_book_ids", "start": "start_date", "end": "end_date", "frequency": "frequency", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        defaults={"frequency": "1d", "market": "cn"},
    ),
    "stock-connect": DatasetSpec(
        name="stock-connect",
        function="get_stock_connect",
        category="money-flow",
        description="陆股通持股/交易相关数据，对应 rqdatac.get_stock_connect。",
        param_map={"ids": "order_book_ids", "start": "start_date", "end": "end_date", "fields": "fields", "expect_df": "expect_df"},
        required=("ids",),
        list_params=("ids", "fields"),
        bool_params=("expect_df",),
        defaults={"expect_df": True},
    ),
    "securities-margin": DatasetSpec(
        name="securities-margin",
        function="get_securities_margin",
        category="money-flow",
        description="融资融券数据，对应 rqdatac.get_securities_margin。",
        param_map={"ids": "order_book_ids", "start": "start_date", "end": "end_date", "fields": "fields", "expect_df": "expect_df", "market": "market"},
        required=("ids",),
        list_params=("ids", "fields"),
        bool_params=("expect_df",),
        defaults={"expect_df": True, "market": "cn"},
    ),
    "block-trade": DatasetSpec(
        name="block-trade",
        function="get_block_trade",
        category="money-flow",
        description="大宗交易，对应 rqdatac.get_block_trade。",
        param_map={"ids": "order_book_ids", "start": "start_date", "end": "end_date", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        defaults={"market": "cn"},
    ),
    "abnormal-stocks": DatasetSpec(
        name="abnormal-stocks",
        function="get_abnormal_stocks",
        category="money-flow",
        description="龙虎榜/异动股票列表，对应 rqdatac.get_abnormal_stocks。",
        param_map={"start": "start_date", "end": "end_date", "types": "types", "market": "market"},
        list_params=("types",),
        defaults={"market": "cn"},
    ),
    "abnormal-stocks-detail": DatasetSpec(
        name="abnormal-stocks-detail",
        function="get_abnormal_stocks_detail",
        category="money-flow",
        description="龙虎榜/异动明细，对应 rqdatac.get_abnormal_stocks_detail。",
        param_map={"ids": "order_book_ids", "start": "start_date", "end": "end_date", "sides": "sides", "types": "types", "market": "market"},
        required=("ids",),
        list_params=("ids", "sides", "types"),
        defaults={"market": "cn"},
    ),
    "etf-daily-units": DatasetSpec(
        name="etf-daily-units",
        function="etf.get_daily_units",
        category="etf",
        description="ETF 份额数据，对应 rqdatac.etf.get_daily_units。",
        param_map={"ids": "order_book_ids", "start": "start_date", "end": "end_date", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        defaults={"market": "cn"},
    ),
    "etf-components": DatasetSpec(
        name="etf-components",
        function="etf.get_components",
        category="etf",
        description="ETF 申赎清单，对应 rqdatac.etf.get_components。",
        param_map={"ids": "order_book_ids", "date": "date", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        defaults={"market": "cn"},
    ),
    "etf-cash-components": DatasetSpec(
        name="etf-cash-components",
        function="etf.get_cash_components",
        category="etf",
        description="ETF 现金差额，对应 rqdatac.etf.get_cash_components。",
        param_map={"ids": "order_book_ids", "start": "start_date", "end": "end_date", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        defaults={"market": "cn"},
    ),
    "fund-instruments": DatasetSpec(
        name="fund-instruments",
        function="fund.all_instruments",
        category="fund",
        description="基金基础信息，对应 rqdatac.fund.all_instruments。",
        param_map={"date": "date", "market": "market"},
        defaults={"market": "cn"},
    ),
    "fund-daily-units": DatasetSpec(
        name="fund-daily-units",
        function="fund.get_daily_units",
        category="fund",
        description="基金份额数据，对应 rqdatac.fund.get_daily_units。",
        param_map={"ids": "order_book_ids", "start": "start_date", "end": "end_date", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        defaults={"market": "cn"},
    ),
    "fund-holdings": DatasetSpec(
        name="fund-holdings",
        function="fund.get_holdings",
        category="fund",
        description="基金持仓数据，对应 rqdatac.fund.get_holdings。",
        param_map={"ids": "order_book_ids", "date": "date", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        defaults={"market": "cn"},
    ),
    "fund-stock-change": DatasetSpec(
        name="fund-stock-change",
        function="fund.get_stock_change",
        category="fund",
        description="基金重大持仓变动，对应 rqdatac.fund.get_stock_change。",
        param_map={"ids": "order_book_ids", "start": "start_date", "end": "end_date", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        defaults={"market": "cn"},
    ),
    "fund-asset-allocation": DatasetSpec(
        name="fund-asset-allocation",
        function="fund.get_asset_allocation",
        category="fund",
        description="基金资产配置，对应 rqdatac.fund.get_asset_allocation。",
        param_map={"ids": "order_book_ids", "date": "date", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        defaults={"market": "cn"},
    ),
    "fund-industry-allocation": DatasetSpec(
        name="fund-industry-allocation",
        function="fund.get_industry_allocation",
        category="fund",
        description="基金行业配置，对应 rqdatac.fund.get_industry_allocation。",
        param_map={"ids": "order_book_ids", "date": "date", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        defaults={"market": "cn"},
    ),
    "fund-nav": DatasetSpec(
        name="fund-nav",
        function="fund.get_nav",
        category="fund",
        description="基金净值，对应 rqdatac.fund.get_nav。",
        param_map={"ids": "order_book_ids", "start": "start_date", "end": "end_date", "fields": "fields", "expect_df": "expect_df", "market": "market"},
        required=("ids",),
        list_params=("ids", "fields"),
        bool_params=("expect_df",),
        defaults={"expect_df": True, "market": "cn"},
    ),
    "fund-benchmark": DatasetSpec(
        name="fund-benchmark",
        function="fund.get_benchmark",
        category="fund",
        description="基金业绩基准，对应 rqdatac.fund.get_benchmark。",
        param_map={"ids": "order_book_ids", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        defaults={"market": "cn"},
    ),
    "consensus-price": DatasetSpec(
        name="consensus-price",
        function="get_consensus_price",
        category="consensus",
        description="一致预期目标价，对应 rqdatac.get_consensus_price。",
        param_map={"ids": "order_book_ids", "start": "start_date", "end": "end_date", "fields": "fields", "adjust_type": "adjust_type", "market": "market"},
        required=("ids",),
        list_params=("ids", "fields"),
        defaults={"adjust_type": "none", "market": "cn"},
    ),
    "consensus-comp-indicators": DatasetSpec(
        name="consensus-comp-indicators",
        function="get_consensus_comp_indicators",
        category="consensus",
        description="公司一致预期综合指标，对应 rqdatac.get_consensus_comp_indicators。",
        param_map={"ids": "order_book_ids", "start": "start_date", "end": "end_date", "fields": "fields", "report_range": "report_range", "market": "market"},
        required=("ids",),
        list_params=("ids", "fields"),
        defaults={"report_range": 0, "market": "cn"},
    ),
    "consensus-indicator": DatasetSpec(
        name="consensus-indicator",
        function="get_consensus_indicator",
        category="consensus",
        description="一致预期指标，对应 rqdatac.get_consensus_indicator。",
        param_map={"ids": "order_book_ids", "fiscal_year": "fiscal_year", "fields": "fields", "start": "start_date", "end": "end_date", "date_rule": "date_rule", "market": "market"},
        required=("ids", "fiscal_year"),
        list_params=("ids", "fields"),
        defaults={"market": "cn"},
    ),
    "consensus-market-estimate": DatasetSpec(
        name="consensus-market-estimate",
        function="get_consensus_market_estimate",
        category="consensus",
        description="市场一致预期，对应 rqdatac.get_consensus_market_estimate。",
        param_map={"indexes": "indexes", "fiscal_year": "fiscal_year", "market": "market"},
        required=("indexes", "fiscal_year"),
        list_params=("indexes",),
        defaults={"market": "cn"},
    ),
    "consensus-industry-rating": DatasetSpec(
        name="consensus-industry-rating",
        function="get_consensus_industry_rating",
        category="consensus",
        description="行业一致预期评级，对应 rqdatac.get_consensus_industry_rating。",
        param_map={"industries": "industries", "start": "start_date", "end": "end_date", "market": "market"},
        required=("industries", "start", "end"),
        list_params=("industries",),
        defaults={"market": "cn"},
    ),
    "consensus-industries": DatasetSpec(
        name="consensus-industries",
        function="all_consensus_industries",
        category="consensus",
        description="一致预期行业列表，对应 rqdatac.all_consensus_industries。",
        param_map={"market": "market"},
        defaults={"market": "cn"},
    ),
    "index-components": DatasetSpec(
        name="index-components",
        function="index_components",
        category="index",
        description="指数成分，对应 rqdatac.index_components。",
        param_map={"ids": "order_book_id", "date": "date", "start": "start_date", "end": "end_date", "return_create_tm": "return_create_tm", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        bool_params=("return_create_tm",),
        defaults={"return_create_tm": False, "market": "cn"},
    ),
    "index-weights": DatasetSpec(
        name="index-weights",
        function="index_weights",
        category="index",
        description="指数权重，对应 rqdatac.index_weights。",
        param_map={"ids": "order_book_id", "date": "date", "start": "start_date", "end": "end_date", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        defaults={"market": "cn"},
    ),
    "index-weights-ex": DatasetSpec(
        name="index-weights-ex",
        function="index_weights_ex",
        category="index",
        description="指数权重扩展数据，对应 rqdatac.index_weights_ex。",
        param_map={"ids": "order_book_id", "date": "date", "start": "start_date", "end": "end_date", "market": "market"},
        required=("ids",),
        list_params=("ids",),
        defaults={"market": "cn"},
    ),
    "index-indicator": DatasetSpec(
        name="index-indicator",
        function="index_indicator",
        category="index",
        description="指数指标，对应 rqdatac.index_indicator。",
        param_map={"ids": "order_book_ids", "start": "start_date", "end": "end_date", "fields": "fields", "market": "market"},
        required=("ids",),
        list_params=("ids", "fields"),
        defaults={"market": "cn"},
    ),
    "index-factor-exposure": DatasetSpec(
        name="index-factor-exposure",
        function="get_index_factor_exposure",
        category="index",
        description="指数因子暴露，对应 rqdatac.get_index_factor_exposure。",
        param_map={"ids": "order_book_ids", "start": "start_date", "end": "end_date", "factors": "factors", "market": "market"},
        required=("ids",),
        list_params=("ids", "factors"),
        defaults={"market": "cn"},
    ),
    "current-news": DatasetSpec(
        name="current-news",
        function="get_current_news",
        category="news",
        description="当前新闻流，对应 rqdatac.get_current_news。",
        param_map={"n": "n", "start_time": "start_time", "end_time": "end_time", "channels": "channels"},
        list_params=("channels",),
    ),
}


def list_datasets(category: str | None = None) -> list[dict[str, Any]]:
    specs = DATASETS.values()
    if category:
        specs = [spec for spec in specs if spec.category == category]
    return [
        {
            "name": spec.name,
            "category": spec.category,
            "function": spec.function,
            "description": spec.description,
        }
        for spec in sorted(specs, key=lambda item: (item.category, item.name))
    ]


def describe_dataset(name: str) -> dict[str, Any]:
    spec = get_dataset(name)
    return {
        "name": spec.name,
        "category": spec.category,
        "function": spec.function,
        "description": spec.description,
        "required": list(spec.required),
        "defaults": spec.defaults,
        "param_map": spec.param_map,
        "list_params": list(spec.list_params),
        "bool_params": list(spec.bool_params),
    }


def get_dataset(name: str) -> DatasetSpec:
    try:
        return DATASETS[name]
    except KeyError as exc:
        raise CliError(f"Unknown dataset `{name}`. Run `rqq data list` to see supported datasets.") from exc


def build_dataset_kwargs(spec: DatasetSpec, raw_params: dict[str, Any]) -> dict[str, Any]:
    params = {**spec.defaults, **{key: value for key, value in raw_params.items() if value is not None}}
    missing = [name for name in spec.required if _is_empty(params.get(name))]
    if missing:
        raise CliError(f"Dataset `{spec.name}` requires: {', '.join(missing)}")

    kwargs: dict[str, Any] = {}
    for public_name, function_name in spec.param_map.items():
        if public_name not in params or params[public_name] is None:
            continue
        value = params[public_name]
        if public_name in spec.list_params:
            value = _as_list(value)
            if public_name == "ids" and function_name == "order_book_id":
                value = value[0]
            elif len(value) == 1 and public_name in {"ids"}:
                value = value[0]
        if public_name in spec.bool_params:
            value = _as_bool(value)
        kwargs[function_name] = value
    return kwargs


def call_dataset(name: str, raw_params: dict[str, Any], resolver: Callable[[str], Any]) -> Any:
    spec = get_dataset(name)
    target = resolver(spec.function)
    kwargs = build_dataset_kwargs(spec, raw_params)
    return target(**kwargs)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [value]


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
    return bool(value)


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == []
