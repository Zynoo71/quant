from __future__ import annotations

import json
import sys
import types

import pytest

from rqsdk_quant.cli import main


@pytest.fixture(autouse=True)
def _isolate_license(monkeypatch, tmp_path):
    """Keep tests off the real ~/.rqq/credentials; each test starts with no stored license."""
    import rqsdk_quant.rqdata_client as rc

    monkeypatch.setattr(rc, "LICENSE_PATH", tmp_path / "no-credentials")


def test_business_latest_frame_melts_wide_stock_columns():
    import pandas as pd

    from rqsdk_quant.business import _latest_frame

    frame = pd.DataFrame(
        {
            "date": ["2024-01-02"],
            "000001.XSHE": [False],
            "600000.XSHG": [True],
        }
    )

    out = _latest_frame("st", frame, ["000001.XSHE", "600000.XSHG"])

    assert set(out["order_book_id"]) == {"000001.XSHE", "600000.XSHG"}
    assert "st__value" in out.columns


def test_business_latest_frame_can_force_input_id_when_source_has_order_book_id():
    import pandas as pd

    from rqsdk_quant.business import _latest_frame

    frame = pd.DataFrame({"order_book_id": ["600000.XSHG"], "weight": [0.1]})

    out = _latest_frame("index_weights", frame, ["000300.XSHG"], ("index_id",))

    assert out["order_book_id"].tolist() == ["000300.XSHG"]
    assert out["index_weights__source_order_book_id"].tolist() == ["600000.XSHG"]


def test_data_call_uses_dotted_rqdatac_function(monkeypatch, capsys):
    rqdatac = types.SimpleNamespace()
    rqdatac.init = lambda: None
    rqdatac.user = types.SimpleNamespace(get_quota=lambda: {"remaining": 123})
    monkeypatch.setitem(sys.modules, "rqdatac", rqdatac)

    main(["data", "call", "user.get_quota", "--format", "json"])

    out = capsys.readouterr().out
    assert json.loads(out) == {"remaining": 123}


def test_data_price_parses_fields(monkeypatch, capsys):
    calls = {}

    def get_price(**kwargs):
        calls.update(kwargs)
        return {"ok": True}

    rqdatac = types.SimpleNamespace(init=lambda: None, get_price=get_price)
    monkeypatch.setitem(sys.modules, "rqdatac", rqdatac)

    main(
        [
            "data",
            "price",
            "000001.XSHE",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-31",
            "--fields",
            "open,close",
            "--format",
            "json",
        ]
    )

    assert calls["order_book_ids"] == "000001.XSHE"
    assert calls["fields"] == ["open", "close"]
    assert json.loads(capsys.readouterr().out) == {"ok": True}


def test_data_list_includes_registered_datasets(capsys):
    main(["data", "list", "--category", "market", "--format", "json"])

    out = json.loads(capsys.readouterr().out)
    names = {row["name"] for row in out}
    assert "price" in names
    assert "current-snapshot" in names


def test_data_describe_price(capsys):
    main(["data", "describe", "price", "--format", "json"])

    out = json.loads(capsys.readouterr().out)
    assert out["function"] == "get_price"
    assert out["param_map"]["ids"] == "order_book_ids"
    assert "ids" in out["required"]


def test_data_fetch_uses_dataset_registry(monkeypatch, capsys):
    calls = {}

    def get_price(**kwargs):
        calls.update(kwargs)
        return {"ok": True}

    rqdatac = types.SimpleNamespace(init=lambda: None, get_price=get_price)
    monkeypatch.setitem(sys.modules, "rqdatac", rqdatac)

    main(
        [
            "data",
            "fetch",
            "price",
            "--ids",
            "000001.XSHE",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-31",
            "--fields",
            "open,close",
            "--param",
            "expect_df=false",
            "--format",
            "json",
        ]
    )

    assert calls["order_book_ids"] == "000001.XSHE"
    assert calls["start_date"] == "2024-01-01"
    assert calls["fields"] == ["open", "close"]
    assert calls["expect_df"] is False
    assert json.loads(capsys.readouterr().out) == {"ok": True}


def _help_text(capsys, argv):
    with pytest.raises(SystemExit):
        main(argv)
    # argparse reflows help/epilog across lines; collapse whitespace for matching.
    return " ".join(capsys.readouterr().out.split())


