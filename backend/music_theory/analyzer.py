"""Harmonic and musical theory analyzer.
Implements Krumhansl-Schmuckler key-finding algorithm, chord identification,
harmonic function analysis, register conflict detection, and musical density.
"""
import math
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass

PITCH_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Krumhansl-Schmuckler Key Profiles (weights for 12 pitch classes)
# Major: tonic, min2, maj2, min3, maj3, p4, tritone, p5, min6, maj6, min7, maj7
MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
# Minor:
MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

CHORD_TEMPLATES = {
    "maj": [0, 4, 7],
    "min": [0, 3, 7],
    "dim": [0, 3, 6],
    "aug": [0, 4, 8],
    "maj7": [0, 4, 7, 11],
    "7": [0, 4, 7, 10],
    "min7": [0, 3, 7, 10],
    "m7b5": [0, 3, 6, 10],
    "dim7": [0, 3, 6, 9],
    "sus2": [0, 2, 7],
    "sus4": [0, 5, 7]
}

ROMAN_NUMERALS_MAJOR = {
    0: "I", 2: "ii", 4: "iii", 5: "IV", 7: "V", 9: "vi", 11: "vii°"
}

ROMAN_NUMERALS_MINOR = {
    0: "i", 2: "ii°", 3: "III", 5: "iv", 7: "v", 8: "VI", 10: "VII"
}


@dataclass
class PitchClass:
    pitch: int  # 0 to 11
    name: str


@dataclass
class KeyEstimate:
    root: str
    mode: str  # 'major' or 'minor'
    confidence: float
    correlations: Dict[str, float]


@dataclass
class ChordInfo:
    root: str
    chord_type: str
    notes: List[str]
    start_time: float
    end_time: float
    roman_numeral: Optional[str] = None
    bass_note: Optional[str] = None


