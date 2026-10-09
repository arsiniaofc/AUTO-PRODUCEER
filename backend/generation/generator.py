"""Algorithmic and Neural Music Generator.
Supports Full Song, Individual Track, Continuation, Variation, Arrangement, and Infill.
Outputs structured JSON and valid Standard MIDI (.mid) files.
"""
import os
import random
import time
from typing import List, Dict, Any, Optional
from backend.midi.parser import MidiParser, MidiSong, MidiTrack, MidiNote
from backend.music_theory.analyzer import PITCH_NAMES, HarmonicAnalyzer, CHORD_TEMPLATES
from backend.storage.db import get_db_connection, log_action

GENERATED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "generated")

SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "pentatonic_major": [0, 2, 4, 7, 9],
    "pentatonic_minor": [0, 3, 5, 7, 10]
}

PROGRESSIONS = {
    "major": [
        ["I", "V", "vi", "IV"],      # Pop / EDM classic
        ["ii", "V", "I", "vi"],      # Jazz / Neo-soul
        ["I", "IV", "V", "IV"],      # Rock / Anthem
        ["vi", "IV", "I", "V"]       # Melodic emotional
    ],
    "minor": [
        ["i", "VI", "III", "VII"],   # Epic / Cinematic
        ["i", "iv", "v", "i"],       # Classic minor
        ["i", "VI", "iv", "v"],      # Dark trap / synthwave
        ["i", "VII", "VI", "VII"]    # Phrygian cadence vibe
    ]
}


