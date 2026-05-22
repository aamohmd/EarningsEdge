# Ilyas — Data Nervous System

> [!CAUTION]
> Owns everything upstream of retrieval — including transcript cleaning.
> If this layer produces dirty data, every other layer breaks.

| File | Responsibility |
|------|---------------|
| `data/scrapers/earnings_calendar.py` | Upcoming earnings dates — Web Scraper API |
| `data/scrapers/sec_filings.py` | 10-Q / 10-K structured content — Web Scraper API |
| `data/scrapers/hiring_signals.py` | LinkedIn job postings per company — Web Scraper API |
| `data/scrapers/transcripts_raw.py` | Raw transcript HTML — Web Scraper API |
| `data/clean/transcript_cleaner.py` | **Strip HTML, normalize speakers, remove paywalls, separate Q&A from prepared remarks** |
| `data/sources/yfinance.py` | EPS, revenue, guidance, P/E |
| `data/sources/polygon.py` | News feed, options flow |
| `data/embed/embedder.py` | Chunk + embed all content → pgvector |
| `data/db/schema.sql` | Full schema: tickers, signals, filings, transcripts, briefs |
| `data/db/ingest.py` | Clean → chunk → embed → store pipeline |
| `data/jobs/monitor.py` | Background polling — watchlist every 15 min |
| `data/jobs/scheduler.py` | Cron scheduler |

## The Hard Parts

### Transcript cleaning is the hardest data task

Raw scraped transcript HTML is not parseable text. What arrives:

```html
<div class="sa-art">Q - John Smith (Morgan Stanley): Can you talk about
margins? &amp;nbsp; A - Jensen Huang: Sure, look, we&#39;re...
<span class="premium-paywall">Subscribe to read</span>...
[Operator Instructions]...
```

What Adil needs:

```json
{
  "prepared_remarks": "string — management statements only",
  "qa_section": [
    {
      "analyst": "John Smith, Morgan Stanley",
      "question": "string",
      "management_answer": "string"
    }
  ],
  "quarter": "Q3",
  "year": 2024
}
```

This parser is Ilyas's hardest task. Own it explicitly.
Do not let it fall between Ilyas and Adil.

## Roadmap

### Phase 1: Foundation
- [ ] Docker: PostgreSQL + pgvector running
- [ ] `schema.sql` applied — all tables created
- [ ] Share DB_URL + confirm schema with team [A]

### Phase 2: Core Implementation
- [ ] `earnings_calendar.py` — Bright Data Web Scraper API
- [ ] `sec_filings.py` — 10-Q/10-K via Bright Data
- [ ] `embed.py` — chunk + embed filings → pgvector
- [ ] **Test**: Mohamed queries NVDA embeddings 

### Phase 3: Integration
- [ ] `transcripts_raw.py` — raw HTML via Bright Data
- [ ] `transcript_cleaner.py` — HTML strip, speaker norm, Q&A split, paywall remove (output: structured JSON per transcript)
- [ ] Verify Adil can read transcripts table [B]
- [ ] `hiring_signals.py` — LinkedIn via Bright Data

### Phase 4: Full Pipeline
- [ ] `yfinance.py` + `polygon.py` pipelines
- [ ] `monitor.py` — background polling job
- [ ] `/internal/signal-ready` ping [C]
- [ ] Pre-load: NVDA, TSLA, AMD — 4 quarters each
- [ ] Stress test: 3 tickers simultaneously

### Phase 5: Polish & Demo Prep
- [ ] Retry logic for scraper failures
- [ ] Freshness flag: signals > 2hr marked stale
- [ ] Verify full ingestion end-to-end with both teammates
