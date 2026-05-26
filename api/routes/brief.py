from fastapi import APIRouter, HTTPException

brief_router = APIRouter(prefix="/brief", tags=["brief"])

@brief_router.post("/{ticker}")
async def generate_brief(ticker: str):
    """
    Generate raw earnings brief for a given ticker.
    (Setup stub - no logic implemented yet)
    """
    return {
        "status": "stub",
        "ticker": ticker.upper(),
        "message": "Brief setup stub"
    }