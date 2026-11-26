@echo off
chcp 65001 >nul
title Tangerine Grand Hotel — Web Server
cd /d "%~dp0"

echo ============================================================
echo   TANGERINE GRAND HOTEL — HE THONG GIAO DIEN WEB (TC-04)
echo ============================================================

:: 1. Tim trinh thong dich Python phu hop
set "PY=python"
if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    set "PY=%LOCALAPPDATA%\Python\bin\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    set "PY=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
) else if exist "C:\msys64\ucrt64\bin\python.exe" (
    set "PY=C:\msys64\ucrt64\bin\python.exe"
)

:: 2. Tu dong kiem tra va cai dat thu vien web neu may chua co
"%PY%" -c "import fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [THONG BAO] Phat hien may chua co thu vien FastAPI/Uvicorn.
    echo Dang tu dong cai dat thu vien can thiet, vui long cho giay lat...
    "%PY%" -m pip install fastapi uvicorn
    echo [OK] Da cai dat xong thu vien!
    echo.
)

:: 3. Neu co tien trinh may chu cu dang chiem cong 8000 thi khoi dong lai de nap ban cap nhat moi nhat
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /C:":8000 " ^| findstr "LISTENING"') do (
    echo [THONG BAO] Dang khoi dong lai may chu tren cong 8000...
    taskkill /F /PID %%a >nul 2>&1
)

echo Dang khoi dong he thong...
echo Dia chi truy cap: http://localhost:8000
echo.

:: 4. Mo trinh duyet sau khi khoi dong
start /b cmd /c "ping 127.0.0.1 -n 3 >nul && start http://localhost:8000"

:: 5. Chay may chu truc tiep (dong cua so de tat may chu)
"%PY%" backend/run.py
