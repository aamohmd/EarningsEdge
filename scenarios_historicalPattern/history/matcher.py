"""
scenarios_historicalPattern/history/matcher.py

Finds the 2-3 most similar past pre-earnings briefs using cosine similarity on pgvector.

DB path: queries `briefs` table via DATABASE_URL env var using cosine distance (<=>).
Fallback: loads historical_matches from mocks/contract_E_enriched_brief.json if no DB.

SQL (approximate):
  SELECT id, ticker, quarter, raw_brief_json, enriched_brief_json,
         1 - (embedding <=> %s::vector) AS similarity_score
  FROM briefs
  WHERE ticker = %s AND (1 - (embedding <=> %s::vector)) >= 0.70
  ORDER BY embedding <=> %s::vector LIMIT 3;

Input:  current_embedding (list[float]), ticker (str, optional)
Output: matches (list[dict]) — top 2-3 similar briefs
"""

import json
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_SIMILARITY_THRESHOLD = 0.70
_LIMIT = 3


def _load_mock_fallback(ticker: str) -> list:
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidates = [
        os.path.join(base_dir, "mocks", "contract_E_enriched_brief.json"),
        "mocks/contract_E_enriched_brief.json",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path) as f:
                    mock_data = json.load(f)
                return [
                    {
                        "brief_id":            "mock-uuid",
                        "ticker":              ticker or "NVDA",
                        "quarter":             m.get("quarter", "Unknown"),
                        "similarity_score":    m.get("similarity_score", 0.85),
                        "raw_brief_json":      {"ticker": ticker or "NVDA"},
                        "enriched_brief_json": {
                            "setup_summary": m.get("setup_summary"),
                            "outcome":       m.get("outcome"),
                            "return_5d":     m.get("return_5d"),
                        },
                    }
                    for m in mock_data.get("historical_matches", [])
                ]
            except Exception as e:
                logger.error(f"Error loading mock at {path}: {e}")

    logger.warning("No DATABASE_URL and no mock file found — returning empty list")
    return []


def match_historical_briefs(current_embedding: list, ticker: str = None) -> list:
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor

            conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
            with conn.cursor() as cur:
                if ticker:
                    cur.execute(
                        """
                        SELECT id, ticker, quarter, raw_brief_json, enriched_brief_json,
                               1 - (embedding <=> %s::vector) AS similarity_score
                        FROM briefs
                        WHERE ticker = %s AND (1 - (embedding <=> %s::vector)) >= %s
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s;
                        """,
                        (current_embedding, ticker, current_embedding, _SIMILARITY_THRESHOLD, current_embedding, _LIMIT),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, ticker, quarter, raw_brief_json, enriched_brief_json,
                               1 - (embedding <=> %s::vector) AS similarity_score
                        FROM briefs
                        WHERE (1 - (embedding <=> %s::vector)) >= %s
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s;
                        """,
                        (current_embedding, current_embedding, _SIMILARITY_THRESHOLD, current_embedding, _LIMIT),
                    )
                rows = cur.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"DB query failed: {e} — falling back to mock")

    return _load_mock_fallback(ticker)
