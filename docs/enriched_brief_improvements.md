# Enriched Brief [E] — Proposed Improvements

> Improvements we can add to the JSON output to make it richer, more actionable, and more impressive for judges.

---

## Current [E] Output (Baseline)

```json
{
  "scenarios": {
    "bull":  {"summary": "string", "confidence": 0.65, "drivers": ["string"]},
    "base":  {"summary": "string", "confidence": 0.25, "drivers": ["string"]},
    "bear":  {"summary": "string", "confidence": 0.10, "risks":   ["string"]}
  },
  "historical_matches": [
    {
      "quarter": "Q2 2023",
      "similarity_score": 0.92,
      "setup_summary": "string",
      "outcome": "string",
      "return_5d": "+28.4%"
    }
  ]
}
```

---

## 1. Add Confidence Breakdown (Show the Math)

**Why:** Judges will ask "where does 65% come from?" — showing the breakdown makes it defensible.

```json
"scenarios": {
  "bull": {
    "summary": "...",
    "confidence": 0.65,
    "confidence_breakdown": {
      "raw_signal_ratio": 0.67,
      "authority_adjustment": "+0.05",
      "recency_adjustment": "-0.07",
      "source_weights_used": [
        {"source_type": "filing", "weight": 1.4, "count": 2},
        {"source_type": "transcript", "weight": 1.2, "count": 1}
      ]
    },
    "drivers": ["..."]
  }
}
```

---

## 2. Add Key Triggers Per Scenario

**Why:** Tells the reader what to watch for — if trigger X happens, scenario Y becomes more likely.

```json
"bull": {
  "summary": "...",
  "confidence": 0.65,
  "drivers": ["..."],
  "triggers": [
    "Blackwell shipment numbers exceed 100K units in guidance",
    "Gross margin guidance returns above 76%"
  ]
}
```

---

## 3. Add Price Target Ranges

**Why:** Makes the output actionable for traders. Even rough ranges add value.

```json
"bull": {
  "summary": "...",
  "confidence": 0.65,
  "expected_move": {
    "range_low": "+8%",
    "range_high": "+15%",
    "based_on": "historical_matches"
  }
}
```

> This can be computed from the `return_5d` values in historical matches.

---

## 4. Add Signal Quality Metadata

**Why:** Not all signals are equal — a signal from a 10-K filing is stronger than a news rumor.

```json
"scenarios": {
  "signal_quality_summary": {
    "total_signals": 5,
    "high_authority_signals": 3,
    "low_authority_signals": 2,
    "avg_source_recency_days": 12,
    "freshest_source": "2024-05-20T00:00:00Z",
    "oldest_source": "2024-04-15T00:00:00Z"
  }
}
```

---

## 5. Add Contradiction Impact

**Why:** Shows the reader what conflicting information existed and how it affected the confidence.

```json
"contradiction_impact": {
  "contradictions_found": 1,
  "confidence_impact": "-0.05 on bull",
  "details": [
    {
      "claim_a": "News: Blackwell production delayed",
      "claim_b": "CEO: Blackwell is in full production",
      "resolution": "Prioritized direct management quote",
      "affected_scenario": "bull",
      "net_effect": "Maintained bull confidence — management source outweighs news"
    }
  ]
}
```

---

## 6. Add Quantitative Grounding (yFinance / Polygon Data)

**Why:** Adds hard financial numbers alongside the qualitative analysis. Makes it feel like a real analyst report.

```json
"quantitative_context": {
  "current_price": 924.50,
  "consensus_eps": 5.57,
  "forward_pe": 42.3,
  "revenue_growth_yoy": "122%",
  "options_implied_move": "±9.2%",
  "short_interest_pct": "1.2%",
  "data_source": "yfinance"
}
```

---

## 7. Add Sentiment Trend (Not Just Current State)

**Why:** Shows whether sentiment is improving or deteriorating over time, not just a snapshot.

```json
"sentiment_trend": {
  "current": "bullish",
  "30d_ago": "neutral",
  "direction": "improving",
  "momentum": "strong",
  "analyst_upgrades_30d": 3,
  "analyst_downgrades_30d": 0
}
```

---

## 8. Enrich Historical Matches with More Context

**Why:** Current matches only have summary + outcome. Adding more detail makes the pattern matching more convincing.

