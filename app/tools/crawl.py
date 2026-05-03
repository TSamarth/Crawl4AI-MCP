"""
Core crawling tools: crawl_url and crawl_many.

Both tools apply a two-pass content filter pipeline:
  1. PruningContentFilter  – removes boilerplate (always)
  2. BM25ContentFilter     – query-focused relevance (when query provided)

Results are stored in SQLite + ChromaDB for later semantic search.
"""
from __future__ import annotations

# import asyncio
from typing import Any, Dict, List, Optional

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai import MemoryAdaptiveDispatcher
from crawl4ai.content_filter_strategy import BM25ContentFilter, PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from fastmcp import Context

from app.config import config
from app.storage.chroma_store import get_chroma
from app.storage.chunker import TextChunker
from app.storage.sqlite_store import get_store
from app.utils import get_cache_mode, make_id

_chunker = TextChunker(
    chunk_size=config.CHUNK_SIZE_TOKENS,
    overlap=config.CHUNK_OVERLAP_TOKENS,
)


def _build_run_config(
    query: Optional[str] = None,
    css_selector: Optional[str] = None,
    excluded_tags: Optional[List[str]] = None,
    cache_mode_str: Optional[str] = None,
    take_screenshot: bool = False,
    wait_for: Optional[str] = None,
    js_code: Optional[str] = None,
) -> CrawlerRunConfig:
    """Build a CrawlerRunConfig with research-optimised content filtering."""
    tags = excluded_tags or ["nav", "footer", "aside", "header", "script", "style"]

    # Two-pass filter: Prune first, then BM25 if query provided
    prune_filter = PruningContentFilter(
        threshold=config.PRUNING_THRESHOLD,
        threshold_type="dynamic",
        min_word_threshold=config.MIN_WORD_THRESHOLD,
    )

    if query:
        bm25_filter = BM25ContentFilter(
            user_query=query,
            bm25_threshold=config.BM25_THRESHOLD,
            language="english",
        )
        md_generator = DefaultMarkdownGenerator(content_filter=bm25_filter)
    else:
        md_generator = DefaultMarkdownGenerator(content_filter=prune_filter)

    return CrawlerRunConfig(
        markdown_generator=md_generator,
        css_selector=css_selector,
        excluded_tags=tags,
        remove_overlay_elements=True,
        remove_forms=True,
        exclude_external_links=False,
        exclude_social_media_links=True,
        cache_mode=get_cache_mode(cache_mode_str or config.CACHE_MODE),
        page_timeout=config.PAGE_TIMEOUT_MS,
        screenshot=take_screenshot,
        wait_for=wait_for,
        js_code=js_code,
        verbose=False,
    )


async def _persist_result(
    result: Any,
    session_id: Optional[str],
    strategy: str,
    query: Optional[str],
    total_score: float = 0.0,
) -> str:
    """Save crawl result to SQLite and ChromaDB. Returns page_id."""
    page_id = make_id()
    meta = result.metadata or {}
    title = meta.get("title", "") if isinstance(meta, dict) else ""

    raw_md = ""
    fit_md = ""
    if result.markdown:
        if hasattr(result.markdown, "raw_markdown"):
            raw_md = result.markdown.raw_markdown or ""
            fit_md = result.markdown.fit_markdown or raw_md
        else:
            raw_md = str(result.markdown)
            fit_md = raw_md

    store = await get_store()
    await store.save_page(
        page_id=page_id,
        session_id=session_id,
        url=result.url,
        title=title,
        raw_markdown=raw_md,
        fit_markdown=fit_md,
        strategy=strategy,
        total_score=total_score,
        status_code=result.status_code,
        success=result.success,
        error=result.error_message if not result.success else None,
    )

    # Save links
    internal_links = [
        {**lnk, "link_type": "internal"}
        for lnk in (result.links.get("internal", []) if result.links else [])
    ]
    external_links = [
        {**lnk, "link_type": "external"}
        for lnk in (result.links.get("external", []) if result.links else [])
    ]
    await store.save_links(page_id, internal_links + external_links)

    # Chunk and store in ChromaDB
    if fit_md.strip():
        chunks = _chunker.chunk(fit_md, url=result.url, title=title)
        if chunks:
            chroma = get_chroma()
            chunk_ids = [make_id() for _ in chunks]
            chunk_texts = [c.text for c in chunks]
            metadatas = [
                {
                    "url": result.url,
                    "title": title,
                    "session_id": session_id or "",
                    "query": query or "",
                    "chunk_index": str(c.chunk_index),
                    "strategy": strategy,
                    "page_id": page_id,
                }
                for c in chunks
            ]
            try:
                chroma.add_chunks(chunk_ids, chunk_texts, metadatas)
            except Exception:
                pass  # ChromaDB (Ollama) may be unavailable — don't fail the crawl

            chunk_records = [
                {
                    "id": cid,
                    "chunk_index": c.chunk_index,
                    "chunk_text": c.text,
                    "token_count": c.token_count,
                    "chroma_doc_id": cid,
                }
                for cid, c in zip(chunk_ids, chunks)
            ]
            await store.save_chunks(page_id, chunk_records)

    return page_id


