@echo off
setlocal
set PROJDIR=%~dp0
cd /d "%PROJDIR%"
if not exist .venv (
  echo Please run the game once to set up the virtual environment.
  exit /b 1
)
call .venv\Scripts\activate
pyinstaller build.spec
