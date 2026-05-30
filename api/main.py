"""
api/main.py

FastAPI application entry point.

Endpoints:
    POST /brief/{ticker}   — full enriched brief (cache-first)
    GET  /signals/{ticker} — signals only (lightweight)
    POST /compare          — two tickers in parallel
    GET  /health           — health check
    GET  /cache/status     — shows which demo tickers are cached

Run:
    uvicorn api.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes.brief   import router as brief_router
from api.routes.compare import router as compare_router
from api.cache import cache_status, DEMO_TICKERS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# LIFESPAN — startup / shutdown
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("EarningsEdge API starting up")
    status = cache_status()
    cached = [t for t, s in status.items() if s["cached"]]
    missing = [t for t, s in status.items() if not s["cached"]]

    if cached:
        logger.info(f"Cache warm: {', '.join(cached)}")
    if missing:
        logger.warning(
            f"Cache cold for: {', '.join(missing)} — "
            f"run `python api/cache.py` before demo"
        )

    yield

    # Shutdown
    logger.info("EarningsEdge API shutting down")


# =============================================================================
# APP
# =============================================================================

app = FastAPI(
    title="EarningsEdge",
    description="Autonomous pre-earnings intelligence platform. Ticker in — grounded multi-layer brief out.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins for hackathon demo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(brief_router,   tags=["Brief"])
app.include_router(compare_router, tags=["Compare"])


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/health", tags=["Meta"])
async def health():
    return {"status": "ok", "service": "EarningsEdge"}


# =============================================================================
# CACHE STATUS
# =============================================================================

@app.get("/cache/status", tags=["Meta"])
async def get_cache_status():
    """Shows which demo tickers are pre-cached and ready."""
    status = cache_status()
    all_cached = all(s["cached"] for s in status.values())
    return JSONResponse(content={
        "demo_ready": all_cached,
        "tickers":    status,
    })
