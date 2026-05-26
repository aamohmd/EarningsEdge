"""
outcome.py — Historical Outcome Retriever (Adil)

PURPOSE:
    For each matched historical brief, retrieve what actually happened
    after that earnings quarter — the stock price reaction, beat/miss, etc.

INPUT:
    matches (list[dict]) — The matched historical briefs from matcher.py:
        [{"brief_id": "uuid", "ticker": "NVDA", "quarter": "Q2 2023", "similarity_score": 0.92, ...}]

OUTPUT:
    matches_with_outcomes (list[dict]) — Same matches enriched with outcome data:
        [
            {
                "quarter": "Q2 2023",
                "similarity_score": 0.92,
                "setup_summary": "Similar transition period from Ampere to Hopper...",
                "outcome": "Stock gapped up 24% post-earnings...",
                "return_5d": "+28.4%"
            }
        ]

HOW IT WORKS:
    1. For each matched brief, look up the stored outcome data in the database
    2. Outcome data includes:
       - setup_summary: what the pre-earnings setup looked like
       - outcome: what actually happened (narrative)
       - return_5d: 5-day stock return after earnings
    3. If outcome data is missing for a match, generate a summary from the brief itself

DATA SOURCE:
    - Outcomes are stored alongside historical briefs in the `briefs` table
    - For the MVP/demo, outcomes are part of the manually seeded mock historical data
    - Future: automatically compute outcomes from yFinance price data

NOTES:
    - The outcome narrative should be concise (1-2 sentences)
    - return_5d should be formatted as "+X.X%" or "-X.X%"
    - If no outcome data exists for a match, skip it gracefully
"""

# TODO: Define retrieve_outcomes(matches: list[dict]) -> list[dict]
# TODO: Query the database for outcome data per matched brief
# TODO: Format setup_summary, outcome, and return_5d
# TODO: Handle missing outcome data gracefully
