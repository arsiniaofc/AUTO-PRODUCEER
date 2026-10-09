import unittest
from backend.model.transformer import MusicTransformerLM, ModelConfig
from backend.generation.generator import MusicGenerator


class TestModelAndGeneration(unittest.TestCase):
    def test_model_initialization(self):
        config = ModelConfig(vocab_size=100, seq_len=32, d_model=64, n_heads=2, n_layers=2)
        model = MusicTransformerLM(config)
        self.assertIsNotNone(model)

    def test_full_song_generation(self):
        result = MusicGenerator.generate_full_song(
            title="Teste Unitario",
            root_key="C",
            scale="major",
            bpm=120.0,
            bars=4
        )
        self.assertEqual(result["title"], "Teste Unitario")
        self.assertEqual(result["bars"], 4)
        self.assertGreater(len(result["tracks"]), 0)
        self.assertIn("C Major", result["key"])


if __name__ == "__main__":
    unittest.main()
