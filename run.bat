@echo off
chcp 65001 > nul
title RiskGuard AI

echo.
echo  ====================================================
echo   RiskGuard AI - Road Accident Risk Assessment
echo   Pearson BTEC Level 6 - Independent Project
echo  ====================================================
echo.

cd /d "%~dp0"

echo [1/4] Checking Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERROR: Python not found! Install from https://python.org
    pause & exit /b 1
)
python --version

echo.
echo [2/4] Checking packages...
python -c "import flask,sklearn,pandas,numpy,joblib,flask_sqlalchemy,flask_cors" >nul 2>&1
if %errorlevel% neq 0 (
    echo  Installing packages (please wait)...
    python -m pip install flask scikit-learn pandas numpy joblib flask-sqlalchemy flask-cors -q
)
echo  Packages OK.

echo.
echo [3/4] Checking ML model...
if not exist "model\risk_model.pkl" (
    echo  Training model (30-60 seconds)...
    python setup.py
    if %errorlevel% neq 0 ( echo ERROR in setup.py & pause & exit /b 1 )
) else (
    echo  Model OK.
)

echo.
echo [4/4] Starting server...
echo.
echo  ====================================================
echo   Browser da ochingiz:
echo.
echo       http://127.0.0.1:5000
echo.
echo   Dasturni to'xtatish uchun: Ctrl+C
echo  ====================================================
echo.

python app.py

echo.
pause
