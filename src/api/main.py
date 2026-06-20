import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from src.ingestion.loader import run_ingestion
from src.api.routes import health, forecast, summary, ask, market
from src.api.routes.metrics_route import router as metrics_router
from src.api.metrics import REQUEST_COUNT, REQUEST_LATENCY, INGESTION_ROWS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_ingestion_report: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ingestion_report
    logger.info("Running data ingestion on startup...")
    _ingestion_report = run_ingestion()
    logger.info("Ingestion complete: %s", _ingestion_report)
    # Publish ingestion row counts to Prometheus
    INGESTION_ROWS.labels(type="raw").set(_ingestion_report.get("raw_rows", 0))
    INGESTION_ROWS.labels(type="clean").set(_ingestion_report.get("clean_rows", 0))
    INGESTION_ROWS.labels(type="dropped").set(_ingestion_report.get("dropped_rows", 0))
    yield


app = FastAPI(
    title="CPG Sales Intelligence API",
    description="AI-powered CPG sales analytics: forecasting, insights, and natural language Q&A.",
    version="3.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    endpoint = request.url.path
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=endpoint,
        status=response.status_code,
    ).inc()
    REQUEST_LATENCY.labels(endpoint=endpoint).observe(duration)
    return response


app.include_router(health.router)
app.include_router(forecast.router)
app.include_router(summary.router)
app.include_router(ask.router)
app.include_router(market.router)
app.include_router(metrics_router)


@app.get("/data-quality", tags=["health"])
def data_quality():
    """Returns the ingestion quality report from the last startup run."""
    return _ingestion_report
