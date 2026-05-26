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

# TODO: Define count_signals(raw_brief: dict) -> dict
# TODO: Count bull_signals and bear_signals from the brief
# TODO: Group signals by source_type (filing, transcript, news, hiring)
# TODO: Include risk_flags in the counts
