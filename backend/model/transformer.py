"""Autoregressive Music Transformer Language Model.
Built on PyTorch with pure-Python execution fallback.
Optimized for modest CPU (e.g. AMD Ryzen 5, 8GB RAM).
"""
import math
import json
import os
import random
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


@dataclass
class ModelConfig:
    vocab_size: int = 256
    seq_len: int = 128
    d_model: int = 128
    n_heads: int = 4
    n_layers: int = 3
    dim_feedforward: int = 256
    dropout: float = 0.1
    device: str = "cpu"


if HAS_TORCH:
    class MusicTransformerLM(nn.Module):
        """PyTorch Autoregressive Decoder-Only Transformer for Music Tokens."""

        def __init__(self, config: ModelConfig):
            super().__init__()
            self.config = config
            self.token_emb = nn.Embedding(config.vocab_size, config.d_model)
            self.pos_emb = nn.Embedding(config.seq_len, config.d_model)
            self.drop = nn.Dropout(config.dropout)

            encoder_layer = nn.TransformerEncoderLayer(
                d_model=config.d_model,
                nhead=config.n_heads,
                dim_feedforward=config.dim_feedforward,
                dropout=config.dropout,
                activation="gelu",
                batch_first=True
            )
            self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=config.n_layers)
            self.ln_f = nn.LayerNorm(config.d_model)
            self.head = nn.Linear(config.d_model, config.vocab_size, bias=False)
            self.token_emb.weight = self.head.weight  # Weight tying

        def forward(self, idx: torch.Tensor, targets: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
            b, t = idx.size()
            positions = torch.arange(0, t, dtype=torch.long, device=idx.device).unsqueeze(0)

            x = self.token_emb(idx) + self.pos_emb(positions)
            x = self.drop(x)

            # Causal mask so position i cannot attend to position j > i
            causal_mask = nn.Transformer.generate_square_subsequent_mask(t).to(idx.device)
            x = self.transformer(x, mask=causal_mask, is_causal=True)
            x = self.ln_f(x)
            logits = self.head(x)

            loss = None
            if targets is not None:
                loss = F.cross_entropy(logits.view(-1, logits.size(-1)), targets.view(-1), ignore_index=0)

            return logits, loss

        @torch.no_grad()
        def generate(self, prompt_tokens: List[int], max_new_tokens: int = 64, temperature: float = 0.9, top_k: int = 40) -> List[int]:
            self.eval()
            tokens = list(prompt_tokens)
            device = next(self.parameters()).device

            for _ in range(max_new_tokens):
                ctx = tokens[-self.config.seq_len:]
                idx = torch.tensor([ctx], dtype=torch.long, device=device)
                logits, _ = self.forward(idx)
                next_logits = logits[0, -1, :] / max(0.1, temperature)

                # Top-K filtering
                if top_k > 0:
                    v, _ = torch.topk(next_logits, min(top_k, next_logits.size(-1)))
                    next_logits[next_logits < v[-1]] = -float('Inf')

                probs = F.softmax(next_logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1).item()
                tokens.append(next_token)

                # Stop token
                if next_token == 2:  # [EOS]
                    break

            return tokens

else:
    # Pure Python probabilistic n-gram / transition matrix fallback when PyTorch is not yet installed
    class MusicTransformerLM:
        def __init__(self, config: ModelConfig):
            self.config = config
            self.transitions: Dict[Tuple[int, ...], Dict[int, int]] = {}
            self.vocab_size = config.vocab_size

        def fit_tokens(self, token_sequences: List[List[int]], n: int = 3):
            """Trains an n-gram Markov transition table."""
            for seq in token_sequences:
                for i in range(len(seq) - 1):
                    for order in range(1, min(n + 1, i + 2)):
                        ctx = tuple(seq[max(0, i - order + 1):i + 1])
                        next_tok = seq[i + 1]
                        if ctx not in self.transitions:
                            self.transitions[ctx] = {}
                        self.transitions[ctx][next_tok] = self.transitions[ctx].get(next_tok, 0) + 1

        def generate(self, prompt_tokens: List[int], max_new_tokens: int = 64, temperature: float = 0.9, top_k: int = 40) -> List[int]:
            tokens = list(prompt_tokens)
            for _ in range(max_new_tokens):
                # Try context length 3 down to 1
                found = False
                for order in [3, 2, 1]:
                    if len(tokens) >= order:
                        ctx = tuple(tokens[-order:])
                        if ctx in self.transitions and self.transitions[ctx]:
                            candidates = self.transitions[ctx]
                            toks = list(candidates.keys())
                            counts = list(candidates.values())

                            # Apply temperature
                            weights = [math.pow(c, 1.0 / max(0.1, temperature)) for c in counts]
                            total = sum(weights)
                            probs = [w / total for w in weights]

                            chosen = random.choices(toks, weights=probs, k=1)[0]
                            tokens.append(chosen)
                            found = True
                            break

                if not found:
                    # Random plausible musical pitch or position token
                    chosen = random.randint(4, min(self.vocab_size - 1, 100))
                    tokens.append(chosen)

                if tokens[-1] == 2:  # [EOS]
                    break
            return tokens
