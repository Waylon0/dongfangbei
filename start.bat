@echo off
chcp 65001 >nul
echo ============================================
echo   断层多边形自动追踪系统
echo   Fault Polygon Auto-Tracking System
echo ============================================
echo.

set "ANACONDA_PYTHON=d:\my anaconda\python.exe"

echo [1/2] 启动后端 FastAPI (port 8000)...
start "Backend API" "%ANACONDA_PYTHON%" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

echo [2/2] 启动前端 Vite Dev (port 5173)...
echo.
echo 浏览器打开: http://localhost:5173
echo.
cd /d "%~dp0frontend"
npm run dev
