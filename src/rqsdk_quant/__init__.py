"""rqsdk_quant package."""

from importlib.metadata import PackageNotFoundError, version

try:  # single source of truth: the installed package version (from pyproject.toml)
    __version__ = version("rqsdk-quant")
except PackageNotFoundError:  # running from source without an install
    __version__ = "0.0.0"
