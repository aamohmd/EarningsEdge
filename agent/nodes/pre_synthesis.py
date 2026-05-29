"""
agent/nodes/pre_synthesis.py

Runs before the LLM synthesis chain.
Takes raw chunks from web_fetch + RAG and prepares them for synthesis:

  1. Recency filter  — drops chunks older than the cutoff for their source type
  2. Deduplication   — removes near-duplicate chunks, keeps the higher-authority version
  3. Rough labelling — assigns bull / bear / risk / neutral to each kept chunk
  4. Sentiment roll-up — weighted aggregate across all kept chunks

Input:  list of raw chunks (from web_fetch or RAG)
Output: {chunks, discarded, analyst_sentiment, stats}
"""

from datetime import datetime, timedelta
from difflib import SequenceMatcher

RECENCY_CUTOFFS = {
    "news":        timedelta(days=30),
    "filings":     timedelta(days=180),   # last 2 quarters
    "transcripts": timedelta(days=365),   # last 4 quarters
    "transcript":  timedelta(days=365),   # alias
    "filing":      timedelta(days=180),   # alias
    "hiring":      timedelta(days=60),
}

def compute_recency_weight(chunk: dict, reference_date: datetime) -> float:
    source_type = chunk.get("source_type", "news").lower()
    cutoff = RECENCY_CUTOFFS.get(source_type, timedelta(days=30))

    try:
        pub_date = datetime.strptime(chunk["date"], "%Y-%m-%d")
    except (KeyError, ValueError):
        return 0.3

    age = reference_date - pub_date

    if age > cutoff:
        return -1.0

    weight = 1.0 - (0.9 * (age.days / cutoff.days))
    return round(max(0.1, weight), 3)

def apply_recency_filter(chunks: list, reference_date: datetime) -> tuple[list, list]:
    kept = []
    discarded = []

    for chunk in chunks:
        weight = compute_recency_weight(chunk, reference_date)
        if weight == -1.0:
            discarded.append({**chunk, "discard_reason": "stale"})
        else:
            kept.append({**chunk, "recency_weight": weight})

    return kept, discarded

DEDUP_SIMILARITY_THRESHOLD = 0.82

def text_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def deduplicate(chunks: list) -> tuple[list, list]:
    kept = []
    removed = []

    for candidate in chunks:
        is_duplicate = False

        for i, existing in enumerate(kept):
            sim = text_similarity(candidate["chunk"], existing["chunk"])

            if sim >= DEDUP_SIMILARITY_THRESHOLD:
                is_duplicate = True

                candidate_score = (
                    candidate.get("authority", 0.5),
                    candidate.get("recency_weight", 0.5)
                )
                existing_score = (
                    existing.get("authority", 0.5),
                    existing.get("recency_weight", 0.5)
                )

                if candidate_score > existing_score:
                    removed.append({**existing, "discard_reason": f"duplicate of {candidate['id']}"})
                    kept[i] = candidate
                else:
                    removed.append({**candidate, "discard_reason": f"duplicate of {existing['id']}"})

                break

        if not is_duplicate:
            kept.append(candidate)

    return kept, removed

BULL_KEYWORDS = [
    "record", "surged", "growth", "beat", "raised", "upgrade", "expansion",
    "demand", "sold out", "production", "committed", "strong", "outperform",
    "increased", "acceleration", "momentum", "secured", "wins", "milestone"
]
BEAR_KEYWORDS = [
    "missed", "declined", "fell", "delayed", "pressure", "concern", "risk",
    "downgrade", "cut", "lower", "bottleneck", "competition", "restrictions",
    "lost", "decelerat", "warning", "guidance cut", "margin compression"
]

def rough_label(chunk: dict) -> str:
    text = chunk["chunk"].lower()
    source_type = chunk.get("source_type", "").lower()

    risk_signals = ["department of commerce", "export restriction", "regulation",
                    "antitrust", "geopolit", "sanction", "competition from"]
    if any(r in text for r in risk_signals):
        return "risk"

    bull_score = sum(1 for kw in BULL_KEYWORDS if kw in text)
    bear_score = sum(1 for kw in BEAR_KEYWORDS if kw in text)

    if bull_score > bear_score:
        return "bull"
    elif bear_score > bull_score:
        return "bear"
    else:
        return "neutral"

def compute_analyst_sentiment(chunks: list) -> str:
    weighted_bull = 0.0
    weighted_bear = 0.0

    for chunk in chunks:
        label = rough_label(chunk)
        authority = chunk.get("authority", 0.5)
        recency = chunk.get("recency_weight", 0.5)
        weight = authority * recency

        if label == "bull":
            weighted_bull += weight
        elif label == "bear":
            weighted_bear += weight

    if weighted_bull == 0 and weighted_bear == 0:
        return "neutral"
    if weighted_bull > weighted_bear * 1.5:
        return "bullish"
    if weighted_bear > weighted_bull:
        return "bearish"
    return "neutral"

def run_pre_synthesis(
    chunks: list,
    reference_date: datetime = None
) -> dict:
    if reference_date is None:
        reference_date = datetime.utcnow()

    after_recency, stale = apply_recency_filter(chunks, reference_date)
    after_dedup, duplicates = deduplicate(after_recency)
    sentiment = compute_analyst_sentiment(after_dedup)

    all_discarded = stale + duplicates

    return {
        "chunks": after_dedup,
        "discarded": all_discarded,
        "analyst_sentiment": sentiment,
        "stats": {
            "input_count":     len(chunks),
            "kept_count":      len(after_dedup),
            "stale_count":     len(stale),
            "duplicate_count": len(duplicates),
        }
    }
