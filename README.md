# EarningsEdge

> **Bright Data AI Builder Weekend** · Track 2: Finance & Market Intelligence
>
> Autonomous pre-earnings intelligence platform. Ticker in — grounded multi-layer
> brief out. Built on a production RAG pipeline with live web data via Bright Data.

---

## Table of Contents

- [What It Does](#what-it-does)
- [Architecture](#architecture)
- [Team & Ownership](#team--ownership)
- [The Hard Parts](#the-hard-parts)
- [Integration Points](#integration-points)
- [Data Contracts](#data-contracts)
- [Execution Strategy](#execution-strategy)
- [Roadmap](#roadmap)
- [Bright Data Tools](#bright-data-tools)
- [Stack](#stack)
- [Quick Start](#quick-start)

---

## What It Does

**Input:** Stock ticker — `NVDA`, `TSLA`, `AMD`

**Output:** Three-layer intelligence package:

```
Layer 1 — Raw Brief (Mohamed)
  Bull signals, bear signals, risk flags
  Grounded in live web data + SEC filings + transcripts
  Source-cited, contradiction-resolved

Layer 2 — Scenario Engine (Adil)
  Bull / Base / Bear cases
  Confidence from signal counting, not LLM gut feel
  Key assumptions + triggers per scenario

Layer 3 — Historical Pattern Match (Adil)
  2–3 most similar past pre-earnings setups from DB
  "This setup resembles Q2 2023 — here is what happened"
  Semantic similarity over stored historical briefs
```

**Demo:** NVDA in under 35 seconds. NVDA vs AMD comparison in under 45 seconds.
Pre-cached. Bulletproof.

---

## Architecture

```mermaid
graph TD
    classDef mohamed fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#000;
    classDef adil fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000;
    classDef ilyas fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:#000;
    
    API1("POST /brief/{ticker}"):::mohamed
    API2("POST /compare"):::mohamed
    API3("GET  /signals/{ticker}"):::mohamed
    
    FastAPI["FastAPI (Mohamed)"]:::mohamed
    API1 --> FastAPI
    API2 --> FastAPI
    API3 --> FastAPI
    
    subgraph LangGraph Agent [LangGraph Agent Mohamed]
        direction TB
        Router["Router Node"]:::mohamed
        WebFetch["Web Fetch Node<br/>(SERP API & Web Unlocker)"]:::mohamed
        RAG["RAG Node<br/>(pgvector, BM25, RRF, Cross-encoder)"]:::mohamed
        PreSynth["Pre-Synthesis Node<br/>(Dedup, recency, flag contradictions)"]:::mohamed
        Synth["Synthesis Node<br/>(Reasoning chain to JSON)"]:::mohamed
        
        Router --> WebFetch
        WebFetch --> RAG
        RAG --> PreSynth
        PreSynth --> Synth
    end
    
    FastAPI --> Router
    
    subgraph Intelligence Layer [Intelligence Layer Adil]
        direction TB
        Scenario["Scenario Engine<br/>(Bull/Bear signals to confidence %)"]:::adil
        Pattern["Historical Pattern Matcher<br/>(Cosine sim on past briefs)"]:::adil
    end
    
    Synth -- raw brief JSON --> Intelligence Layer
    
    subgraph Data Layer [Data Layer Ilyas]
        direction TB
        Scrapers["Scrapers<br/>(Earnings, Filings, LinkedIn, Transcripts)"]:::ilyas
        DB[("DB (PostgreSQL & pgvector)")]:::ilyas
        Jobs["Jobs<br/>(Monitor, Embed, Ingest)"]:::ilyas
    end
    
    Intelligence Layer -- enriched brief --> FastAPI
    
    Data Layer -. data flow .-> LangGraph Agent
    Data Layer -. data flow .-> Intelligence Layer
```

### Parallelization — Designed From Day One

```mermaid
gantt
    title Parallelization Timeline (~34s Total)
    dateFormat  mm:ss
    axisFormat  %M:%S
    
    section Data Fetch
    SERP API call           :a1, 00:00, 8s
    Web Unlocker call       :a2, 00:00, 8s
    pgvector retrieval      :a3, 00:00, 8s
    
    section Fusion
    Pre-synthesis & RAG     :a4, 00:08, 4s
    
    section Synthesis
    Reasoning chain         :a5, 00:12, 12s
    
    section Intelligence
    Scenario Engine         :a6, 00:24, 10s
    Pattern Match           :a7, 00:24, 10s
```

---

## Team & Ownership

This project is built by three people, with strict data contracts between layers to allow parallel development during the hackathon. Detailed responsibilities, technical challenges, and roadmaps are broken out into individual documents:

- [Mohamed — Retrieval Brain & Agent](docs/mohamed.md)
- [Ilyas — Data Nervous System & ETL](docs/ilyas.md)
- [Adil — Intelligence Amplifier & Scenarios](docs/adil.md)

---

## Integration Points

```
Ilyas                Mohamed               Adil
    │                        │                       │
    │──[A] DB_URL + schema──▶│                       │
    │                        │                       │
    │──[B] transcripts ──────┼──────────────────────▶│
    │   table direct read    │   (T3 reads DB direct) │
    │                        │                       │
    │──[C] signal-ready ────▶│                       │
    │   ping on ingest       │                       │
    │                        │                       │
    │                        │──[D] raw brief ───────▶│
    │                        │   JSON                 │
    │                        │                       │
    │                        │◀─[E] enriched brief───│
    │                        │                       │
    │◀─[F] watchlist add─────┼───────────────────────│
    │   new ticker           │                       │
```

---

## Data Contracts

### [D] Raw Brief — Mohamed → Adil

```python
{
  "ticker": "NVDA",
  "brief_id": "uuid",
  "generated_at": "iso-timestamp",
  "bull_signals": [
    {"text": "string", "source_id": "uuid", "source_type": "filing|news|transcript"}
  ],
  "bear_signals": [
    {"text": "string", "source_id": "uuid", "source_type": "string"}
  ],
  "risk_flags": ["string"],
  "analyst_sentiment": "bullish|neutral|bearish",
  "comparable_quarter": "string",
  "sources": [
    {"id": "uuid", "url": "string", "type": "string", "date": "iso", "authority": 0.9}
  ],
  "contradictions_resolved": [
    {"claim_a": "string", "claim_b": "string", "resolution": "string"}
  ]
}
```

### [E] Enriched Brief — Adil → Mohamed

```python
{
  "scenarios": {
    "bull":  {"summary": "string", "confidence": 0.38, "drivers": ["string"]},
    "base":  {"summary": "string", "confidence": 0.42, "drivers": ["string"]},
    "bear":  {"summary": "string", "confidence": 0.20, "risks":   ["string"]}
  },
  "historical_matches": [
    {
      "quarter": "Q2 2023",
      "similarity_score": 0.87,
      "setup_summary": "string",
      "outcome": "string",
      "return_5d": "+4.2%"
    }
  ]
}
```

---

## Execution Strategy

### Phase 1 — Lock Before Building

- [ ] All three agree on schemas [D] and [E] — write them down, no changes after
- [ ] Ilyas: DB running, schema applied, DB_URL shared
- [ ] Mohamed: Synthesis prompt iteration on mock data — not wiring, just prompting
- [ ] Adil: Enricher stub that accepts [D] and returns [E] shape with mock data

> [!WARNING]
> **Rule: do not wire before the prompt works. Do not wire before the schema is locked.**

### Demo Safety

Pre-run full pipeline on NVDA, TSLA, AMD once everything connects.
Store enriched briefs in `api/cache.py`. Demo these three from cache.
Live pipeline still runs for any other ticker — judges can test it.
Cache is the fallback, not the cheat.

---

## Future Optimizations (Low-Hanging Fruit)

To make the platform **faster** and **better** without requiring extensive research or heavy re-architecture, we can implement the following easy wins:

### Speed Optimizations
- **Parallelize Intelligence Layer**: Don't wait for final text synthesis. Pass the intermediate classified chunks from `pre_synthesis.py` directly to the Scenario Engine. This allows the synthesis and intelligence layers to run concurrently, cutting execution time from ~34s to ~24s.
- **Model Tiering**: Use a blazingly fast model (like Claude 3 Haiku or LLaMA-3 via Groq) for the routing, classification, and coherence steps. Reserve the slower, heavier models (GPT-4o/Claude 3.5 Sonnet) exclusively for the final text generation step.
- **SSE Streaming**: Use FastAPI `StreamingResponse` to stream the JSON chunks to the frontend as they resolve. The user sees the raw brief load instantly, masking the remaining backend latency.

### Quality Optimizations
- **Quantitative Grounding**: Add a quick API call to yFinance/Polygon to pull hard numbers (Consensus EPS, Forward P/E) and inject them into Adil's Scenario Engine to make the confidence scores mathematically grounded.
- **Automated Reflection**: Add a conditional edge in LangGraph after the Coherence check. If the check fails (e.g., a bear signal ends up in the bull section), trigger a fast self-correction prompt before returning the payload to the user.

---

## Roadmap

For detailed daily schedules and checklists, see the individual team member documents:
- [Mohamed's Roadmap](docs/mohamed.md#roadmap)
- [Ilyas's Roadmap](docs/ilyas.md#roadmap)
- [Adil's Roadmap](docs/adil.md#roadmap)

---

## Bright Data Tools

| Tool | Owner | Used In |
|------|-------|---------|
| **SERP API** | Mohamed | `web_fetch.py` — live news per ticker |
| **Web Unlocker** | Mohamed | `web_fetch.py` — Seeking Alpha transcripts |
| **MCP Server** | Mohamed | LangGraph agent web context |
| **Web Scraper API** | Ilyas | Earnings calendar, SEC filings, LinkedIn, transcripts |

---

## Stack

```
Backend         FastAPI, Python 3.11+
Agent           LangGraph, LangChain
Storage         PostgreSQL, pgvector, SQLAlchemy
RAG             LlamaIndex, BM25, RRF fusion, cross-encoder reranking
Data            Bright Data (4 tools), yFinance, Polygon.io
Infrastructure  Docker
LLM             OpenAI GPT-4o / Anthropic Claude
```

---

## Quick Start

```bash
git clone https://github.com/your-team/earningsedge
cd earningsedge
pip install -r requirements.txt

cp .env.example .env
# BRIGHT_DATA_API_KEY=
# OPENAI_API_KEY=
# DATABASE_URL=postgresql://user:pass@localhost:5432/earningsedge

docker-compose up -d postgres
python data/db/migrate.py
uvicorn api.main:app --reload

# Test
curl -X POST http://localhost:8000/brief/NVDA
```
