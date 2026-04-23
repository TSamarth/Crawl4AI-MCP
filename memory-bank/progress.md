# Progress

## What Works (Implemented)
- [x] Project structure with uv, all dependencies installed
- [x] Configuration system (app/config.py) with env var loading
- [x] SQLite storage (crawl_sessions, crawled_pages, chunks, page_links)
- [x] ChromaDB store with Ollama embedding function
- [x] Token-based text chunker (tiktoken cl100k_base)
- [x] Tool: score_and_triage_urls (LinkPreviewConfig + BM25 scoring)
- [x] Tool: crawl_url (single URL, two-pass content filter)
- [x] Tool: crawl_many (batch, MemoryAdaptiveDispatcher, streaming)
- [x] Tool: deep_crawl (BFS with depth/page limits, domain/pattern filters)
- [x] Tool: adaptive_crawl (AdaptiveCrawler.digest() wrapper)
- [x] Tool: search_chunks (ChromaDB cosine similarity search)
- [x] Tool: get_crawl_stats (SQLite + ChromaDB metrics)
- [x] Resource: crawl4ai://status
- [x] Resource: crawl4ai://capabilities
- [x] Prompt: deep_research_plan
- [x] FastMCP server (stdio transport)
- [x] common.py DRY registration
- [x] Test suite (5 test files, conftest with FastMCP Client fixture)
- [x] Memory bank (all 6 files)

## What's Left / Known Issues
- [x] Tests validated — all 20 pass (6 storage, 6 triage+search, 8 crawl+deep_crawl)
- [ ] AdaptiveCrawler `max_pages` param name needs verification for v0.8.6
- [x] README written (README.md)
- [ ] crawl4ai-setup not run (Playwright browser install)
- [ ] .env file not created from .env.example
- [ ] Ollama models not verified (nomic-embed-text, llama3.2)

## Known Decisions / Trade-offs
1. **Re-crawl in adaptive_crawl:** AdaptiveCrawler doesn't expose per-page results
   so we re-crawl URLs post-discovery. Minor inefficiency, correctness priority.
2. **Storage optional for crawl tools:** ChromaDB failures are swallowed.
   This keeps crawl tools working without Ollama, at cost of missing embeddings.
3. **No session auto-creation:** Sessions must be explicitly created or the
   session_id is passed as metadata only (no FK violation due to IGNORE).