def _format_result(result: Any, page_id: str) -> Dict[str, Any]:
    """Format a CrawlResult into the standard tool response dict."""
    meta = result.metadata or {}
    title = meta.get("title", "") if isinstance(meta, dict) else ""

    raw_md = ""
    fit_md = ""
    if result.markdown:
        if hasattr(result.markdown, "raw_markdown"):
            raw_md = result.markdown.raw_markdown or ""
            fit_md = result.markdown.fit_markdown or raw_md
        else:
            raw_md = str(result.markdown)
            fit_md = raw_md

    return {
        "success": result.success,
        "url": result.url,
        "page_id": page_id,
        "title": title,
        "raw_markdown": raw_md,
        "fit_markdown": fit_md,
        "internal_links": [lnk.get("href") for lnk in (result.links or {}).get("internal", [])],
        "external_links": [lnk.get("href") for lnk in (result.links or {}).get("external", [])],
        "metadata": {
            "word_count": len(raw_md.split()),
            "fit_word_count": len(fit_md.split()),
            "status_code": result.status_code,
        },
        "screenshot_base64": result.screenshot or None,
        "error": result.error_message if not result.success else None,
    }


# ── Tool: crawl_url ──────────────────────────────────────────────────────────

async def crawl_url(
    url: str,
    query: Optional[str] = None,
    session_id: Optional[str] = None,
    css_selector: Optional[str] = None,
    excluded_tags: Optional[List[str]] = None,
    cache_mode: Optional[str] = None,
    take_screenshot: bool = False,
    wait_for: Optional[str] = None,
    js_code: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Crawl a single URL and extract high-quality research content.

    Applies a two-pass content filter:
    1. PruningContentFilter removes boilerplate and low-quality blocks.
    2. BM25ContentFilter (when query provided) focuses content on research topic.

    The result is stored in SQLite and ChromaDB for later retrieval.

    Args:
        url: Target URL to crawl.
        query: Research query for BM25 relevance filtering and storage metadata.
        session_id: Research session identifier for grouping results.
        css_selector: Focus crawl on a specific CSS region (e.g. "main.content").
        excluded_tags: HTML tags to strip (default: nav, footer, aside, header).
        cache_mode: Override cache behaviour: enabled | bypass | disabled.
        take_screenshot: Capture a base64 screenshot of the page.
        wait_for: CSS or JS condition to wait for before extracting.
        js_code: JavaScript to execute after page load.

    Returns:
        Dict with success, url, title, raw_markdown, fit_markdown, links, metadata.
    """
    if ctx:
        await ctx.info(f"Crawling: {url}")

    browser_cfg = BrowserConfig(headless=True, text_mode=not take_screenshot, light_mode=True)
    run_cfg = _build_run_config(
        query=query,
        css_selector=css_selector,
        excluded_tags=excluded_tags,
        cache_mode_str=cache_mode,
        take_screenshot=take_screenshot,
        wait_for=wait_for,
        js_code=js_code,
    )

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url, config=run_cfg)

    page_id = await _persist_result(result, session_id, "crawl_url", query)

    if ctx:
        status = "✅" if result.success else "❌"
        await ctx.info(f"{status} {url} — page_id: {page_id}")

    return _format_result(result, page_id)


# ── Tool: crawl_many ─────────────────────────────────────────────────────────

async def crawl_many(
    urls: List[str],
    query: Optional[str] = None,
    session_id: Optional[str] = None,
    max_concurrent: int = 5,
    cache_mode: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Crawl multiple URLs concurrently with memory-adaptive dispatch.

    Uses MemoryAdaptiveDispatcher to automatically throttle concurrency when
    system memory exceeds 70%, preventing OOM during large research batches.
    Results are stored incrementally in SQLite + ChromaDB.

    Args:
        urls: List of URLs to crawl (typically the qualified_urls from triage).
        query: Shared research query for BM25 filtering and storage metadata.
        session_id: Research session identifier for grouping results.
        max_concurrent: Maximum concurrent crawl sessions (default 5).
        cache_mode: Override cache behaviour: enabled | bypass | disabled.

    Returns:
        Dict with results list, summary stats, and session_id.
    """
    if not urls:
        return {"results": [], "stats": {"total": 0, "success": 0, "failed": 0}, "session_id": session_id}

    if ctx:
        await ctx.info(f"Batch crawling {len(urls)} URLs (max_concurrent={max_concurrent})")

    effective_concurrent = min(max_concurrent, config.MAX_CONCURRENT_CRAWLS)

    browser_cfg = BrowserConfig(headless=True, text_mode=True, light_mode=True)
    run_cfg = _build_run_config(query=query, cache_mode_str=cache_mode)

    dispatcher = MemoryAdaptiveDispatcher(
        memory_threshold_percent=70.0,
        max_session_permit=effective_concurrent,
    )

    results_out = []
    success_count = 0
    fail_count = 0

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        async for result in await crawler.arun_many(
            urls=urls,
            config=run_cfg.clone(stream=True),
            dispatcher=dispatcher,
        ):
            page_id = await _persist_result(result, session_id, "crawl_many", query)
            formatted = _format_result(result, page_id)
            results_out.append(formatted)

            if result.success:
                success_count += 1
                if ctx:
                    await ctx.info(f"  ✅ {result.url}")
            else:
                fail_count += 1
                if ctx:
                    await ctx.warning(f"  ❌ {result.url}: {result.error_message}")

    if ctx:
        await ctx.info(f"Batch done: {success_count} succeeded, {fail_count} failed")

    return {
        "results": results_out,
        "stats": {
            "total": len(urls),
            "success": success_count,
            "failed": fail_count,
        },
        "session_id": session_id,
    }

