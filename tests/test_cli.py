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


# --------------------------------------------------------------------------- #
# Catalog model (offline, no rqdatac)
# --------------------------------------------------------------------------- #

def test_catalog_is_atomic_and_well_formed():
    from rqsdk_quant.datasets import DATASETS, MODULES

    assert len(DATASETS) > 200
    for name, spec in DATASETS.items():
        assert spec.name == name                     # dict key == name (unique)
        assert spec.category in MODULES              # official module slug
        assert spec.function                         # dotted rqdatac path
        assert "." not in name                       # public names are kebab, not dotted


def test_build_kwargs_derives_required_list_and_bool():
    from rqsdk_quant.datasets import build_dataset_kwargs, get_dataset

    spec = get_dataset("price")
    kwargs = build_dataset_kwargs(spec, {"ids": "000001.XSHE,600000.XSHG", "fields": "open,close", "skip_suspended": "true"})
    assert kwargs["order_book_ids"] == ["000001.XSHE", "600000.XSHG"]
    assert kwargs["fields"] == ["open", "close"]
    assert kwargs["skip_suspended"] is True
    assert kwargs["expect_df"] is True               # injected by default


def test_build_kwargs_single_id_dataset_unwraps_to_scalar():
    from rqsdk_quant.datasets import build_dataset_kwargs, get_dataset

    # get_ticks takes a singular order_book_id; a comma list collapses to the first.
    kwargs = build_dataset_kwargs(get_dataset("ticks"), {"ids": "000001.XSHE"})
    assert kwargs["order_book_id"] == "000001.XSHE"


def test_build_kwargs_maps_underlying_and_omits_expect_df():
    from rqsdk_quant.datasets import build_dataset_kwargs, get_dataset

    spec = get_dataset("futures-dominant")
    kwargs = build_dataset_kwargs(spec, {"underlying": "AG"})
    assert kwargs == {"underlying_symbol": "AG"}      # no expect_df (function has none)


def test_build_kwargs_reports_all_missing_required():
    from rqsdk_quant.datasets import build_dataset_kwargs, get_dataset
    from rqsdk_quant.errors import CliError

    with pytest.raises(CliError) as exc:
        build_dataset_kwargs(get_dataset("financials-pit"), {"ids": "000001.XSHE"})
    msg = str(exc.value)
    assert "--fields" in msg                 # flag form, not the rqdatac name
    assert "--start-quarter" in msg
    assert "rqq data describe financials-pit" in msg  # points at the fix
    assert "rqq data get financials-pit" in msg       # carries a runnable example


def test_reference_builds_offline_and_groups_by_module():
    # reference.py must not import rqdatac.
    import rqsdk_quant.reference as reference

    ref = reference.build_help_reference()
    slugs = {m["slug"] for m in ref["modules"]}
    assert {"generic-api", "stock-mod", "fund-mod", "futures-mod"} <= slugs
    total = sum(len(m["datasets"]) for m in ref["modules"])
    assert total == len(reference.DATASETS)


# --------------------------------------------------------------------------- #
# data list / describe
# --------------------------------------------------------------------------- #

def test_data_list_filters_by_module(capsys):
    main(["data", "list", "--category", "fund-mod", "--format", "json"])
    rows = json.loads(capsys.readouterr().out)
    assert rows
    assert all(row["category"] == "fund-mod" for row in rows)
    assert {"fund-nav", "fund-holdings"} <= {row["name"] for row in rows}


def test_data_list_defaults_to_markdown_table(capsys):
    main(["data", "list", "--category", "generic-api"])
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines[0].startswith("| name | category | module | function | description |")
    assert any("get_price" in line for line in lines)


def test_data_describe_price(capsys):
    main(["data", "describe", "price", "--format", "json"])
    out = json.loads(capsys.readouterr().out)
    assert out["function"] == "get_price"
    assert out["example"].startswith("rqq data get price --ids")
    ids_row = next(p for p in out["params"] if p["param"] == "--ids")
    assert ids_row["required"] is True
    assert ids_row["kind"] == "list"
    assert ids_row["说明"]  # non-empty description


