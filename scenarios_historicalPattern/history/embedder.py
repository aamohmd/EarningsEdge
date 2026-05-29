"""
embedder.py — Brief Embedding for Similarity Search (Adil)

PURPOSE:
    Embed the current raw brief into a vector representation
    that can be compared against historical briefs stored in Supabase.

INPUT:
    raw_brief (dict) — The [D] Raw Brief from Mohamed

OUTPUT:
    embedding (list[float]) — A vector (1536 dimensions if using OpenAI text-embedding-3-small)

HOW IT WORKS:
    1. Extract the key textual content from the brief:
       - Concatenate bull_signals texts
       - Concatenate bear_signals texts
       - Include risk_flags
       - Include analyst_sentiment
    2. Pass the concatenated text to an embedding model
    3. Return the vector

EMBEDDING MODEL:
    - Use OpenAI text-embedding-3-small (1536 dims) to match the pgvector schema
    - Must match the same model used to embed historical briefs in the DB

NOTES:
    - The embedding captures the "shape" of the brief (what signals dominate, what risks exist)
    - This allows cosine similarity to find briefs with similar signal patterns
    - The brief text should be formatted consistently for reliable similarity matching
"""

import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

def format_brief_for_embedding(raw_brief: dict) -> str:

    ticker = raw_brief.get("ticker", "UNKNOWN")
    sentiment = raw_brief.get("analyst_sentiment", "neutral")
    
    bull_signals = raw_brief.get("bull_signals") or []
    bear_signals = raw_brief.get("bear_signals") or []
    risk_flags = raw_brief.get("risk_flags") or []
    
    bull_texts = [sig.get("text") for sig in bull_signals if isinstance(sig, dict) and sig.get("text")]
    bear_texts = [sig.get("text") for sig in bear_signals if isinstance(sig, dict) and sig.get("text")]
    
    risk_texts = []
    for r in risk_flags:
        if isinstance(r, dict) and r.get("text"):
            risk_texts.append(r.get("text"))
        elif isinstance(r, str):
            risk_texts.append(r)
            
    text_parts = [
        f"Ticker: {ticker}",
        f"Sentiment: {sentiment}",
        "Bull Drivers:",
        *("- " + text for text in bull_texts),
        "Bear Drivers:",
        *("- " + text for text in bear_texts),
        "Risk Flags:",
        *("- " + text for text in risk_texts)
    ]
    return "\n".join(text_parts)

def embed_brief(raw_brief: dict) -> list:
    
    formatted_text = format_brief_for_embedding(raw_brief)
    try:
        # Lazy client initialization to avoid import-time key errors
        client = OpenAI()
        response = client.embeddings.create(
            input=[formatted_text],
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    except Exception as e:
        logger.warning(f"Error calling OpenAI embedding API: {e}. Falling back to zero-vector.")
        return [0.0] * 1536
