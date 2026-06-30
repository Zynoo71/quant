# One-line install for the rqq CLI (Windows, PowerShell).
#   irm https://raw.githubusercontent.com/Zynoo71/quant/main/install.ps1 | iex
$ErrorActionPreference = "Stop"

$Repo = "git+https://github.com/Zynoo71/quant.git"

# 1. Ensure uv is installed (it also fetches a suitable Python).
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "==> Installing uv..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

# 2. Install the rqq CLI with the data extra as a global tool.
Write-Host "==> Installing rqq (rqsdk-quant[data])..."
uv tool install --force "rqsdk-quant[data] @ $Repo"
uv tool update-shell

Write-Host ""
Write-Host "==> Done. Open a new terminal (so 'rqq' is on PATH), then:"
Write-Host ""
Write-Host "  1) Paste your Ricequant license (validated and stored under ~/.rqq, takes effect immediately):"
Write-Host '       rqq license -l "<your_license_key>"'
Write-Host "     (or just 'rqq license' to paste interactively; account:password also works)"
Write-Host ""
Write-Host "  2) Try it:"
Write-Host "       rqq help"
Write-Host "       rqq data get price --ids 000001.XSHE --start 2024-01-02 --end 2024-01-03"
