@echo off
title Autonomous Music Producer - Instalador
echo ========================================================
echo  Autonomous Music Producer - Instalador de Dependencias
echo  Compativel com Windows 10 e Windows 11
echo ========================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao foi encontrado no PATH do Windows!
    echo Por favor, instale o Python 3.10 ou superior em python.org
    echo e marque a opcao "Add Python to PATH" durante a instalacao.
    echo.
    pause
    exit /b 1
)

echo [1/3] Atualizando gerenciador pip...
python -m pip install --upgrade pip

echo.
echo [2/3] Instalando dependencias do projeto...
python -m pip install -r requirements.txt

echo.
echo ========================================================
echo [3/3] Instalacao concluida com sucesso!
echo ========================================================
echo Para iniciar o aplicativo a qualquer momento, execute:
echo   iniciar_windows.bat  OU  python iniciar.py
echo ========================================================
echo.
pause