def _rqdatac_with_failing_init():
    """A stand-in rqdatac whose init() always fails, as if no license is configured."""

    def boom():
        raise ValueError("username/password/addr or uri expected")

    return types.SimpleNamespace(init=boom)


def _mock_rqdatac_for_license(monkeypatch, captured):
    def fake_init(**kwargs):
        captured.update(kwargs)

    rqdatac = types.SimpleNamespace(
        init=fake_init,
        user=types.SimpleNamespace(get_quota=lambda: {"remaining": 100}),
    )
    monkeypatch.setitem(sys.modules, "rqdatac", rqdatac)


def test_license_set_stores_license_key(monkeypatch, tmp_path, capsys):
    import rqsdk_quant.rqdata_client as rc

    monkeypatch.setattr(rc, "LICENSE_PATH", tmp_path / "credentials")
    captured = {}
    _mock_rqdatac_for_license(monkeypatch, captured)

    main(["license", "-l", "MYKEY123", "--format", "json"])

    expected = "tcp://license:MYKEY123@rqdatad-pro.ricequant.com:16011"
    assert (tmp_path / "credentials").read_text().strip() == expected
    assert captured["uri"] == expected  # validated before saving
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ok"


def test_license_set_account_password_uri(monkeypatch, tmp_path):
    import rqsdk_quant.rqdata_client as rc

    monkeypatch.setattr(rc, "LICENSE_PATH", tmp_path / "credentials")
    _mock_rqdatac_for_license(monkeypatch, {})

    main(["license", "-l", "13888888888:secret", "--format", "json"])

    assert (tmp_path / "credentials").read_text().strip() == "tcp://13888888888:secret@rqdatad-pro.ricequant.com:16011"


def test_license_set_validation_failure_does_not_save(monkeypatch, tmp_path, capsys):
    import rqsdk_quant.rqdata_client as rc

    monkeypatch.setattr(rc, "LICENSE_PATH", tmp_path / "credentials")

    def boom(**kwargs):
        raise ValueError("auth failed")

    rqdatac = types.SimpleNamespace(init=boom, user=types.SimpleNamespace(get_quota=lambda: {}))
    monkeypatch.setitem(sys.modules, "rqdatac", rqdatac)

    with pytest.raises(SystemExit) as exc:
        main(["license", "-l", "BADKEY"])

    assert exc.value.code == 2
    assert "License validation failed" in capsys.readouterr().err
    assert not (tmp_path / "credentials").exists()


def test_data_fetch_uses_stored_license(monkeypatch, tmp_path):
    import rqsdk_quant.rqdata_client as rc

    cred_file = tmp_path / "credentials"
    cred_file.write_text("tcp://license:STORED@rqdatad-pro.ricequant.com:16011\n")
    monkeypatch.setattr(rc, "LICENSE_PATH", cred_file)

    captured = {}

    def fake_init(**kwargs):
        captured.update(kwargs)

    rqdatac = types.SimpleNamespace(init=fake_init, get_price=lambda **k: {"ok": True})
    monkeypatch.setitem(sys.modules, "rqdatac", rqdatac)

    main(["data", "get", "price", "--ids", "000001.XSHE", "--format", "json"])

    assert captured["uri"] == "tcp://license:STORED@rqdatad-pro.ricequant.com:16011"


def test_init_failure_gives_license_reminder(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "rqdatac", _rqdatac_with_failing_init())

    # A well-formed request reaches init; a missing license must surface a clear,
    # actionable reminder (exit 2), not the raw rqdatac ValueError (exit 1).
    with pytest.raises(SystemExit) as exc:
        main(["data", "fetch", "price", "--ids", "000001.XSHE", "--start", "2024-01-02", "--end", "2024-01-03"])

    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "no valid Ricequant license" in err
    assert "rqq license" in err


def test_info_init_failure_gives_license_reminder(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "rqdatac", _rqdatac_with_failing_init())

    with pytest.raises(SystemExit) as exc:
        main(["data", "info"])

    assert exc.value.code == 2
    assert "rqq license" in capsys.readouterr().err


def test_fetch_missing_required_reported_before_init(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "rqdatac", _rqdatac_with_failing_init())

    with pytest.raises(SystemExit) as exc:
        main(["data", "fetch", "price"])  # missing --ids

    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "requires: ids" in err
    assert "username/password" not in err  # not masked by the init failure