def test_data_describe_markdown_renders_example_and_params(capsys):
    main(["data", "describe", "price"])
    out = capsys.readouterr().out
    assert "- **function**: get_price" in out
    assert "- **example**: rqq data get price --ids 000001.XSHE" in out
    assert "### params" in out
    assert "| --ids | True |" in out


def test_every_dataset_has_example_and_param_descriptions():
    from rqsdk_quant.datasets import DATASETS, describe_dataset, param_description

    non_stock = {"fund-mod", "convertible-mod", "options-mod", "futures-mod", "indices-mod"}
    for name, spec in DATASETS.items():
        info = describe_dataset(name)
        assert info["example"].startswith(f"rqq data get {name}")
        for req in spec.required:                    # example shows every required param
            ex = info["example"]
            shown = ("--" + req.replace("_", "-")) in ex or f"--param {req}=" in ex or f"--param '{req}=" in ex
            assert shown, f"{name}: required {req} missing from example"
            desc = param_description(req)             # ...with real guidance, not an echoed name
            assert desc.strip().lower() != req.replace("_", " ").lower(), f"{name}:{req} has no 说明"
        assert info["params"]                        # at least one param documented
        for row in info["params"]:                   # every param has REAL guidance, not an echoed name
            pub = row["param"].lstrip("-")
            assert row["说明"].strip().lower() != pub.replace("-", " ").lower(), f"{name}:{pub} has no 说明"
        if spec.category in non_stock:               # example id fits the module, not a stock code
            assert "000001.XSHE" not in info["example"], f"{name} example uses a stock id"


def test_flag_params_stay_in_sync_with_cli():
    from rqsdk_quant.cli import KNOWN_FLAG_DESTS
    from rqsdk_quant.datasets import FLAG_PARAMS

    assert set(KNOWN_FLAG_DESTS) == set(FLAG_PARAMS)  # drift guard for build_example


def test_every_example_is_parseable_no_fake_flags():
    import shlex
    from rqsdk_quant.cli import build_parser
    from rqsdk_quant.datasets import DATASETS, build_example

    parser = build_parser()
    for name in DATASETS:
        example = build_example(DATASETS[name])
        argv = shlex.split(example)[1:]              # drop the leading "rqq"
        parser.parse_args(argv)                       # SystemExit here = an unrunnable example


# --------------------------------------------------------------------------- #
# data fetch / get / call
# --------------------------------------------------------------------------- #

def test_data_fetch_uses_dataset_registry(monkeypatch, capsys):
    calls = {}

    def get_price(**kwargs):
        calls.update(kwargs)
        return {"ok": True}

    rqdatac = types.SimpleNamespace(init=lambda: None, get_price=get_price)
    monkeypatch.setitem(sys.modules, "rqdatac", rqdatac)

    main(["data", "fetch", "price", "--ids", "000001.XSHE", "--start", "2024-01-01",
          "--end", "2024-01-31", "--fields", "open,close", "--no-expect-df", "--format", "json"])

    assert calls["order_book_ids"] == "000001.XSHE"
    assert calls["start_date"] == "2024-01-01"
    assert calls["fields"] == ["open", "close"]
    assert calls["expect_df"] is False
    assert json.loads(capsys.readouterr().out) == {"ok": True}


def test_data_get_alias_uses_dataset_registry(monkeypatch, capsys):
    calls = {}
    rqdatac = types.SimpleNamespace(init=lambda: None, get_price=lambda **k: calls.update(k) or {"ok": True})
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


def test_data_fetch_underlying_namespaced_futures(monkeypatch, capsys):
    calls = {}
    futures = types.SimpleNamespace(get_dominant=lambda **k: calls.update(k) or [{"date": "2024-01-02", "dominant": "AG2402"}])
    rqdatac = types.SimpleNamespace(init=lambda: None, futures=futures)
    monkeypatch.setitem(sys.modules, "rqdatac", rqdatac)

    main(["data", "fetch", "futures-dominant", "--underlying", "AG", "--format", "json"])
    assert calls == {"underlying_symbol": "AG"}


