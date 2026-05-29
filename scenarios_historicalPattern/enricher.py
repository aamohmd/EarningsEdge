"""
scenarios_historicalPattern/enricher.py

Entry point for Adil's enrichment layer.
Takes the [D] Raw Brief from synthesis and returns the [E] Enriched Brief.

  Step 1 — Scenario Engine:  signal counting → source authority → confidence → scenarios
  Step 2 — Pattern Agent:    embed brief → match historical briefs → retrieve outcomes

Input:  raw_brief (dict) — Contract [D] from synthesis.py
Output: {"scenarios": {...}, "historical_matches": [...]} — Contract [E]

Call from Mohamed's pipeline:
  from scenarios_historicalPattern.enricher import enrich
  enriched = enrich(raw_brief)

enrich() is synchronous. If calling from async context:
  enriched = await asyncio.to_thread(enrich, raw_brief)
"""

import logging
from scenarios_historicalPattern.scenario.engine import run_scenario_engine
from scenarios_historicalPattern.history.pattern_agent import run_pattern_agent

logger = logging.getLogger(__name__)


def enrich(raw_brief: dict) -> dict:
    if not isinstance(raw_brief, dict):
        raise ValueError("raw_brief must be a dictionary")

    try:
        scenarios = run_scenario_engine(raw_brief)
    except Exception as e:
        logger.error(f"Scenario engine failed: {e}", exc_info=True)
        scenarios = {
            "bull": {"summary": "Error generating scenario", "confidence": 0.33, "drivers": []},
            "base": {"summary": "Error generating scenario", "confidence": 0.34, "drivers": []},
            "bear": {"summary": "Error generating scenario", "confidence": 0.33, "risks": []},
        }

    try:
        historical_matches = run_pattern_agent(raw_brief)
    except Exception as e:
        logger.error(f"Pattern agent failed: {e}", exc_info=True)
        historical_matches = []

    return {
        "scenarios": scenarios,
        "historical_matches": historical_matches,
    }
