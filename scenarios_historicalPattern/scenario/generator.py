"""
scenarios_historicalPattern/scenario/generator.py

Generates Bull / Base / Bear investment scenarios with formulaic confidence scores.
Final step in the Scenario Engine pipeline.

Confidence formula (traceable, no LLM):
  1. raw_bull = bull_count / total_signals
  2. Adjust by average combined_weight of bull sources
  3. Same for bear
  4. Adjust by analyst_sentiment and yfinance recommendation key consensus
  5. base_conf = 1.0 - bull_conf - bear_conf  (clamped to min 0.05)
  6. Scores always sum to 1.0

Input:  signal_counts (dict), scored_sources (list), raw_brief (dict)
Output: scenarios (dict) — "scenarios" portion of Contract [E]
"""

import os
import json
import logging
import httpx
from openai import OpenAI

logger = logging.getLogger(__name__)


def _get_openai_client():
    aiml_key = os.getenv("AIML_API_KEY")
    if aiml_key:
        return OpenAI(
            api_key=aiml_key,
            base_url="https://api.aimlapi.com/v1",
            http_client=httpx.Client(http2=False)
        )
    return OpenAI()


def _get_model():
    if os.getenv("AIML_API_KEY"):
        return "meta-llama/Llama-3.3-70B-Instruct-Turbo"
    return "gpt-4o-mini"


def _avg_weight(signals: list, source_map: dict, fallback: float = 0.9) -> float:
    weights = []
    for sig in signals:
        sid = sig.get("source_id") if isinstance(sig, dict) else None
        src = source_map.get(sid)
        weights.append(src.get("combined_weight", fallback) if src else fallback)
    return sum(weights) / len(weights) if weights else 1.0