def test_data_fetch_factor_passes_universe(monkeypatch, capsys):
    calls = {}
    rqdatac = types.SimpleNamespace(init=lambda: None, get_factor=lambda **k: calls.update(k) or {"ok": True})
    monkeypatch.setitem(sys.modules, "rqdatac", rqdatac)

    main(["data", "fetch", "factor", "--ids", "000001.XSHE", "--factor", "pe_ratio_ttm",
          "--universe", "000300.XSHG", "--format", "json"])
    assert calls["universe"] == "000300.XSHG"
    assert calls["factor"] == ["pe_ratio_ttm"]


def test_data_fetch_extra_param_reaches_rqdatac(monkeypatch, capsys):
    calls = {}
    rqdatac = types.SimpleNamespace(init=lambda: None, get_factor=lambda **k: calls.update(k) or {"ok": True})
    monkeypatch.setitem(sys.modules, "rqdatac", rqdatac)

    # `rule` is not a curated flag — it must still reach rqdatac via --param.
    main(["data", "fetch", "factor", "--ids", "000001.XSHE", "--factor", "pe_ratio_ttm",
          "--param", "expect_df=false", "--format", "json"])
    assert calls["expect_df"] is False


def test_data_call_uses_dotted_rqdatac_function(monkeypatch, capsys):
    rqdatac = types.SimpleNamespace(init=lambda: None, user=types.SimpleNamespace(get_quota=lambda: {"remaining": 123}))
    monkeypatch.setitem(sys.modules, "rqdatac", rqdatac)

    main(["data", "call", "user.get_quota", "--format", "json"])
    assert json.loads(capsys.readouterr().out) == {"remaining": 123}


# --------------------------------------------------------------------------- #
# offline validation precedes license init
# --------------------------------------------------------------------------- #

def _rqdatac_with_failing_init():
    def boom():
        raise ValueError("username/password/addr or uri expected")

    return types.SimpleNamespace(init=boom)


def test_init_failure_gives_license_reminder(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "rqdatac", _rqdatac_with_failing_init())
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


