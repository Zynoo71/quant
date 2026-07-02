from __future__ import annotations

import json
import os
import re
import warnings
from contextlib import contextmanager, redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any

from .datasets import build_dataset_kwargs, get_dataset
from .errors import CliError

LICENSE_PATH = Path.home() / ".rqq" / "credentials"
_LICENSE_HOST = "rqdatad-pro.ricequant.com:16011"


def _license_uri(cred: str) -> str:
    """Build an rqdatac connection uri from a license key or `account:password`."""
    cred = cred.strip()
    if "://" in cred:
        return cred  # already a full uri
    if ":" in cred:
        return f"tcp://{cred}@{_LICENSE_HOST}"  # account:password
    return f"tcp://license:{cred}@{_LICENSE_HOST}"  # bare license key


def _redact_uri(uri: str) -> str:
    return re.sub(r"(tcp://[^:/]+:)[^@]+(@)", r"\1****\2", uri)


def stored_license_uri() -> str | None:
    if LICENSE_PATH.exists():
        return LICENSE_PATH.read_text(encoding="utf-8").strip() or None
    return None


def set_license(cred: str) -> dict[str, Any]:
    """Validate a license (key or account:password) and persist it under ~/.rqq."""
    if not cred or not cred.strip():
        raise CliError("Empty license. Paste a license key or account:password.")
    uri = _license_uri(cred)
    rqdatac = load_rqdatac()
    with _suppress_known_warnings():
        try:
            with redirect_stdout(StringIO()):
                rqdatac.init(uri=uri)
                quota = rqdatac.user.get_quota()
        except Exception as exc:
            raise CliError(
                f"License validation failed — check the key/credentials. ({type(exc).__name__}: {exc})"
            ) from exc

    LICENSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    LICENSE_PATH.write_text(uri + "\n", encoding="utf-8")
    try:
        os.chmod(LICENSE_PATH, 0o600)
    except OSError:
        pass
    return {"status": "ok", "stored_at": str(LICENSE_PATH), "license": _redact_uri(uri), "quota": quota}


def license_info() -> dict[str, Any]:
    uri = stored_license_uri()
    env = os.environ.get("RQDATAC2_CONF") or os.environ.get("RQDATAC_CONF")
    return {
        "stored_file": str(LICENSE_PATH),
        "stored": _redact_uri(uri) if uri else "(none)",
        "env_RQDATAC2_CONF": _redact_uri(env) if env else "(none)",
    }


def clear_license() -> dict[str, Any]:
    if LICENSE_PATH.exists():
        LICENSE_PATH.unlink()
        return {"status": "cleared", "file": str(LICENSE_PATH)}
    return {"status": "nothing to clear", "file": str(LICENSE_PATH)}


def load_rqdatac() -> Any:
    try:
        import rqdatac  # type: ignore
    except ImportError as exc:
        raise CliError(
            "rqdatac is not installed. Install the data extras with `uv sync --extra data`."
        ) from exc
    return rqdatac


def init_rqdatac() -> Any:
    rqdatac = load_rqdatac()
    uri = stored_license_uri()
    with _suppress_known_warnings():
        try:
            if uri:
                rqdatac.init(uri=uri)
            else:
                rqdatac.init()
        except Exception as exc:
            detail = f"{type(exc).__name__}: {exc}"
            if "connection number exceeds" in str(exc):
                raise CliError(
                    "并发连接数已达上限（同一 license 约 6 个并发连接），license 本身没有问题。"
                    f"等待其他 rqq/rqdatac 进程结束后重试，或减少同时发起的命令数。({detail})"
                ) from exc
            raise CliError(
                "rqdatac failed to initialize — no valid Ricequant license is configured. "
                'Configure one with `rqq license -l "<license_key>"` (or `"<account>:<password>"`), '
                f"then retry. Underlying error: {detail}"
            ) from exc
    return rqdatac


def rq_info() -> Any:
    rqdatac = init_rqdatac()
    buffer = StringIO()
    with redirect_stdout(buffer):
        result = rqdatac.info()
    text = _redact_license(buffer.getvalue())
    if result is None:
        return text.strip()
    return {"info": text.strip(), "result": result}


def rq_quota() -> Any:
    rqdatac = init_rqdatac()
    with _suppress_known_warnings():
        return rqdatac.user.get_quota()


def rq_fetch_dataset(name: str, params: dict[str, Any]) -> Any:
    # Validate the request offline (unknown dataset / missing required params)
    # before touching the license, so a mistake gives a precise error instead of
    # being masked by an rqdatac init failure.
    spec = get_dataset(name)
    kwargs = build_dataset_kwargs(spec, params)
    rqdatac = init_rqdatac()
    with _suppress_known_warnings():
        return _resolve_attr(rqdatac, spec.function)(**kwargs)


def rq_call(function_name: str, args_json: str | None, kwargs_json: str | None) -> Any:
    rqdatac = init_rqdatac()
    target = _resolve_attr(rqdatac, function_name)
    args = _load_json(args_json, default=[])
    kwargs = _load_json(kwargs_json, default={})
    if not isinstance(args, list):
        raise CliError("--args must be a JSON array.")
    if not isinstance(kwargs, dict):
        raise CliError("--kwargs must be a JSON object.")
    with _suppress_known_warnings():
        return target(*args, **kwargs)


@contextmanager
def _suppress_known_warnings() -> Any:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Your account will be expired after.*", category=UserWarning)
        warnings.filterwarnings("ignore", message="'nav' is deprecated.*", category=UserWarning)
        yield


def _resolve_attr(root: Any, dotted_name: str) -> Any:
    current = root
    for part in dotted_name.split("."):
        if not part:
            raise CliError(f"Invalid function name: {dotted_name}")
        if not hasattr(current, part):
            raise CliError(f"rqdatac has no attribute path: {dotted_name}")
        current = getattr(current, part)
    if not callable(current):
        raise CliError(f"rqdatac attribute is not callable: {dotted_name}")
    return current


def _load_json(value: str | None, default: Any) -> Any:
    if value is None:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise CliError(f"Invalid JSON: {exc}") from exc


def _redact_license(text: str) -> str:
    text = re.sub(r"(You are using license:\s*)\S+", r"\1[REDACTED]", text)
    text = re.sub(r"tcp://license:[^@]+@", "tcp://license:[REDACTED]@", text)
    return text
