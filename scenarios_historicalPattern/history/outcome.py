"""
scenarios_historicalPattern/history/outcome.py

Retrieves historical outcomes for matched briefs and formats them for Contract [E].

Input:  matches (list[dict]) — from matcher.py
Output: matches_with_outcomes (list[dict])
  [{"quarter", "similarity_score", "setup_summary", "outcome", "return_5d"}]
"""


def retrieve_outcomes(matches: list) -> list:
    enriched = []
    for match in matches:
        quarter          = match.get("quarter", "Unknown Quarter")
        similarity_score = match.get("similarity_score", 0.0)
        setup_summary    = "No historical setup summary available."
        outcome          = "No historical outcome available."
        return_5d        = "0.0%"

        ebj = match.get("enriched_brief_json")
        if isinstance(ebj, dict):
            setup_summary = ebj.get("setup_summary", setup_summary)
            outcome       = ebj.get("outcome", outcome)
            return_5d     = ebj.get("return_5d", return_5d)
        else:
            raw = match.get("raw_brief_json")
            if isinstance(raw, dict):
                ticker = raw.get("ticker", "UNKNOWN")
                setup_summary = f"Pre-earnings setup for {ticker} during {quarter}."

        if isinstance(return_5d, (int, float)):
            return_5d = f"{'+' if return_5d >= 0 else ''}{return_5d}%"

        enriched.append({
            "quarter":          quarter,
            "similarity_score": round(similarity_score, 2),
            "setup_summary":    setup_summary,
            "outcome":          outcome,
            "return_5d":        return_5d,
        })

    return enriched
