"""
engine.py — Scenario Engine Pipeline (Adil)

PURPOSE:
    Wires the three scenario components into a single callable pipeline:
        signal_counter → source_authority → generator

    This is the convenience wrapper that enricher.py calls.

INPUT:
    raw_brief (dict) — The [D] Raw Brief from Mohamed

OUTPUT:
    scenarios (dict) — The "scenarios" portion of [E]:
        {
            "bull":  {"summary": "string", "confidence": float, "drivers": ["string"]},
            "base":  {"summary": "string", "confidence": float, "drivers": ["string"]},
            "bear":  {"summary": "string", "confidence": float, "risks":   ["string"]}
        }

PIPELINE:
    1. signal_counter.count_signals(raw_brief) → signal_counts
    2. source_authority.score_sources(raw_brief["sources"]) → scored_sources
    3. generator.generate_scenarios(signal_counts, scored_sources, raw_brief) → scenarios

NOTES:
    - Single function call: run_scenario_engine(raw_brief) -> scenarios
    - All sub-steps are pure functions — easy to unit test individually
"""
from scenarios_historicalPattern.scenario.signal_counter import count_signals
from scenarios_historicalPattern.scenario.source_authority import score_sources
from scenarios_historicalPattern.scenario.generator import generate_scenarios

def run_scenario_engine(raw_brief: dict) -> dict:

    if not isinstance(raw_brief, dict):
        raise ValueError("raw_brief must be a dictionary")

    # Validate required fields for the raw brief [D]
    required_fields = ["ticker", "bull_signals", "bear_signals", "risk_flags", "sources", "generated_at"]
    for field in required_fields:
        if field not in raw_brief:
            raise KeyError(f"Missing required field '{field}' in raw_brief")

    # 1. Count and categorize bull/bear signals
    signal_counts = count_signals(raw_brief)

    # 2. Score each source based on type authority and recency decay
    scored_sources = score_sources(raw_brief.get("sources", []), raw_brief.get("generated_at"))

    # 3. Generate investment scenarios with formula-based confidence scores
    scenarios = generate_scenarios(signal_counts, scored_sources, raw_brief)

    return scenarios
