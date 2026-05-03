"""
Configuration management for the Crawl4AI MCP server.
Loads settings from environment variables / .env file.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


def _env_int(key: str, default: int) -> int:
    return int(os.getenv(key, str(default)))


def _env_float(key: str, default: float) -> float:
    return float(os.getenv(key, str(default)))


@dataclass
class Config:
    # ── Server ──────────────────────────────────────────────────────────────
    SERVER_NAME: str = "crawl4ai-research-server"
    SERVER_VERSION: str = "0.1.0"

    # ── Ollama ───────────────────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = field(
        default_factory=lambda: _env("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    OLLAMA_EMBED_MODEL: str = field(
        default_factory=lambda: _env("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    )
    OLLAMA_LLM_MODEL: str = field(
        default_factory=lambda: _env("OLLAMA_LLM_MODEL", "llama3.2")
    )

    # ── Storage ──────────────────────────────────────────────────────────────
    CHROMA_PERSIST_DIR: str = field(
        default_factory=lambda: _env("CHROMA_PERSIST_DIR", "./data/chroma")
    )
    SQLITE_DB_PATH: str = field(
        default_factory=lambda: _env("SQLITE_DB_PATH", "./data/research.db")
    )

    # ── Crawling ─────────────────────────────────────────────────────────────
    MAX_CONCURRENT_CRAWLS: int = field(
        default_factory=lambda: _env_int("MAX_CONCURRENT_CRAWLS", 5)
    )
    PAGE_TIMEOUT_MS: int = field(
        default_factory=lambda: _env_int("PAGE_TIMEOUT_MS", 30000)
    )
    # "enabled" | "bypass" | "disabled"
    CACHE_MODE: str = field(
        default_factory=lambda: _env("CACHE_MODE", "enabled")
    )

    # ── Content Quality ──────────────────────────────────────────────────────
    PRUNING_THRESHOLD: float = field(
        default_factory=lambda: _env_float("PRUNING_THRESHOLD", 0.45)
    )
    BM25_THRESHOLD: float = field(
        default_factory=lambda: _env_float("BM25_THRESHOLD", 1.0)
    )
    MIN_WORD_THRESHOLD: int = field(
        default_factory=lambda: _env_int("MIN_WORD_THRESHOLD", 50)
    )

    # ── Chunking ─────────────────────────────────────────────────────────────
    # Hard context-window limit of the embedding model (in its own tokens).
    # Used to derive a safe CHUNK_SIZE_TOKENS when not explicitly set.
    EMBED_MODEL_MAX_TOKENS: int = field(
        default_factory=lambda: _env_int("EMBED_MODEL_MAX_TOKENS", 512)
    )
    # Safety factor: cl100k (tiktoken) produces fewer tokens than BERT-style
    # tokenizers for the same text.  For typical English prose the ratio is
    # ~1.33×, but URL-dense or minified-code content can reach 1.7–1.8×.
    # 0.6 × 512 = 307 → rounded to 304, giving headroom for worst-case inputs.
    EMBED_TOKENIZER_SAFETY_FACTOR: float = field(
        default_factory=lambda: _env_float("EMBED_TOKENIZER_SAFETY_FACTOR", 0.6)
    )
    CHUNK_SIZE_TOKENS: int = field(
        default_factory=lambda: _env_int(
            "CHUNK_SIZE_TOKENS",
            # Default: 60% of embed model window, rounded down to nearest 8
            int(_env_int("EMBED_MODEL_MAX_TOKENS", 512)
                * _env_float("EMBED_TOKENIZER_SAFETY_FACTOR", 0.6 ) // 8 * 8),
        )
    )
    CHUNK_OVERLAP_TOKENS: int = field(
        default_factory=lambda: _env_int("CHUNK_OVERLAP_TOKENS", 40)
    )

    def ensure_data_dirs(self) -> None:
        """Create data directories if they don't exist."""
        Path(self.CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.SQLITE_DB_PATH).parent.mkdir(parents=True, exist_ok=True)


# Singleton instance
config = Config()

