from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from src.ingestion.loader import run_ingestion
from src.api.routes import health, forecast, summary, ask, market

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_ingestion_report: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ingestion_report
    logger.info("Running data ingestion on startup...")
    _ingestion_report = run_ingestion()
    logger.info("Ingestion complete: %s", _ingestion_report)
    yield


app = FastAPI(
    title="CPG Sales Intelligence API",
    description="AI-powered CPG sales analytics: forecasting, insights, and natural language Q&A.",
    version="3.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(forecast.router)
app.include_router(summary.router)
app.include_router(ask.router)
app.include_router(market.router)


@app.get("/data-quality", tags=["health"])
def data_quality():
    """Returns the ingestion quality report from the last startup run."""
    return _ingestion_report
