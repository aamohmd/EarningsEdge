"""
scenarios_historicalPattern/scenario/generator.py

Generates Bull / Base / Bear investment scenarios with formulaic confidence scores.
Final step in the Scenario Engine pipeline.

Confidence formula (traceable, no LLM):
  1. raw_bull = bull_count / total_signals
  2. Adjust by average combined_weight of bull sources
  3. Same for bear
  4. base_conf = 1.0 - bull_conf - bear_conf  (clamped to min 0.05)
  5. Scores always sum to 1.0

Input:  signal_counts (dict), scored_sources (list), raw_brief (dict)
Output: scenarios (dict) — "scenarios" portion of Contract [E]
"""


def _avg_weight(signals: list, source_map: dict, fallback: float = 0.9) -> float:
    weights = []
    for sig in signals:
        sid = sig.get("source_id") if isinstance(sig, dict) else None
        src = source_map.get(sid)
        weights.append(src.get("combined_weight", fallback) if src else fallback)
    return sum(weights) / len(weights) if weights else 1.0


def compute_confidence(signal_counts: dict, scored_sources: list, raw_brief: dict) -> dict:
    bull_count = signal_counts.get("bull_count", 0)
    bear_count = signal_counts.get("bear_count", 0)
    total      = bull_count + bear_count

    if total == 0:
        return {"bull": 0.33, "base": 0.34, "bear": 0.33}

    source_map  = {src.get("id"): src for src in scored_sources if src.get("id")}
    bull_signals = raw_brief.get("bull_signals") or []
    bear_signals = raw_brief.get("bear_signals") or []
    risk_flags   = raw_brief.get("risk_flags") or []

    bear_all = bear_signals + [r for r in risk_flags if isinstance(r, dict)]
    bear_all += [{"source_id": None}] * sum(1 for r in risk_flags if isinstance(r, str))

    adj_bull = (bull_count / total) * _avg_weight(bull_signals, source_map)
    adj_bear = (bear_count / total) * _avg_weight(bear_all, source_map)

    total_adj = adj_bull + adj_bear
    if total_adj >= 0.95:
        scale    = 0.95 / total_adj
        bull_conf = round(adj_bull * scale, 2)
        bear_conf = round(adj_bear * scale, 2)
    else:
        bull_conf = round(adj_bull, 2)
        bear_conf = round(adj_bear, 2)

    base_conf = round(max(0.05, 1.0 - bull_conf - bear_conf), 2)
    return {"bull": bull_conf, "base": base_conf, "bear": bear_conf}


def generate_scenarios(signal_counts: dict, scored_sources: list, raw_brief: dict) -> dict:
    confidence   = compute_confidence(signal_counts, scored_sources, raw_brief)
    bull_signals = raw_brief.get("bull_signals") or []
    bear_signals = raw_brief.get("bear_signals") or []
    risk_flags   = raw_brief.get("risk_flags") or []
    ticker       = raw_brief.get("ticker", "the company")

    drivers = [s.get("text") for s in bull_signals if isinstance(s, dict) and s.get("text")] \
              or ["No significant bull drivers identified."]

    risks = [s.get("text") for s in bear_signals if isinstance(s, dict) and s.get("text")]
    for r in risk_flags:
        if isinstance(r, dict) and r.get("text"):
            risks.append(r["text"])
        elif isinstance(r, str):
            risks.append(r)
    risks = risks or ["No significant downside risks identified."]

    if len(drivers) >= 2:
        bull_summary = f"Strong growth prospects for {ticker} driven by: {drivers[0]} Additionally, {drivers[1]}."
    else:
        bull_summary = f"Positive outlook for {ticker} supported by: {drivers[0]}"

    if len(risks) >= 2:
        bear_summary = f"Downside pressure on {ticker} due to: {risks[0]} Also compounded by: {risks[1]}."
    else:
        bear_summary = f"Negative outlook for {ticker} primarily due to: {risks[0]}"

    if drivers and risks:
        base_summary = f"Moderate growth for {ticker}. While {drivers[0]} is positive, it is offset by concerns around {risks[0]}."
    elif drivers:
        base_summary = f"Steady performance for {ticker} anchored by {drivers[0]} with neutral expectations elsewhere."
    elif risks:
        base_summary = f"Sideways trading for {ticker} as progress is capped by {risks[0]}."
    else:
        base_summary = f"Base scenario assumes business-as-usual operations for {ticker}."

    return {
        "bull": {"summary": bull_summary, "confidence": confidence["bull"], "drivers": drivers[:3]},
        "base": {"summary": base_summary, "confidence": confidence["base"], "drivers": drivers[:2] + risks[:1]},
        "bear": {"summary": bear_summary, "confidence": confidence["bear"], "risks":   risks[:3]},
    }
