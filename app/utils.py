"""
Shared utilities for the Crawl4AI MCP server.
"""
from __future__ import annotations

import uuid
from crawl4ai import CacheMode


def make_id() -> str:
    return str(uuid.uuid4())


def get_cache_mode(mode: str) -> CacheMode:
    mapping = {
        "enabled": CacheMode.ENABLED,
        "bypass": CacheMode.BYPASS,
        "disabled": CacheMode.DISABLED,
        "read_only": CacheMode.READ_ONLY,
        "write_only": CacheMode.WRITE_ONLY,
    }
    return mapping.get(mode.lower(), CacheMode.ENABLED)
