# Mohamed — Retrieval Brain & Personal Build Guide

> [!IMPORTANT]
> The hardest parts live here. Everything downstream depends on brief quality.

> **One sentence:** I take a ticker like `NVDA`, fetch live data, retrieve stored documents,
> think through everything, and return a clean JSON brief for Adil to enrich.

---

## The Big Picture — Data Flow

```
[User types: NVDA]
       │
       ▼
  FastAPI (api/)
       │
       ▼
  LangGraph Agent (agent/)
       │
       ├── 1. Router        → decides what sources to use
       ├── 2. Web Fetch     → grabs live news + transcripts from Bright Data
       ├── 3. RAG Node      → searches the database for stored docs
       ├── 4. Pre-Synthesis → cleans, labels, flags contradictions
       └── 5. Synthesis     → thinks + writes the final JSON brief
       │
       ▼
  Raw Brief JSON  ──────────────────────────────────► Adil enriches it
                                                            │
  FastAPI receives enriched brief ◄─────────────────────────┘
       │
       ▼
  Response to user
```

---

## File Map — What I Own

```
earningsedge/
│
├── api/
│   ├── main.py              ← FastAPI app entry point
│   ├── cache.py             ← Pre-cached NVDA/TSLA/AMD for demo
│   └── routes/
│       ├── brief.py         ← POST /brief/{ticker}
│       ├── compare.py       ← POST /compare  (runs two tickers in parallel)
│       └── signals.py       ← GET /signals/{ticker}
│
├── agent/
│   ├── graph.py             ← Wires all nodes together into one pipeline
│   └── nodes/
│       ├── router.py        ← Node 1: decides which sources to fetch
│       ├── web_fetch.py     ← Node 2: calls Bright Data APIs
│       ├── rag_node.py      ← Node 3: queries the database
│       ├── pre_synthesis.py ← Node 4: cleans + labels chunks
│       └── synthesis.py     ← Node 5: produces the final JSON brief
│
├── rag/
│   ├── retriever.py         ← pgvector + BM25 hybrid search
│   ├── reranker.py          ← Cross-encoder reranking scoped to ticker
│   └── recency.py           ← Hard date filters per content type
│
└── mock/
    └── nvda_chunks.py       ← Fake data to test synthesis before DB is ready
```

---

## Every File — Input → What It Does → Output

---

### `mock/nvda_chunks.py`
**What it is:** Fake hardcoded data. Not part of production. Just for testing.

**Input:** Nothing. It's a static file.

**Output:**
```python
chunks = [
    {
        "chunk": "NVDA data center revenue grew 409% YoY.",
        "source": "10-Q filing",
        "date": "2024-10-15",
        "source_type": "filing"
    },
    {
        "chunk": "Gross margins hit record 74.6% this quarter.",
        "source": "earnings transcript",
        "date": "2024-10-20",
        "source_type": "transcript"
    },
    {
        "chunk": "Analysts flagging potential margin compression in H2 2025.",
        "source": "Seeking Alpha",
        "date": "2024-11-01",
        "source_type": "news"
    },
    # Add contradicting chunks on purpose to test pre_synthesis
]
```

**Build this first.** Everything else runs on this until Ilyas's DB is ready.

---

### `agent/nodes/pre_synthesis.py`
**What it is:** The cleaning step. Runs before any LLM writing happens.

> [!IMPORTANT]
> Skip this and your brief will be internally inconsistent in ways that are
> hard to spot during the demo but obvious to any finance reader.

**Input:** Raw list of chunks from web fetch + RAG
```python
[
    {
        "chunk": "NVDA gross margins hit record 74.6%.",
        "source": "earnings transcript",
        "date": "2024-10-20",
        "source_type": "transcript"
    },
    {
        "chunk": "Gross margins under pressure as competition intensifies.",
        "source": "Reuters",
        "date": "2024-11-03",
        "source_type": "news"
    }
]
```

**What it does:**
1. Deduplicates near-identical chunks
2. Applies recency weights (older = less weight)
3. Labels each chunk: `bull_signal / bear_signal / risk / neutral`
4. Detects contradictions between chunks and flags them with `contradicts` IDs

**Output:** Labeled + flagged chunks ready for synthesis
```python
[
    {
        "chunk": "NVDA gross margins hit record 74.6%.",
        "source": "earnings transcript",
        "date": "2024-10-20",
        "source_type": "transcript",
        "label": "bull_signal",
        "recency_weight": 0.95,
        "contradicts": ["chunk_id_2"]   # ← flags the Reuters chunk
    },
    {
        "chunk": "Gross margins under pressure as competition intensifies.",
        "source": "Reuters",
        "date": "2024-11-03",
        "source_type": "news",
        "label": "bear_signal",
        "recency_weight": 0.80,
        "contradicts": ["chunk_id_1"]
    }
]
```

The synthesis prompt then reasons *over* the contradiction, not through it.

---

### `agent/nodes/synthesis.py`
**What it is:** The brain. 5 sequential LLM calls that produce the final brief.

> One prompt will not produce analyst-quality output. Five calls will.
> Start building this early with mock context before retrieval is wired.

