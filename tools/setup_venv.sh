#!/usr/bin/env bash
# Create the Python venv used by the tasmia ASR tools and install deps.
# Re-running is fast: pip reuses its download cache (~/.cache/pip).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="${TASMIA_VENV:-/tmp/opencode/warsh-venv}"

python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install -q --upgrade pip
# torch comes from the PyTorch CPU index; everything else from PyPI.
# Two separate commands: the --index-url applies to the whole call.
"$VENV/bin/python" -m pip install -q --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
"$VENV/bin/python" -m pip install -q --no-cache-dir transformers scipy numpy

echo "venv ready at $VENV"
