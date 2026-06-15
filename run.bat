@echo off
chcp 65001 > nul
title RiskGuard AI — Starting...

echo.
echo  ============================================================
echo   RiskGuard AI — Road Accident Risk Assessment System
echo   Pearson BTEC Level 6 ^| PDP University ^| Mubina Rustamova
echo  ============================================================
echo.

cd /d "%~dp0"

:: ── Step 1: Python check ──────────────────────────────────────────
echo  [1/4]  Checking Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo   ERROR: Python is not installed!
    echo   Please download Python 3.11 from: https://python.org/downloads
    echo   Make sure to tick "Add Python to PATH" during installation.
    echo.
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo   Found: %PYVER%

:: ── Step 2: Install ALL required packages ─────────────────────────
echo.
echo  [2/4]  Installing / checking packages (this may take 1-2 min on first run)...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo.
    echo   ERROR: Package installation failed.
    echo   Try running:  python -m pip install -r requirements.txt
    echo.
    pause & exit /b 1
)
echo   All packages OK.

:: ── Step 3: Create .env if missing ────────────────────────────────
if not exist ".env" (
    echo.
    echo  [3/4]  Creating default .env file...
    (
        echo ADMIN_USERNAME=admin
        echo ADMIN_PASSWORD=admin123
        echo SECRET_KEY=riskguard-secret-key-2026
    ) > .env
    echo   Default login:  admin  /  admin123
) else (
    echo.
    echo  [3/4]  .env found — credentials loaded.
)

:: ── Step 4: Train model if not present ────────────────────────────
echo.
if not exist "model\risk_model.pkl" (
    echo  [4/4]  Training ML model — please wait 3-5 minutes...
    echo         ^(this only happens once^)
    echo.
    python setup.py
    if %errorlevel% neq 0 (
        echo.
        echo   ERROR: Model training failed. Check setup.py output above.
        echo.
        pause & exit /b 1
    )
) else (
    echo  [4/4]  ML model found — skipping training.
)

:: ── Launch ────────────────────────────────────────────────────────
echo.
echo  ============================================================
echo   READY!  Open your browser and go to:
echo.
echo         http://127.0.0.1:5000
echo.
echo   Login:    admin
echo   Password: admin123
echo.
echo   To stop:  press Ctrl+C in this window
echo  ============================================================
echo.

python app.py

echo.
echo  Server stopped.
pause
