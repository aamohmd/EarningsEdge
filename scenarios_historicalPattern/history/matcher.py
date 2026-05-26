"""
matcher.py — Historical Brief Matcher (Adil)

PURPOSE:
    Find the 2-3 most similar past pre-earnings briefs from the database
    using cosine similarity over pgvector embeddings.

INPUT:
    current_embedding (list[float]) — The embedded current brief (from embedder.py)
    ticker (str) — Optional: filter to same ticker or search across all tickers

OUTPUT:
    matches (list[dict]) — Top 2-3 most similar historical briefs:
        [
            {
                "brief_id": "uuid",
                "ticker": "NVDA",
                "quarter": "Q2 2023",
                "similarity_score": 0.92,
                "raw_brief_json": {...}  # The stored historical [D] brief
            }
        ]

HOW IT WORKS:
    1. Query the `briefs` table in Supabase using pgvector cosine similarity
    2. Order by similarity score descending
    3. Apply a minimum similarity threshold (e.g., 0.70) to filter noise
    4. Return top 2-3 matches

SQL QUERY (approximate):
    SELECT id, ticker, quarter, raw_brief_json,
           1 - (embedding <=> $1) AS similarity_score
    FROM briefs
    WHERE ticker = $2  -- optional filter
    ORDER BY embedding <=> $1
    LIMIT 3;

NOTES:
    - Uses Supabase's pgvector extension for efficient similarity search
    - Similarity threshold should be tunable (start at 0.70, adjust during testing)
    - If < 3 results above threshold, return whatever is available
    - If 0 results, return empty list (enricher.py handles the fallback)
"""

# TODO: Define match_historical_briefs(current_embedding, ticker=None) -> list[dict]
# TODO: Connect to Supabase / PostgreSQL
# TODO: Run cosine similarity query on the briefs table
# TODO: Apply similarity threshold filtering
# TODO: Return top 2-3 matches with similarity scores
