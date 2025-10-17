#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -d ".venv" ]; then
  echo "Creating local virtual environment..."
  python3 -m venv .venv
fi
source .venv/bin/activate
python3 -m pip install --upgrade pip --quiet
python3 -c "import pygame" 2>/dev/null || python3 -m pip install --quiet pygame
python3 src/main.py
