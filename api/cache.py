"""
api/cache.py

Pre-cached enriched briefs for demo tickers.
Cache is the fallback, not the cheat — real pipeline still runs for any other ticker.

Usage:
    from api.cache import get_cached, set_cached, DEMO_TICKERS

Pre-populate before demo:
    python api/cache.py
"""

import json
import os
import asyncio
from datetime import datetime
from pathlib import Path

DEMO_TICKERS = ["NVDA", "TSLA", "AMD"]

# Cache stored as JSON files in api/cache_data/
CACHE_DIR = Path(__file__).parent / "cache_data"
CACHE_DIR.mkdir(exist_ok=True)


def get_cached(ticker: str) -> dict | None:
    """Returns cached brief or None if not cached."""
    path = CACHE_DIR / f"{ticker.upper()}.json"
    if not path.exists():
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        print(f"[cache] HIT — {ticker.upper()}")
        return data
    except Exception:
        return None


def set_cached(ticker: str, brief: dict) -> None:
    """Stores a brief in the cache."""
    path = CACHE_DIR / f"{ticker.upper()}.json"
    with open(path, "w") as f:
        json.dump(brief, f, indent=2, default=str)
    print(f"[cache] STORED — {ticker.upper()}")


def clear_cache(ticker: str | None = None) -> None:
    """Clears cache for one ticker or all."""
    if ticker:
        path = CACHE_DIR / f"{ticker.upper()}.json"
        path.unlink(missing_ok=True)
        print(f"[cache] CLEARED — {ticker.upper()}")
    else:
        for f in CACHE_DIR.glob("*.json"):
            f.unlink()
        print("[cache] CLEARED ALL")


def cache_status() -> dict:
    """Returns status of all cached tickers."""
    status = {}
    for ticker in DEMO_TICKERS:
        path = CACHE_DIR / f"{ticker}.json"
        if path.exists():
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            status[ticker] = {
                "cached": True,
                "cached_at": mtime.isoformat(),
                "size_kb": round(path.stat().st_size / 1024, 1),
            }
        else:
            status[ticker] = {"cached": False}
    return status


# =============================================================================
# PRE-POPULATE — run this before the demo
# python api/cache.py
# =============================================================================
async def populate_cache():
    """Runs the full pipeline for all demo tickers and caches results."""
    from agent.graph import run_pipeline

    print("\n" + "=" * 60)
    print("  CACHE PRE-POPULATION")
    print(f"  Tickers: {', '.join(DEMO_TICKERS)}")
    print("=" * 60)

    for ticker in DEMO_TICKERS:
        print(f"\n→ Running pipeline for {ticker}...")
        start = datetime.utcnow()

        try:
            brief = await run_pipeline(ticker)
            elapsed = (datetime.utcnow() - start).total_seconds()

            if brief and "error" not in brief:
                set_cached(ticker, brief)
                print(f"  ✓ {ticker} cached in {elapsed:.1f}s")
            else:
                print(f"  ✗ {ticker} pipeline error: {brief.get('error', 'unknown')}")

        except Exception as e:
            print(f"  ✗ {ticker} exception: {e}")

    print("\n" + "=" * 60)
    print("  CACHE STATUS")
    print("=" * 60)
    for ticker, status in cache_status().items():
        if status["cached"]:
            print(f"  ✓ {ticker} — {status['size_kb']}KB — cached at {status['cached_at']}")
        else:
            print(f"  ✗ {ticker} — NOT CACHED")


if __name__ == "__main__":
    asyncio.run(populate_cache())
