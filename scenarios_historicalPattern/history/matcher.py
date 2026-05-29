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

import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def match_historical_briefs(current_embedding: list, ticker: str = None) -> list:
    """
    Finds the 2-3 most similar past pre-earnings briefs using cosine similarity.
    Queries Supabase/PostgreSQL if DATABASE_URL is set, otherwise falls back to
    loading from the mock file in mocks/contract_E_enriched_brief.json.
    """
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
            with conn.cursor() as cur:
                if ticker:
                    query = """
                        SELECT id, ticker, quarter, raw_brief_json, enriched_brief_json,
                               1 - (embedding <=> %s::vector) AS similarity_score
                        FROM briefs
                        WHERE ticker = %s AND (1 - (embedding <=> %s::vector)) >= 0.70
                        ORDER BY embedding <=> %s::vector
                        LIMIT 3;
                    """
                    cur.execute(query, (current_embedding, ticker, current_embedding, current_embedding))
                else:
                    query = """
                        SELECT id, ticker, quarter, raw_brief_json, enriched_brief_json,
                               1 - (embedding <=> %s::vector) AS similarity_score
                        FROM briefs
                        WHERE (1 - (embedding <=> %s::vector)) >= 0.70
                        ORDER BY embedding <=> %s::vector
                        LIMIT 3;
                    """
                    cur.execute(query, (current_embedding, current_embedding, current_embedding))
                
                rows = cur.fetchall()
                conn.close()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"Failed to query database for historical matching: {e}. Falling back to mock file.")

    # Fallback: Load from mocks/contract_E_enriched_brief.json
    import json
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    mock_paths = [
        os.path.join(base_dir, "mocks", "contract_E_enriched_brief.json"),
        "mocks/contract_E_enriched_brief.json",
        "../mocks/contract_E_enriched_brief.json"
    ]
    
    for path in mock_paths:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    mock_data = json.load(f)
                    matches = mock_data.get("historical_matches", [])
                    results = []
                    for match in matches:
                        results.append({
                            "brief_id": "mock-uuid",
                            "ticker": ticker or "NVDA",
                            "quarter": match.get("quarter", "Unknown"),
                            "similarity_score": match.get("similarity_score", 0.85),
                            "raw_brief_json": {"ticker": ticker or "NVDA"},
                            "enriched_brief_json": {
                                "setup_summary": match.get("setup_summary"),
                                "outcome": match.get("outcome"),
                                "return_5d": match.get("return_5d")
                            }
                        })
                    return results
            except Exception as e:
                logger.error(f"Error loading mock file at {path}: {e}")
                
    logger.warning("No database URL and no mock file found. Returning empty list.")
    return []
