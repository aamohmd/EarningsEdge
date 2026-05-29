"""
scenarios_historicalPattern/history/embedder.py

Embeds the current raw brief into a vector for similarity search against historical briefs.
Uses OpenAI text-embedding-3-small (1536 dims). Falls back to zero-vector on failure.

Input:  raw_brief (dict) — Contract [D]
Output: embedding (list[float]) — 1536-dimensional vector
"""

import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)


def _format_for_embedding(raw_brief: dict) -> str:
    ticker    = raw_brief.get("ticker", "UNKNOWN")
    sentiment = raw_brief.get("analyst_sentiment", "neutral")

    bull_texts = [s.get("text") for s in (raw_brief.get("bull_signals") or []) if isinstance(s, dict) and s.get("text")]
    bear_texts = [s.get("text") for s in (raw_brief.get("bear_signals") or []) if isinstance(s, dict) and s.get("text")]

    risk_texts = []
    for r in (raw_brief.get("risk_flags") or []):
        if isinstance(r, dict) and r.get("text"):
            risk_texts.append(r["text"])
        elif isinstance(r, str):
            risk_texts.append(r)

    return "\n".join([
        f"Ticker: {ticker}",
        f"Sentiment: {sentiment}",
        "Bull Drivers:",
        *("- " + t for t in bull_texts),
        "Bear Drivers:",
        *("- " + t for t in bear_texts),
        "Risk Flags:",
        *("- " + t for t in risk_texts),
    ])


def embed_brief(raw_brief: dict) -> list:
    try:
        client   = OpenAI()
        response = client.embeddings.create(
            input=[_format_for_embedding(raw_brief)],
            model="text-embedding-3-small",
        )
        return response.data[0].embedding
    except Exception as e:
        logger.warning(f"OpenAI embedding failed: {e} — returning zero-vector")
        return [0.0] * 1536
