@echo off
TITLE Face Emotion System - Multi Runner
echo [*] Dang khoi dong he thong...

:: Lay duong dan thu muc hien tai
set ROOT_DIR=%~dp0

:: 1. Khoi dong Backend (FastAPI)
echo [+] Dang mo Backend trong cua so moi...
start "BACKEND - FastAPI" cmd /k "cd /d %ROOT_DIR%emotion\emotion && echo [BACKEND] Dang chay server... && (.venv\Scripts\python -m app.main || py -3.11 -m app.main || python -m app.main)"

:: 2. Khoi dong Frontend (Vite)
echo [+] Dang mo Frontend trong cua so moi...
start "FRONTEND - React" cmd /k "cd /d %ROOT_DIR%frontend-AI && echo [FRONTEND] Dang chay npm run dev... && npm run dev"

echo.
echo [!] XONG! Vui long kiem tra 2 cua so Terminal moi mo.
echo [!] Neu Backend bao loi 'Port 8000 already in use', hay dong cac terminal cu va thu lai.
echo.
pause