**Input:** Labeled chunks from `pre_synthesis.py`

**The 5 calls:**

| Call | What you send the LLM | What you get back |
|------|----------------------|-------------------|
| 1 | All chunks → "classify each as bull/bear/risk/neutral/contradicted" | Each chunk gets a confirmed label |
| 2 | Flagged contradictions → "which source wins and why?" | Resolution text per contradiction |
| 3 | Classified chunks → "write bull section, bear section, risk section independently" | Three sections of text |
| 4 | All three sections → "does anything appear in both bull and bear? fix it" | Cleaned, coherent sections |
| 5 | Everything → "format into this exact JSON schema" | Final raw brief JSON |

**Output:** The raw brief JSON — what you hand to Adil
```json
{
  "ticker": "NVDA",
  "brief_id": "uuid",
  "generated_at": "2024-05-22T10:00:00Z",
  "bull_signals": [
    {
      "text": "Data center revenue grew 400% YoY.",
      "source_id": "source-uuid-1",
      "source_type": "filing"
    }
  ],
  "bear_signals": [
    {
      "text": "Gross margins dipped 0.5% due to supply chain costs.",
      "source_id": "source-uuid-3",
      "source_type": "transcript"
    }
  ],
  "risk_flags": [
    "US export restrictions to China affecting ~10% of revenue."
  ],
  "analyst_sentiment": "bullish",
  "comparable_quarter": "Q2 2023",
  "sources": [...],
  "contradictions_resolved": [
    {
      "claim_a": "Reuters: margins under pressure.",
      "claim_b": "Transcript: margins hit record 74.6%.",
      "resolution": "Prioritized earnings transcript as primary management source."
    }
  ]
}
```

---

### `agent/nodes/web_fetch.py`
**What it is:** Fetches live data from the internet using Bright Data. Both calls run in parallel.

**Input:**
```python
{
    "ticker": "NVDA",
    "days_to_earnings": 7
}
```

**What it does (in parallel via asyncio):**
- SERP API → searches for latest news about the ticker
- Web Unlocker → scrapes Seeking Alpha transcripts

**Output:** Raw text chunks with metadata
```python
[
    {
        "chunk": "NVDA reports record data center revenue...",
        "source": "https://seekingalpha.com/...",
        "date": "2024-11-01",
        "source_type": "news"
    },
    ...
]
```

---

### `agent/nodes/rag_node.py`
**What it is:** Searches Ilyas's database for stored documents relevant to the ticker.

**Input:**
```python
{
    "ticker": "NVDA",
    "query": "NVDA earnings revenue margins guidance"
}
```

**What it does:**
- Runs hybrid search: pgvector (semantic) + BM25 (keyword)
- Applies recency filters (news: 30 days, filings: 180 days, transcripts: 365 days)
- Boosts ticker symbol matches 3x so AMD results don't pollute NVDA queries

**Output:** Retrieved chunks (same shape as web_fetch output)
```python
[
    {
        "chunk": "From the 10-Q: operating expenses increased 12%...",
        "source": "https://sec.gov/...",
        "date": "2024-10-15",
        "source_type": "filing"
    },
    ...
]
```

---

### `agent/nodes/router.py`
**What it is:** Decides which sources to prioritize based on how close earnings are.

**Input:**
```python
{
    "ticker": "NVDA",
    "days_to_earnings": 7   # Ilyas provides this
}
```

**Logic:**
```
7+ days to earnings  → prioritize filings + transcripts (historical depth)
< 7 days             → prioritize live news (recency matters most)
< 2 days             → news only, maximum recency filter
```

**Output:**
```python
{
    "fetch_web": True,
    "fetch_rag": True,
    "recency_mode": "aggressive",   # or "standard" or "historical"
    "sources_priority": ["news", "transcript", "filing"]
}
```

---

### `agent/graph.py`
**What it is:** Wires all 5 nodes together into one LangGraph pipeline.

**Input:** Ticker string `"NVDA"`

**What it does:** Connects nodes in order:
```
router → web_fetch → rag_node → pre_synthesis → synthesis
```

**Output:** Raw brief JSON (ready for Adil)

> If LangGraph feels too heavy during the hackathon, a simple `asyncio` chain
> works fine and is faster to debug.

---

### `rag/retriever.py`
**What it is:** The actual search logic used by `rag_node.py`.

**Input:**
```python
query = "NVDA margins revenue guidance"
ticker = "NVDA"
```

**What it does:**
- pgvector search → semantic similarity over stored embeddings
- BM25 search → keyword match, ticker symbol boosted 3x
- RRF fusion → combines both ranked lists into one final ranking

**Output:** Top-N ranked chunks

---

### `rag/reranker.py`
**What it is:** A cross-encoder that re-scores the top chunks from `retriever.py`.

**Input:** Query + list of candidate chunks from retriever

**What it does:** Cross-encoder scores each chunk against the query — more accurate
than vector similarity alone, run only on the top candidates to stay fast

**Output:** Same chunks, re-sorted by relevance score

---

### `rag/recency.py`
**What it is:** Hard date filter applied before retrieval ranking.

