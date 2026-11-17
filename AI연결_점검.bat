@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "python\python.exe" (
  "python\python.exe" jeju_med\tools\llm_check.py
) else (
  where python >nul 2>nul && (python jeju_med\tools\llm_check.py) || (py -3 jeju_med\tools\llm_check.py)
)
