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

def retrieve_outcomes(matches: list) -> list:
  
    enriched_matches = []
    for match in matches:
        quarter = match.get("quarter", "Unknown Quarter")
        similarity_score = match.get("similarity_score", 0.0)
        
        # Default fallback values
        setup_summary = "No historical setup summary available."
        outcome = "No historical outcome available."
        return_5d = "0.0%"
        
        # Extract values from enriched_brief_json if available
        ebj = match.get("enriched_brief_json")
        if isinstance(ebj, dict):
            setup_summary = ebj.get("setup_summary", setup_summary)
            outcome = ebj.get("outcome", outcome)
            return_5d = ebj.get("return_5d", return_5d)
        else:
            # Fallback checks inside raw_brief_json or direct match keys
            raw_brief = match.get("raw_brief_json")
            if isinstance(raw_brief, dict):
                # Simple fallback heuristic summary from the ticker
                ticker = raw_brief.get("ticker", "UNKNOWN")
                setup_summary = f"Pre-earnings setup for {ticker} during {quarter}."
        
        # Ensure return_5d is formatted with percent sign and sign indicator (+/-)
        if isinstance(return_5d, (int, float)):
            sign = "+" if return_5d >= 0 else ""
            return_5d = f"{sign}{return_5d}%"
            
        enriched_matches.append({
            "quarter": quarter,
            "similarity_score": round(similarity_score, 2),
            "setup_summary": setup_summary,
            "outcome": outcome,
            "return_5d": return_5d
        })
    return enriched_matches