```json
"historical_matches": [
  {
    "quarter": "Q2 2023",
    "ticker": "NVDA",
    "similarity_score": 0.92,
    "setup_summary": "...",
    "outcome": "...",
    "return_5d": "+28.4%",
    "return_30d": "+35.1%",
    "earnings_surprise_pct": "+22%",
    "pre_earnings_sentiment": "bullish",
    "key_similarity_factors": [
      "Architecture transition (Ampere → Hopper vs Hopper → Blackwell)",
      "Massive data center demand surge",
      "Supply chain concerns present but contained"
    ],
    "key_differences": [
      "Current valuation is 3x higher than Q2 2023",
      "Export restrictions are a new factor"
    ]
  }
]
```

---

## 9. Add a Risk Matrix

**Why:** Consolidates all risk factors into a structured, scannable format.

```json
"risk_matrix": [
  {
    "risk": "US export controls on China",
    "probability": "medium",
    "impact": "high",
    "affected_revenue_pct": "~10%",
    "scenario_most_affected": "bear"
  },
  {
    "risk": "TSMC CoWoS packaging bottleneck",
    "probability": "low",
    "impact": "medium",
    "affected_revenue_pct": "~5%",
    "scenario_most_affected": "base"
  }
]
```

---

## 10. Add an Overall Verdict / TL;DR

**Why:** Busy readers want the bottom line. One sentence that summarizes everything.

```json
"verdict": {
  "tldr": "Strong bull case driven by Blackwell demand and data center momentum. Key risk is export controls. Setup closely resembles Q2 2023 which saw +28% post-earnings.",
  "recommended_scenario": "bull",
  "confidence_level": "high",
  "watchlist_priority": "top"
}
```

---

## Full Improved [E] Schema (All Improvements Combined)

```json
{
  "ticker": "NVDA",
  "generated_at": "2024-05-22T10:05:00Z",
  "enrichment_latency_ms": 8400,

  "verdict": {
    "tldr": "...",
    "recommended_scenario": "bull",
    "confidence_level": "high",
    "watchlist_priority": "top"
  },

  "scenarios": {
    "bull": {
      "summary": "...",
      "confidence": 0.65,
      "confidence_breakdown": { "..." : "..." },
      "drivers": ["..."],
      "triggers": ["..."],
      "expected_move": { "range_low": "+8%", "range_high": "+15%" }
    },
    "base": {
      "summary": "...",
      "confidence": 0.25,
      "confidence_breakdown": { "..." : "..." },
      "drivers": ["..."],
      "triggers": ["..."],
      "expected_move": { "range_low": "-2%", "range_high": "+5%" }
    },
    "bear": {
      "summary": "...",
      "confidence": 0.10,
      "confidence_breakdown": { "..." : "..." },
      "risks": ["..."],
      "triggers": ["..."],
      "expected_move": { "range_low": "-12%", "range_high": "-5%" }
    }
  },

  "signal_quality_summary": {
    "total_signals": 5,
    "high_authority_signals": 3,
    "low_authority_signals": 2,
    "avg_source_recency_days": 12
  },

  "contradiction_impact": {
    "contradictions_found": 1,
    "details": ["..."]
  },

  "quantitative_context": {
    "current_price": 924.50,
    "consensus_eps": 5.57,
    "forward_pe": 42.3,
    "options_implied_move": "±9.2%"
  },

  "sentiment_trend": {
    "current": "bullish",
    "direction": "improving",
    "momentum": "strong"
  },

  "risk_matrix": [
    { "risk": "...", "probability": "medium", "impact": "high" }
  ],

  "historical_matches": [
    {
      "quarter": "Q2 2023",
      "similarity_score": 0.92,
      "setup_summary": "...",
      "outcome": "...",
      "return_5d": "+28.4%",
      "return_30d": "+35.1%",
      "key_similarity_factors": ["..."],
      "key_differences": ["..."]
    }
  ]
}
```

---

## Priority for Hackathon

| Priority | Improvement | Effort | Impact |
|----------|------------|--------|--------|
| 🟢 P0 | Confidence breakdown (show the math) | Low | High |
| 🟢 P0 | Key triggers per scenario | Low | High |
| 🟢 P0 | Verdict / TL;DR | Low | High |
| 🟡 P1 | Quantitative grounding (yFinance) | Medium | High |
| 🟡 P1 | Enriched historical matches (similarity factors + differences) | Medium | High |
| 🟡 P1 | Risk matrix | Low | Medium |
| 🟡 P1 | Signal quality metadata | Low | Medium |
| 🔵 P2 | Expected price move ranges | Medium | Medium |
| 🔵 P2 | Sentiment trend | Medium | Medium |
| 🔵 P2 | Contradiction impact details | Low | Low |

> [!TIP]
> Start with P0 items — they're low effort, high impact, and will impress judges the most. P1 items should come in Phase 4-5 if time allows.
