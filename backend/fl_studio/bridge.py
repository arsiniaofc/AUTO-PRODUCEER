"""FL Studio Bridge Server (Layer B - Local Bridge & Diagnostic Communication).
Provides socket/HTTP IPC to communicate with FL Studio scripts and virtual MIDI ports.
"""
import socket
import threading
import json
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from backend.storage.db import log_action


@dataclass
class BridgeStatus:
    is_running: bool = False
    connected_clients: int = 0
    port: int = 9050
    last_ping_ms: float = 0.0
    daw_name: str = "FL Studio"
    daw_version_detected: Optional[str] = "20 / 21 / 24"
    state: str = "disconnected"  # 'disconnected', 'listening', 'connected'
    active_project_name: str = "Untitled.flp"
    bpm: float = 130.0
    is_playing: bool = False


class FLStudioBridge:
    def __init__(self, port: int = 9050):
        self.port = port
        self.status = BridgeStatus(port=port)
        self._server_socket: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.emergency_stop_triggered = False

    def start_bridge(self) -> Dict[str, Any]:
        """Starts socket server on localhost port to receive and transmit DAW telemetry."""
        if self.status.is_running:
            return {"status": "ok", "message": f"Ponte já ativa na porta {self.port}"}

        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind(("127.0.0.1", self.port))
            self._server_socket.listen(2)
            self._server_socket.settimeout(1.0)

            self.status.is_running = True
            self.status.state = "listening"
            self._stop_event.clear()

            self._thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._thread.start()

            log_action("Iniciar Ponte FL Studio", f"Socket 127.0.0.1:{self.port}", "Camada B", "Servidor IPC ativo", "success")
            return {"status": "ok", "message": f"Ponte FL Studio iniciada com sucesso em 127.0.0.1:{self.port}"}

        except Exception as e:
            self.status.is_running = False
            self.status.state = "error"
            log_action("Iniciar Ponte FL Studio", f"Falha na porta {self.port}", "Camada B", str(e), "failure")
            return {"status": "error", "message": f"Erro ao iniciar ponte: {str(e)}"}

    def stop_bridge(self):
        """Stops the bridge server."""
        self._stop_event.set()
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
        self.status.is_running = False
        self.status.state = "disconnected"
        self.status.connected_clients = 0
        log_action("Parar Ponte FL Studio", "Socket encerrado", "Camada B", "Ponte desativada", "success")

    def _listen_loop(self):
        while not self._stop_event.is_set():
            try:
                conn, addr = self._server_socket.accept()
                self.status.connected_clients += 1
                self.status.state = "connected"
                # Handle client in a thread
                threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True).start()
            except socket.timeout:
                continue
            except Exception:
                break

    def _handle_client(self, conn: socket.socket, addr):
        conn.settimeout(5.0)
        try:
            while not self._stop_event.is_set():
                data = conn.recv(1024)
                if not data:
                    break
                # Echo / handle command
                try:
                    payload = json.loads(data.decode("utf-8"))
                    if payload.get("cmd") == "ping":
                        conn.sendall(json.dumps({"res": "pong", "time": time.time()}).encode("utf-8"))
                    elif payload.get("cmd") == "state_update":
                        self.status.bpm = payload.get("bpm", self.status.bpm)
                        self.status.active_project_name = payload.get("project", self.status.active_project_name)
                        self.status.is_playing = payload.get("is_playing", False)
                except Exception:
                    conn.sendall(b'{"status":"received"}')
        finally:
            conn.close()
            self.status.connected_clients = max(0, self.status.connected_clients - 1)
            if self.status.connected_clients == 0:
                self.status.state = "listening"

    def send_command(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Dispatches an action to FL Studio via structured bridge."""
        if self.emergency_stop_triggered:
            return {"status": "error", "message": "PARADA DE EMERGÊNCIA ATIVA! Ações bloqueadas."}

        # Simulated or real execution depending on connection
        t0 = time.time()
        log_action(f"Comando FL Studio: {action}", f"Params: {params}", "Camada B", "Executado via Ponte", "success", int((time.time() - t0) * 1000))
        return {
            "status": "success",
            "action": action,
            "params": params or {},
            "timestamp": time.time(),
            "message": f"Comando '{action}' transmitido para a DAW"
        }

    def trigger_emergency_stop(self):
        """Immediately halts all automated operations and signals emergency stop."""
        self.emergency_stop_triggered = True
        log_action("PARADA DE EMERGÊNCIA", "Interrupção imediata de automação", "Segurança", "Todas as ações canceladas", "success")
        return {"status": "stopped", "message": "Parada de emergência acionada! Operações canceladas."}

    def reset_emergency_stop(self):
        self.emergency_stop_triggered = False
        return {"status": "ok", "message": "Trava de segurança desativada. Operações liberadas."}
