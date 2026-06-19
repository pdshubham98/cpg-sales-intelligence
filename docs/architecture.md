# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Docker Container                     │
│                                                             │
│  ┌─────────────┐        ┌──────────────────────────────┐   │
│  │  Streamlit  │───────▶│        FastAPI               │   │
│  │  UI :8501   │  HTTP  │  /health  /forecast          │   │
│  │  4 pages    │        │  /sales-summary  /ask        │   │
│  └─────────────┘        │  /insights  /trends          │   │
│                         └──────────┬─────────────────┬─┘   │
│                                    │                 │      │
│                         ┌──────────▼──┐    ┌────────▼────┐ │
│                         │   SQLite    │    │  LLM Layer  │ │
│                         │  db/sales.db│    │  (Groq API  │ │
│                         │             │    │  / Gemini)  │ │
│                         └─────────────┘    └─────────────┘ │
│                                ▲                            │
│                    ┌───────────┴───────┐                    │
│                    │  ETL Ingestion    │                    │
│                    │  + 8 Quality Rules│                    │
│                    └───────────┬───────┘                    │
│                                │                            │
│                    ┌───────────▼───────┐                    │
│                    │  data/raw/  CSVs  │                    │
│                    │  sales_transactions│                   │
│                    │  products  regions│                    │
│                    └───────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
                              ▲
                   ┌──────────┴──────────┐
                   │  GitHub Actions CI  │
                   │  lint → test → build│
                   └─────────────────────┘
```

## Component Responsibilities

| Component | File(s) | Responsibility |
|---|---|---|
| ETL Ingestion | `src/ingestion/loader.py` | Multi-source adapter pattern; 9 quality rules; EUR→USD normalisation; late-arriving detection |
| DB Schema | `src/ingestion/schema.py` | SQLite DDL, `get_connection()` |
| Forecasting | `src/forecasting/model.py` | Linear regression with cyclical seasonal features (sin/cos month) by region/category/product |
| LLM Layer | `src/insights/llm.py` | Groq/Gemini routing, trend summary, Q&A, insights |
| Market Data | `src/market/benchmarks.py` | Live quarterly revenue for major CPG companies via Yahoo Finance |
| FastAPI | `src/api/main.py` + `routes/` | REST API with 7 endpoints |
| Streamlit UI | `ui/app.py` | 4-page dashboard: Overview, Forecasting, Sales Assistant, AI Insights |
| Tests | `tests/` | 60 pytest tests, all mocked |
| CI | `.github/workflows/ci.yml` | Lint → test → Docker build + smoke test |

## Data Flow

1. Container starts → FastAPI lifespan triggers `run_ingestion()`
2. Ingestion reads `data/raw/*.csv`, applies 8 quality rules, writes clean data to SQLite
3. FastAPI routes query SQLite for analytics and forecasting
4. LLM routes fetch aggregated context from SQLite, then call Groq/Gemini API
5. Streamlit calls FastAPI over HTTP, renders results in the browser

## Extension Points

| What to extend | Current | Next step |
|---|---|---|
| Add a new data source | Two CSV sources with adapter pattern | Add entry to `_SOURCE_REGISTRY` in `loader.py` with a new adapter function |
| Scale data processing | pandas | Replace `loader.py` with PySpark; same quality rules, distributed execution |
| Scale storage | SQLite | Replace `get_connection()` with PostgreSQL (`psycopg2`); schema is compatible |
| LLM provider | Groq / Gemini | Add case to `_call_llm()` in `llm.py`; one `LLM_PROVIDER` env var change |
| Forecasting model | LinearRegression + seasonal features | Replace `model.py` with Prophet or XGBoost; same interface |
| Currency conversion | Fixed EUR→USD rate in `loader.py` | Replace `_EUR_TO_USD` constant with a live FX API call |
| Market benchmarks | Yahoo Finance via yfinance | Swap `get_quarterly_revenue()` for any financial data provider |
| Deployment | Docker single-host | Push image to ECR + deploy to ECS or Kubernetes |
