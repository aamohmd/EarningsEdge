"""
scenarios_historicalPattern/scenario/engine.py

Wires the three scenario components into a single callable:
  signal_counter → source_authority → generator

Input:  raw_brief (dict) — Contract [D]
Output: scenarios (dict) — "scenarios" portion of Contract [E]
  {
    "bull": {"summary": str, "confidence": float, "drivers": [str]},
    "base": {"summary": str, "confidence": float, "drivers": [str]},
    "bear": {"summary": str, "confidence": float, "risks":   [str]},
  }
"""

from scenarios_historicalPattern.scenario.signal_counter import count_signals
from scenarios_historicalPattern.scenario.source_authority import score_sources
from scenarios_historicalPattern.scenario.generator import generate_scenarios


def run_scenario_engine(raw_brief: dict) -> dict:
    if not isinstance(raw_brief, dict):
        raise ValueError("raw_brief must be a dictionary")

    required_fields = ["ticker", "bull_signals", "bear_signals", "risk_flags", "sources", "generated_at"]
    for field in required_fields:
        if field not in raw_brief:
            raise KeyError(f"Missing required field '{field}' in raw_brief")

    signal_counts = count_signals(raw_brief)
    scored_sources = score_sources(raw_brief.get("sources", []), raw_brief.get("generated_at"))
    return generate_scenarios(signal_counts, scored_sources, raw_brief)
