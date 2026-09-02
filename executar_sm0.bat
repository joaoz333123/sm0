@echo off
echo ========================================
echo  SM0 - Utilitario de Espelhamento Android
echo ========================================
echo.
echo [1/2] Verificando dependencias...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao verificar dependencias.
    pause
    exit /b %errorlevel%
)
echo.
echo [2/2] Iniciando aplicacao SM0...
start "" pythonw main.py
exit
