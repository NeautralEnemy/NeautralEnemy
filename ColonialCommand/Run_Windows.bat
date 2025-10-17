@echo off
setlocal
set PROJDIR=%~dp0
cd /d "%PROJDIR%"
if not exist ".venv" (
  echo Creating local virtual environment...
  py -3 -m venv .venv || python -m venv .venv
)
call .venv\Scripts\activate
python -m pip install --upgrade pip --quiet
python -c "import pygame" 2>NUL || (
  echo Installing dependencies...
  pip install --quiet pygame
)
python src\main.py
