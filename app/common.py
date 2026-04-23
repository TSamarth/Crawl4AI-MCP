"""
Central registration of all MCP tools, resources, and prompts.
Follows the DRY common.py pattern — both server entry points import this.
"""
from __future__ import annotations

from fastmcp import FastMCP

from app.tools.adaptive_crawl import adaptive_crawl
from app.tools.crawl import crawl_many, crawl_url
from app.tools.deep_crawl import deep_crawl
from app.tools.search import get_crawl_stats, search_chunks
from app.tools.triage import score_and_triage_urls
from app.resources.static import get_capabilities, get_status
from app.prompts.research import deep_research_plan


def register_all(mcp: FastMCP) -> None:
    """Register all tools, resources, and prompts with the FastMCP server."""

    # ── Tools ────────────────────────────────────────────────────────────────
    mcp.tool()(score_and_triage_urls)
    mcp.tool()(crawl_url)
    mcp.tool()(crawl_many)
    mcp.tool()(deep_crawl)
    mcp.tool()(adaptive_crawl)
    mcp.tool()(search_chunks)
    mcp.tool()(get_crawl_stats)

    # ── Resources ────────────────────────────────────────────────────────────
    mcp.resource("crawl4ai://status")(get_status)
    mcp.resource("crawl4ai://capabilities")(get_capabilities)

    # ── Prompts ──────────────────────────────────────────────────────────────
    mcp.prompt()(deep_research_plan)