def test_fetch_unknown_dataset_reported_before_init(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "rqdatac", _rqdatac_with_failing_init())

    with pytest.raises(SystemExit) as exc:
        main(["data", "fetch", "nope", "--ids", "000001.XSHE"])

    assert exc.value.code == 2
    assert "Unknown dataset" in capsys.readouterr().err


def test_generate_unknown_scenario_reported_before_init(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "rqdatac", _rqdatac_with_failing_init())

    with pytest.raises(SystemExit) as exc:
        main(["data", "generate", "nope-scenario"])

    assert exc.value.code == 2
    assert "Unknown scenario" in capsys.readouterr().err


def test_build_unknown_business_dataset_reported_before_init(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "rqdatac", _rqdatac_with_failing_init())

    with pytest.raises(SystemExit) as exc:
        main(["data", "build", "nope-snapshot"])

    assert exc.value.code == 2
    assert "Unknown business dataset" in capsys.readouterr().err


def test_top_level_help_has_quickstart_examples(capsys):
    out = _help_text(capsys, ["--help"])
    assert "Quick start" in out
    assert "rqq license -l" in out
    assert "rqq data get price --ids 000001.XSHE" in out
    assert "rqq help" in out


def test_data_help_has_tips(capsys):
    out = _help_text(capsys, ["data", "--help"])
    assert "rqq data describe <dataset>" in out
    assert "--param KEY=VALUE" in out


def test_fetch_subcommand_help_is_detailed_and_points_to_describe(capsys):
    out = _help_text(capsys, ["data", "fetch", "--help"])
    # enriched parameter help carries formats/examples
    assert "YYYY-MM-DD" in out
    assert "YYYYqN" in out
    # epilog points to where dataset-specific params live
    assert "rqq data describe <dataset>" in out


def test_generate_subcommand_help_points_to_scenario_plan(capsys):
    out = _help_text(capsys, ["data", "generate", "--help"])
    assert "rqq data scenario plan <scenario>" in out


def test_business_build_help_points_to_business_plan(capsys):
    out = _help_text(capsys, ["data", "business", "build", "--help"])
    assert "rqq data business plan <dataset>" in out


def test_help_reference_markdown_lists_commands_and_datasets(capsys):
    main(["help"])

    out = capsys.readouterr().out
    assert "### commands" in out
    assert "### datasets" in out
    assert "### scenarios" in out
    assert "### business_datasets" in out
    assert "data fetch <dataset> [params]" in out
    assert "get_price" in out


def test_help_reference_json_carries_params_and_defaults(capsys):
    main(["help", "--format", "json"])

    out = json.loads(capsys.readouterr().out)
    assert out["cli"] == "rqq"
    assert out["default_format"] == "markdown"

    price = next(row for row in out["datasets"] if row["name"] == "price")
    assert "ids" in price["required"]
    assert price["defaults"]["frequency"] == "1d"
    assert "fields" in price["optional"]

    commands = {row["command"] for row in out["commands"]}
    assert any("fetch" in command for command in commands)
    scenario_names = {row["name"] for row in out["scenarios"]}
    assert "company-quality" in scenario_names


def test_data_help_alias_matches_top_level_help(capsys):
    main(["data", "help", "--format", "json"])
    data_help = json.loads(capsys.readouterr().out)

    main(["help", "--format", "json"])
    top_help = json.loads(capsys.readouterr().out)

    assert data_help == top_help


def test_data_list_defaults_to_markdown_table(capsys):
    main(["data", "list", "--category", "market"])

    out = capsys.readouterr().out
    lines = out.strip().splitlines()
    assert lines[0].startswith("| name | category | function | description |")
    assert set(lines[1].replace(" ", "")) <= {"|", "-"}
    assert any("get_price" in line for line in lines)


def test_data_describe_markdown_renders_nested_sections(capsys):
    main(["data", "describe", "price"])

    out = capsys.readouterr().out
    assert "- **function**: get_price" in out
    assert "### param_map" in out
    assert "| ids | order_book_ids |" in out


def test_data_get_alias_uses_dataset_registry(monkeypatch, capsys):
    calls = {}

    def get_price(**kwargs):
        calls.update(kwargs)
        return {"ok": True}

    rqdatac = types.SimpleNamespace(init=lambda: None, get_price=get_price)
    monkeypatch.setitem(sys.modules, "rqdatac", rqdatac)

    main(["data", "get", "price", "--ids", "000001.XSHE", "--format", "json"])

    assert calls["order_book_ids"] == "000001.XSHE"
    assert json.loads(capsys.readouterr().out) == {"ok": True}


