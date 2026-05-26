# Pre-cached NVDA/TSLA/AMD for demo/fallback purposes

CACHE = {
    "NVDA": {
        "ticker": "NVDA",
        "brief_id": "demo-brief-nvda-123",
        "generated_at": "2026-05-26T12:00:00Z",
        "bull_signals": [
            {
                "text": "Data center revenue grew 400% YoY (Demo Cache).",
                "source_id": "demo-source-1",
                "source_type": "filing"
            }
        ],
        "bear_signals": [
            {
                "text": "Gross margins dipped 0.5% due to supply chain costs (Demo Cache).",
                "source_id": "demo-source-2",
                "source_type": "transcript"
            }
        ],
        "risk_flags": [
            "US export restrictions to China affecting revenue."
        ],
        "analyst_sentiment": "bullish",
        "comparable_quarter": "Q2 2025",
        "sources": [],
        "contradictions_resolved": []
    },
    "TSLA": {
        "ticker": "TSLA",
        "brief_id": "demo-brief-tsla-123",
        "generated_at": "2026-05-26T12:00:00Z",
        "bull_signals": [
            {
                "text": "Full Self-Driving (FSD) beta release showing accelerated adoption (Demo Cache).",
                "source_id": "demo-source-3",
                "source_type": "news"
            }
        ],
        "bear_signals": [
            {
                "text": "Automotive gross margins under pressure from pricing actions (Demo Cache).",
                "source_id": "demo-source-4",
                "source_type": "filing"
            }
        ],
        "risk_flags": [
            "Regulatory scrutiny on autopilot systems."
        ],
        "analyst_sentiment": "neutral",
        "comparable_quarter": "Q3 2025",
        "sources": [],
        "contradictions_resolved": []
    },
    "AMD": {
        "ticker": "AMD",
        "brief_id": "demo-brief-amd-123",
        "generated_at": "2026-05-26T12:00:00Z",
        "bull_signals": [
            {
                "text": "MI300 series AI accelerators ramp surpassing expectation (Demo Cache).",
                "source_id": "demo-source-5",
                "source_type": "transcript"
            }
        ],
        "bear_signals": [
            {
                "text": "Client segment recovery remains slower than expected (Demo Cache).",
                "source_id": "demo-source-6",
                "source_type": "news"
            }
        ],
        "risk_flags": [
            "Intense competition in client and data center CPU markets."
        ],
        "analyst_sentiment": "bullish",
        "comparable_quarter": "Q4 2025",
        "sources": [],
        "contradictions_resolved": []
    }
}

def get_cached(ticker: str):
    """
    Retrieve pre-cached brief for a given ticker if available.
    """
    return CACHE.get(ticker.upper(), None)
