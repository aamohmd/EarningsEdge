from fastapi import FastAPI
from routes.brief import brief_router
from routes.compare import compare_router
from routes.signals import signals_router

app = FastAPI(
    title="EarningsEdge API",
    description="API for EarningsEdge agents and pipeline",
    version="1.0.0"
)

# Mount the routes
app.include_router(brief_router)
app.include_router(compare_router)
app.include_router(signals_router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}


