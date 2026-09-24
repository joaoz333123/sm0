@echo off
chcp 65001 >nul
title Backup Samsung S22 - Sem WhatsApp
echo =======================================================
echo   Iniciando Backup Seguro do Samsung Galaxy S22
echo   Destino: inventario_backup\arquivos_copiados
echo =======================================================
python backup_sem_whatsapp.py
echo.
pause
