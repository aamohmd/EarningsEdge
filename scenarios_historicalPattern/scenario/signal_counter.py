"""
scenarios_historicalPattern/scenario/signal_counter.py

Counts and categorizes bull / bear / risk signals from the raw brief [D].
Pure logic — no LLM calls, no DB calls.

Input:  raw_brief (dict)
Output: signal_counts (dict)
  {
    "bull_count": int, "bear_count": int, "risk_count": int, "total_signals": int,
    "bull_by_source": {"filing": int, "transcript": int, "news": int, "hiring": int},
    "bear_by_source": {"filing": int, "transcript": int, "news": int, "hiring": int},
  }
"""


def count_signals(raw_brief: dict) -> dict:
    bull_signals = raw_brief.get("bull_signals") or []
    bear_signals = raw_brief.get("bear_signals") or []
    risk_flags   = raw_brief.get("risk_flags") or []

    bull_by_source = {"filing": 0, "transcript": 0, "news": 0, "hiring": 0}
    bear_by_source = {"filing": 0, "transcript": 0, "news": 0, "hiring": 0}

    def get_source_type(sig) -> str:
        if isinstance(sig, dict):
            t = sig.get("source_type", "news")
            if isinstance(t, str):
                return t.lower()
        return "news"

    for sig in bull_signals:
        t = get_source_type(sig)
        bull_by_source[t if t in bull_by_source else "news"] += 1

    for sig in bear_signals:
        t = get_source_type(sig)
        bear_by_source[t if t in bear_by_source else "news"] += 1

    risk_count = 0
    for risk in risk_flags:
        risk_count += 1
        t = get_source_type(risk)
        bear_by_source[t if t in bear_by_source else "news"] += 1

    bull_count = sum(bull_by_source.values())
    bear_count = sum(bear_by_source.values())

    return {
        "bull_count":    bull_count,
        "bear_count":    bear_count,
        "risk_count":    risk_count,
        "total_signals": bull_count + bear_count,
        "bull_by_source": bull_by_source,
        "bear_by_source": bear_by_source,
    }
