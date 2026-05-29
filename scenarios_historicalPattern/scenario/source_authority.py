"""
scenarios_historicalPattern/scenario/source_authority.py

Scores each source from the raw brief by type authority and recency decay.
Pure math — no LLM calls, no DB calls.

Authority weights by source type:
  filing: 1.4 | transcript: 1.2 | news: 0.9 | hiring: 0.8

Recency: exponential decay with 30-day half-life.
  weight = exp(-ln(2)/30 * days_old)
  Today = 1.0 | 30d ago = 0.5 | 60d ago = 0.25

Input:  sources (list), reference_date (str ISO, optional)
Output: scored_sources (list)
  [{"id", "type", "authority_weight", "recency_weight", "combined_weight"}]
"""

import math
from datetime import datetime, timezone

AUTHORITY_WEIGHTS = {
    "filing":     1.4,
    "transcript": 1.2,
    "news":       0.9,
    "hiring":     0.8,
}

_DECAY_LAMBDA = math.log(2.0) / 30.0


def parse_iso_datetime(dt_str: str) -> datetime:
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)


def exp_decay(date_str: str, reference_date_str: str = None) -> float:
    try:
        src_date = parse_iso_datetime(date_str)
        ref_date = parse_iso_datetime(reference_date_str) if reference_date_str else datetime.now(timezone.utc)
        days_old = max(0.0, (ref_date - src_date).total_seconds() / 86400.0)
        return math.exp(-_DECAY_LAMBDA * days_old)
    except Exception:
        return 1.0


def score_sources(sources: list, reference_date: str = None) -> list:
    scored = []
    for src in sources:
        if not isinstance(src, dict):
            continue

        stype = src.get("type", "news")
        stype = stype.lower() if isinstance(stype, str) else "news"

        auth_weight = AUTHORITY_WEIGHTS.get(stype, 0.9)
        rec_weight  = exp_decay(src["date"], reference_date) if src.get("date") else 1.0

        scored.append({
            "id":               src.get("id"),
            "type":             stype,
            "authority_weight": auth_weight,
            "recency_weight":   rec_weight,
            "combined_weight":  auth_weight * rec_weight,
        })

    return scored
