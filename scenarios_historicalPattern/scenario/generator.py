"""
generator.py — Scenario Generator (Adil)

PURPOSE:
    Generate Bull / Base / Bear investment scenarios from weighted signals.
    This is the final step in the Scenario Engine pipeline.

    The confidence scores come from a FORMULA, not from an LLM.
    This is the key differentiator — a judge can ask "where does 65% come from?"
    and the answer is a traceable calculation.

INPUT:
    signal_counts (dict) — From signal_counter.py:
        {"bull_count": int, "bear_count": int, "bull_by_source": {...}, "bear_by_source": {...}}

    scored_sources (list) — From source_authority.py:
        [{"id": "uuid", "type": "string", "combined_weight": float}]

    raw_brief (dict) — The original [D] for extracting signal text, risk flags, etc.

OUTPUT:
    scenarios (dict) — The "scenarios" portion of [E]:
        {
            "bull":  {"summary": "string", "confidence": 0.65, "drivers": ["string"]},
            "base":  {"summary": "string", "confidence": 0.25, "drivers": ["string"]},
            "bear":  {"summary": "string", "confidence": 0.10, "risks":   ["string"]}
        }

CONFIDENCE FORMULA:
    1. raw_bull = bull_count / (bull_count + bear_count)
    2. raw_bear = bear_count / (bull_count + bear_count)
    3. Apply authority weighting:  adjusted = raw × sum(authority_weights for matching sources)
    4. Apply recency weighting:   adjusted *= avg(recency_weights for matching sources)
    5. base_conf = 1.0 - bull_conf - bear_conf
    6. Confidence scores MUST always sum to 1.0

NOTES:
    - Summaries can use an LLM to generate readable text from the signals
    - Drivers/risks are extracted from the bull/bear signal texts
    - Edge case: if all signals are bull (or all bear), clamp base to minimum 0.05
"""

# TODO: Define compute_confidence(signal_counts, scored_sources) -> dict
# TODO: Define generate_scenarios(signal_counts, scored_sources, raw_brief) -> dict
# TODO: Implement the confidence formula (signal count × authority × recency)
# TODO: Extract drivers from bull_signals text
# TODO: Extract risks from bear_signals text + risk_flags
# TODO: Generate readable summaries for each scenario
# TODO: Ensure confidence scores always sum to 1.0
