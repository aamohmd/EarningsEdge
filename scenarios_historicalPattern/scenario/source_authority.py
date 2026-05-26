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

# TODO: Define AUTHORITY_WEIGHTS dict
# TODO: Define exp_decay(date: str) -> float  (30-day half-life)
# TODO: Define score_sources(sources: list) -> list
# TODO: Compute authority_weight from source type
# TODO: Compute recency_weight from source date
# TODO: Return combined_weight = authority × recency
