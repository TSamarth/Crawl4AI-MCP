"""
Crawl4AI Research MCP Server — Entry Point.

Runs as a stdio MCP server for local use with Google ADK.
Start with: uv run python -m app.server
"""
from __future__ import annotations

from fastmcp import FastMCP

from app.config import config
from app.common import register_all

# Ensure data directories exist on startup
config.ensure_data_dirs()

# Create the FastMCP server
mcp = FastMCP(
    config.SERVER_NAME,
    instructions=(
        "Crawl4AI Research MCP Server. "
        "Provides web crawling, URL triage, deep/adaptive crawling, "
        "and semantic search tools for agentic deep research workflows. "
        "Use score_and_triage_urls first to evaluate sources, then choose "
        "the appropriate crawl strategy (adaptive_crawl, deep_crawl, or crawl_many). "
        "Results are stored in ChromaDB + SQLite for retrieval via search_chunks."
    ),
)

# Register all components
register_all(mcp)


# if __name__ == "__main__":
#     mcp.run(transport="stdio")
