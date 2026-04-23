# Active Context

## Current Status
**Phase: Implementation Complete (Phases 1–8)**
Date: 2026-04-22

## What Was Just Built
Full implementation of the Crawl4AI FastMCP server across all 8 phases:

### Files Created
```
app/
├── server.py          — FastMCP entry point (stdio transport)
├── common.py          — DRY tool/resource/prompt registration
├── config.py          — Environment-based configuration
├── utils.py           — Shared helpers (make_id, get_cache_mode)
├── tools/
│   ├── triage.py      — score_and_triage_urls
│   ├── crawl.py       — crawl_url, crawl_many
│   ├── deep_crawl.py  — deep_crawl (BFS)
│   ├── adaptive_crawl.py — adaptive_crawl (AdaptiveCrawler)
│   └── search.py      — search_chunks, get_crawl_stats
├── storage/
│   ├── sqlite_store.py — SQLite persistence layer
│   ├── chroma_store.py — ChromaDB vector store
│   └── chunker.py     — Token-based text chunker
├── resources/
│   └── static.py      — crawl4ai://status, crawl4ai://capabilities
└── prompts/
    └── research.py    — deep_research_plan prompt
tests/
├── conftest.py        — FastMCP Client fixture
├── test_crawl.py      — crawl_url, crawl_many tests
├── test_triage.py     — score_and_triage_urls tests
├── test_deep_crawl.py — deep_crawl BFS tests
├── test_search.py     — search_chunks, get_crawl_stats tests
└── test_storage.py    — SQLiteStore, ChromaStore, chunker tests
memory-bank/           — All 6 memory bank files
```

## Active Decisions Made

### 1. Single-pass BM25 over two-pass in crawl_url
For `crawl_url` without query: PruningContentFilter only.
With query: BM25ContentFilter directly (BM25 does its own structure analysis).
The "two-pass" described in planning is implemented as a choice between the two.

### 2. AdaptiveCrawler re-crawl pattern
`AdaptiveCrawler.digest()` doesn't expose per-page CrawlResult directly.
We re-crawl each discovered URL after adaptive exploration for proper storage.
This is slightly redundant but ensures consistent storage with BM25 fit_markdown.
**TODO:** Monitor Crawl4AI updates for direct result access from AdaptiveCrawler.

### 3. ChromaDB graceful degradation
ChromaDB/Ollama failures are caught and logged but don't fail crawl tools.
The server remains fully functional for crawling even without Ollama running.
Only `search_chunks` will return an error if ChromaDB is unavailable.

### 4. Session ID is caller-provided
The ADK agent passes a `session_id` string to group related crawls.
The server never auto-generates session IDs — full control stays with caller.

## Next Steps / Open Items
1. ~~**Run tests**~~ — All 20 tests pass ✅
2. ~~**README**~~ — Written ✅
3. **Run `crawl4ai-setup`** — Install Playwright browsers before first real crawl
4. **Create `.env`** — Copy `.env.example` and configure Ollama endpoints
5. **Verify AdaptiveCrawler API** — `max_pages` parameter name may differ in v0.8.6
6. **ADK integration** — Write/test the Google ADK MCPToolset configuration

