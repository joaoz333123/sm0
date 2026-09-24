@echo off
chcp 65001 >nul
title Backup Samsung S22 - Sem WhatsApp
cls
echo =======================================================
echo   Iniciando Backup Seguro do Samsung Galaxy S22
echo   Destino: inventario_backup\arquivos_copiados
echo =======================================================
echo.
python -u backup_sem_whatsapp.py
echo.
echo Pressione qualquer tecla para fechar esta janela...
pause >nul
