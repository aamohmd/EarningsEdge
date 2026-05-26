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

# TODO: Define format_brief_for_embedding(raw_brief: dict) -> str
# TODO: Define embed_brief(raw_brief: dict) -> list[float]
# TODO: Call OpenAI embedding API (or use langchain's embedding wrapper)
# TODO: Ensure the embedding model matches what's used for historical briefs
