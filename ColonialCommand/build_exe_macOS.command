#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "Please run the game once to set up the virtual environment."
  exit 1
fi
source .venv/bin/activate
pyinstaller build.spec
