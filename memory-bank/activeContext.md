# Active Context

## Current Status
**Phase: Chunking Strategy Upgrade (Phase 9)**
Date: 2026-05-06

## What Was Just Built
Replaced the manual tiktoken-based `TextChunker` with Crawl4AI's native chunking
strategies and added opt-in LLM extraction across all crawl tools.

### Changes Made
```
app/config.py       — Added 6 new config fields (CHUNKING_STRATEGY, window/step/overlap
                      words, REGEX_CHUNKING_PATTERNS, LLM_EXTRACTION_ENABLED)
app/storage/chunker.py — Added get_crawl4ai_chunker() factory + chunk_text() primary
                         path; kept TextChunker class as legacy fallback (tests still pass)
app/tools/crawl.py  — Removed TextChunker instance; import chunk_text; added
                      _build_llm_extraction_strategy(); dual-path _persist_result
                      (LLM extracted_content → native chunking fallback); added
                      use_llm_extraction param to crawl_url + crawl_many
app/tools/deep_crawl.py — Removed hardcoded LLMExtractionStrategy; import
                          _build_llm_extraction_strategy; use_llm_extraction param
app/tools/adaptive_crawl.py — Replaced TextChunker with chunk_text(); added
                               extraction metadata key
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

### 5. Chunking strategy is uniform across all tools
All 4 crawl tools use `chunk_text()` (Crawl4AI native) for consistency.
Controlled by `CHUNKING_STRATEGY` env var: `sliding_window` | `regex` | `overlapping`.
Default: `sliding_window` (window_size=200 words, step=160 words).

### 6. LLM extraction is opt-in
`use_llm_extraction` param on `crawl_url`, `crawl_many`, `deep_crawl` (default: False,
or `config.LLM_EXTRACTION_ENABLED` if not specified per call).
When enabled, `_persist_result` reads from `result.extracted_content` (LLM blocks)
instead of running the standalone chunking strategy.

### 7. TextChunker kept for backward compatibility
Legacy `TextChunker` class stays in `chunker.py` so existing tests and any
external code referencing it continue to work without changes.

## Next Steps / Open Items
1. ~~**Chunking strategy upgrade**~~ — Implemented ✅ (all 12 tests pass)
2. **Verify AdaptiveCrawler API** — `max_pages` parameter name may differ in v0.8.6
3. **ADK integration** — Write/test the Google ADK MCPToolset configuration
4. **LLM extraction E2E test** — Add a test that mocks `result.extracted_content`
   and verifies `_persist_result` takes the LLM path correctly
