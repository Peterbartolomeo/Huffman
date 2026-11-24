@echo off
cd /d "%~dp0"
:loop
python home_monitor.py
timeout /t 60
goto loop
