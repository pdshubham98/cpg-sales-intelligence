from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

router = APIRouter(tags=["observability"])


@router.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics():
    """Prometheus-format metrics: request counts, LLM latency, ingestion rows."""
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
