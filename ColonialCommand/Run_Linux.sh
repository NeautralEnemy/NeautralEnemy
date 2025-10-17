#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -d ".venv" ]; then
  echo "Creating local virtual environment..."
  python3 -m venv .venv
fi
source .venv/bin/activate
python3 -m pip install --upgrade pip --quiet
python3 - <<'PY'
try:
    import pygame  # noqa
except Exception:
    import sys, subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame", "-q"])
import runpy; runpy.run_path("src/main.py")
PY
