@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 제주 읍면동별 진료과목 분포 비교 Agent를 시작합니다...
if exist "python\python.exe" (
  "python\python.exe" jeju_med\server.py
) else (
  where python >nul 2>nul && (python jeju_med\server.py) || (py -3 jeju_med\server.py)
)
pause
