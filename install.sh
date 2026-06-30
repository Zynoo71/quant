#!/bin/sh
# One-line install for the rqq CLI (Linux / macOS).
#   curl -fsSL https://raw.githubusercontent.com/Zynoo71/quant/main/install.sh | sh
set -e

REPO="git+https://github.com/Zynoo71/quant.git"

# 1. Ensure uv is installed (it also fetches a suitable Python).
if ! command -v uv >/dev/null 2>&1; then
  echo "==> Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

# 2. Install the rqq CLI with the data extra as a global tool.
echo "==> Installing rqq (rqsdk-quant[data])..."
uv tool install --force "rqsdk-quant[data] @ ${REPO}"
uv tool update-shell >/dev/null 2>&1 || true

cat <<'EOF'

==> Done. Open a new terminal (so `rqq` is on PATH), then:

  1) Paste your Ricequant license (validated and stored under ~/.rqq, takes effect immediately):
       rqq license -l "<your_license_key>"
     (or just `rqq license` to paste interactively; account:password also works)

  2) Try it:
       rqq help
       rqq data get price --ids 000001.XSHE --start 2024-01-02 --end 2024-01-03
EOF
