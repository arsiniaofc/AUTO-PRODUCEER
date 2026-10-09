"""Musical Tokenizer inspired by REMI (Revamped MIDI) representation.
Converts multi-track MIDI notes into categorical token sequences and back.
"""
import math
from typing import List, Dict, Any, Tuple, Optional
from .parser import MidiSong, MidiTrack, MidiNote


class MidiTokenizer:
    """Tokenizes symbolic music into discrete tokens suitable for Transformer models."""

    SPECIAL_TOKENS = ["[PAD]", "[BOS]", "[EOS]", "[MASK]"]
    NUM_POSITIONS = 16  # 16 sixteenths per 4/4 bar
    NUM_TRACKS = 8
    MIN_PITCH = 21
    MAX_PITCH = 108
    NUM_VELOCITIES = 8  # 8 quantized velocity bins
    NUM_DURATIONS = 32  # 1 to 32 sixteenth steps

    def __init__(self):
        self.vocab: Dict[str, int] = {}
        self.inv_vocab: Dict[int, str] = {}
        self._build_vocabulary()

    def _build_vocabulary(self):
        vocab_list = list(self.SPECIAL_TOKENS)

        # Bar token
        vocab_list.append("Bar")

        # Position tokens
        for p in range(self.NUM_POSITIONS):
            vocab_list.append(f"Position_{p}")

        # Track tokens
        for trk in range(self.NUM_TRACKS):
            vocab_list.append(f"Track_{trk}")

        # Pitch tokens
        for pitch in range(self.MIN_PITCH, self.MAX_PITCH + 1):
            vocab_list.append(f"Pitch_{pitch}")

        # Duration tokens
        for d in range(1, self.NUM_DURATIONS + 1):
            vocab_list.append(f"Duration_{d}")

        # Velocity bins
        for v in range(1, self.NUM_VELOCITIES + 1):
            vocab_list.append(f"Velocity_{v}")

        # Tempo bins (40 to 200 bpm in steps of 10)
        for bpm in range(40, 210, 10):
            vocab_list.append(f"Tempo_{bpm}")

        # Common chords
        for root in ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]:
            for c_type in ["maj", "min", "7", "maj7", "min7"]:
                vocab_list.append(f"Chord_{root}_{c_type}")

        self.vocab = {tok: idx for idx, tok in enumerate(vocab_list)}
        self.inv_vocab = {idx: tok for idx, tok in enumerate(vocab_list)}

    @property
    def vocab_size(self) -> int:
        return len(self.vocab)

    def encode_song(self, song: MidiSong, max_bars: int = 32) -> List[int]:
        """Encodes MidiSong into token ID sequence."""
        tokens = ["[BOS]"]

        # Quantize tempo
        bpm_quantized = min(200, max(40, int(round(song.bpm / 10.0) * 10)))
        tempo_tok = f"Tempo_{bpm_quantized}"
        if tempo_tok in self.vocab:
            tokens.append(tempo_tok)

        # Collect and quantize all notes across tracks
        # 1 beat = 4 sixteenths; 1 bar = 4 beats = 16 sixteenths
        notes_by_bar_pos: Dict[Tuple[int, int], List[Tuple[int, MidiNote]]] = {}

        for trk_idx, track in enumerate(song.tracks):
            track_id = min(self.NUM_TRACKS - 1, trk_idx)
            for note in track.notes:
                start_sixteenths = int(round(note.start * 4.0))
                bar_num = start_sixteenths // self.NUM_POSITIONS
                if bar_num >= max_bars:
                    continue
                pos_in_bar = start_sixteenths % self.NUM_POSITIONS
                key = (bar_num, pos_in_bar)
                if key not in notes_by_bar_pos:
                    notes_by_bar_pos[key] = []
                notes_by_bar_pos[key].append((track_id, note))

        if not notes_by_bar_pos:
            tokens.append("[EOS]")
            return [self.vocab.get(t, 0) for t in tokens]

        total_bars = min(max_bars, max(k[0] for k in notes_by_bar_pos.keys()) + 1)

        for bar in range(total_bars):
            tokens.append("Bar")
            for pos in range(self.NUM_POSITIONS):
                key = (bar, pos)
                if key in notes_by_bar_pos:
                    tokens.append(f"Position_{pos}")
                    # Sort notes by track, then pitch
                    notes_sorted = sorted(notes_by_bar_pos[key], key=lambda x: (x[0], x[1].pitch))
                    for trk_id, note in notes_sorted:
                        pitch = max(self.MIN_PITCH, min(self.MAX_PITCH, note.pitch))
                        dur_sixteenths = max(1, min(self.NUM_DURATIONS, int(round(note.duration * 4.0))))
                        vel_bin = max(1, min(self.NUM_VELOCITIES, int(round((note.velocity / 127.0) * self.NUM_VELOCITIES))))

                        tokens.append(f"Track_{trk_id}")
                        tokens.append(f"Pitch_{pitch}")
                        tokens.append(f"Duration_{dur_sixteenths}")
                        tokens.append(f"Velocity_{vel_bin}")

        tokens.append("[EOS]")
        return [self.vocab.get(t, 0) for t in tokens]

    def decode_tokens(self, token_ids: List[int], default_bpm: float = 120.0) -> MidiSong:
        """Decodes token ID sequence back into MidiSong object."""
        tracks_map: Dict[int, MidiTrack] = {}
        for trk_id in range(self.NUM_TRACKS):
            track_names = ["Drums", "Bass", "Chords", "Melody", "Pad", "Guitar", "Arp", "FX"]
            is_drum = trk_id == 0
            program = 0
            if trk_id == 1:
                program = 33  # Electric Bass
            elif trk_id == 2:
                program = 4   # Electric Piano
            elif trk_id == 3:
                program = 80  # Synth Lead
            elif trk_id == 4:
                program = 48  # String Ensemble
            tracks_map[trk_id] = MidiTrack(
                name=track_names[trk_id] if trk_id < len(track_names) else f"Track {trk_id}",
                channel=9 if is_drum else trk_id,
                program=program,
                is_drum=is_drum,
                notes=[]
            )

        current_bar = 0
        current_pos = 0
        current_track = 1
        current_bpm = default_bpm

        i = 0
        while i < len(token_ids):
            tok_id = token_ids[i]
            token_str = self.inv_vocab.get(tok_id, "")
            i += 1

            if token_str == "[EOS]":
                break
            elif token_str.startswith("Tempo_"):
                try:
                    current_bpm = float(token_str.split("_")[1])
                except Exception:
                    pass
            elif token_str == "Bar":
                current_bar += 1
                current_pos = 0
            elif token_str.startswith("Position_"):
                try:
                    current_pos = int(token_str.split("_")[1])
                except Exception:
                    pass
            elif token_str.startswith("Track_"):
                try:
                    current_track = int(token_str.split("_")[1])
                except Exception:
                    pass
            elif token_str.startswith("Pitch_"):
                try:
                    pitch = int(token_str.split("_")[1])
                    duration_sixteenths = 2
                    velocity_bin = 5

                    # Check next tokens for Duration and Velocity
                    if i < len(token_ids) and self.inv_vocab.get(token_ids[i], "").startswith("Duration_"):
                        dur_str = self.inv_vocab[token_ids[i]]
                        duration_sixteenths = int(dur_str.split("_")[1])
                        i += 1

                    if i < len(token_ids) and self.inv_vocab.get(token_ids[i], "").startswith("Velocity_"):
                        vel_str = self.inv_vocab[token_ids[i]]
                        velocity_bin = int(vel_str.split("_")[1])
                        i += 1

                    total_sixteenths = (max(0, current_bar - 1) * self.NUM_POSITIONS) + current_pos
                    start_beats = total_sixteenths / 4.0
                    duration_beats = duration_sixteenths / 4.0
                    velocity = int(round((velocity_bin / self.NUM_VELOCITIES) * 127))

                    if current_track in tracks_map:
                        tracks_map[current_track].notes.append(
                            MidiNote(
                                pitch=pitch,
                                start=start_beats,
                                duration=duration_beats,
                                velocity=velocity,
                                channel=tracks_map[current_track].channel
                            )
                        )
                except Exception:
                    pass

        active_tracks = [t for t in tracks_map.values() if t.notes]
        if not active_tracks:
            active_tracks = list(tracks_map.values())[:2]

        max_beats = max((n.start + n.duration for t in active_tracks for n in t.notes), default=4.0)
        dur_sec = round(max_beats * (60.0 / current_bpm), 2)

        return MidiSong(
            ticks_per_beat=480,
            bpm=current_bpm,
            tracks=active_tracks,
            duration_sec=dur_sec
        )
