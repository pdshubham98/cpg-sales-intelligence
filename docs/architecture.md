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
| ETL Ingestion | `src/ingestion/loader.py` | Load CSVs, apply 8 quality rules, write to SQLite |
| DB Schema | `src/ingestion/schema.py` | SQLite DDL, `get_connection()` |
| Forecasting | `src/forecasting/model.py` | Monthly-aggregate linear regression by region/category |
| LLM Layer | `src/insights/llm.py` | Groq/Gemini routing, trend summary, Q&A, insights |
| FastAPI | `src/api/main.py` + `routes/` | REST API with 6 endpoints |
| Streamlit UI | `ui/app.py` | 4-page dashboard: Overview, Forecasting, Ask Data, AI Insights |
| Tests | `tests/` | 52 pytest tests, all mocked |
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
| Scale data processing | pandas | Replace `loader.py` with PySpark; same quality rules, distributed execution |
| Scale storage | SQLite | Replace `get_connection()` with PostgreSQL (`psycopg2`); schema is compatible |
| LLM provider | Groq / Gemini | Add case to `_call_llm()` in `llm.py`; one `LLM_PROVIDER` env var change |
| Forecasting model | LinearRegression | Replace `model.py` with Prophet or XGBoost; same interface |
| Deployment | Docker single-host | Push image to ECR + deploy to ECS or Kubernetes |
