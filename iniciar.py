#!/usr/bin/env python3
"""
Autonomous Music Producer - Ponto de Entrada Principal
Execução: python iniciar.py
"""
import os
import sys
import time
import socket
import webbrowser
import threading
from server import run_server, ROOT_DIR


def check_system_diagnostics():
    print("+" + "-" * 62 + "+")
    print("|      AUTONOMOUS MUSIC PRODUCER - IA MUSICAL & FL STUDIO      |")
    print("+" + "-" * 62 + "+")
    print(f"|  Python: {sys.version.split(' ')[0]:<15} Plataforma: {sys.platform:<22} |")

    # Check optional packages
    packages = [
        ("sqlite3", "Persistência e Metadados"),
        ("torch", "Deep Learning / PyTorch CPU"),
        ("mido", "Processamento MIDI Avançado"),
        ("pyflp", "Leitor de Projetos FL Studio"),
        ("psutil", "Monitoramento de CPU/RAM")
    ]

    print("|" + " " * 62 + "|")
    print("|  Verificação de Módulos Locais:                              |")
    for pkg_name, desc in packages:
        try:
            __import__(pkg_name)
            status = "[OK] Instalado"
        except ImportError:
            status = "[!] Opcional/Nativo"
        print(f"|  - {pkg_name:<10}: {status:<18} ({desc:<21})|")

    print("+" + "-" * 62 + "+\n")


def is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def open_browser_delayed(url: str, delay_sec: float = 1.2):
    def _open():
        time.sleep(delay_sec)
        try:
            webbrowser.open(url)
            print(f"Navegador aberto automaticamente em: {url}")
        except Exception:
            pass
    threading.Thread(target=_open, daemon=True).start()


def main():
    check_system_diagnostics()

    # Create local directories
    for folder in ["train", "data", "data/generated", "data/processed", "models", "logs", "frontend"]:
        os.makedirs(os.path.join(ROOT_DIR, folder), exist_ok=True)

    target_port = 8000
    while not is_port_available(target_port) and target_port < 8010:
        target_port += 1

    url = f"http://127.0.0.1:{target_port}"
    print(f"Iniciando servidor local em {url}...")
    open_browser_delayed(url)

    try:
        run_server(target_port)
    except KeyboardInterrupt:
        print("\nAplicação encerrada pelo usuário.")
        sys.exit(0)


if __name__ == "__main__":
    main()
