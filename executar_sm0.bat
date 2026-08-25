@echo off
echo ========================================
echo  SM0 - Utilitario de Espelhamento Android
echo ========================================
echo.
echo [1/2] Verificando e instalando dependencias...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar dependencias.
    pause
    exit /b %errorlevel%
)
echo.
echo [2/2] Iniciando aplicacao SM0...
python main.py
if %errorlevel% neq 0 (
    echo [ERRO] A aplicacao encerrou com erro.
    pause
)
