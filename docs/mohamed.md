# Mohamed — Retrieval Brain & Pipeline

> [!IMPORTANT]
> Scope revised: one person, demo-focused. RAG skipped for demo. Pipeline is web_fetch → pre_synthesis → synthesis → API.

| File | Responsibility |
|------|---------------|
| `agent/graph.py` | Wires web_fetch → pre_synthesis → synthesis |
| `agent/nodes/web_fetch.py` | SERP API + Web Unlocker — parallel async calls ✅ |
| `agent/nodes/pre_synthesis.py` | Dedup, recency weighting, contradiction flagging ✅ |
| `agent/nodes/synthesis.py` | 5-step reasoning chain → structured JSON brief ✅ |
| `intelligence/yfinance.py` | EPS, revenue, P/E — injects real numbers into synthesis |
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

### 2. Synthesis is a reasoning chain, not a single prompt

```
Call 0 → Detect contradiction pairs across all chunks
Call 1 → Classify each chunk: bull / bear / risk / neutral / contradicted
Call 2 → Resolve flagged contradictions — pick the more authoritative source
Call 3 → Generate bull section, bear section, risk section independently
Call 4 → Coherence check — flag anything appearing in both bull and bear
Call 5 → Format to final JSON schema (Contract D)
```

## Roadmap

### Phase 1 — Foundation ✅
- [x] `mock/nvda_chunks.py` with realistic contradicting chunks
- [x] Synthesis prompt iteration on mock data
- [x] Confirm schema [D] with Adil — no changes after this

### Phase 2 — Core Implementation ✅
- [x] `pre_synthesis.py` — dedup, recency weight, contradiction flag
- [x] `synthesis.py` — 5-call reasoning chain
- [x] Test synthesis on mock pre-synthesis output

### Phase 3 — Integration (demo-focused, no RAG)

**Today**
- [x] `web_fetch.py` — SERP API + Web Unlocker, full article fetch, filters applied
- [x] `graph.py` — wire web_fetch → pre_synthesis → synthesis, test NVDA live brief
- [x] `yfinance.py` — EPS, revenue, P/E injected into synthesis context

**Tomorrow**
- [ ] `api/main.py` + `api/routes/brief.py` — `POST /brief/{ticker}`
- [ ] `api/routes/compare.py` — `asyncio.gather` on two parallel runs
- [ ] `api/cache.py` — pre-run NVDA, TSLA, AMD and store results

### Phase 4 — Demo Prep
- [ ] Error handling + fallbacks for Bright Data failures
- [ ] Latency profiling — full brief < 35s
- [ ] Demo run clean ×3

---

**Cut entirely**
- ~~`rag_node.py`~~ — no DB for demo, web_fetch gives sufficient signal
- ~~`schema.sql` / `seed_db.py` / `embedder.py`~~ — Ilyas's scope, skipped
- ~~`sec_filings.py`~~ — not demo-critical
- ~~`earnings_calendar.py`~~ — not needed
- ~~`hiring_signals.py`~~ — LinkedIn scraping, too slow
- ~~`polygon.py`~~ — duplicates web_fetch
- ~~`monitor.py` / `scheduler.py`~~ — background jobs, demo doesn't need
- ~~`transcript_cleaner.py`~~ — SA paywall blocking
