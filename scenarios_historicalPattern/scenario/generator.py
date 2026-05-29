"""
generator.py — Scenario Generator (Adil)

PURPOSE:
    Generate Bull / Base / Bear investment scenarios from weighted signals.
    This is the final step in the Scenario Engine pipeline.

    The confidence scores come from a FORMULA, not from an LLM.
    This is the key differentiator — a judge can ask "where does 65% come from?"
    and the answer is a traceable calculation.

INPUT:
    signal_counts (dict) — From signal_counter.py:
        {"bull_count": int, "bear_count": int, "bull_by_source": {...}, "bear_by_source": {...}}

    scored_sources (list) — From source_authority.py:
        [{"id": "uuid", "type": "string", "combined_weight": float}]

    raw_brief (dict) — The original [D] for extracting signal text, risk flags, etc.

OUTPUT:
    scenarios (dict) — The "scenarios" portion of [E]:
        {
            "bull":  {"summary": "string", "confidence": 0.65, "drivers": ["string"]},
            "base":  {"summary": "string", "confidence": 0.25, "drivers": ["string"]},
            "bear":  {"summary": "string", "confidence": 0.10, "risks":   ["string"]}
        }

CONFIDENCE FORMULA:
    1. raw_bull = bull_count / (bull_count + bear_count)
    2. raw_bear = bear_count / (bull_count + bear_count)
    3. Apply authority weighting:  adjusted = raw × sum(authority_weights for matching sources)
    4. Apply recency weighting:   adjusted *= avg(recency_weights for matching sources)
    5. base_conf = 1.0 - bull_conf - bear_conf
    6. Confidence scores MUST always sum to 1.0

NOTES:
    - Summaries can use an LLM to generate readable text from the signals
    - Drivers/risks are extracted from the bull/bear signal texts
    - Edge case: if all signals are bull (or all bear), clamp base to minimum 0.05
"""

def compute_confidence(signal_counts: dict, scored_sources: list, raw_brief: dict) -> dict:
    
    bull_count = signal_counts.get("bull_count", 0)
    bear_count = signal_counts.get("bear_count", 0)

    total_count = bull_count + bear_count
    if total_count == 0:
        return {"bull": 0.33, "base": 0.34, "bear": 0.33}

    raw_bull = bull_count / total_count
    raw_bear = bear_count / total_count

    # Map sources to their scored weights
    source_map = {src.get("id"): src for src in scored_sources if src.get("id")}

    bull_signals = raw_brief.get("bull_signals") or []
    bear_signals = raw_brief.get("bear_signals") or []
    risk_flags = raw_brief.get("risk_flags") or []

    # Average combined weight of bull sources
    bull_weights = []
    for sig in bull_signals:
        sid = sig.get("source_id")
        src = source_map.get(sid)
        bull_weights.append(src.get("combined_weight", 0.9) if src else 0.9)
    avg_bull_weight = sum(bull_weights) / len(bull_weights) if bull_weights else 1.0

    # Average combined weight of bear + risk sources
    bear_weights = []
    for sig in bear_signals:
        sid = sig.get("source_id")
        src = source_map.get(sid)
        bear_weights.append(src.get("combined_weight", 0.9) if src else 0.9)
    for sig in risk_flags:
        if isinstance(sig, dict):
            sid = sig.get("source_id")
            src = source_map.get(sid)
            bear_weights.append(src.get("combined_weight", 0.9) if src else 0.9)
        else:
            bear_weights.append(0.9)
    avg_bear_weight = sum(bear_weights) / len(bear_weights) if bear_weights else 1.0

    # Adjusted confidence values
    adjusted_bull = raw_bull * avg_bull_weight
    adjusted_bear = raw_bear * avg_bear_weight

    sum_adjusted = adjusted_bull + adjusted_bear
    if sum_adjusted >= 0.95:
        # Scale to ensure at least 0.05 is left for base case
        scale = 0.95 / sum_adjusted
        bull_conf = adjusted_bull * scale
        bear_conf = adjusted_bear * scale
        base_conf = 0.05
    else:
        bull_conf = adjusted_bull
        bear_conf = adjusted_bear
        base_conf = 1.0 - bull_conf - bear_conf

    # Round to 2 decimals
    bull_conf = max(0.0, round(bull_conf, 2))
    bear_conf = max(0.0, round(bear_conf, 2))
    base_conf = round(1.0 - bull_conf - bear_conf, 2)

    return {
        "bull": bull_conf,
        "base": base_conf,
        "bear": bear_conf
    }

def generate_scenarios(signal_counts: dict, scored_sources: list, raw_brief: dict) -> dict:
    """
    Generate Bull / Base / Bear scenarios using formulaic confidence scores.
    Extracts drivers, risks, and formats analyst summaries.
    """
    confidence = compute_confidence(signal_counts, scored_sources, raw_brief)

    bull_signals = raw_brief.get("bull_signals") or []
    bear_signals = raw_brief.get("bear_signals") or []
    risk_flags = raw_brief.get("risk_flags") or []

    # Extract drivers from bull signal text
    drivers = [sig.get("text") for sig in bull_signals if isinstance(sig, dict) and sig.get("text")]
    if not drivers:
        drivers = ["No significant bull drivers identified."]

    # Extract risks from bear signal text + risk flags
    risks = [sig.get("text") for sig in bear_signals if isinstance(sig, dict) and sig.get("text")]
    for r in risk_flags:
        if isinstance(r, dict) and r.get("text"):
            risks.append(r.get("text"))
        elif isinstance(r, str):
            risks.append(r)
    if not risks:
        risks = ["No significant downside risks identified."]

    ticker = raw_brief.get("ticker", "the company")

    # Format summaries
    if len(drivers) >= 2:
        bull_summary = f"Strong growth prospects for {ticker} driven by: {drivers[0]} Additionally, {drivers[1]}."
    elif len(drivers) == 1:
        bull_summary = f"Positive outlook for {ticker} supported by: {drivers[0]}"
    else:
        bull_summary = f"Bull scenario assumes expansion of existing growth lines for {ticker}."

    if len(risks) >= 2:
        bear_summary = f"Downside pressure on {ticker} due to: {risks[0]} Also compounded by: {risks[1]}."
    elif len(risks) == 1:
        bear_summary = f"Negative outlook for {ticker} primarily due to: {risks[0]}"
    else:
        bear_summary = f"Bear scenario assumes macro slowdown or margin contraction for {ticker}."

    if drivers and risks:
        base_summary = f"Moderate growth for {ticker}. While {drivers[0]} is positive, it is offset by concerns around {risks[0]}."
    elif drivers:
        base_summary = f"Steady performance for {ticker} anchored by {drivers[0]} with neutral expectations elsewhere."
    elif risks:
        base_summary = f"Sideways trading for {ticker} as progress is capped by {risks[0]}."
    else:
        base_summary = f"Base scenario assumes business-as-usual operations for {ticker}."

    return {
        "bull": {
            "summary": bull_summary,
            "confidence": confidence["bull"],
            "drivers": drivers[:3]
        },
        "base": {
            "summary": base_summary,
            "confidence": confidence["base"],
            "drivers": drivers[:2] + risks[:1]
        },
        "bear": {
            "summary": bear_summary,
            "confidence": confidence["bear"],
            "risks": risks[:3]
        }
    }
