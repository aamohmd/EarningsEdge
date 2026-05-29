"""
scenarios_historicalPattern/history/pattern_agent.py

Wires the three history components into a single callable:
  embedder → matcher → outcome

Input:  raw_brief (dict) — Contract [D]
Output: historical_matches (list) — "historical_matches" portion of Contract [E]
  [{"quarter", "similarity_score", "setup_summary", "outcome", "return_5d"}]
"""

import logging
from scenarios_historicalPattern.history.embedder import embed_brief
from scenarios_historicalPattern.history.matcher import match_historical_briefs
from scenarios_historicalPattern.history.outcome import retrieve_outcomes

logger = logging.getLogger(__name__)


def run_pattern_agent(raw_brief: dict) -> list:
    if not isinstance(raw_brief, dict):
        raise ValueError("raw_brief must be a dictionary")

    ticker = raw_brief.get("ticker")
    if not ticker:
        logger.warning("No ticker in raw_brief — skipping pattern matching")
        return []

    try:
        embedding = embed_brief(raw_brief)
    except Exception as e:
        logger.error(f"Embedding failed: {e}", exc_info=True)
        return []

    if not embedding or all(v == 0.0 for v in embedding):
        logger.warning("Zero-vector embedding — pattern matching may be imprecise")

    try:
        matches = match_historical_briefs(embedding, ticker=ticker)
    except Exception as e:
        logger.error(f"Historical match failed: {e}", exc_info=True)
        return []

    try:
        return retrieve_outcomes(matches)
    except Exception as e:
        logger.error(f"Outcome retrieval failed: {e}", exc_info=True)
        return []
