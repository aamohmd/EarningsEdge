"""
api/routes/brief.py

POST /brief/{ticker}   — full enriched brief
GET  /signals/{ticker} — bull/bear/risk signals only (lightweight)

Cache-first: checks api/cache.py before running the live pipeline.
Live pipeline still runs for any ticker not in cache.
"""

import time
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from agent.graph import run_pipeline
from api.cache import get_cached

router = APIRouter()


# =============================================================================
# POST /brief/{ticker}
# =============================================================================

@router.post("/brief/{ticker}")
async def get_brief(
    ticker: str,
    use_cache: bool = Query(default=True, description="Set false to force live pipeline run"),
):
    """
    Returns a full enriched pre-earnings intelligence brief for a ticker.

    - Checks cache first for NVDA, TSLA, AMD
    - Runs live pipeline for any other ticker
    - Cache can be bypassed with ?use_cache=false
    """
    ticker = ticker.upper().strip()

    if not ticker.isalpha() or len(ticker) > 6:
        raise HTTPException(status_code=400, detail=f"Invalid ticker: {ticker}")

    start = time.time()

    # Cache check
    if use_cache:
        cached = get_cached(ticker)
        if cached:
            elapsed = round(time.time() - start, 3)
            return JSONResponse(content={
                **cached,
                "_meta": {
                    "source":       "cache",
                    "elapsed_ms":   round(elapsed * 1000),
                }
            })

    # Live pipeline
    try:
        brief = await run_pipeline(ticker)
        elapsed = round(time.time() - start, 3)

        if not brief or "error" in brief:
            raise HTTPException(
                status_code=503,
                detail={
                    "error":   brief.get("error", "pipeline failed"),
                    "ticker":  ticker,
                }
            )

        is_degraded = "data_quality" in brief

        if not is_degraded:
            brief["data_quality"] = {
                "status":             "healthy",
                "web_chunks_fetched": brief.get("pre_synthesis_stats", {}).get("kept_count", "unknown"),
                "cached_at":          None,
                "cache_age_hours":    None,
            }

        return JSONResponse(content={
            **brief,
            "_meta": {
                "source":     "live",
                "elapsed_ms": round(elapsed * 1000),
                "degraded":   is_degraded,
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# GET /signals/{ticker}
# Lightweight endpoint — returns just signals, no scenarios or history
# =============================================================================

@router.get("/signals/{ticker}")
async def get_signals(
    ticker: str,
    use_cache: bool = Query(default=True),
):
    """
    Returns only the bull/bear/risk signals for a ticker.
    Faster response — useful for quick lookups.
    """
    ticker = ticker.upper().strip()

    if not ticker.isalpha() or len(ticker) > 6:
        raise HTTPException(status_code=400, detail=f"Invalid ticker: {ticker}")

    # Try cache first
    brief = get_cached(ticker) if use_cache else None

    if not brief:
        try:
            brief = await run_pipeline(ticker)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    if not brief or "error" in brief:
        raise HTTPException(status_code=503, detail="Pipeline failed")

    return JSONResponse(content={
        "ticker":       brief.get("ticker"),
        "generated_at": brief.get("generated_at"),
        "bull_signals": brief.get("bull_signals", []),
        "bear_signals": brief.get("bear_signals", []),
        "risk_flags":   brief.get("risk_flags", []),
        "analyst_sentiment": brief.get("analyst_sentiment"),
    })
