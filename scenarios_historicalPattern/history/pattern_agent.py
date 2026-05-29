"""
pattern_agent.py — Historical Pattern Matching Pipeline (Adil)

PURPOSE:
    Wires the three history components into a single callable pipeline:
        embedder → matcher → outcome

    This is the convenience wrapper that enricher.py calls.

INPUT:
    raw_brief (dict) — The [D] Raw Brief from Mohamed

OUTPUT:
    historical_matches (list[dict]) — The "historical_matches" portion of [E]:
        [
            {
                "quarter": "Q2 2023",
                "similarity_score": 0.92,
                "setup_summary": "Similar transition period...",
                "outcome": "Stock gapped up 24% post-earnings...",
                "return_5d": "+28.4%"
            }
        ]

PIPELINE:
    1. embedder.embed_brief(raw_brief) → current_embedding
    2. matcher.match_historical_briefs(current_embedding, ticker) → matches
    3. outcome.retrieve_outcomes(matches) → matches_with_outcomes

EDGE CASES:
    - No historical briefs in DB for this ticker → return empty list []
    - < 3 matches above similarity threshold → return whatever is available
    - Embedding API fails → return empty list with a warning log

NOTES:
    - Single function call: run_pattern_agent(raw_brief) -> historical_matches
    - Cold-start: seed the DB with 4-6 manually written historical briefs for NVDA/AMD
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
        logger.warning("No ticker found in raw_brief. Skipping pattern matching.")
        return []
        
    # 1. Embed current brief
    try:
        current_embedding = embed_brief(raw_brief)
    except Exception as e:
        logger.error(f"Failed to embed brief: {e}", exc_info=True)
        return []
        
    # Check if we got a valid non-zero embedding or if embedder returned fallback
    if not current_embedding or all(v == 0.0 for v in current_embedding):
        logger.warning("Embedding failed or returned zero vector. Pattern matching might be less precise.")
        
    # 2. Match historical briefs
    try:
        matches = match_historical_briefs(current_embedding, ticker=ticker)
    except Exception as e:
        logger.error(f"Failed to match historical briefs: {e}", exc_info=True)
        return []
        
    # 3. Retrieve outcomes
    try:
        matches_with_outcomes = retrieve_outcomes(matches)
    except Exception as e:
        logger.error(f"Failed to retrieve outcomes: {e}", exc_info=True)
        return []
        
    logger.info(f"Successfully matched {len(matches_with_outcomes)} historical briefs for {ticker}.")
    return matches_with_outcomes
