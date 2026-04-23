"""
Token-aware sliding window text chunker.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

import tiktoken


@dataclass
class TextChunk:
    text: str
    chunk_index: int
    token_count: int
    char_start: int
    char_end: int


class TextChunker:
    """
    Splits markdown/text into overlapping token-bounded chunks.
    Uses cl100k_base encoding (same as GPT-3.5/4, good for estimation).
    """

    def __init__(self, chunk_size: int = 512, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
        try:
            self._enc = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self._enc = None  # fallback to word-based estimation

    def _tokenize(self, text: str) -> List[int]:
        if self._enc:
            return self._enc.encode(text)
        # Fallback: ~0.75 tokens per character approximation via words
        words = text.split()
        # Return fake token ids using word indices
        return list(range(len(words)))

    def _decode_tokens(self, tokens: List[int], original_text: str) -> str:
        """Decode token ids back to text."""
        if self._enc:
            try:
                return self._enc.decode(tokens)
            except Exception:
                pass
        # Fallback: return word-slice
        words = original_text.split()
        # tokens are word indices in fallback mode
        if not tokens:
            return ""
        start = tokens[0]
        end = tokens[-1] + 1
        return " ".join(words[start:end])

    def chunk(self, text: str, url: str = "", title: str = "") -> List[TextChunk]:
        """
        Chunk text into overlapping token windows.
        Returns list of TextChunk objects.
        """
        if not text or not text.strip():
            return []

        tokens = self._tokenize(text)
        if not tokens:
            return []

        chunks: List[TextChunk] = []
        step = max(1, self.chunk_size - self.overlap)
        chunk_index = 0

        for start in range(0, len(tokens), step):
            end = min(start + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]

            if not chunk_tokens:
                break

            chunk_text = self._decode_tokens(chunk_tokens, text)
            if not chunk_text.strip():
                continue

            # Approximate char positions
            char_start = len(self._decode_tokens(tokens[:start], text))
            char_end = char_start + len(chunk_text)

            chunks.append(
                TextChunk(
                    text=chunk_text,
                    chunk_index=chunk_index,
                    token_count=len(chunk_tokens),
                    char_start=char_start,
                    char_end=char_end,
                )
            )
            chunk_index += 1

            if end >= len(tokens):
                break

        return chunks

