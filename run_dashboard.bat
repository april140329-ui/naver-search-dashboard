@echo off
chcp 65001 > nul
echo ======================================================
echo    네이버 마켓 인사이트 대시보드 (app.py) 실행 중...
echo ======================================================
cd /d "%~dp0"
start "" http://localhost:8501
call .venv\Scripts\python.exe -m streamlit run app.py --server.port 8501
pause
