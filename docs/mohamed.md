# Mohamed — Retrieval Brain

> [!IMPORTANT]
> The hardest parts live here. Everything downstream depends on brief quality.

| File | Responsibility |
|------|---------------|
| `agent/graph.py` | LangGraph graph definition — all nodes wired |
| `agent/nodes/router.py` | Source selection based on ticker + days to earnings |
| `agent/nodes/web_fetch.py` | SERP API + Web Unlocker — parallel async calls |
| `agent/nodes/rag_node.py` | Retrieval with recency filter + ticker boosting |
| `agent/nodes/pre_synthesis.py` | Dedup, recency weighting, contradiction flagging |
| `agent/nodes/synthesis.py` | 5-step reasoning chain → structured JSON brief |
| `rag/retriever.py` | pgvector + BM25 fusion via RRF |
| `rag/reranker.py` | Cross-encoder reranking scoped to ticker |
| `rag/recency.py` | Hard date filters per content type |
| `api/main.py` | FastAPI app |
| `api/routes/brief.py` | `POST /brief/{ticker}` |
| `api/routes/compare.py` | `POST /compare` — asyncio parallel brief pair |
| `api/routes/signals.py` | `GET /signals/{ticker}` |
| `api/cache.py` | Pre-cached enriched briefs for demo tickers |

## The Hard Parts

### 1. Pre-synthesis conflict resolution

Before the LLM writes a single word, incoming chunks need to be classified
and contradictions surfaced explicitly:

```python
# Each chunk gets a label before synthesis
{
  "chunk": "Margins improved 2.3% QoQ...",
  "source": "10-Q filing",
  "date": "2024-10-15",
  "label": "bull_signal",
  "contradicts": ["chunk_id_7"]  # news article saying margins under pressure
}
```

The synthesis prompt then reasons *over* the contradiction, not through it.
Skip this step and the brief will be internally inconsistent in ways that are
hard to spot during the demo but obvious to a finance reader.

### 2. Synthesis is a reasoning chain, not a single prompt

```
Call 1 → Classify each chunk: bull / bear / risk / neutral / contradicted
Call 2 → Resolve flagged contradictions — pick the more authoritative source
Call 3 → Generate bull section, bear section, risk section independently
Call 4 → Coherence check — flag anything appearing in both bull and bear
Call 5 → Format to final JSON schema
```

One prompt will not produce analyst-quality output. Five calls will.
Start building this early with mock context before retrieval is wired.

### 3. RAG scope needs explicit constraints for this use case

Standard similarity retrieval is wrong here. Apply before ranking:

```python
RECENCY_FILTERS = {
    "news":        timedelta(days=30),
    "filings":     timedelta(days=180),   # last 2 quarters
    "transcripts": timedelta(days=365),   # last 4 quarters
    "hiring":      timedelta(days=60),
}

# BM25 must boost ticker symbol matches
# or AMD content contaminates NVDA queries
BM25_TICKER_BOOST = 3.0
```

## Roadmap

### Phase 1 — Foundation
- [x] `mock/nvda_chunks.py` with realistic contradicting chunks
- [x] Synthesis prompt iteration on mock data (goal: brief that reads like an analyst wrote it)
- [x] Confirm schema [D] with Adil — no changes after this

### Phase 2: Core Implementation
- [x] `pre_synthesis.py` — dedup, recency weight, contradiction flag
- [x] `synthesis.py` — 5-call reasoning chain
- [x] Test synthesis on mock pre-synthesis output

### Phase 3: Integration
- [ ] `web_fetch.py` — SERP API + Web Unlocker (async parallel)
- [ ] `rag_node.py` — recency filters + ticker boosting
- [ ] Wire full pipeline: router → fetch → rag → pre_synthesis → synthesis
- [ ] **Milestone**: NVDA → raw brief JSON 

### Phase 4: Full Pipeline
- [ ] FastAPI routes: `/brief`, `/compare`, `/signals`
- [ ] `/compare`: `asyncio.gather` on two parallel runs
- [ ] Call `enricher.py` after synthesis — receive [E]
- [ ] MCP Server integration
- [ ] Integration test with both teammates

### Phase 5: Polish & Demo Prep
- [ ] Error handling + fallbacks for Bright Data failures
- [ ] Graceful DB fallback (e.g., if ticker has no historical data)
- [ ] `cache.py` — pre-run and store NVDA, TSLA, AMD
- [ ] Latency profiling — full enriched brief < 35s
- [ ] Demo run clean ×3
