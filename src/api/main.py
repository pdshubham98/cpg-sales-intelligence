from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from src.ingestion.loader import run_ingestion
from src.api.routes import health, forecast, summary, ask

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Running data ingestion on startup...")
    run_ingestion()
    logger.info("Ingestion complete.")
    yield


app = FastAPI(
    title="CPG Sales Intelligence API",
    description="AI-powered CPG sales analytics: forecasting, insights, and natural language Q&A.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(forecast.router)
app.include_router(summary.router)
app.include_router(ask.router)
