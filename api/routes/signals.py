from fastapi import APIRouter

signals_router = APIRouter(prefix="/signals", tags=["signals"])

@signals_router.get("/{ticker}")
async def get_signals(ticker: str):
    """
    Get lightweight signals for a given ticker.
    (Setup stub - no logic implemented yet)
    """
    return {
        "status": "stub",
        "ticker": ticker.upper(),
        "message": "Signals setup stub"
    }
