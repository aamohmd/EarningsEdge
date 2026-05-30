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

    # Base weight adjustments
    adj_bull = (bull_count / total) * _avg_weight(bull_signals, source_map)
    adj_bear = (bear_count / total) * _avg_weight(bear_all, source_map)

    # 1. Calibrate using analyst_sentiment from synthesis
    sentiment = str(raw_brief.get("analyst_sentiment", "neutral")).lower()
    sentiment_bias = 0.0
    if sentiment == "bullish":
        sentiment_bias = 0.15
    elif sentiment == "bearish":
        sentiment_bias = -0.15

    # 2. Calibrate using yfinance consensus recommendations
    ticker = raw_brief.get("ticker")
    yf_rec = "NEUTRAL"
    if ticker:
        try:
            import yfinance as yf
            info = yf.Ticker(ticker).info
            yf_rec = str(info.get("recommendationKey", "NEUTRAL")).upper()
        except Exception:
            pass

    yf_bias = 0.0
    if yf_rec == "STRONG_BUY":
        yf_bias = 0.20
    elif yf_rec == "BUY":
        yf_bias = 0.10
    elif yf_rec == "STRONG_SELL":
        yf_bias = -0.20
    elif yf_rec == "SELL":
        yf_bias = -0.10

    # Combine biases
    total_bias = sentiment_bias + yf_bias
    adj_bull += total_bias
    adj_bear -= total_bias

    # Clamp raw adjusted scores to prevent negative or zero bounds
    adj_bull = max(0.02, adj_bull)
    adj_bear = max(0.02, adj_bear)

    total_adj = adj_bull + adj_bear
    if total_adj >= 0.95:
        scale    = 0.95 / total_adj
        bull_conf = round(adj_bull * scale, 2)
        bear_conf = round(adj_bear * scale, 2)
    else:
        bull_conf = round(adj_bull, 2)
        bear_conf = round(adj_bear, 2)

    base_conf = round(max(0.05, 1.0 - bull_conf - bear_conf), 2)
    
    # Ensure they sum exactly to 1.0
    total_conf = bull_conf + base_conf + bear_conf
    if total_conf != 1.0:
        base_conf = round(1.0 - bull_conf - bear_conf, 2)

    return {"bull": bull_conf, "base": base_conf, "bear": bear_conf}


def generate_scenarios(signal_counts: dict, scored_sources: list, raw_brief: dict) -> dict:
    confidence   = compute_confidence(signal_counts, scored_sources, raw_brief)
    bull_signals = raw_brief.get("bull_signals") or []
    bear_signals = raw_brief.get("bear_signals") or []
    risk_flags   = raw_brief.get("risk_flags") or []
    ticker       = raw_brief.get("ticker", "the company")
    sentiment    = raw_brief.get("analyst_sentiment", "neutral")

    drivers = [s.get("text") for s in bull_signals if isinstance(s, dict) and s.get("text")] \
              or ["No significant bull drivers identified."]

    risks = [s.get("text") for s in bear_signals if isinstance(s, dict) and s.get("text")]
    for r in risk_flags:
        if isinstance(r, dict) and r.get("text"):
            risks.append(r["text"])
        elif isinstance(r, str):
            risks.append(r)
    risks = risks or ["No significant downside risks identified."]

    # Rule-based fallback summaries
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

    bull_summary = fb_bull_summary
    base_summary = fb_base_summary
    bear_summary = fb_bear_summary

    # Call OpenAI to rewrite into professional analyst prose
    try:
        client = _get_openai_client()
        model = _get_model()

        system_prompt = (
            "You are a senior buy-side research analyst. Your job is to draft professional, concise investment scenario summaries "
            "(Bull, Base, Bear cases) for the upcoming earnings print.\n\n"
            "Writing guidelines:\n"
            "- Sound like a real analyst, not a bot or a summarizer. Write premium financial prose.\n"
            "- Do NOT copy-paste the drivers or risks verbatim. Instead, synthesize them into a cohesive, flowing narrative.\n"
            "- Keep each summary brief: exactly 1-2 clear, dense sentences.\n"
            "- Do not mention list structure, JSON keys, or metadata in the text.\n"
            "- Return your response strictly as a JSON object with the keys 'bull_summary', 'base_summary', and 'bear_summary'."
        )

        user_prompt = (
            f"Draft the Bull, Base, and Bear scenario summaries for {ticker}.\n\n"
            f"Analyst Sentiment Context: {sentiment}\n\n"
            f"Key Bull Drivers:\n{json.dumps(drivers, indent=2)}\n\n"
            f"Key Downside Risks:\n{json.dumps(risks, indent=2)}\n\n"
            "Provide the output strictly in this JSON format:\n"
            "{\n"
            '  "bull_summary": "...",\n'
            '  "base_summary": "...",\n'
            '  "bear_summary": "..."\n'
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

        parsed = json.loads(content.strip())
        bull_summary = parsed.get("bull_summary", fb_bull_summary)
        base_summary = parsed.get("base_summary", fb_base_summary)
        bear_summary = parsed.get("bear_summary", fb_bear_summary)
    except Exception as e:
        logger.warning(f"LLM scenario summary generation failed: {e}. Using rule-based fallbacks.")

    return {
        "bull": {"summary": bull_summary, "confidence": confidence["bull"], "drivers": drivers[:3]},
        "base": {"summary": base_summary, "confidence": confidence["base"], "drivers": drivers[:2] + risks[:1]},
        "bear": {"summary": bear_summary, "confidence": confidence["bear"], "risks":   risks[:3]},
    }
