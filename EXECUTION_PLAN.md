# 48-Hour Hackathon Execution Plan

> **Goal:** Working end-to-end demo by hour 36. Last 12 hours for polish, caching, and pitch prep.

## 🕒 Friday Night (Hours 0 - 6): Foundation & Mocks
**Objective:** De-risk the hardest parts and lock schemas.
- [ ] **Team:** Agree on and freeze JSON schemas for `[D] Raw Brief` and `[E] Enriched Brief`.
- [ ] **Ilyas:** Spin up Supabase (Postgres + pgvector). Run `schema.sql`. Share `DATABASE_URL` with the team.
- [ ] **Mohamed:** Build the 5-step synthesis prompt chain. **Test entirely on hardcoded mock context.** Do not touch LangGraph/wiring until the prompt outputs a perfect analyst-quality brief.
- [ ] **Adil:** Build the Scenario Engine formulas. **Test entirely on Mohamed's mock `[D]` JSON.**
- [ ] **Adil:** Manually write 3-4 historical brief JSONs for NVDA/AMD past quarters to seed the DB (solves the cold-start problem for Pattern Matching).

## 🕒 Saturday Morning (Hours 6 - 16): Data & Retrieval
**Objective:** Data flows in, chunks flow out.
- [ ] **Ilyas:** Implement Bright Data scrapers (Earnings calendar, SEC filings, LinkedIn).
- [ ] **Ilyas:** Build Transcript cleaner (Use a fast LLM to parse HTML to JSON, do not write custom regex).
- [ ] **Ilyas:** Embed all cleaned data into Supabase pgvector. 
- [ ] **Mohamed:** Implement pgvector + BM25 RRF retrieval. Connect to Supabase.
- [ ] **Mohamed:** Implement `web_fetch.py` (SERP + Web Unlocker) for live news.

## 🕒 Saturday Afternoon (Hours 16 - 28): The Big Wire-Up
**Objective:** End-to-end pipeline produces a raw brief.
- [ ] **Mohamed:** Wire the LangGraph (Router -> Fetch -> RAG -> Pre-Synth -> Synthesis).
- [ ] **Team:** Run the pipeline on `NVDA`. 
- [ ] **Adil:** Wire the `pattern_agent` to query Supabase for the historical briefs seeded on Friday.
- [ ] **Adil:** Connect the `enricher.py` to Mohamed's output. 

## 🕒 Saturday Night (Hours 28 - 36): Integration & API
**Objective:** It works via API.
- [ ] **Mohamed:** Finalize FastAPI endpoints (`/brief`, `/compare`).
- [ ] **Mohamed:** Implement `asyncio.gather` for `/compare` to run two tickers in parallel.
- [ ] **Ilyas/Adil:** Add quantitative grounding (yFinance/Polygon) to adjust confidence scores in the Scenario Engine.
- [ ] **Team:** Run end-to-end API test. Measure latency.

## 🕒 Sunday Morning (Hours 36 - 48): Polish & Pitch
**Objective:** Bulletproof the demo.
- [ ] **Team:** Implement `api/cache.py`. Pre-run and cache `NVDA`, `TSLA`, `AMD`, and the `NVDA vs AMD` comparison.
- [ ] **Mohamed:** Add graceful fallbacks (e.g., if a random ticker has no historical data, return "Insufficient historical data" rather than crashing).
- [ ] **Team:** UI/Frontend integration (if applicable) or format terminal output to look incredible.
- [ ] **Team:** Write the pitch. Focus on:
    1. The problem (Pre-earnings is noisy).
    2. The architecture (Parallel LangGraph + Bright Data).
    3. The differentiation (Resolved contradictions, grounded confidence scores, historical pattern matching).
