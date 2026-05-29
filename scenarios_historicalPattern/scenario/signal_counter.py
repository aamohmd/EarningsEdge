"""
signal_counter.py — Signal Counting & Categorization (Adil)

PURPOSE:
    Count and categorize bull vs. bear signals from the raw brief [D].
    This is the first step in the Scenario Engine pipeline.

INPUT:
    raw_brief (dict) — The [D] Raw Brief from Mohamed, containing:
        - bull_signals: list of {"text", "source_id", "source_type"}
        - bear_signals: list of {"text", "source_id", "source_type"}
        - risk_flags: list of strings

OUTPUT:
    signal_counts (dict) — Categorized signal counts:
        {
            "bull_count": int,
            "bear_count": int,
            "risk_count": int,
            "total_signals": int,
            "bull_by_source": {"filing": int, "transcript": int, "news": int, "hiring": int},
            "bear_by_source": {"filing": int, "transcript": int, "news": int, "hiring": int}
        }

NOTES:
    - Signals are grouped by source_type to allow authority weighting downstream
    - risk_flags count as weak bear signals
    - This function is pure logic — no LLM calls, no DB calls
"""
def count_signals(raw_brief: dict) -> dict:

    bull_signals = raw_brief.get("bull_signals") or []
    bear_signals = raw_brief.get("bear_signals") or []
    risk_flags = raw_brief.get("risk_flags") or []

    # Group counts by source type (with standard keys)
    bull_by_source = {"filing": 0, "transcript": 0, "news": 0, "hiring": 0}
    bear_by_source = {"filing": 0, "transcript": 0, "news": 0, "hiring": 0}

    def get_source_type(sig) -> str:
        if isinstance(sig, dict):
            stype = sig.get("source_type", "news")
            if isinstance(stype, str):
                return stype.lower()
        return "news"

    # Count bull signals
    for sig in bull_signals:
        stype = get_source_type(sig)
        if stype in bull_by_source:
            bull_by_source[stype] += 1
        else:
            bull_by_source["news"] += 1

    # Count bear signals
    for sig in bear_signals:
        stype = get_source_type(sig)
        if stype in bear_by_source:
            bear_by_source[stype] += 1
        else:
            bear_by_source["news"] += 1

    # risk_flags count as weak bear signals and are added to bear_by_source
    risk_count = 0
    for risk in risk_flags:
        risk_count += 1
        stype = get_source_type(risk)
        if stype in bear_by_source:
            bear_by_source[stype] += 1
        else:
            bear_by_source["news"] += 1

    bull_count = sum(bull_by_source.values())
    bear_count = sum(bear_by_source.values())
    total_signals = bull_count + bear_count

    return {
        "bull_count": bull_count,
        "bear_count": bear_count,
        "risk_count": risk_count,
        "total_signals": total_signals,
        "bull_by_source": bull_by_source,
        "bear_by_source": bear_by_source
    }
