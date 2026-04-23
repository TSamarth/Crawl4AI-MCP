"""
Static MCP resources: server status and capabilities.
"""
from __future__ import annotations

import importlib.metadata
from typing import Any, Dict

import httpx

from app.config import config
from app.storage.sqlite_store import get_store


async def get_status() -> str:
    """
    Server health status including Crawl4AI version, Ollama connectivity,
    and storage counts.
    """
    # Crawl4AI version
    try:
        c4ai_version = importlib.metadata.version("crawl4ai")
    except Exception:
        c4ai_version = "unknown"

    # Ollama ping
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(config.OLLAMA_BASE_URL)
            ollama_ok = resp.status_code < 500
    except Exception:
        ollama_ok = False

    # SQLite stats
    try:
        store = await get_store()
        stats = await store.get_stats()
    except Exception:
        stats = {}

    # ChromaDB count
    try:
        from app.storage.chroma_store import get_chroma
        chroma_count = get_chroma().count()
    except Exception:
        chroma_count = -1

    lines = [
        f"# Crawl4AI Research MCP Server",
        f"",
        f"**Version:** {config.SERVER_VERSION}",
        f"**Crawl4AI:** {c4ai_version}",
        f"",
        f"## Connectivity",
        f"- Ollama ({config.OLLAMA_BASE_URL}): {'✅ reachable' if ollama_ok else '❌ unreachable'}",
        f"- Embed model: {config.OLLAMA_EMBED_MODEL}",
        f"- LLM model: {config.OLLAMA_LLM_MODEL}",
        f"",
        f"## Storage",
        f"- Sessions: {stats.get('sessions', 0)}",
        f"- Pages crawled: {stats.get('pages_crawled', 0)}",
        f"- Chunks (SQLite): {stats.get('chunks_stored', 0)}",
        f"- Chunks (ChromaDB): {chroma_count if chroma_count >= 0 else 'unavailable'}",
        f"",
        f"## Config",
        f"- Max concurrent crawls: {config.MAX_CONCURRENT_CRAWLS}",
        f"- Page timeout: {config.PAGE_TIMEOUT_MS}ms",
        f"- Cache mode: {config.CACHE_MODE}",
    ]
    return "\n".join(lines)


def get_capabilities() -> str:
    """
    Lists all available MCP tools, their purpose, and crawl strategies.
    """
    return """# Crawl4AI MCP Server — Capabilities

## Tools

### 1. `score_and_triage_urls`
Score and rank a list of URLs before crawling. Uses Crawl4AI's LinkPreviewConfig
with BM25 contextual scoring to identify high-value research sources and
recommend the optimal crawl strategy for each.

### 2. `crawl_url`
Crawl a single URL with two-pass quality filtering (Pruning → BM25).
Returns raw_markdown and fit_markdown. Stores result in SQLite + ChromaDB.

### 3. `crawl_many`
Crawl multiple URLs concurrently with MemoryAdaptiveDispatcher.
Accepts the qualified_urls list from triage. Stores all results incrementally.

### 4. `deep_crawl`
BFS link-following from a seed URL. Explores up to max_depth levels and
max_pages total. Best for documentation sites and blog archives.

### 5. `adaptive_crawl`
Confidence-based exploration using AdaptiveCrawler. Automatically follows
the most relevant links until target confidence is reached. Best for
open-ended research with unknown content distribution.

### 6. `search_chunks`
Semantic search over stored research chunks via ChromaDB + Ollama embeddings.
Call this to retrieve relevant context for synthesis after crawling.

### 7. `get_crawl_stats`
Returns SQLite and ChromaDB storage statistics: sessions, pages, chunks,
top-scoring pages by quality score.

## Resources
- `crawl4ai://status` — Live server health and storage metrics
- `crawl4ai://capabilities` — This document

## Recommended Workflow
1. `score_and_triage_urls` → get qualified URLs + strategy recommendations
2. For each strategy group:
   - `adaptive_crawl` for doc sites (score ≥ 0.75)
   - `deep_crawl` for blog/wiki archives (score ≥ 0.55)
   - `crawl_many` for batches of individual pages
3. `search_chunks` to retrieve relevant content for synthesis
4. `get_crawl_stats` to verify coverage
"""

