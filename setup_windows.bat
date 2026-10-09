@echo off
chcp 65001 > nul
echo ========================================================
echo  Autonomous Music Producer - Instalador de Dependências
echo  Compatível com Windows 10 e 11 (AMD Ryzen / Intel)
echo ========================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python não foi encontrado no PATH do Windows!
    echo Por favor, instale o Python 3.10 ou superior em python.org
    echo e marque a opção "Add Python to PATH" durante a instalação.
    pause
    exit /b 1
)

echo [1/3] Atualizando gerenciador pip...
python -m pip install --upgrade pip

echo [2/3] Instalando dependências de áudio, MIDI e PyTorch para CPU...
python -m pip install -r requirements.txt

echo.
echo [3/3] Instalação concluída com sucesso!
echo.
echo Para iniciar o aplicativo a qualquer momento, execute:
echo   iniciar_windows.bat  OU  python iniciar.py
echo.
pause