class MusicGenerator:
    def __init__(self):
        os.makedirs(GENERATED_DIR, exist_ok=True)

    @classmethod
    def _get_scale_pitches(cls, root_name: str, scale_type: str, octaves: range) -> List[int]:
        root_idx = PITCH_NAMES.index(root_name) if root_name in PITCH_NAMES else 0
        scale_intervals = SCALES.get(scale_type, SCALES["minor"])
        pitches = []
        for oct_num in octaves:
            base = (oct_num + 1) * 12 + root_idx
            for interval in scale_intervals:
                p = base + interval
                if 21 <= p <= 108:
                    pitches.append(p)
        return sorted(pitches)

    @classmethod
    def generate_full_song(cls, title: str = "Nova Composição", root_key: str = "A", scale: str = "minor", bpm: float = 124.0, bars: int = 16) -> Dict[str, Any]:
        """Generates a complete multi-track composition with Drums, Bass, Chords, and Melody."""
        start_time = time.time()
        tracks_data = []

        # 1. Chords Track (Keys / Pad)
        chord_prog = random.choice(PROGRESSIONS.get(scale, PROGRESSIONS["minor"]))
        chord_notes: List[MidiNote] = []
        chord_timeline = []

        # Root pitch for scale
        root_pc = PITCH_NAMES.index(root_key) if root_key in PITCH_NAMES else 0
        scale_intervals = SCALES.get(scale, SCALES["minor"])

        num_loops = max(1, bars // len(chord_prog))
        step_idx = 0

        for loop in range(num_loops):
            for chord_degree in chord_prog:
                if step_idx >= bars:
                    break
                bar_start = float(step_idx * 4.0)  # 4 beats per bar

                # Compute degree root
                deg_offset = 0
                if chord_degree == "I" or chord_degree == "i":
                    deg_offset = scale_intervals[0]
                    c_type = "maj" if scale == "major" else "min"
                elif chord_degree == "ii" or chord_degree == "ii°":
                    deg_offset = scale_intervals[1]
                    c_type = "min" if scale == "major" else "dim"
                elif chord_degree == "iii" or chord_degree == "III":
                    deg_offset = scale_intervals[2]
                    c_type = "min" if scale == "major" else "maj"
                elif chord_degree == "IV" or chord_degree == "iv":
                    deg_offset = scale_intervals[3]
                    c_type = "maj" if scale == "major" else "min"
                elif chord_degree == "V" or chord_degree == "v":
                    deg_offset = scale_intervals[4]
                    c_type = "maj" if scale == "major" else "min"
                elif chord_degree == "vi" or chord_degree == "VI":
                    deg_offset = scale_intervals[5]
                    c_type = "min" if scale == "major" else "maj"
                elif chord_degree == "vii°" or chord_degree == "VII":
                    deg_offset = scale_intervals[6]
                    c_type = "dim" if scale == "major" else "maj"
                else:
                    deg_offset = 0
                    c_type = "min"

                chord_root_pitch = 48 + root_pc + deg_offset  # Octave 3
                chord_root_name = PITCH_NAMES[(root_pc + deg_offset) % 12]
                chord_timeline.append({
                    "bar": step_idx + 1,
                    "degree": chord_degree,
                    "chord": f"{chord_root_name}{c_type}",
                    "start_beat": bar_start
                })

                # Voicing: root, 3rd, 5th, and octave or 7th
                intervals = CHORD_TEMPLATES.get(c_type, [0, 3, 7])
                for iv in intervals:
                    p = chord_root_pitch + iv
                    chord_notes.append(MidiNote(
                        pitch=p,
                        start=bar_start,
                        duration=3.8,  # sustain almost entire bar
                        velocity=random.randint(75, 88),
                        channel=1
                    ))

                step_idx += 1

        tracks_data.append(MidiTrack(name="Chords & Keys", channel=1, program=4, is_drum=False, notes=chord_notes))

        # 2. Bass Track (Root notes + rhythmic bounce)
        bass_notes: List[MidiNote] = []
        for ch in chord_timeline:
            bar_start = ch["start_beat"]
            # Extract root pitch for bass in octave 1-2
            c_name = ch["chord"]
            root_letter = c_name[:2] if len(c_name) > 1 and c_name[1] == "#" else c_name[:1]
            b_root = 36 + PITCH_NAMES.index(root_letter)
            # Rhythmic 8th-note or driving groove
            pattern_types = ["driving_8ths", "syncopated", "root_fifth"]
            pat = pattern_types[step_idx % len(pattern_types)]

            if pat == "driving_8ths":
                for b_i in range(8):
                    beat_pos = bar_start + (b_i * 0.5)
                    vel = 95 if b_i % 2 == 0 else 75
                    bass_notes.append(MidiNote(pitch=b_root, start=beat_pos, duration=0.45, velocity=vel, channel=2))
            else:
                # Syncopated groove (beats 0, 1.5, 2.5, 3.5)
                for pos in [0.0, 1.5, 2.5, 3.5]:
                    beat_pos = bar_start + pos
                    pitch = b_root if pos < 2.5 else b_root + 7  # jump to fifth
                    bass_notes.append(MidiNote(pitch=pitch, start=beat_pos, duration=0.8, velocity=90, channel=2))

        tracks_data.append(MidiTrack(name="Bassline", channel=2, program=33, is_drum=False, notes=bass_notes))

        # 3. Melody / Lead Track (Phrased pentatonic/scale motifs)
        melody_notes: List[MidiNote] = []
        lead_scale = cls._get_scale_pitches(root_key, f"pentatonic_{scale}", octaves=range(4, 6))

        for bar_num in range(bars):
            bar_start = float(bar_num * 4.0)
            # Motif phrase with rests
            beats = [0.0, 0.75, 1.5, 2.0, 2.5, 3.25]
            for b_pos in beats:
                if random.random() < 0.25:
                    continue  # artistic rest
                p = random.choice(lead_scale)
                dur = random.choice([0.5, 0.75, 1.0])
                vel = random.randint(85, 105)
                melody_notes.append(MidiNote(pitch=p, start=bar_start + b_pos, duration=dur, velocity=vel, channel=3))

        tracks_data.append(MidiTrack(name="Lead Melody", channel=3, program=80, is_drum=False, notes=melody_notes))

        # 4. Drums Track (Kick, Snare, Hi-Hat, Crash)
        drum_notes: List[MidiNote] = []
        KICK = 36
        SNARE = 38
        HIHAT = 42
        OPEN_HAT = 46
        CRASH = 49

        for bar_num in range(bars):
            bar_start = float(bar_num * 4.0)

            # Crash on bar 1 and bar 9 (drop)
            if bar_num % 8 == 0:
                drum_notes.append(MidiNote(pitch=CRASH, start=bar_start, duration=2.0, velocity=105, channel=9))

            # 4-on-the-floor Kick
            for beat in range(4):
                drum_notes.append(MidiNote(pitch=KICK, start=bar_start + beat, duration=0.4, velocity=100, channel=9))

            # Snare on beats 2 and 4 (indices 1 and 3)
            drum_notes.append(MidiNote(pitch=SNARE, start=bar_start + 1.0, duration=0.4, velocity=95, channel=9))
            drum_notes.append(MidiNote(pitch=SNARE, start=bar_start + 3.0, duration=0.4, velocity=98, channel=9))

            # 16th or 8th Hi-Hats
            for step in range(8):
                h_pos = bar_start + (step * 0.5)
                # Open hat on upbeats
                if step % 2 == 1 and random.random() < 0.4:
                    drum_notes.append(MidiNote(pitch=OPEN_HAT, start=h_pos, duration=0.4, velocity=85, channel=9))
                else:
                    vel = 85 if step % 2 == 0 else 68
                    drum_notes.append(MidiNote(pitch=HIHAT, start=h_pos, duration=0.25, velocity=vel, channel=9))

        tracks_data.append(MidiTrack(name="Drums & Beat", channel=9, program=0, is_drum=True, notes=drum_notes))

        song = MidiSong(
            ticks_per_beat=480,
            bpm=bpm,
            tracks=tracks_data,
            duration_sec=round(bars * 4.0 * (60.0 / bpm), 2)
        )

        filename = f"gen_full_{int(time.time())}.mid"
        midi_path = os.path.join(GENERATED_DIR, filename)
        MidiParser.write_file(song, midi_path)

        # Record in DB
        conn = get_db_connection()
        cursor = conn.cursor()
        tracks_serializable = [
            {
                "name": t.name,
                "channel": t.channel,
                "is_drum": t.is_drum,
                "note_count": len(t.notes),
                "notes": [{"pitch": n.pitch, "start": n.start, "duration": n.duration, "velocity": n.velocity} for n in t.notes]
            }
            for t in song.tracks
        ]
        cursor.execute("""
            INSERT INTO generations (name, mode, key_signature, scale, bpm, duration_bars, tracks_json, midi_path)
            VALUES (?, 'full_song', ?, ?, ?, ?, ?, ?)
        """, (title, root_key, scale, bpm, bars, str(tracks_serializable), midi_path))
        conn.commit()
        conn.close()

        elapsed_ms = int((time.time() - start_time) * 1000)
        log_action("Geração de Música Completa", f"Gerado {title} ({bars} compassos, {bpm} BPM)", "IA", f"Salvo em {filename}", "success", elapsed_ms)

        return {
            "title": title,
            "filename": filename,
            "midi_path": midi_path,
            "bpm": bpm,
            "key": f"{root_key} {scale.capitalize()}",
            "bars": bars,
            "duration_sec": song.duration_sec,
            "chord_progression": chord_timeline,
            "tracks": tracks_serializable
        }

    @classmethod
    def generate_single_stem(cls, stem_type: str = "bass", root_key: str = "A", scale: str = "minor", bpm: float = 124.0, bars: int = 8) -> Dict[str, Any]:
        """Generates a standalone stem track."""
        stem_type = stem_type.lower()
        notes: List[MidiNote] = []
        root_pc = PITCH_NAMES.index(root_key) if root_key in PITCH_NAMES else 0
        scale_pitches = cls._get_scale_pitches(root_key, scale, octaves=range(2, 5))

        if stem_type in ["drums", "bateria"]:
            name = "Drum Pattern"
            channel = 9
            is_drum = True
            for b in range(bars):
                b_start = b * 4.0
                for beat in range(4):
                    notes.append(MidiNote(36, b_start + beat, 0.4, 100, 9))
                notes.append(MidiNote(38, b_start + 1.0, 0.4, 95, 9))
                notes.append(MidiNote(38, b_start + 3.0, 0.4, 98, 9))
                for s in range(8):
                    notes.append(MidiNote(42, b_start + s * 0.5, 0.25, 75, 9))
        elif stem_type in ["bass", "baixo"]:
            name = "Bassline Stem"
            channel = 2
            is_drum = False
            base_pitch = 36 + root_pc
            for b in range(bars):
                b_start = b * 4.0
                for p_off in [0.0, 1.0, 1.75, 2.5, 3.25]:
                    pitch = base_pitch if p_off < 2.0 else base_pitch + random.choice([0, 3, 5, 7])
                    notes.append(MidiNote(pitch, b_start + p_off, 0.6, 90, 2))
        else:  # melody or chords
            name = f"{stem_type.capitalize()} Stem"
            channel = 3
            is_drum = False
            for b in range(bars):
                b_start = b * 4.0
                for p_off in [0.0, 0.75, 1.5, 2.25, 3.0]:
                    pitch = random.choice(scale_pitches)
                    notes.append(MidiNote(pitch, b_start + p_off, 0.7, 88, 3))

        track = MidiTrack(name=name, channel=channel, is_drum=is_drum, notes=notes)
        song = MidiSong(bpm=bpm, tracks=[track], duration_sec=round(bars * 4.0 * (60.0 / bpm), 2))

        filename = f"gen_stem_{stem_type}_{int(time.time())}.mid"
        midi_path = os.path.join(GENERATED_DIR, filename)
        MidiParser.write_file(song, midi_path)

        return {
            "title": name,
            "filename": filename,
            "midi_path": midi_path,
            "bpm": bpm,
            "key": f"{root_key} {scale.capitalize()}",
            "bars": bars,
            "tracks": [{
                "name": track.name,
                "channel": track.channel,
                "is_drum": track.is_drum,
                "note_count": len(track.notes),
                "notes": [{"pitch": n.pitch, "start": n.start, "duration": n.duration, "velocity": n.velocity} for n in track.notes]
            }]
        }