class HarmonicAnalyzer:
    def __init__(self):
        pass

    @staticmethod
    def midi_to_note_name(midi_number: int) -> str:
        """Converts MIDI note number (0-127) to note name with octave, e.g. 60 -> C4"""
        pitch_idx = midi_number % 12
        octave = (midi_number // 12) - 1
        return f"{PITCH_NAMES[pitch_idx]}{octave}"

    @staticmethod
    def calculate_pitch_class_distribution(notes: List[Dict[str, Any]]) -> List[float]:
        """Calculates duration-weighted or count-weighted 12-dimensional pitch class histogram.
        Ignores drum/percussion channel 9 notes to preserve harmonic accuracy.
        """
        distribution = [0.0] * 12
        if not notes:
            return distribution

        pitched_notes = [n for n in notes if not n.get("is_drum") and n.get("channel") != 9]
        if not pitched_notes:
            # If ONLY drum notes exist, allow them as fallback with lower confidence
            pitched_notes = notes

        for n in pitched_notes:
            pitch = n.get("pitch", 60) % 12
            duration = max(0.1, n.get("duration", 0.5))
            velocity = n.get("velocity", 80) / 127.0
            weight = duration * velocity
            distribution[pitch] += weight

        total = sum(distribution)
        if total > 0:
            distribution = [x / total for x in distribution]
        return distribution

    @classmethod
    def estimate_key(cls, notes: List[Dict[str, Any]]) -> KeyEstimate:
        """Krumhansl-Schmuckler Key-Finding Algorithm based on pitch class correlation."""
        if not notes:
            return KeyEstimate(root="C", mode="major", confidence=0.0, correlations={})

        has_pitched = any(not n.get("is_drum") and n.get("channel") != 9 for n in notes)
        if not has_pitched:
            return KeyEstimate(root="Percussão", mode="rítmico", confidence=0.95, correlations={})

        hist = cls.calculate_pitch_class_distribution(notes)
        if sum(hist) == 0:
            return KeyEstimate(root="C", mode="major", confidence=0.0, correlations={})

        def pearson_corr(x: List[float], y: List[float]) -> float:
            n = len(x)
            mean_x = sum(x) / n
            mean_y = sum(y) / n
            cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
            var_x = sum((x[i] - mean_x) ** 2 for i in range(n))
            var_y = sum((y[i] - mean_y) ** 2 for i in range(n))
            denom = math.sqrt(var_x * var_y)
            return cov / denom if denom > 1e-9 else 0.0

        correlations = {}
        for shift in range(12):
            root_name = PITCH_NAMES[shift]
            # Rotate profiles to match root
            maj_shifted = [MAJOR_PROFILE[(i - shift) % 12] for i in range(12)]
            min_shifted = [MINOR_PROFILE[(i - shift) % 12] for i in range(12)]

            corr_maj = pearson_corr(hist, maj_shifted)
            corr_min = pearson_corr(hist, min_shifted)

            correlations[f"{root_name} Major"] = round(corr_maj, 4)
            correlations[f"{root_name} Minor"] = round(corr_min, 4)

        best_key, best_corr = max(correlations.items(), key=lambda item: item[1])
        parts = best_key.split(" ")
        root = parts[0]
        mode = parts[1].lower()

        # Confidence: delta between top 1 and top 2 correlations
        sorted_corr = sorted(correlations.values(), reverse=True)
        confidence = float(sorted_corr[0] - sorted_corr[1]) if len(sorted_corr) > 1 else 1.0
        confidence = max(0.0, min(1.0, confidence * 3.0))  # Normalize

        return KeyEstimate(
            root=root,
            mode=mode,
            confidence=round(confidence, 3),
            correlations=correlations
        )

    @classmethod
    def identify_chord_from_pitches(cls, pitches: List[int], key_root: str = "C", key_mode: str = "major") -> Optional[ChordInfo]:
        """Identifies root and chord type from pitch collection."""
        if not pitches:
            return None

        lowest_pitch = min(pitches)
        bass_note = cls.midi_to_note_name(lowest_pitch)

        unique_pcs = sorted(list(set(p % 12 for p in pitches)))
        if len(unique_pcs) < 2:
            return None

        best_match = None
        best_score = -1

        for root_pc in range(12):
            root_name = PITCH_NAMES[root_pc]
            for c_type, template in CHORD_TEMPLATES.items():
                expected_pcs = set((root_pc + interval) % 12 for interval in template)
                overlap = len(expected_pcs.intersection(unique_pcs))
                extra = len(set(unique_pcs) - expected_pcs)
                missing = len(expected_pcs - set(unique_pcs))
                # Heuristic score
                score = (overlap * 3) - (extra * 1.5) - (missing * 1.0)
                if score > best_score and overlap >= 2:
                    best_score = score
                    best_match = (root_name, c_type, [PITCH_NAMES[p] for p in sorted(list(expected_pcs))])

        if best_match and best_score > 0:
            root_name, c_type, notes = best_match
            # Calculate Roman Numeral
            try:
                root_pc = PITCH_NAMES.index(root_name)
                key_pc = PITCH_NAMES.index(key_root)
                interval = (root_pc - key_pc) % 12
                mapping = ROMAN_NUMERALS_MAJOR if key_mode == "major" else ROMAN_NUMERALS_MINOR
                roman = mapping.get(interval, "?")
                if c_type in ["min", "min7", "dim"] and roman.isupper():
                    roman = roman.lower()
                elif c_type in ["maj", "maj7", "7"] and roman.islower():
                    roman = roman.upper()
                if "7" in c_type:
                    roman += "7"
            except Exception:
                roman = None

            return ChordInfo(
                root=root_name,
                chord_type=c_type,
                notes=notes,
                start_time=0.0,
                end_time=1.0,
                roman_numeral=roman,
                bass_note=bass_note
            )
        return None

    @classmethod
    def analyze_harmonic_progression(cls, notes: List[Dict[str, Any]], key_root: str = "C", key_mode: str = "major", step_duration: float = 2.0) -> List[Dict[str, Any]]:
        """Segments notes over time slices (e.g., 1-2 bars) and extracts chord progression."""
        if not notes:
            return []

        max_time = max(n.get("start", 0) + n.get("duration", 0) for n in notes)
        steps = int(math.ceil(max_time / step_duration))
        progression = []

        for i in range(steps):
            t_start = i * step_duration
            t_end = t_start + step_duration

            # Notes sounding in this time slice
            slice_notes = [
                n["pitch"] for n in notes
                if (n.get("start", 0) < t_end) and (n.get("start", 0) + n.get("duration", 0) > t_start)
            ]

            chord = cls.identify_chord_from_pitches(slice_notes, key_root, key_mode)
            if chord:
                progression.append({
                    "step": i + 1,
                    "time_start": round(t_start, 2),
                    "time_end": round(t_end, 2),
                    "chord": f"{chord.root}{chord.chord_type}",
                    "roman": chord.roman_numeral or "-",
                    "notes": chord.notes,
                    "bass": chord.bass_note
                })
        return progression

    @classmethod
    def detect_register_conflicts(cls, tracks_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identifies acoustic conflicts such as bass collisions or congested mid-frequencies."""
        conflicts = []
        bass_tracks = []
        for t in tracks_data:
            name = t.get("name", "").lower()
            notes = t.get("notes", [])
            avg_pitch = sum(n.get("pitch", 60) for n in notes) / len(notes) if notes else 60
            if "bass" in name or "sub" in name or "808" in name or avg_pitch < 48:
                bass_tracks.append((t.get("name", "Track"), notes))

        if len(bass_tracks) > 1:
            conflicts.append({
                "type": "low_frequency_masking",
                "severity": "medium",
                "tracks": [b[0] for b in bass_tracks],
                "description": "Múltiplas trilhas operando na mesma região sub-grave (< 100 Hz). Risco de cancelamento de fase ou embolamento no FL Studio.",
                "solution": "Aplicar corte High-Pass (Fruity Parametric EQ 2) em um dos canais ou rotear sidechain com o Kick."
            })
        return conflicts
