from fastapi import APIRouter
from pydantic import BaseModel

compare_router = APIRouter(prefix="/compare", tags=["compare"])

class CompareRequest(BaseModel):
    tickers: list[str]

@compare_router.post("")
async def compare_tickers(request: CompareRequest):
    """
    Run pipeline for multiple tickers in parallel and return the briefs.
    (Setup stub - no logic implemented yet)
    """
    return {
        "status": "stub",
        "tickers": [ticker.upper() for ticker in request.tickers],
        "message": "Compare setup stub"
    }
