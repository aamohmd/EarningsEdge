# Adil — Intelligence Amplifier

> [!NOTE]
> Two components, both done properly.
> Runs after Mohamed's brief is produced. Zero extra web calls — runs on stored data.

| File | Responsibility |
|------|---------------|
| `intelligence/enricher.py` | Orchestrator — runs both agents, returns enriched brief |
| `intelligence/scenario/signal_counter.py` | Count + weight bull/bear signals from brief |
| `intelligence/scenario/source_authority.py` | Score each source: recency × authority |
| `intelligence/scenario/generator.py` | Generate Bull / Base / Bear from weighted signals |
| `intelligence/scenario/engine.py` | Wire counting → weighting → generation |
| `intelligence/history/embedder.py` | Embed current brief for similarity search |
| `intelligence/history/matcher.py` | Cosine sim over historical briefs in DB |
| `intelligence/history/outcome.py` | Retrieve what happened after each matched setup |
| `intelligence/history/pattern_agent.py` | Wire match → outcome → narrative |

## The Hard Parts

### Confidence scores must be derived, not generated

LLM-generated confidence percentages are not defensible.
A judge will ask. The answer must be a formula:

```python
def compute_confidence(brief: dict, sources: list) -> dict:
    bull_count = len(brief["bull_signals"])
    bear_count = len(brief["bear_signals"])
    total = bull_count + bear_count + 1e-9

    raw_bull = bull_count / total
    raw_bear = bear_count / total

    # Weight by source authority (filing > transcript > news)
    authority_weights = {
        "filing": 1.4,
        "transcript": 1.2,
        "news": 0.9,
        "hiring": 0.8,
    }
    # Weight by recency (exponential decay, 30-day half-life)
    recency_weights = [exp_decay(s["date"]) for s in sources]

    bull_conf = weighted_adjust(raw_bull, authority_weights, recency_weights)
    base_conf = 1 - bull_conf - bear_conf
    bear_conf = weighted_adjust(raw_bear, authority_weights, recency_weights)

    return {"bull": bull_conf, "base": base_conf, "bear": bear_conf}
```

Even a rough version of this is defensible. Pure LLM output is not.

## Roadmap

### Phase 1: Foundation
- [ ] Read schema [D] from Mohamed — lock it
- [ ] `enricher.py` stub — accepts [D], returns [E] with mock data
- [ ] `signal_counter.py` — count bull/bear from brief signals

### Phase 2: Core Implementation
- [ ] `source_authority.py` — score by type + recency decay
- [ ] confidence formula — signal count × authority weight
- [ ] `generator.py` — Bull / Base / Bear from weighted signals
- [ ] **Test**: scenario engine on mock [D] 

### Phase 3: Integration
- [ ] `history/embedder.py` — embed current brief
- [ ] **MOCK DATA**: Manually write 4-6 historical brief JSONs for NVDA/AMD and insert into Supabase to solve the cold-start problem.
- [ ] `history/matcher.py` — cosine sim over historical briefs DB
- [ ] `history/outcome.py` — retrieve stored outcomes per match
- [ ] `pattern_agent.py` — match → outcome → narrative
- [ ] **Test**: pattern matcher on 2 pre-loaded (mocked) historical briefs 

### Phase 4: Full Pipeline
- [ ] Wire `enricher.py`: `scenario_engine` + `pattern_agent` → [E]
- [ ] Integration test with Mohamed's live brief output
- [ ] Edge case: < 3 historical briefs in DB → graceful fallback
- [ ] Validate [E] schema matches what Mohamed expects

### Phase 5: Polish & Demo Prep
- [ ] Confidence score sanity check — do percentages sum to 1.0
- [ ] Historical match quality check — similarity threshold tuning
- [ ] Edge case: ticker with no historical briefs → skip cleanly
- [ ] **End-to-end**: raw brief in → enriched brief out < 12s 
