@echo off
title Autonomous Music Producer
echo Iniciando Autonomous Music Producer...
python iniciar.py
if errorlevel 1 (
    echo.
    echo Ocorreu um problema ao iniciar o servidor local.
    echo Verifique se o Python esta instalado ou execute setup_windows.bat.
    echo.
    pause
)
