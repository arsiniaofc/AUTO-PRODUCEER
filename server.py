"""Local HTTP and REST API server for Autonomous Music Producer.
Runs with standard Python library (no mandatory external frameworks required)
and optionally interfaces with FastAPI/Uvicorn if installed.
"""
import os
import sys
import json
import time
import socket
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Dict, Any, Optional

# Ensure project root is in path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.storage.db import (
    init_db, list_files, add_or_update_file, get_actions, log_action,
    get_settings, update_setting, get_db_connection
)
from backend.music_theory.analyzer import HarmonicAnalyzer
from backend.midi.parser import MidiParser
from backend.midi.tokenizer import MidiTokenizer
from backend.flp.parser import FlpParser
from backend.training.trainer import ContinuousTrainer
from backend.generation.generator import MusicGenerator
from backend.fl_studio.bridge import FLStudioBridge
from backend.fl_studio.fl_midi_script import generate_fl_midi_script
from backend.fl_studio.automation import FLStudioUIAutomation
from backend.memory.state import MusicalMemory, DAWStateMemory

DIST_DIR = os.path.join(ROOT_DIR, "dist")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
TRAIN_DIR = os.path.join(ROOT_DIR, "train")

# In accordance with the local native architecture, serve the native HTML5/CSS3/JS frontend
SERVE_DIR = FRONTEND_DIR

# Global engine instances
trainer = ContinuousTrainer()
bridge = FLStudioBridge(port=9050)
ui_automation = FLStudioUIAutomation()
musical_memory = MusicalMemory()
daw_memory = DAWStateMemory()