**Rules:**
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

**Input:** Chunk with a date and source_type field

**Output:** True (keep) or False (discard before ranking)

---

### `api/routes/brief.py`
**What it is:** The main endpoint.

**Request:**
```
POST /brief/NVDA
```

**What it does:**
1. Checks `cache.py` first — if cached, return immediately
2. Otherwise, runs the full LangGraph agent pipeline
3. Sends raw brief to Adil's enricher
4. Returns the full enriched brief

**Response:** Raw brief JSON + Adil's scenarios + historical matches combined

---

### `api/routes/compare.py`
**What it is:** Runs two tickers in parallel and returns both briefs.

**Request:**
```
POST /compare
Body: {"tickers": ["NVDA", "AMD"]}
```

**What it does:**
```python
results = await asyncio.gather(
    run_pipeline("NVDA"),
    run_pipeline("AMD")
)
```

**Response:** Two enriched briefs side by side

---

### `api/routes/signals.py`
**What it is:** Lightweight endpoint — returns just the signals, no full brief.

**Request:**
```
GET /signals/NVDA
```

**Response:**
```json
{
  "ticker": "NVDA",
  "bull_signals": [...],
  "bear_signals": [...],
  "risk_flags": [...]
}
```

---

### `api/cache.py`
**What it is:** Pre-run pipeline results stored for the demo. Real output, just saved ahead of time.

```python
CACHE = {
    "NVDA": { ...full enriched brief... },
    "TSLA": { ...full enriched brief... },
    "AMD":  { ...full enriched brief... },
}

def get_cached(ticker: str):
    return CACHE.get(ticker.upper(), None)
```

**Why it exists:** Demo insurance. If anything breaks live, these three always work.
Cache is the fallback, not the cheat.

---

## What Ilyas Gives Me

| What | How I use it |
|------|-------------|
| `DATABASE_URL` | Connect in `rag/retriever.py` |
| DB schema | Know which tables/columns to query |
| Signal-ready ping | Tells me when new data is ingested for a ticker |

## What I Give Adil

The raw brief JSON from `synthesis.py`.
He returns the enriched brief with scenarios + historical matches appended.

---

## Build Order

```
Step 1  → mock/nvda_chunks.py          (fake data, 10 mins)
Step 2  → agent/nodes/pre_synthesis.py (label + flag chunks)
Step 3  → agent/nodes/synthesis.py     (5-call reasoning chain)
          ↑ Test steps 1–3 together on mock data. Don't move on until
            the output reads like something an analyst actually wrote.
Step 4  → rag/recency.py               (simple date filter)
Step 5  → rag/retriever.py             (pgvector + BM25 + RRF)
Step 6  → rag/reranker.py              (cross-encoder)
Step 7  → agent/nodes/rag_node.py      (uses retriever + reranker)
Step 8  → agent/nodes/web_fetch.py     (Bright Data calls, async parallel)
Step 9  → agent/nodes/router.py        (source selection logic)
Step 10 → agent/graph.py               (wire all nodes together)
          ↑ Milestone: NVDA → raw brief JSON end to end
Step 11 → api/routes/brief.py          (main endpoint)
Step 12 → api/routes/compare.py        (parallel endpoint)
Step 13 → api/routes/signals.py        (signals endpoint)
Step 14 → api/main.py                  (mount all routes)
Step 15 → api/cache.py                 (pre-run NVDA/TSLA/AMD, store results)
```

---

## Roadmap

### Phase 1 — Foundation
- [ ] `mock/nvda_chunks.py` with realistic contradicting chunks
- [ ] Synthesis prompt iteration on mock data (goal: brief that reads like an analyst wrote it)
- [ ] Confirm schema [D] with Adil — no changes after this

### Phase 2 — Core Implementation
- [ ] `pre_synthesis.py` — dedup, recency weight, contradiction flag
- [ ] `synthesis.py` — 5-call reasoning chain
- [ ] Test synthesis end-to-end on mock pre-synthesis output

### Phase 3 — Integration
- [ ] `web_fetch.py` — SERP API + Web Unlocker (async parallel)
- [ ] `rag_node.py` — recency filters + ticker boosting
- [ ] Wire full pipeline: router → fetch → rag → pre_synthesis → synthesis
- [ ] **Milestone:** NVDA → raw brief JSON

### Phase 4 — Full Pipeline
- [ ] FastAPI routes: `/brief`, `/compare`, `/signals`
- [ ] `/compare`: `asyncio.gather` on two parallel pipeline runs
- [ ] Call Adil's enricher after synthesis — receive enriched brief [E]
- [ ] MCP Server integration
- [ ] Integration test with both teammates

### Phase 5 — Polish & Demo Prep
- [ ] Error handling + fallbacks for Bright Data failures
- [ ] Graceful DB fallback (if ticker has no historical data)
- [ ] `cache.py` — pre-run and store NVDA, TSLA, AMD
- [ ] Latency profiling — full enriched brief < 35s
- [ ] Demo run clean ×3

---

## The One Rule

> Build and test synthesis on mock data **before** wiring anything.
> A pipeline producing a bad brief faster is worthless.
