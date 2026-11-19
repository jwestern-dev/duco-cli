@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto virtual
where python >nul 2>nul
if not errorlevel 1 goto systempython
where py >nul 2>nul
if not errorlevel 1 goto pylauncher
echo Python is missing. Install Python 3.11 or newer, then follow README.md.
set result=1
goto finished
:virtual
".venv\Scripts\python.exe" run.py %*
goto capture
:systempython
python run.py %*
goto capture
:pylauncher
py -3 run.py %*
:capture
set result=%errorlevel%
:finished
if not "%result%"=="0" pause
exit /b %result%
