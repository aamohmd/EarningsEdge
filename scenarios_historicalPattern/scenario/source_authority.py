"""
source_authority.py — Source Authority & Recency Scoring (Adil)

PURPOSE:
    Score each source from the raw brief by two factors:
        1. Source type authority — filings are more authoritative than news
        2. Recency decay — newer sources are weighted more heavily

    This allows the confidence formula to be grounded in data quality,
    not just raw signal counts.

INPUT:
    sources (list) — The sources array from [D] Raw Brief:
        [{"id": "uuid", "url": "string", "type": "string", "date": "iso", "authority": 0.9}]

OUTPUT:
    scored_sources (list) — Same sources with computed weights:
        [{"id": "uuid", "type": "string", "authority_weight": float, "recency_weight": float, "combined_weight": float}]

AUTHORITY WEIGHTS (by source type):
    - "filing":     1.4   (SEC filings — most authoritative)
    - "transcript": 1.2   (Earnings call transcripts — direct from management)
    - "news":       0.9   (News articles — secondary sources)
    - "hiring":     0.8   (LinkedIn hiring signals — weakest signal)

RECENCY DECAY:
    - Exponential decay with a 30-day half-life
    - Formula: weight = exp(-lambda * days_old)  where lambda = ln(2) / 30
    - A source from today = 1.0, from 30 days ago = 0.5, from 60 days ago = 0.25

NOTES:
    - This is pure math — no LLM calls
    - The combined_weight is authority_weight × recency_weight
    - These weights feed into the confidence formula in generator.py
"""
from datetime import datetime, timezone
import math

AUTHORITY_WEIGHTS = {
    "filing": 1.4,
    "transcript": 1.2,
    "news": 0.9,
    "hiring": 0.8
}

def parse_iso_datetime(dt_str: str) -> datetime:
    try:
        # Standard ISO-8601 parsing, replacing Z with +00:00 for timezone support
        clean_str = dt_str.replace('Z', '+00:00')
        return datetime.fromisoformat(clean_str)
    except Exception:
        return datetime.now(timezone.utc)

def exp_decay(date_str: str, reference_date_str: str = None) -> float:
    """
    Exponential decay with a 30-day half-life.
    weight = exp(-lambda * days_old) where lambda = ln(2) / 30
    """
    try:
        src_date = parse_iso_datetime(date_str)
        ref_date = parse_iso_datetime(reference_date_str) if reference_date_str else datetime.now(timezone.utc)
        
        delta = ref_date - src_date
        days_old = max(0.0, delta.total_seconds() / (24.0 * 3600.0))
        
        decay_lambda = math.log(2.0) / 30.0
        return math.exp(-decay_lambda * days_old)
    except Exception:
        return 1.0

def score_sources(sources: list, reference_date: str = None) -> list:
    """
    Score each source by its type authority and recency decay.
    """
    scored = []
    for src in sources:
        if not isinstance(src, dict):
            continue
        
        src_id = src.get("id")
        stype = src.get("type", "news")
        if isinstance(stype, str):
            stype = stype.lower()
        else:
            stype = "news"

        # 1. Authority Weight
        auth_weight = AUTHORITY_WEIGHTS.get(stype, 0.9)

        # 2. Recency Weight
        date_str = src.get("date")
        rec_weight = exp_decay(date_str, reference_date) if date_str else 1.0

        # 3. Combined weight
        combined_weight = auth_weight * rec_weight

        scored.append({
            "id": src_id,
            "type": stype,
            "authority_weight": auth_weight,
            "recency_weight": rec_weight,
            "combined_weight": combined_weight
        })
    return scored