def test_data_fetch_uses_nested_fund_dataset(monkeypatch, capsys):
    calls = {}

    def get_holdings(**kwargs):
        calls.update(kwargs)
        return [{"fund_id": kwargs["order_book_ids"], "weight": 0.1}]

    rqdatac = types.SimpleNamespace(init=lambda: None, fund=types.SimpleNamespace(get_holdings=get_holdings))
    monkeypatch.setitem(sys.modules, "rqdatac", rqdatac)

    main(["data", "fetch", "fund-holdings", "--ids", "000003", "--date", "2023-12-31", "--format", "json"])

    assert calls["order_book_ids"] == "000003"
    assert calls["date"] == "2023-12-31"
    assert json.loads(capsys.readouterr().out) == [{"fund_id": "000003", "weight": 0.1}]


def test_data_fetch_factor_passes_universe(monkeypatch, capsys):
    calls = {}

    def get_factor(**kwargs):
        calls.update(kwargs)
        return {"ok": True}

    rqdatac = types.SimpleNamespace(init=lambda: None, get_factor=get_factor)
    monkeypatch.setitem(sys.modules, "rqdatac", rqdatac)

    main(
        [
            "data",
            "fetch",
            "factor",
            "--ids",
            "000001.XSHE",
            "--factor",
            "pe_ratio_ttm",
            "--universe",
            "000300.XSHG",
            "--format",
            "json",
        ]
    )

    assert calls["universe"] == "000300.XSHG"
    assert json.loads(capsys.readouterr().out) == {"ok": True}


def test_data_fetch_current_news_params(monkeypatch, capsys):
    calls = {}

    def get_current_news(**kwargs):
        calls.update(kwargs)
        return [{"channel": "a-stock", "content": "news"}]

    rqdatac = types.SimpleNamespace(init=lambda: None, get_current_news=get_current_news)
    monkeypatch.setitem(sys.modules, "rqdatac", rqdatac)

    main(["data", "fetch", "current-news", "--n", "1", "--channels", "a-stock,global", "--format", "json"])

    assert calls["n"] == 1
    assert calls["channels"] == ["a-stock", "global"]
    assert json.loads(capsys.readouterr().out) == [{"channel": "a-stock", "content": "news"}]


def test_scenario_list_includes_doc_modules(capsys):
    main(["data", "scenario", "list", "--format", "json"])

    out = json.loads(capsys.readouterr().out)
    names = {row["name"] for row in out}
    assert "company-quality" in names
    assert "capital-confirmation" in names


def test_scenario_plan_marks_missing_required_params(capsys):
    main(["data", "scenario", "plan", "company-quality", "--ids", "000001.XSHE", "--format", "json"])

    out = json.loads(capsys.readouterr().out)
    financials = next(step for step in out["steps"] if step["name"] == "financials-pit")
    assert financials["status"] == "skipped"
    assert "start_quarter" in financials["missing"]
    assert "end_quarter" in financials["missing"]


def test_scenario_generate_writes_files(monkeypatch, tmp_path, capsys):
    def get_price(**kwargs):
        return [{"order_book_id": kwargs["order_book_ids"], "close": 10}]

    def get_turnover_rate(**kwargs):
        return [{"order_book_id": kwargs["order_book_ids"], "turnover_rate": 1.2}]

    def is_st_stock(**kwargs):
        return [{"order_book_id": kwargs["order_book_ids"], "is_st": False}]

    def is_suspended(**kwargs):
        return [{"order_book_id": kwargs["order_book_ids"], "is_suspended": False}]

    rqdatac = types.SimpleNamespace(
        init=lambda: None,
        get_price=get_price,
        get_turnover_rate=get_turnover_rate,
        is_st_stock=is_st_stock,
        is_suspended=is_suspended,
    )
    monkeypatch.setitem(sys.modules, "rqdatac", rqdatac)

    main(
        [
            "data",
            "generate",
            "price-trend",
            "--ids",
            "000001.XSHE",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--output-dir",
            str(tmp_path),
            "--file-format",
            "json",
            "--format",
            "json",
        ]
    )

    out = json.loads(capsys.readouterr().out)
    assert out["scenario"] == "price-trend"
    assert len(out["files"]) == 4
    assert (tmp_path / "price-trend" / "01-price.json").exists()
    assert (tmp_path / "price-trend" / "manifest.json").exists()


