import unittest
from backend.music_theory.analyzer import HarmonicAnalyzer, PITCH_NAMES


class TestMusicTheory(unittest.TestCase):
    def test_c_major_key_estimation(self):
        # C major triad: C, E, G
        notes = [
            {"pitch": 60, "duration": 1.0, "velocity": 100},  # C4
            {"pitch": 64, "duration": 1.0, "velocity": 100},  # E4
            {"pitch": 67, "duration": 1.0, "velocity": 100},  # G4
        ]
        estimate = HarmonicAnalyzer.estimate_key(notes)
        self.assertEqual(estimate.root, "C")
        self.assertEqual(estimate.mode, "major")
        self.assertGreater(estimate.confidence, 0.0)

    def test_chord_identification(self):
        # A minor: A, C, E
        pitches = [57, 60, 64]
        chord = HarmonicAnalyzer.identify_chord_from_pitches(pitches, key_root="A", key_mode="minor")
        self.assertIsNotNone(chord)
        self.assertEqual(chord.root, "A")
        self.assertEqual(chord.chord_type, "min")
        self.assertEqual(chord.roman_numeral, "i")

    def test_midi_to_note_name(self):
        self.assertEqual(HarmonicAnalyzer.midi_to_note_name(60), "C4")
        self.assertEqual(HarmonicAnalyzer.midi_to_note_name(69), "A4")


if __name__ == "__main__":
    unittest.main()
