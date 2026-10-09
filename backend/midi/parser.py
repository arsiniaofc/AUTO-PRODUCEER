"""Standard MIDI File (SMF 1.0) parser and writer.
Implemented in pure Python with support for mido if present.
"""
import struct
import os
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class MidiNote:
    pitch: int
    start: float  # in seconds or beats
    duration: float
    velocity: int = 80
    channel: int = 0


@dataclass
class MidiTrack:
    name: str = "Track"
    channel: int = 0
    program: int = 0  # General MIDI instrument
    is_drum: bool = False
    notes: List[MidiNote] = field(default_factory=list)


@dataclass
class MidiSong:
    ticks_per_beat: int = 480
    bpm: float = 120.0
    time_signature: str = "4/4"
    tracks: List[MidiTrack] = field(default_factory=list)
    duration_sec: float = 0.0

    @property
    def total_notes(self) -> int:
        return sum(len(t.notes) for t in self.tracks)


class MidiParser:
    """Pure Python SMF parser and serializer."""

    @staticmethod
    def _read_vlq(data: bytes, offset: int) -> Tuple[int, int]:
        """Reads a Variable Length Quantity (VLQ). Returns (value, new_offset)."""
        value = 0
        while offset < len(data):
            byte = data[offset]
            offset += 1
            value = (value << 7) | (byte & 0x7F)
            if not (byte & 0x80):
                break
        return value, offset

    @staticmethod
    def _write_vlq(value: int) -> bytes:
        """Encodes an integer into Variable Length Quantity bytes."""
        buffer = bytearray([value & 0x7F])
        value >>= 7
        while value > 0:
            buffer.insert(0, (value & 0x7F) | 0x80)
            value >>= 7
        return bytes(buffer)

    @classmethod
    def parse_file(cls, filepath: str) -> MidiSong:
        """Parses a .mid file into MidiSong structure with full track/channel separation."""
        with open(filepath, "rb") as f:
            data = f.read()

        if len(data) < 14 or data[:4] != b"MThd":
            raise ValueError(f"Arquivo não é um MIDI válido: cabeçalho MThd ausente em {filepath}")

        # Header chunk: 4 bytes length, format (2), tracks (2), division (2)
        _, smf_format, num_tracks, division = struct.unpack(">IHHH", data[4:14])
        ticks_per_beat = division if division > 0 else 480

        offset = 14
        tracks: List[MidiTrack] = []
        tempo_bpm = 120.0
        time_sig = "4/4"
        channel_programs: Dict[int, int] = {}

        for track_idx in range(num_tracks):
            if offset + 8 > len(data):
                break
            chunk_type = data[offset:offset + 4]
            chunk_len = struct.unpack(">I", data[offset + 4:offset + 8])[0]
            offset += 8

            if chunk_type != b"MTrk":
                offset += chunk_len
                continue

            track_data = data[offset:offset + chunk_len]
            offset += chunk_len

            trk_offset = 0
            current_tick = 0
            running_status = 0
            # Track notes separated by channel: channel -> list of MidiNote
            channel_notes: Dict[int, List[MidiNote]] = {}
            # Active notes: (channel, pitch) -> list of (start_tick, velocity) to support polyphony
            active_notes: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}
            track_name = f"Track {track_idx + 1}"
            track_program = 0

            while trk_offset < len(track_data):
                delta, trk_offset = cls._read_vlq(track_data, trk_offset)
                current_tick += delta
                if trk_offset >= len(track_data):
                    break

                status = track_data[trk_offset]
                if status >= 0x80:
                    running_status = status
                    trk_offset += 1
                else:
                    if running_status == 0:
                        trk_offset += 1
                        continue
                    status = running_status

                msg_type = status & 0xF0
                msg_channel = status & 0x0F

                if status == 0xFF:  # Meta event
                    running_status = 0  # Meta cancels running status
                    if trk_offset >= len(track_data):
                        break
                    meta_type = track_data[trk_offset]
                    trk_offset += 1
                    meta_len, trk_offset = cls._read_vlq(track_data, trk_offset)
                    meta_payload = track_data[trk_offset:trk_offset + meta_len]
                    trk_offset += meta_len

                    if meta_type == 0x03:  # Track name
                        try:
                            decoded_name = meta_payload.decode("utf-8", errors="ignore").strip()
                            if decoded_name:
                                track_name = decoded_name
                        except Exception:
                            pass
                    elif meta_type == 0x51 and meta_len == 3:  # Set tempo
                        us_per_beat = struct.unpack(">I", b"\x00" + meta_payload)[0]
                        if us_per_beat > 0:
                            tempo_bpm = round(60000000.0 / us_per_beat, 2)
                    elif meta_type == 0x58 and meta_len >= 2:  # Time signature
                        num = meta_payload[0]
                        den = 2 ** meta_payload[1]
                        time_sig = f"{num}/{den}"
                    elif meta_type == 0x2F:  # End of track
                        break

                elif status in (0xF0, 0xF7):  # SysEx
                    running_status = 0
                    sysex_len, trk_offset = cls._read_vlq(track_data, trk_offset)
                    trk_offset += sysex_len

                elif msg_type == 0x90:  # Note On
                    if trk_offset + 1 >= len(track_data):
                        break
                    pitch = track_data[trk_offset]
                    vel = track_data[trk_offset + 1]
                    trk_offset += 2
                    key = (msg_channel, pitch)

                    if vel > 0:
                        if key not in active_notes:
                            active_notes[key] = []
                        active_notes[key].append((current_tick, vel))
                    else:
                        # Velocity 0 is Note Off
                        if key in active_notes and active_notes[key]:
                            start_t, v = active_notes[key].pop(0)
                            dur_beats = max(0.1, (current_tick - start_t) / ticks_per_beat)
                            start_beats = start_t / ticks_per_beat
                            if msg_channel not in channel_notes:
                                channel_notes[msg_channel] = []
                            channel_notes[msg_channel].append(MidiNote(
                                pitch=pitch, start=start_beats, duration=dur_beats, velocity=v, channel=msg_channel
                            ))

                elif msg_type == 0x80:  # Note Off
                    if trk_offset + 1 >= len(track_data):
                        break
                    pitch = track_data[trk_offset]
                    vel = track_data[trk_offset + 1]
                    trk_offset += 2
                    key = (msg_channel, pitch)
                    if key in active_notes and active_notes[key]:
                        start_t, v = active_notes[key].pop(0)
                        dur_beats = max(0.1, (current_tick - start_t) / ticks_per_beat)
                        start_beats = start_t / ticks_per_beat
                        if msg_channel not in channel_notes:
                            channel_notes[msg_channel] = []
                        channel_notes[msg_channel].append(MidiNote(
                            pitch=pitch, start=start_beats, duration=dur_beats, velocity=v, channel=msg_channel
                        ))

                elif msg_type == 0xC0:  # Program Change
                    if trk_offset < len(track_data):
                        prog = track_data[trk_offset]
                        trk_offset += 1
                        channel_programs[msg_channel] = prog
                        track_program = prog

                elif msg_type in (0xA0, 0xB0, 0xE0):
                    trk_offset += 2
                elif msg_type == 0xD0:
                    trk_offset += 1

            # Close any unclosed notes at end of track
            for (ch, pitch), note_list in active_notes.items():
                for start_t, v in note_list:
                    dur_beats = max(0.25, (current_tick - start_t) / ticks_per_beat)
                    start_beats = start_t / ticks_per_beat
                    if ch not in channel_notes:
                        channel_notes[ch] = []
                    channel_notes[ch].append(MidiNote(
                        pitch=pitch, start=start_beats, duration=dur_beats, velocity=v, channel=ch
                    ))

            # If format 0 or multi-channel track, split into tracks per channel
            if len(channel_notes) > 1:
                for ch, c_notes in sorted(channel_notes.items()):
                    is_drum = ch == 9
                    c_name = f"{track_name} (Ch {ch + 1})" if not is_drum else "Drums (Ch 10)"
                    tracks.append(MidiTrack(
                        name=c_name,
                        channel=ch,
                        program=channel_programs.get(ch, track_program),
                        is_drum=is_drum,
                        notes=sorted(c_notes, key=lambda n: n.start)
                    ))
            elif len(channel_notes) == 1:
                ch, c_notes = list(channel_notes.items())[0]
                is_drum = ch == 9
                tracks.append(MidiTrack(
                    name=track_name,
                    channel=ch,
                    program=channel_programs.get(ch, track_program),
                    is_drum=is_drum,
                    notes=sorted(c_notes, key=lambda n: n.start)
                ))
            elif track_name and track_name != f"Track {track_idx + 1}":
                tracks.append(MidiTrack(name=track_name, notes=[]))

        # Calculate duration in seconds
        max_beats = 0.0
        for t in tracks:
            for n in t.notes:
                max_beats = max(max_beats, n.start + n.duration)
        sec_per_beat = 60.0 / max(20.0, tempo_bpm)
        duration_sec = round(max_beats * sec_per_beat, 2)

        return MidiSong(
            ticks_per_beat=ticks_per_beat,
            bpm=tempo_bpm,
            time_signature=time_sig,
            tracks=tracks,
            duration_sec=duration_sec
        )

    @classmethod
    def write_file(cls, song: MidiSong, filepath: str):
        """Serializes MidiSong into a Standard MIDI File."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        ticks_per_beat = song.ticks_per_beat or 480
        num_tracks = len(song.tracks) + 1  # 1 tempo track + music tracks

        header = struct.pack(">4sIHHH", b"MThd", 6, 1, num_tracks, ticks_per_beat)

        # Track 0: Tempo and Time Signature
        us_per_beat = int(round(60000000.0 / max(20.0, song.bpm)))
        trk0_events = bytearray()
        # Time signature 4/4
        trk0_events += b"\x00\xFF\x58\x04\x04\x02\x18\x08"
        # Tempo
        trk0_events += b"\x00\xFF\x51\x03" + struct.pack(">I", us_per_beat)[1:]
        # End of track
        trk0_events += b"\x00\xFF\x2F\x00"
        track_0 = struct.pack(">4sI", b"MTrk", len(trk0_events)) + trk0_events

        music_tracks_bytes = bytearray()
        for trk in song.tracks:
            # Build timed event list
            events = []
            for n in trk.notes:
                start_tick = int(round(n.start * ticks_per_beat))
                end_tick = int(round((n.start + n.duration) * ticks_per_beat))
                events.append((start_tick, 0x90 | (n.channel & 0x0F), n.pitch, max(1, min(127, n.velocity))))
                events.append((end_tick, 0x80 | (n.channel & 0x0F), n.pitch, 0))

            events.sort(key=lambda e: (e[0], 0 if e[1] & 0xF0 == 0x80 else 1))

            trk_data = bytearray()
            # Track Name meta
            name_bytes = trk.name.encode("utf-8")
            trk_data += b"\x00\xFF\x03" + cls._write_vlq(len(name_bytes)) + name_bytes
            # Program Change
            trk_data += b"\x00" + bytes([0xC0 | (trk.channel & 0x0F), trk.program & 0x7F])

            last_tick = 0
            for ev in events:
                tick, status, p, v = ev
                delta = max(0, tick - last_tick)
                last_tick = tick
                trk_data += cls._write_vlq(delta)
                trk_data += bytes([status, p, v])

            # End of track
            trk_data += b"\x00\xFF\x2F\x00"
            music_tracks_bytes += struct.pack(">4sI", b"MTrk", len(trk_data)) + trk_data

        with open(filepath, "wb") as f:
            f.write(header)
            f.write(track_0)
            f.write(music_tracks_bytes)
