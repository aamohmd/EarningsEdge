"""
api/routes/compare.py

POST /compare — runs two tickers in parallel via asyncio.gather
Returns both enriched briefs side by side.

Demo usage: NVDA vs AMD comparison in under 45 seconds (cached: instant)
"""

import asyncio
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agent.graph import run_pipeline
from api.cache import get_cached

router = APIRouter()


class CompareRequest(BaseModel):
    tickers: list[str]


@router.post("/compare")
async def compare_tickers(request: CompareRequest):
    """
    Runs two tickers in parallel and returns both briefs side by side.

    Both cache hits:    ~instant
    One cache, one live: ~15-35s
    Both live:           ~35s (parallel, not sequential)
    """
    tickers = [t.upper().strip() for t in request.tickers]

    # Validate
    if len(tickers) != 2:
        raise HTTPException(
            status_code=400,
            detail="Exactly 2 tickers required for comparison"
        )
    for t in tickers:
        if not t.isalpha() or len(t) > 6:
            raise HTTPException(status_code=400, detail=f"Invalid ticker: {t}")

    if tickers[0] == tickers[1]:
        raise HTTPException(status_code=400, detail="Tickers must be different")

    start = time.time()

    async def get_brief(ticker: str) -> dict:
        """Gets brief from cache or live pipeline."""
        cached = get_cached(ticker)
        if cached:
            return {**cached, "_source": "cache"}
        result = await run_pipeline(ticker)
        return {**result, "_source": "live"}

    # Run both in parallel
    results = await asyncio.gather(
        get_brief(tickers[0]),
        get_brief(tickers[1]),
        return_exceptions=True,
    )

    elapsed = round(time.time() - start, 3)

    # Handle individual failures gracefully
    output = {}
    for i, (ticker, result) in enumerate(zip(tickers, results)):
        if isinstance(result, Exception):
            output[ticker] = {
                "error": str(result),
                "ticker": ticker,
            }
        elif "error" in result:
            output[ticker] = result
        else:
            output[ticker] = result

    return JSONResponse(content={
        "comparison": output,
        "_meta": {
            "tickers":    tickers,
            "elapsed_ms": round(elapsed * 1000),
            "sources":    {
                t: results[i].get("_source", "unknown")
                for i, t in enumerate(tickers)
                if not isinstance(results[i], Exception)
            }
        }
    })