def _get_yfinance_data(ticker: str) -> dict:
    """Fetch yfinance data once and reuse for confidence + expected_move + sentiment_trend."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        info = t.info

        rec_key = str(info.get("recommendationKey", "NEUTRAL")).upper()
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        target_mean = info.get("targetMeanPrice")
        target_low = info.get("targetLowPrice")
        target_high = info.get("targetHighPrice")
        num_analysts = info.get("numberOfAnalystOpinions", 0)

        rec_trend = {}
        try:
            recs = t.recommendations
            if recs is not None and not recs.empty:
                recent = recs.tail(10)
                upgrades = sum(1 for _, r in recent.iterrows()
                               if str(r.get("To Grade", "")).lower() in ["buy", "strong buy", "outperform", "overweight"])
                downgrades = sum(1 for _, r in recent.iterrows()
                                 if str(r.get("To Grade", "")).lower() in ["sell", "underperform", "underweight"])
                rec_trend = {"upgrades_recent": upgrades, "downgrades_recent": downgrades}
        except Exception:
            pass

        return {
            "recommendation_key": rec_key,
            "current_price": current_price,
            "target_mean": target_mean,
            "target_low": target_low,
            "target_high": target_high,
            "num_analysts": num_analysts,
            "rec_trend": rec_trend,
        }
    except Exception:
        return {"recommendation_key": "NEUTRAL"}


def compute_confidence(signal_counts: dict, scored_sources: list, raw_brief: dict, yf_data: dict = None) -> dict:
    """Returns confidence scores AND a full breakdown showing the math."""
    bull_count = signal_counts.get("bull_count", 0)
    bear_count = signal_counts.get("bear_count", 0)
    total      = bull_count + bear_count

    if total == 0:
        return {
            "scores": {"bull": 0.33, "base": 0.34, "bear": 0.33},
            "breakdown": {
                "bull": {"raw_signal_ratio": 0.0, "authority_adjustment": 0.0, "sentiment_adjustment": 0.0, "yfinance_adjustment": 0.0},
                "bear": {"raw_signal_ratio": 0.0, "authority_adjustment": 0.0, "sentiment_adjustment": 0.0, "yfinance_adjustment": 0.0},
            }
        }

    source_map  = {src.get("id"): src for src in scored_sources if src.get("id")}
    bull_signals = raw_brief.get("bull_signals") or []
    bear_signals = raw_brief.get("bear_signals") or []
    risk_flags   = raw_brief.get("risk_flags") or []

    bear_all = bear_signals + [r for r in risk_flags if isinstance(r, dict)]
    bear_all += [{"source_id": None}] * sum(1 for r in risk_flags if isinstance(r, str))

    raw_bull_ratio = bull_count / total
    raw_bear_ratio = bear_count / total

    bull_avg_weight = _avg_weight(bull_signals, source_map)
    bear_avg_weight = _avg_weight(bear_all, source_map)
    adj_bull = raw_bull_ratio * bull_avg_weight
    adj_bear = raw_bear_ratio * bear_avg_weight
    bull_authority_adj = round(adj_bull - raw_bull_ratio, 4)
    bear_authority_adj = round(adj_bear - raw_bear_ratio, 4)

    sentiment = str(raw_brief.get("analyst_sentiment", "neutral")).lower()
    sentiment_bias = 0.0
    if sentiment == "bullish":
        sentiment_bias = 0.15
    elif sentiment == "bearish":
        sentiment_bias = -0.15

    yf_rec = (yf_data or {}).get("recommendation_key", "NEUTRAL")
    yf_bias = 0.0
    if yf_rec == "STRONG_BUY":
        yf_bias = 0.20
    elif yf_rec == "BUY":
        yf_bias = 0.10
    elif yf_rec == "STRONG_SELL":
        yf_bias = -0.20
    elif yf_rec == "SELL":
        yf_bias = -0.10

    total_bias = sentiment_bias + yf_bias
    adj_bull += total_bias
    adj_bear -= total_bias

    adj_bull = max(0.02, adj_bull)
    adj_bear = max(0.02, adj_bear)

    total_adj = adj_bull + adj_bear
    if total_adj >= 0.95:
        scale     = 0.95 / total_adj
        bull_conf = round(adj_bull * scale, 2)
        bear_conf = round(adj_bear * scale, 2)
    else:
        bull_conf = round(adj_bull, 2)
        bear_conf = round(adj_bear, 2)

    base_conf = round(max(0.05, 1.0 - bull_conf - bear_conf), 2)

    total_conf = bull_conf + base_conf + bear_conf
    if total_conf != 1.0:
        base_conf = round(1.0 - bull_conf - bear_conf, 2)

    source_type_counts = {}
    for src in scored_sources:
        stype = src.get("type", "news")
        if stype not in source_type_counts:
            source_type_counts[stype] = {"weight": src.get("authority_weight", 0.9), "count": 0}
        source_type_counts[stype]["count"] += 1
    source_weights_used = [
        {"source_type": k, "weight": v["weight"], "count": v["count"]}
        for k, v in source_type_counts.items()
    ]

    breakdown = {
        "bull": {
            "raw_signal_ratio": round(raw_bull_ratio, 4),
            "authority_adjustment": bull_authority_adj,
            "sentiment_adjustment": round(sentiment_bias, 2),
            "yfinance_adjustment": round(yf_bias, 2),
            "yfinance_consensus": yf_rec,
            "source_weights_used": source_weights_used,
        },
        "bear": {
            "raw_signal_ratio": round(raw_bear_ratio, 4),
            "authority_adjustment": bear_authority_adj,
            "sentiment_adjustment": round(-sentiment_bias, 2),
            "yfinance_adjustment": round(-yf_bias, 2),
            "yfinance_consensus": yf_rec,
            "source_weights_used": source_weights_used,
        },
    }

    return {
        "scores": {"bull": bull_conf, "base": base_conf, "bear": bear_conf},
        "breakdown": breakdown,
    }


def _compute_expected_move(yf_data: dict, historical_matches: list = None) -> dict:
    """Compute expected price move ranges from yfinance targets + historical returns."""
    current = yf_data.get("current_price")
    target_low = yf_data.get("target_low")
    target_high = yf_data.get("target_high")
    target_mean = yf_data.get("target_mean")

    if current and target_mean:
        mean_pct = ((target_mean / current) - 1) * 100
        bull_high = f"+{((target_high / current) - 1) * 100:.0f}%" if target_high else f"+{mean_pct * 1.2:.0f}%"
        bull_low = f"+{max(1, mean_pct * 0.5):.0f}%"
        bear_low = f"-{abs(mean_pct * 0.8):.0f}%"
        bear_high = f"-{max(1, abs(mean_pct * 0.3)):.0f}%"
        base_low = f"-{max(1, mean_pct * 0.1):.0f}%"
        base_high = f"+{max(1, mean_pct * 0.3):.0f}%"

        return {
            "bull": {"range_low": bull_low, "range_high": bull_high, "based_on": "analyst_price_targets"},
            "base": {"range_low": base_low, "range_high": base_high, "based_on": "analyst_price_targets"},
            "bear": {"range_low": bear_low, "range_high": bear_high, "based_on": "analyst_price_targets"},
        }

    return {
        "bull": {"range_low": "+5%", "range_high": "+15%", "based_on": "default_estimate"},
        "base": {"range_low": "-2%", "range_high": "+5%", "based_on": "default_estimate"},
        "bear": {"range_low": "-15%", "range_high": "-5%", "based_on": "default_estimate"},
    }


def _generate_llm_content(ticker: str, sentiment: str, drivers: list, risks: list, confidence: dict) -> dict:
    """Single LLM call that generates summaries, triggers, and verdict."""
    try:
        client = _get_openai_client()
        model = _get_model()

        system_prompt = (
            "You are a senior buy-side research analyst. Draft investment scenario summaries, "
            "key triggers, and a verdict for the upcoming earnings print.\n\n"
            "Writing guidelines:\n"
            "- Sound like a real analyst, not a bot. Write premium financial prose.\n"
            "- Do NOT copy-paste drivers or risks verbatim. Synthesize into cohesive narratives.\n"
            "- Keep each summary brief: exactly 1-2 clear, dense sentences.\n"
            "- Triggers are specific, measurable events that would confirm the scenario.\n"
            "- Verdict is one sentence summarizing the overall setup.\n"
            "- Return ONLY valid JSON, no markdown fences."
        )

        user_prompt = (
            f"Draft scenarios for {ticker} (analyst sentiment: {sentiment}).\n\n"
            f"Bull confidence: {confidence.get('bull', 0.5):.0%} | "
            f"Bear confidence: {confidence.get('bear', 0.1):.0%}\n\n"
            f"Key Bull Drivers:\n{json.dumps(drivers, indent=2)}\n\n"
            f"Key Downside Risks:\n{json.dumps(risks, indent=2)}\n\n"
            "Return this exact JSON structure:\n"
            "{\n"
            '  "bull_summary": "1-2 sentence bull case",\n'
            '  "base_summary": "1-2 sentence base case",\n'
            '  "bear_summary": "1-2 sentence bear case",\n'
            '  "bull_triggers": ["trigger 1", "trigger 2"],\n'
            '  "bear_triggers": ["trigger 1", "trigger 2"],\n'
            '  "base_triggers": ["trigger 1", "trigger 2"],\n'
            '  "verdict_tldr": "One sentence overall setup summary"\n'
            "}"
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        content = response.choices[0].message.content.strip()

        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        return json.loads(content.strip())
    except Exception as e:
        logger.warning(f"LLM content generation failed: {e}. Using rule-based fallbacks.")
        return {}


def generate_scenarios(signal_counts: dict, scored_sources: list, raw_brief: dict) -> dict:
    ticker       = raw_brief.get("ticker", "the company")
    sentiment    = raw_brief.get("analyst_sentiment", "neutral")

    yf_data = _get_yfinance_data(ticker) if ticker != "the company" else {}

    conf_result  = compute_confidence(signal_counts, scored_sources, raw_brief, yf_data)
    confidence   = conf_result["scores"]
    breakdown    = conf_result["breakdown"]

    bull_signals = raw_brief.get("bull_signals") or []
    bear_signals = raw_brief.get("bear_signals") or []
    risk_flags   = raw_brief.get("risk_flags") or []

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
        fb_bull_summary = f"Strong growth prospects for {ticker} driven by: {drivers[0]} Additionally, {drivers[1]}."
    else:
        fb_bull_summary = f"Positive outlook for {ticker} supported by: {drivers[0]}"

    if len(risks) >= 2:
        fb_bear_summary = f"Downside pressure on {ticker} due to: {risks[0]} Also compounded by: {risks[1]}."
    else:
        fb_bear_summary = f"Negative outlook for {ticker} primarily due to: {risks[0]}"

    if drivers and risks:
        fb_base_summary = f"Moderate growth for {ticker}. While {drivers[0]} is positive, it is offset by concerns around {risks[0]}."
    elif drivers:
        fb_base_summary = f"Steady performance for {ticker} anchored by {drivers[0]} with neutral expectations elsewhere."
    elif risks:
        fb_base_summary = f"Sideways trading for {ticker} as progress is capped by {risks[0]}."
    else:
        fb_base_summary = f"Base scenario assumes business-as-usual operations for {ticker}."

    fb_bull_triggers = [f"{ticker} beats EPS and revenue consensus estimates", f"Management raises forward guidance"]
    fb_bear_triggers = [f"{ticker} misses EPS or revenue estimates", f"Management lowers or withdraws guidance"]
    fb_base_triggers = [f"{ticker} meets consensus with inline guidance", f"No major surprises in key metrics"]

    top_scenario = max(confidence, key=confidence.get)
    fb_verdict = (
        f"{top_scenario.capitalize()} case most likely at {confidence[top_scenario]:.0%} confidence. "
        f"Key driver: {drivers[0] if top_scenario == 'bull' else risks[0]}."
    )

    llm = _generate_llm_content(ticker, sentiment, drivers, risks, confidence)

    bull_summary  = llm.get("bull_summary", fb_bull_summary)
    base_summary  = llm.get("base_summary", fb_base_summary)
    bear_summary  = llm.get("bear_summary", fb_bear_summary)
    bull_triggers = llm.get("bull_triggers", fb_bull_triggers)
    bear_triggers = llm.get("bear_triggers", fb_bear_triggers)
    base_triggers = llm.get("base_triggers", fb_base_triggers)
    verdict_tldr  = llm.get("verdict_tldr", fb_verdict)

    expected_move = _compute_expected_move(yf_data)

    verdict_confidence = "high" if confidence[top_scenario] >= 0.60 else ("medium" if confidence[top_scenario] >= 0.40 else "low")
    watchlist = "top" if verdict_confidence == "high" else ("watch" if verdict_confidence == "medium" else "monitor")

    return {
        "bull": {
            "summary": bull_summary,
            "confidence": confidence["bull"],
            "confidence_breakdown": breakdown.get("bull", {}),
            "drivers": drivers[:3],
            "triggers": bull_triggers[:2],
            "expected_move": expected_move.get("bull", {}),
        },
        "base": {
            "summary": base_summary,
            "confidence": confidence["base"],
            "drivers": drivers[:2] + risks[:1],
            "triggers": base_triggers[:2],
            "expected_move": expected_move.get("base", {}),
        },
        "bear": {
            "summary": bear_summary,
            "confidence": confidence["bear"],
            "confidence_breakdown": breakdown.get("bear", {}),
            "risks": risks[:3],
            "triggers": bear_triggers[:2],
            "expected_move": expected_move.get("bear", {}),
        },
        "verdict": {
            "tldr": verdict_tldr,
            "recommended_scenario": top_scenario,
            "confidence_level": verdict_confidence,
            "watchlist_priority": watchlist,
        },
        "_yf_data": yf_data,  # pass through for enricher to use
    }
