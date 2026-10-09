import unittest
import os
from backend.midi.parser import MidiParser, MidiSong, MidiTrack, MidiNote
from backend.midi.tokenizer import MidiTokenizer


class TestMidiPipeline(unittest.TestCase):
    def setUp(self):
        self.test_file = "data/test_unit.mid"
        os.makedirs("data", exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.test_file):
            try:
                os.remove(self.test_file)
            except Exception:
                pass

    def test_write_and_parse_midi(self):
        song = MidiSong(
            ticks_per_beat=480,
            bpm=128.0,
            tracks=[
                MidiTrack(name="Bass", channel=1, notes=[
                    MidiNote(pitch=36, start=0.0, duration=1.0, velocity=90),
                    MidiNote(pitch=38, start=1.0, duration=1.0, velocity=85),
                ])
            ]
        )
        MidiParser.write_file(song, self.test_file)
        self.assertTrue(os.path.exists(self.test_file))

        loaded = MidiParser.parse_file(self.test_file)
        self.assertEqual(loaded.bpm, 128.0)
        self.assertEqual(len(loaded.tracks), 1)
        self.assertEqual(len(loaded.tracks[0].notes), 2)
        self.assertEqual(loaded.tracks[0].notes[0].pitch, 36)

    def test_remi_tokenizer(self):
        tok = MidiTokenizer()
        self.assertGreater(tok.vocab_size, 50)
        song = MidiSong(
            bpm=120.0,
            tracks=[
                MidiTrack(name="Melody", notes=[
                    MidiNote(pitch=60, start=0.0, duration=0.5, velocity=80),
                    MidiNote(pitch=62, start=0.5, duration=0.5, velocity=80)
                ])
            ]
        )
        tokens = tok.encode_song(song)
        self.assertIn("[BOS]", tok.inv_vocab[tokens[0]])
        self.assertIn("[EOS]", tok.inv_vocab[tokens[-1]])

        decoded = tok.decode_tokens(tokens)
        self.assertGreaterEqual(len(decoded.tracks), 1)


if __name__ == "__main__":
    unittest.main()