def test_init_concurrency_limit_gives_targeted_message(monkeypatch, capsys):
    def boom(*args, **kwargs):
        raise RuntimeError("connection number exceeds")

    monkeypatch.setitem(sys.modules, "rqdatac", types.SimpleNamespace(init=boom))
    with pytest.raises(SystemExit) as exc:
        main(["data", "info"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "并发连接数已达上限" in err
    assert "no valid Ricequant license" not in err  # not misreported as a license problem


def test_fetch_missing_required_reported_before_init(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "rqdatac", _rqdatac_with_failing_init())
    with pytest.raises(SystemExit) as exc:
        main(["data", "fetch", "price"])  # missing --ids
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--ids" in err and "缺少必填参数" in err
    assert "username/password" not in err  # not masked by the init failure


def test_fetch_unknown_dataset_reported_before_init(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "rqdatac", _rqdatac_with_failing_init())
    with pytest.raises(SystemExit) as exc:
        main(["data", "fetch", "nope", "--ids", "000001.XSHE"])
    assert exc.value.code == 2
    assert "未知数据集" in capsys.readouterr().err


def test_unknown_dataset_suggests_close_match():
    from rqsdk_quant.datasets import get_dataset
    from rqsdk_quant.errors import CliError

    with pytest.raises(CliError) as exc:
        get_dataset("fund_nav")           # underscore typo for fund-nav
    assert "fund-nav" in str(exc.value)   # did-you-mean suggestion


def test_unrecognized_flag_hints_describe_and_param(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["data", "get", "price", "--ids", "000001.XSHE", "--nope", "x"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "unrecognized arguments" in err
    assert "rqq data describe" in err     # hint: where to find real params
    assert "--param" in err               # hint: escape hatch


def test_fetch_runtime_error_wrapped_with_recovery_hint(monkeypatch, capsys):
    def get_price(**kwargs):
        raise ValueError("fields: got invalided value cn")

    rqdatac = types.SimpleNamespace(init=lambda: None, get_price=get_price)
    monkeypatch.setitem(sys.modules, "rqdatac", rqdatac)
    monkeypatch.delenv("RQQ_DEBUG", raising=False)

    with pytest.raises(SystemExit) as exc:
        main(["data", "get", "price", "--ids", "000001.XSHE"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "调用失败" in err
    assert "ValueError: fields: got invalided value cn" in err   # keeps raw rqdatac message
    assert "rqq data describe price" in err                      # + recovery hint


def test_fetch_runtime_error_reraises_full_traceback_under_debug(monkeypatch):
    def get_price(**kwargs):
        raise ValueError("boom")

    rqdatac = types.SimpleNamespace(init=lambda: None, get_price=get_price)
    monkeypatch.setitem(sys.modules, "rqdatac", rqdatac)
    monkeypatch.setenv("RQQ_DEBUG", "1")

    with pytest.raises(ValueError):       # RQQ_DEBUG=1 surfaces the original traceback
        main(["data", "get", "price", "--ids", "000001.XSHE"])


# --------------------------------------------------------------------------- #
# license
# --------------------------------------------------------------------------- #

def _mock_rqdatac_for_license(monkeypatch, captured):
    def fake_init(**kwargs):
        captured.update(kwargs)

    rqdatac = types.SimpleNamespace(init=fake_init, user=types.SimpleNamespace(get_quota=lambda: {"remaining": 100}))
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
    assert json.loads(capsys.readouterr().out)["status"] == "ok"


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
    rqdatac = types.SimpleNamespace(init=lambda **k: captured.update(k), get_price=lambda **k: {"ok": True})
    monkeypatch.setitem(sys.modules, "rqdatac", rqdatac)

    main(["data", "get", "price", "--ids", "000001.XSHE", "--format", "json"])
    assert captured["uri"] == "tcp://license:STORED@rqdatad-pro.ricequant.com:16011"


# --------------------------------------------------------------------------- #
# help / reference
# --------------------------------------------------------------------------- #

def _help_text(capsys, argv):
    with pytest.raises(SystemExit):
        main(argv)
    return " ".join(capsys.readouterr().out.split())  # collapse argparse line wraps


def test_top_level_help_has_quickstart_examples(capsys):
    out = _help_text(capsys, ["--help"])
    assert "Quick start" in out
    assert "rqq license -l" in out
    assert "rqq data get price --ids 000001.XSHE" in out


def test_data_help_has_tips(capsys):
    out = _help_text(capsys, ["data", "--help"])
    assert "rqq data describe <dataset>" in out
    assert "--param KEY=VALUE" in out


def test_fetch_subcommand_help_is_detailed_and_points_to_describe(capsys):
    out = _help_text(capsys, ["data", "fetch", "--help"])
    assert "YYYY-MM-DD" in out
    assert "YYYYqN" in out
    assert "rqq data describe <dataset>" in out


def test_help_reference_markdown_lists_commands_and_modules(capsys):
    main(["help"])
    out = capsys.readouterr().out
    assert "### commands" in out
    assert "### modules" in out
    assert "data fetch <dataset> [params]" in out
    assert "get_price" in out


def test_help_reference_json_groups_datasets_by_module(capsys):
    main(["help", "--format", "json"])
    out = json.loads(capsys.readouterr().out)
    assert out["cli"] == "rqq"
    assert out["default_format"] == "markdown"

    rows = [d for m in out["modules"] for d in m["datasets"]]
    price = next(row for row in rows if row["name"] == "price")
    assert price["function"] == "get_price"
    assert "ids" in price["required"]
    assert "fields" in price["optional"]
    assert any("fetch" in row["command"] for row in out["commands"])


def test_data_help_alias_matches_top_level_help(capsys):
    main(["data", "help", "--format", "json"])
    data_help = json.loads(capsys.readouterr().out)
    main(["help", "--format", "json"])
    top_help = json.loads(capsys.readouterr().out)
    assert data_help == top_help


# --------------------------------------------------------------------------- #
# Windows UTF-8 output
# --------------------------------------------------------------------------- #

def test_force_utf8_io_corrects_non_utf8_stdout(monkeypatch):
    import io

    import rqsdk_quant.cli as climod

    buf = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(buf, encoding="gbk"))  # emulate Windows redirect
    climod._force_utf8_io()

    assert sys.stdout.encoding == "utf-8"
    sys.stdout.write("当前分钟行情")
    sys.stdout.flush()
    assert buf.getvalue() == "当前分钟行情".encode("utf-8")
