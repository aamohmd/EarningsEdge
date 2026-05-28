"""
INPUT — [D] Raw Brief:
    {
        "ticker": "NVDA",
        "brief_id": "uuid",
        "generated_at": "iso-timestamp",
        "bull_signals": [{"text": "...", "source_id": "uuid", "source_type": "filing|news|transcript"}],
        "bear_signals": [{"text": "...", "source_id": "uuid", "source_type": "string"}],
        "risk_flags": ["string"],
        "analyst_sentiment": "bullish|neutral|bearish",
        "comparable_quarter": "string",
        "sources": [{"id": "uuid", "url": "string", "type": "string", "date": "iso", "authority": 0.9}],
        "contradictions_resolved": [{"claim_a": "string", "claim_b": "string", "resolution": "string"}]
    }

OUTPUT — [E] Enriched Brief:
    {
        "scenarios": {
            "bull":  {"summary": "string", "confidence": 0.65, "drivers": ["string"]},
            "base":  {"summary": "string", "confidence": 0.25, "drivers": ["string"]},
            "bear":  {"summary": "string", "confidence": 0.10, "risks":   ["string"]}
        },
        "historical_matches": [
            {
                "quarter": "Q2 2023",
                "similarity_score": 0.92,
                "setup_summary": "string",
                "outcome": "string",
                "return_5d": "+28.4%"
            }
        ]
    }

"""
import logging
from scenarios_historicalPattern.scenario.engine import run_scenario_engine
from scenarios_historicalPattern.history.pattern_agent import run_pattern_agent

logger = logging.getLogger(__name__)

def enrich(raw_brief: dict) -> dict:

    if not isinstance(raw_brief, dict):
        raise ValueError("raw_brief must be a dictionary")

    # 1. Run Scenario Engine
    try:
        scenarios = run_scenario_engine(raw_brief)
    except Exception as e:
        logger.error(f"Error running scenario engine: {e}", exc_info=True)
        # Graceful fallback for scenarios to avoid crashing the pipeline
        scenarios = {
            "bull": {"summary": "Error generating scenario", "confidence": 0.33, "drivers": []},
            "base": {"summary": "Error generating scenario", "confidence": 0.34, "drivers": []},
            "bear": {"summary": "Error generating scenario", "confidence": 0.33, "risks": []}
        }

    # 2. Run Historical Pattern Matcher
    try:
        historical_matches = run_pattern_agent(raw_brief)
    except Exception as e:
        logger.error(f"Error running pattern agent: {e}", exc_info=True)
        # Graceful fallback for historical matches (empty list)
        historical_matches = []

    # 3. Combine both outputs into the Enriched Brief [E]
    return {
        "scenarios": scenarios,
        "historical_matches": historical_matches
    }