def test_business_list_includes_composed_datasets(capsys):
    main(["data", "business", "list", "--format", "json"])

    out = json.loads(capsys.readouterr().out)
    names = {row["name"] for row in out}
    assert "company-quality-snapshot" in names
    assert "research-monitor-snapshot" in names
    assert "fund-position-snapshot" in names
    assert "consensus-attention-snapshot" in names
    assert "index-relative-strength-snapshot" in names
    assert "event-news-snapshot" in names


def test_business_plan_marks_missing_component_params(capsys):
    main(["data", "business", "plan", "company-quality-snapshot", "--ids", "000001.XSHE", "--format", "json"])

    out = json.loads(capsys.readouterr().out)
    financials = next(component for component in out["components"] if component["name"] == "financials")
    assert financials["status"] == "skipped"
    assert "start_quarter" in financials["missing"]


def test_business_build_composes_snapshot(monkeypatch, tmp_path, capsys):
    def one_row(**kwargs):
        ids = kwargs["order_book_ids"]
        order_book_id = ids[0] if isinstance(ids, list) else ids
        return [{"order_book_id": order_book_id, "date": "2024-01-02", "value": 1}]

    rqdatac = types.SimpleNamespace(
        init=lambda: None,
        get_price=lambda **kwargs: [{"order_book_id": kwargs["order_book_ids"], "date": "2024-01-02", "close": 10}],
        get_turnover_rate=one_row,
        is_st_stock=lambda **kwargs: [{"order_book_id": kwargs["order_book_ids"], "date": "2024-01-02", "is_st": False}],
        is_suspended=lambda **kwargs: [{"order_book_id": kwargs["order_book_ids"], "date": "2024-01-02", "is_suspended": False}],
        get_announcement=one_row,
        get_investor_qa=one_row,
        get_investor_ra=one_row,
        get_capital_flow=one_row,
        get_stock_connect=one_row,
        get_securities_margin=one_row,
    )
    monkeypatch.setitem(sys.modules, "rqdatac", rqdatac)

    main(
        [
            "data",
            "business",
            "build",
            "research-monitor-snapshot",
            "--ids",
            "000001.XSHE",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--output-dir",
            str(tmp_path),
            "--file-format",
            "json",
            "--format",
            "json",
        ]
    )

    out = json.loads(capsys.readouterr().out)
    assert out["business_dataset"] == "research-monitor-snapshot"
    assert out["rows"] == 1
    assert out["skipped"] == []
    assert (tmp_path / "research-monitor-snapshot" / "research_monitor_snapshot.json").exists()
    assert (tmp_path / "research-monitor-snapshot" / "manifest.json").exists()


def test_data_build_alias_builds_business_dataset(monkeypatch, tmp_path, capsys):
    rqdatac = types.SimpleNamespace(
        init=lambda: None,
        get_price=lambda **kwargs: [{"order_book_id": kwargs["order_book_ids"], "date": "2024-01-02", "close": 10}],
        get_turnover_rate=lambda **kwargs: [{"order_book_id": kwargs["order_book_ids"], "date": "2024-01-02", "value": 1}],
        is_st_stock=lambda **kwargs: [{"order_book_id": kwargs["order_book_ids"], "date": "2024-01-02", "value": False}],
        is_suspended=lambda **kwargs: [{"order_book_id": kwargs["order_book_ids"], "date": "2024-01-02", "value": False}],
        get_announcement=lambda **kwargs: [],
        get_investor_qa=lambda **kwargs: [],
        get_investor_ra=lambda **kwargs: [],
        get_capital_flow=lambda **kwargs: [],
        get_stock_connect=lambda **kwargs: [],
        get_securities_margin=lambda **kwargs: [],
    )
    monkeypatch.setitem(sys.modules, "rqdatac", rqdatac)

    main(
        [
            "data",
            "build",
            "research-monitor-snapshot",
            "--ids",
            "000001.XSHE",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-02",
            "--output-dir",
            str(tmp_path),
            "--file-format",
            "json",
            "--format",
            "json",
        ]
    )

    out = json.loads(capsys.readouterr().out)
    assert out["business_dataset"] == "research-monitor-snapshot"
    assert (tmp_path / "research-monitor-snapshot" / "research_monitor_snapshot.json").exists()