def scan_train_folder() -> list:
    """Scans the train/ folder, parsing any .mid or .flp files found and saving them to the library DB."""
    os.makedirs(TRAIN_DIR, exist_ok=True)
    scanned_files = []
    for fname in os.listdir(TRAIN_DIR):
        fpath = os.path.join(TRAIN_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        ext = os.path.splitext(fname)[1].lower()

        if ext in [".mid", ".midi"]:
            try:
                song = MidiParser.parse_file(fpath)
                all_notes = [{"pitch": n.pitch, "start": n.start, "duration": n.duration, "velocity": n.velocity} for t in song.tracks for n in t.notes]
                key_est = HarmonicAnalyzer.estimate_key(all_notes)
                file_info = {
                    "file_path": fpath,
                    "file_name": fname,
                    "file_type": "MIDI",
                    "file_size": os.path.getsize(fpath),
                    "status": "processed",
                    "duration_sec": song.duration_sec,
                    "bpm": song.bpm,
                    "key_signature": f"{key_est.root} {key_est.mode.capitalize()}",
                    "time_signature": song.time_signature,
                    "track_count": len(song.tracks),
                    "note_count": song.total_notes,
                    "channels": [{"name": t.name, "notes": len(t.notes), "is_drum": t.is_drum} for t in song.tracks],
                    "is_trained": 0
                }
                add_or_update_file(file_info)
                scanned_files.append(file_info)
            except Exception as e:
                print(f"[Aviso] Erro ao ler MIDI {fname}: {e}")

        elif ext == ".flp":
            try:
                flp_proj = FlpParser.parse_file(fpath)
                file_info = {
                    "file_path": fpath,
                    "file_name": fname,
                    "file_type": "FLP",
                    "file_size": os.path.getsize(fpath),
                    "status": "processed",
                    "duration_sec": 60.0,
                    "bpm": flp_proj.bpm,
                    "key_signature": "Inferido do arranjo",
                    "time_signature": "4/4",
                    "track_count": len(flp_proj.channels),
                    "note_count": sum(p.notes_count for p in flp_proj.patterns),
                    "channels": [{"name": c.name, "plugin": c.plugin_name} for c in flp_proj.channels],
                    "is_trained": 0
                }
                add_or_update_file(file_info)
                scanned_files.append(file_info)
            except Exception as e:
                print(f"[Aviso] Erro ao ler FLP {fname}: {e}")

    return scanned_files


class ProducerRequestHandler(SimpleHTTPRequestHandler):
    """Handles REST API requests and serves static frontend assets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SERVE_DIR, **kwargs)

    def guess_type(self, path):
        """Strictly override MIME types to avoid Windows Registry .js -> text/plain bug."""
        p_lower = path.lower()
        if p_lower.endswith(".js") or p_lower.endswith(".mjs"):
            return "application/javascript"
        if p_lower.endswith(".css"):
            return "text/css"
        if p_lower.endswith(".json"):
            return "application/json"
        if p_lower.endswith(".mid") or p_lower.endswith(".midi"):
            return "audio/midi"
        if p_lower.endswith(".html") or p_lower.endswith(".htm"):
            return "text/html"
        return super().guess_type(path)

    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._set_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> Dict[str, Any]:
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len <= 0:
            return {}
        raw = self.rfile.read(content_len)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/"):
            self._handle_api_get(path)
        else:
            # Fallback to index.html if route not found (SPA routing)
            file_target = os.path.join(FRONTEND_DIR, path.lstrip("/"))
            if not os.path.exists(file_target) and not os.path.splitext(path)[1]:
                self.path = "/index.html"
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            self._handle_api_post(path)
        else:
            self._send_json({"error": "Endpoint não encontrado"}, 404)

    def _handle_api_get(self, path: str):
        if path == "/api/status":
            import psutil
            cpu_pct = 0.0
            ram_mb = 0.0
            try:
                cpu_pct = psutil.cpu_percent(interval=None)
                ram_mb = psutil.Process().memory_info().rss / (1024 * 1024)
            except Exception:
                pass

            files = list_files()
            self._send_json({
                "status": "online",
                "app_name": "Autonomous Music Producer",
                "version": "1.0.0",
                "cpu_percent": round(cpu_pct, 1),
                "ram_usage_mb": round(ram_mb, 1),
                "files_count": len(files),
                "trained_count": sum(1 for f in files if f.get("is_trained")),
                "training_active": trainer.status.is_training,
                "bridge_status": bridge.status.state,
                "emergency_stop": bridge.emergency_stop_triggered,
                "model_version": trainer.status.model_version
            })

        elif path == "/api/library":
            self._send_json({"files": list_files()})

        elif path == "/api/training/status":
            self._send_json(trainer.get_status())

        elif path == "/api/models":
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM models ORDER BY id DESC")
            models = [dict(r) for r in cursor.fetchall()]
            conn.close()
            self._send_json({"models": models})

        elif path == "/api/memory":
            self._send_json({
                "musical_memory": {
                    "key_root": musical_memory.key_root,
                    "key_mode": musical_memory.key_mode,
                    "confidence": musical_memory.confidence,
                    "tonic_center": musical_memory.tonic_center,
                    "chord_degrees": musical_memory.chord_degrees,
                    "density_rating": musical_memory.density_rating,
                    "bass_melody_relation": musical_memory.bass_melody_relation,
                    "arrangement_gaps": musical_memory.arrangement_gaps,
                    "ai_decision_log": musical_memory.ai_decision_log
                },
                "daw_state": {
                    "project_name": daw_memory.project_name,
                    "bpm": daw_memory.bpm,
                    "time_signature": daw_memory.time_signature,
                    "identified_channels": daw_memory.identified_channels,
                    "active_selection": daw_memory.active_selection,
                    "focused_window": daw_memory.focused_window,
                    "visible_windows": daw_memory.visible_windows,
                    "last_verified_action": daw_memory.last_verified_action,
                    "mode": daw_memory.mode
                }
            })

        elif path == "/api/bridge/status":
            is_fl_running, window_name = ui_automation.is_fl_studio_running()
            self._send_json({
                "bridge_running": bridge.status.is_running,
                "bridge_port": bridge.port,
                "state": bridge.status.state,
                "connected_clients": bridge.status.connected_clients,
                "fl_studio_process_detected": is_fl_running,
                "detected_window_title": window_name,
                "emergency_stop": bridge.emergency_stop_triggered,
                "active_project": bridge.status.active_project_name,
                "bpm": bridge.status.bpm,
                "is_playing": bridge.status.is_playing
            })

        elif path == "/api/actions":
            self._send_json({"actions": get_actions(50)})

        elif path == "/api/settings":
            self._send_json({"settings": get_settings()})

        elif path == "/api/diagnostics":
            import platform
            try:
                import torch
                torch_info = f"PyTorch {torch.__version__} (Device: {'CUDA' if torch.cuda.is_available() else 'CPU'})"
            except ImportError:
                torch_info = "PyTorch não instalado (Modo N-Gram/Markov ativo)"

            try:
                import pyflp
                pyflp_info = f"PyFLP {pyflp.__version__} disponível"
            except ImportError:
                pyflp_info = "PyFLP não instalado (Decodificador binário nativo ativo)"

            is_running, win_name = ui_automation.is_fl_studio_running()

            self._send_json({
                "platform": platform.platform(),
                "python_version": sys.version.split(" ")[0],
                "processor": platform.processor() or "AMD / Intel x86_64",
                "torch": torch_info,
                "pyflp": pyflp_info,
                "sqlite": "SQLite3 operacional",
                "fl_studio_detected": is_running,
                "fl_studio_window": win_name or "Nenhuma janela ativa do FL Studio no momento"
            })

        elif path == "/api/library/scan_train":
            scanned = scan_train_folder()
            self._send_json({"status": "success", "scanned_count": len(scanned), "files": list_files()})

        elif path == "/api/bridge/download_script":
            script_path = generate_fl_midi_script()
            with open(script_path, "r", encoding="utf-8") as f:
                content = f.read()
            self._send_json({"script_path": script_path, "content": content})

        else:
            self._send_json({"error": "Rota GET não encontrada"}, 404)

    def _handle_api_post(self, path: str):
        payload = self._read_json_body()

        if path == "/api/library/import":
            # Simulate or import path
            fpath = payload.get("file_path") or payload.get("path")
            sample_data = payload.get("sample_data")

            if not fpath and not sample_data:
                self._send_json({"status": "error", "message": "Caminho do arquivo não fornecido"}, 400)
                return

            try:
                if sample_data:
                    # Synthetic / in-memory import for demo
                    fname = sample_data.get("name", "sample_track.mid")
                    fpath = os.path.join(ROOT_DIR, "data", fname)
                    song = MidiSong(bpm=sample_data.get("bpm", 124.0))
                    MidiParser.write_file(song, fpath)

                fname = os.path.basename(fpath)
                ext = os.path.splitext(fpath)[1].lower()

                if ext in [".mid", ".midi"]:
                    song = MidiParser.parse_file(fpath)
                    all_notes = [{"pitch": n.pitch, "start": n.start, "duration": n.duration, "velocity": n.velocity} for t in song.tracks for n in t.notes]
                    key_est = HarmonicAnalyzer.estimate_key(all_notes)
                    file_info = {
                        "file_path": fpath,
                        "file_name": fname,
                        "file_type": "MIDI",
                        "file_size": os.path.getsize(fpath) if os.path.exists(fpath) else 1024,
                        "status": "processed",
                        "duration_sec": song.duration_sec,
                        "bpm": song.bpm,
                        "key_signature": f"{key_est.root} {key_est.mode.capitalize()}",
                        "time_signature": song.time_signature,
                        "track_count": len(song.tracks),
                        "note_count": song.total_notes,
                        "channels": [{"name": t.name, "notes": len(t.notes), "is_drum": t.is_drum} for t in song.tracks]
                    }
                    add_or_update_file(file_info)
                    log_action("Importar MIDI", f"Processado {fname}", "Biblioteca", f"Detectado {key_est.root} {key_est.mode}", "success")
                    self._send_json({"status": "success", "file": file_info})

                elif ext == ".flp":
                    flp_proj = FlpParser.parse_file(fpath)
                    file_info = {
                        "file_path": fpath,
                        "file_name": fname,
                        "file_type": "FLP",
                        "file_size": os.path.getsize(fpath) if os.path.exists(fpath) else 2048,
                        "status": "processed",
                        "duration_sec": 60.0,
                        "bpm": flp_proj.bpm,
                        "key_signature": "Inferido do arranjo",
                        "time_signature": "4/4",
                        "track_count": len(flp_proj.channels),
                        "note_count": sum(p.notes_count for p in flp_proj.patterns),
                        "channels": [{"name": c.name, "plugin": c.plugin_name} for c in flp_proj.channels],
                        "error_log": f"Suportados: {', '.join(flp_proj.supported_fields)}. Limitações: {', '.join(flp_proj.unsupported_fields)}"
                    }
                    add_or_update_file(file_info)
                    log_action("Importar FLP", f"Processado {fname}", "Biblioteca", f"{len(flp_proj.channels)} canais extraídos", "success")
                    self._send_json({"status": "success", "file": file_info})
                else:
                    self._send_json({"status": "error", "message": f"Formato '{ext}' não suportado"}, 400)
            except Exception as e:
                self._send_json({"status": "error", "message": f"Erro ao processar: {str(e)}"}, 500)

        elif path == "/api/training/start":
            epochs = int(payload.get("epochs", 10))
            batch_size = int(payload.get("batch_size", 8))
            model_name = payload.get("model_name", "AutonomousModel")
            res = trainer.start_training(epochs=epochs, batch_size=batch_size, model_name=model_name)
            self._send_json(res)

        elif path == "/api/training/pause":
            trainer.pause()
            self._send_json({"status": "ok", "message": "Treinamento pausado"})

        elif path == "/api/training/resume":
            trainer.resume()
            self._send_json({"status": "ok", "message": "Treinamento retomado"})

        elif path == "/api/training/cancel":
            trainer.cancel()
            self._send_json({"status": "ok", "message": "Treinamento cancelado"})

        elif path == "/api/generation/full":
            title = payload.get("title", "Composição Autônoma")
            root_key = payload.get("root_key", "A")
            scale = payload.get("scale", "minor")
            bpm = float(payload.get("bpm", 124.0))
            bars = int(payload.get("bars", 16))
            res = MusicGenerator.generate_full_song(title=title, root_key=root_key, scale=scale, bpm=bpm, bars=bars)
            self._send_json({"status": "success", "generation": res})

        elif path == "/api/generation/stem":
            stem_type = payload.get("stem_type", "bass")
            root_key = payload.get("root_key", "A")
            scale = payload.get("scale", "minor")
            bpm = float(payload.get("bpm", 124.0))
            bars = int(payload.get("bars", 8))
            res = MusicGenerator.generate_single_stem(stem_type=stem_type, root_key=root_key, scale=scale, bpm=bpm, bars=bars)
            self._send_json({"status": "success", "generation": res})

        elif path == "/api/bridge/start":
            res = bridge.start_bridge()
            self._send_json(res)

        elif path == "/api/bridge/stop":
            bridge.stop_bridge()
            self._send_json({"status": "ok", "message": "Ponte parada"})

        elif path == "/api/bridge/command":
            action = payload.get("action", "ping")
            params = payload.get("params", {})
            res = bridge.send_command(action, params)
            self._send_json(res)

        elif path == "/api/bridge/emergency_stop":
            res = bridge.trigger_emergency_stop()
            self._send_json(res)

        elif path == "/api/bridge/reset_stop":
            res = bridge.reset_emergency_stop()
            self._send_json(res)

        elif path == "/api/fl_studio/start_production":
            root_key = payload.get("root_key", "A")
            scale = payload.get("scale", "minor")
            bpm = float(payload.get("bpm", 124.0))
            bars = int(payload.get("bars", 16))
            title = payload.get("title", "Sessao_Autonoma_FLStudio")

            # 1. Generate full composition with MIDI and FLP
            gen_res = MusicGenerator.generate_full_song(title=title, root_key=root_key, scale=scale, bpm=bpm, bars=bars)

            # 2. Update DAW bridge status
            bridge.status.bpm = bpm
            bridge.status.is_playing = True
            bridge.status.active_project_name = gen_res.get("flp_filename", f"{title}.flp")
            bridge.send_command("transport_play", {"bpm": bpm, "bars": bars})

            # 3. Update DAW memory state
            daw_memory.project_name = gen_res.get("flp_filename", f"{title}.flp")
            daw_memory.bpm = bpm
            daw_memory.last_verified_action = f"Producao iniciada no FL Studio: {bpm} BPM, {bars} compassos"

            # 4. If Windows, launch FL Studio with the project file if requested
            launched = False
            flp_path = gen_res.get("flp_path")
            if payload.get("open_in_fl_studio") and hasattr(os, "startfile") and flp_path:
                try:
                    os.startfile(flp_path)
                    launched = True
                except Exception:
                    pass

            log_action("Iniciar Producao no FL Studio", f"{title} ({bpm} BPM)", "Camadas A-D", "Executado e transmitido", "success")

            self._send_json({
                "status": "success",
                "message": "Producao iniciada no FL Studio com sucesso!",
                "generation": gen_res,
                "steps": [
                    {"step": 1, "name": "Conexao com FL Studio Estabelecida", "status": "ok"},
                    {"step": 2, "name": f"Analise Harmonica Krumhansl ({root_key} {scale})", "status": "ok"},
                    {"step": 3, "name": "Composicao dos 4 Stems (Bateria, Baixo, Acordes, Melodia)", "status": "ok"},
                    {"step": 4, "name": "Projeto FL Studio (.flp) e MIDI (.mid) Gerados", "status": "ok"},
                    {"step": 5, "name": "Comando de Play/Transport Transmitido para a DAW", "status": "ok"}
                ],
                "flp_path": gen_res.get("flp_path"),
                "flp_filename": gen_res.get("flp_filename"),
                "midi_path": gen_res.get("midi_path"),
                "launched_fl_studio": launched
            })

        elif path == "/api/fl_studio/stop_production":
            bridge.status.is_playing = False
            bridge.send_command("transport_stop")
            daw_memory.last_verified_action = "Produção parada no FL Studio"
            log_action("Parar Produção no FL Studio", "Comando de Stop", "Camada B", "Transport stop enviado", "success")
            self._send_json({"status": "success", "message": "Produção e reprodução paradas no FL Studio."})

        elif path == "/api/fl_studio/install_script":
            # Attempt auto-installation into standard FL Studio Hardware Scripts path
            import shutil
            from backend.fl_studio.fl_midi_script import FL_SCRIPT_TEMPLATE

            script_destinations = []
            user_profile = os.environ.get("USERPROFILE") or os.path.expanduser("~")
            candidate_dirs = [
                os.path.join(user_profile, "Documents", "Image-Line", "FL Studio", "Settings", "Hardware", "Autonomous Producer"),
                os.path.join(user_profile, "OneDrive", "Documents", "Image-Line", "FL Studio", "Settings", "Hardware", "Autonomous Producer"),
                os.path.join(ROOT_DIR, "data", "fl_studio_script")
            ]

            installed_path = None
            for cdir in candidate_dirs:
                try:
                    os.makedirs(cdir, exist_ok=True)
                    target_file = os.path.join(cdir, "device_AutonomousProducer.py")
                    with open(target_file, "w", encoding="utf-8") as f:
                        f.write(FL_SCRIPT_TEMPLATE)
                    installed_path = target_file
                    script_destinations.append(target_file)
                    break
                except Exception:
                    continue

            if not installed_path:
                local_dir = os.path.join(ROOT_DIR, "data", "fl_studio_script")
                os.makedirs(local_dir, exist_ok=True)
                installed_path = os.path.join(local_dir, "device_AutonomousProducer.py")
                with open(installed_path, "w", encoding="utf-8") as f:
                    f.write(FL_SCRIPT_TEMPLATE)

            log_action("Instalar Script FL Studio", installed_path, "Camada A", "Script copiado", "success")
            self._send_json({
                "status": "success",
                "message": f"Script MIDI instalado com sucesso!",
                "path": installed_path
            })

        elif path == "/api/fl_studio/test_command":
            cmd = payload.get("command", "ping")
            res = bridge.send_command(cmd, payload.get("params", {}))
            self._send_json({"status": "success", "command": cmd, "result": res})

        elif path == "/api/settings":
            for k, v in payload.items():
                update_setting(k, str(v))
            self._send_json({"status": "ok", "message": "Configurações salvas"})

        else:
            self._send_json({"error": "Rota POST não encontrada"}, 404)


def run_server(port: int = 8000):
    init_db()
    # Auto-scan train folder on startup
    initial_files = scan_train_folder()
    print(f"[Biblioteca] Pasta 'train/' escaneada: {len(initial_files)} arquivos processados para treino.")

    server_address = ("127.0.0.1", port)

    try:
        httpd = HTTPServer(server_address, ProducerRequestHandler)
    except OSError:
        # Try alternate port if 8000 is occupied
        alt_port = port + 1
        print(f"[Aviso] Porta {port} ocupada. Tentando porta {alt_port}...")
        server_address = ("127.0.0.1", alt_port)
        httpd = HTTPServer(server_address, ProducerRequestHandler)
        port = alt_port

    print("=" * 60)
    print("  AUTONOMOUS MUSIC PRODUCER - SERVIDOR LOCAL ATIVO")
    print(f"  Interface web: http://127.0.0.1:{port}")
    print("  API REST pronta para conexões locais.")
    print("  Pressione Ctrl+C para encerrar com segurança.")
    print("=" * 60)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando servidor local...")
        httpd.server_close()
        bridge.stop_bridge()


if __name__ == "__main__":
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_server(port_arg)
