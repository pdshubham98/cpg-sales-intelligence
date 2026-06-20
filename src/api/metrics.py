"""
Prometheus metrics definitions.
Import this module once — counters/histograms are module-level singletons.
"""
from prometheus_client import Counter, Histogram, Gauge

REQUEST_COUNT = Counter(
    "cpg_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "cpg_http_request_duration_seconds",
    "HTTP request latency",
    ["endpoint"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

LLM_LATENCY = Histogram(
    "cpg_llm_call_duration_seconds",
    "LLM API call latency",
    ["provider"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

LLM_ERRORS = Counter(
    "cpg_llm_errors_total",
    "LLM call failures",
    ["provider"],
)

LLM_FALLBACKS = Counter(
    "cpg_llm_fallbacks_total",
    "Times Groq fell back to Gemini",
)

INGESTION_ROWS = Gauge(
    "cpg_ingestion_rows",
    "Row counts from last ingestion run",
    ["type"],  # raw, clean, dropped
)
