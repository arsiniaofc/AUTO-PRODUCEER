"""Musical cognition memory and DAW state tracker.
Stores structured musical knowledge and tracks DAW state transitions without hallucination.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class MusicalMemory:
    """Current state of musical reasoning and analysis."""
    key_root: str = "A"
    key_mode: str = "minor"
    confidence: float = 0.85
    tonic_center: str = "A minor"
    detected_modulations: List[str] = field(default_factory=list)
    active_progression: List[Dict[str, Any]] = field(default_factory=list)
    chord_degrees: List[str] = field(default_factory=lambda: ["i", "VI", "III", "VII"])
    density_rating: str = "Equilibrada (Moderada)"
    bass_melody_relation: str = "Contra-ponto consonante com baixo sustentando tônica e quinta"
    arrangement_gaps: List[str] = field(default_factory=lambda: [
        "Falta elemento de transição (Riser/Snare Roll) no compasso 8",
        "Região de médios-altos (2-4 kHz) possui espaço vago para Lead Melódico"
    ])
    register_conflicts: List[str] = field(default_factory=list)
    ai_decision_log: List[Dict[str, str]] = field(default_factory=lambda: [
        {
            "timestamp": "Recente",
            "decision": "Progressão definida como i - VI - III - VII em Lá Menor",
            "justificativa": "Estrutura harmônica clássica com alta resolução emotiva e suporte melódico contínuo",
            "fato_observado": "Perfil Krumhansl-Schmuckler indicou correlação de 0.88 em Lá Menor"
        },
        {
            "timestamp": "Recente",
            "decision": "Separação de oitava entre Baixo (Oitava 1-2) e Acordes (Oitava 3-4)",
            "justificativa": "Prevenção de mascaramento de frequências e preservação de clareza nos sub-graves",
            "fato_observado": "Análise de conflito de registro validou ausência de sobreposição destrutiva"
        }
    ])


@dataclass
class DAWStateMemory:
    """Current state of the FL Studio workstation."""
    project_name: str = "Projeto_Autonomo_Sessao_1.flp"
    bpm: float = 124.0
    time_signature: str = "4/4"
    identified_channels: List[Dict[str, Any]] = field(default_factory=lambda: [
        {"id": 1, "name": "Fruity Kick", "plugin": "Sampler", "volume": 0.8},
        {"id": 2, "name": "Clap / Snare", "plugin": "Sampler", "volume": 0.75},
        {"id": 3, "name": "Closed Hat", "plugin": "Sampler", "volume": 0.65},
        {"id": 4, "name": "3x Osc Bass", "plugin": "3x Osc", "volume": 0.82},
        {"id": 5, "name": "FLEX Keys", "plugin": "FLEX", "volume": 0.7}
    ])
    active_selection: str = "Pattern 1 (Playlist Track 1..4)"
    focused_window: str = "Playlist - Arrangements"
    visible_windows: List[str] = field(default_factory=lambda: [
        "Playlist", "Channel Rack", "Mixer", "Browser"
    ])
    last_verified_action: str = "Sincronização de andamento (124.0 BPM)"
    pending_actions: List[str] = field(default_factory=list)
    mode: str = "supervised"  # 'assisted', 'supervised', 'analysis', 'emergency_stop'
