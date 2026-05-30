# Mohamed — Retrieval Brain & Pipeline

> [!IMPORTANT]
> Scope revised: one person, demo-focused. RAG skipped for demo. Pipeline is web_fetch → pre_synthesis → synthesis → API.

| File | Responsibility |
|------|---------------|
| `agent/graph.py` | Wires web_fetch → pre_synthesis → synthesis ✅ |
| `agent/nodes/router.py` | Source priority + recency mode from earnings date ✅ |
| `agent/nodes/web_fetch.py` | SERP API + Web Unlocker — parallel async, retry logic ✅ |
| `agent/nodes/pre_synthesis.py` | Dedup, recency weighting, sentiment counting ✅ |
| `agent/nodes/synthesis.py` | 6-call reasoning chain → structured JSON brief ✅ |
| `intelligence/yfinance.py` | EPS, revenue, P/E — pre-labeled chunks + context string ✅ |
| `api/main.py` | FastAPI app |
| `api/routes/brief.py` | `POST /brief/{ticker}` |
| `api/routes/compare.py` | `POST /compare` — asyncio parallel brief pair |
| `api/cache.py` | Pre-cached briefs for NVDA, TSLA, AMD |

## The Hard Parts (done)

### 1. Pre-synthesis conflict resolution

Before the LLM writes a single word, incoming chunks need to be classified
and contradictions surfaced explicitly:

```python
{
  "chunk": "Margins improved 2.3% QoQ...",
  "source": "10-Q filing",
  "date": "2024-10-15",
  "label": "bull_signal",
  "contradicts": ["chunk_id_7"]  # news article saying margins under pressure
}
```

The synthesis prompt then reasons *over* the contradiction, not through it.

### 2. Synthesis is a 6-call reasoning chain, not a single prompt

```
Call 0 → Detect contradiction pairs across all chunks
Call 1 → Classify each chunk: bull / bear / risk / neutral / contradicted
Call 2 → Resolve flagged contradictions — authority hierarchy, not implication
Call 3 → Generate bull section, bear section, risk section independently
Call 4 → Coherence check — flag anything appearing in both bull and bear
Call 5 → Format to final JSON schema (Contract D)
```

### 3. Key pipeline decisions

- **No RAG for demo** — web_fetch + yfinance gives sufficient signal
- **Hybrid model** — Llama-3.3-70B-Instruct-Turbo for all calls (free, fast, capable)
- **Retry logic** — exponential backoff on 502s from Bright Data
- **yfinance chunks** — pre-labeled at authority 0.90, injected regardless of web fetch quality
- **Adil's enricher** — wired via `asyncio.to_thread` (sync→async safe)

---

## Roadmap

### Phase 1 — Foundation ✅
- [x] `mock/nvda_chunks.py` — 16 chunks, 7 contradiction pairs, stress-tested
- [x] Synthesis prompt iteration on mock data
- [x] Schema [D] confirmed with Adil — locked

### Phase 2 — Core Implementation ✅
- [x] `pre_synthesis.py` — dedup, recency filter, sentiment counting
- [x] `synthesis.py` — 6-call reasoning chain, hybrid model tiering
- [x] End-to-end test on mock data — 5/7 contradictions caught

### Phase 3 — Integration ✅
- [x] `web_fetch.py` — SERP + Web Unlocker, full article fetch, density/verb filters, retry on 502
- [x] `router.py` — earnings date lookup, recency mode, source priority
- [x] `graph.py` — LangGraph pipeline, conditional edges, graceful fallbacks
- [x] `yfinance.py` — pre-labeled chunks + context string injected into Call 3
- [x] Tested NVDA, TSLA, AMD — all three producing valid enriched briefs
- [x] Stable across 3 consecutive runs (10/14/10 chunks despite 502s)

### Phase 4 — API & Demo Prep ✅
- [x] `api/main.py` — FastAPI app, CORS, lifespan, health check
- [x] `api/routes/brief.py` — `POST /brief/{ticker}` with cache check first
- [x] `api/routes/compare.py` — `POST /compare` via `asyncio.gather`
- [x] `api/cache.py` — pre-run NVDA, TSLA, AMD and store enriched briefs
- [x] Error handling — Bright Data fallback, synthesis failure response
- [x] Latency profiling — full enriched brief < 35s
- [x] Demo run clean ×3

---

## Open Issues (flag to teammates)

### Adil
- [ ] Historical matches returning NVDA data for TSLA and AMD — pattern matcher not ticker-scoped
- [ ] Scenario summaries copy-pasting signal text verbatim — needs analyst prose rewrite
- [ ] Bull/bear confidence miscalibrated (equal scores on strongly bullish setups)

---

## Cut Entirely
- ~~`rag_node.py`~~ — no DB for demo, web_fetch gives sufficient signal
- ~~`schema.sql` / `seed_db.py` / `embedder.py`~~ — Ilyas's scope, skipped
- ~~`sec_filings.py`~~ — not demo-critical
- ~~`earnings_calendar.py`~~ — not needed
- ~~`hiring_signals.py`~~ — LinkedIn scraping, too slow
- ~~`polygon.py`~~ — duplicates web_fetch
- ~~`monitor.py` / `scheduler.py`~~ — background jobs, demo doesn't need
- ~~`transcript_cleaner.py`~~ — SA paywall blocking