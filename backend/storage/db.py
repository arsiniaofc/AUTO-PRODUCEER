"""Database storage module using SQLite for metadata, configurations, models and logs.
"""
import sqlite3
import json
import os
from typing import List, Dict, Any, Optional

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "producer.db")


_db_initialized = False

def get_db_connection() -> sqlite3.Connection:
    global _db_initialized
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if not _db_initialized:
        _db_initialized = True
        init_db()
    return conn


def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()

    # Files table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT UNIQUE NOT NULL,
        file_name TEXT NOT NULL,
        file_type TEXT NOT NULL,
        file_size INTEGER DEFAULT 0,
        imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        processed_at TIMESTAMP,
        status TEXT DEFAULT 'pending',
        duration_sec REAL DEFAULT 0.0,
        bpm REAL DEFAULT 120.0,
        key_signature TEXT DEFAULT 'Unknown',
        time_signature TEXT DEFAULT '4/4',
        track_count INTEGER DEFAULT 0,
        note_count INTEGER DEFAULT 0,
        channels_json TEXT DEFAULT '[]',
        error_log TEXT,
        is_trained INTEGER DEFAULT 0
    )
    """)

    # Models / Checkpoints table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS models (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        version TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        checkpoint_path TEXT,
        loss REAL DEFAULT 0.0,
        epochs INTEGER DEFAULT 0,
        vocabulary_size INTEGER DEFAULT 0,
        architecture_json TEXT,
        is_active INTEGER DEFAULT 0
    )
    """)

    # Generations table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS generations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        mode TEXT NOT NULL,
        key_signature TEXT,
        scale TEXT,
        bpm REAL,
        duration_bars INTEGER,
        tracks_json TEXT,
        midi_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Actions log table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS actions_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        planned_action TEXT NOT NULL,
        executed_action TEXT,
        layer TEXT,
        result TEXT,
        status TEXT,
        duration_ms INTEGER,
        details TEXT
    )
    """)

    # Settings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # Default settings if not exist
    defaults = {
        "device": "cpu",
        "batch_size": "8",
        "seq_len": "128",
        "d_model": "128",
        "n_heads": "4",
        "n_layers": "3",
        "learning_rate": "0.0005",
        "fl_bridge_port": "9050",
        "fl_midi_port": "3001",
        "auto_backup": "true",
        "autonomous_mode": "supervised"
    }

    for k, v in defaults.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    conn.commit()
    conn.close()


def add_or_update_file(file_data: Dict[str, Any]) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO files (
            file_path, file_name, file_type, file_size, status,
            duration_sec, bpm, key_signature, time_signature,
            track_count, note_count, channels_json, error_log, is_trained, processed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(file_path) DO UPDATE SET
            file_name=excluded.file_name,
            file_type=excluded.file_type,
            file_size=excluded.file_size,
            status=excluded.status,
            duration_sec=excluded.duration_sec,
            bpm=excluded.bpm,
            key_signature=excluded.key_signature,
            time_signature=excluded.time_signature,
            track_count=excluded.track_count,
            note_count=excluded.note_count,
            channels_json=excluded.channels_json,
            error_log=excluded.error_log,
            processed_at=CURRENT_TIMESTAMP
    """, (
        file_data.get("file_path", ""),
        file_data.get("file_name", ""),
        file_data.get("file_type", ""),
        file_data.get("file_size", 0),
        file_data.get("status", "pending"),
        file_data.get("duration_sec", 0.0),
        file_data.get("bpm", 120.0),
        file_data.get("key_signature", "Unknown"),
        file_data.get("time_signature", "4/4"),
        file_data.get("track_count", 0),
        file_data.get("note_count", 0),
        json.dumps(file_data.get("channels", [])),
        file_data.get("error_log", None),
        file_data.get("is_trained", 0)
    ))
    conn.commit()
    file_id = cursor.lastrowid
    conn.close()
    return file_id


def list_files() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM files ORDER BY imported_at DESC")
    rows = cursor.fetchall()
    result = []
    for row in rows:
        d = dict(row)
        try:
            d["channels"] = json.loads(d.get("channels_json") or "[]")
        except Exception:
            d["channels"] = []
        result.append(d)
    conn.close()
    return result


def log_action(planned: str, executed: str, layer: str, result: str, status: str, duration_ms: int = 0, details: str = ""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO actions_log (planned_action, executed_action, layer, result, status, duration_ms, details)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (planned, executed, layer, result, status, duration_ms, details))
    conn.commit()
    conn.close()


def get_actions(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM actions_log ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_settings() -> Dict[str, str]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    rows = cursor.fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def update_setting(key: str, value: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
    conn.commit()
    conn.close()
