@echo off
chcp 65001 > nul
echo Iniciando Autonomous Music Producer...
python iniciar.py
if %errorlevel% neq 0 (
    echo.
    echo Ocorreu um problema ao iniciar. Pressione qualquer tecla para sair.
    pause
)
