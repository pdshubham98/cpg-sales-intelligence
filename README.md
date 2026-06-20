# CPG Sales Intelligence

AI-powered analytics platform for CPG revenue forecasting, data quality validation, and natural language business insights.

## Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| UI | Streamlit (4-page dashboard) |
| Storage | SQLite (WAL mode) |
| Ingestion | Pandas + multi-source adapter pattern + 9 quality rules |
| Forecasting | scikit-learn LinearRegression with cyclical seasonal features |
| LLM | Groq `llama-3.3-70b-versatile` (primary) / Gemini `gemini-1.5-flash` (fallback) |
| Tests | pytest — 69 tests, all mocked |
| CI/CD | GitHub Actions (secrets scan → lint → test → Docker build) |
| Container | Docker + docker-compose |

## Quickstart (Local)

```bash
# 1. Clone and enter the project
git clone https://github.com/pdshubham98/cpg-sales-intelligence.git
cd cpg-sales-intelligence

# 2. Create your .env file
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the API (runs ingestion automatically on startup)
uvicorn src.api.main:app --reload

# 5. In a second terminal, start the UI
streamlit run ui/app.py
```

- API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Dashboard: http://localhost:8501

## Quickstart (Docker)

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

docker-compose up --build
```

Both services start automatically. No other setup required.

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Service health + DB row counts + last ingestion timestamp |
| GET | `/sales-summary` | Aggregated KPIs by region, category, channel, month |
| POST | `/forecast` | Revenue forecast by region, category, or product |
| POST | `/ask` | Natural language Q&A against sales data + industry benchmarks |
| POST | `/insights` | 5 actionable AI-generated business insights |
| GET | `/trends` | LLM-generated trend summary |
| GET | `/market-benchmarks` | Live quarterly revenue for major CPG companies (Yahoo Finance) |
| GET | `/metrics` | Prometheus metrics (request counts, latency, LLM stats, ingestion rows) |

### POST /forecast — example

```json
{
  "dimension_type": "region",
  "dimension_value": "R001",
  "periods": 3
}
```

### POST /ask — example

```json
{
  "question": "Which region has the highest revenue?"
}
```

## Tests

```bash
pytest tests/ -v
```

No API keys required — all LLM calls are mocked.

## LLM Provider

Controlled by the `LLM_PROVIDER` env var:

```bash
LLM_PROVIDER=groq    # default — uses GROQ_API_KEY
LLM_PROVIDER=gemini  # fallback — uses GEMINI_API_KEY
```

Get a free Groq key at https://console.groq.com

**Auto-fallback:** If Groq exhausts all retries (3 attempts with exponential backoff) and `GEMINI_API_KEY` is set, the request automatically falls back to Gemini — no config change needed.

## Optional API Key Auth

Set `SECRET_KEY` in `.env` to enable bearer-token protection on all AI endpoints:

```bash
SECRET_KEY=my-secret-token
```

When set, requests must include `X-Api-Key: my-secret-token`. If `SECRET_KEY` is empty (default), auth is disabled — useful for local dev and demos.

## Observability

The `/metrics` endpoint exposes Prometheus-compatible metrics:

| Metric | Type | Description |
|---|---|---|
| `cpg_http_requests_total` | Counter | Request count by endpoint and status |
| `cpg_http_request_duration_seconds` | Histogram | Request latency by endpoint |
| `cpg_llm_call_duration_seconds` | Histogram | LLM call latency by provider |
| `cpg_llm_errors_total` | Counter | LLM error count by provider |
| `cpg_llm_fallbacks_total` | Counter | Groq→Gemini auto-fallback count |
| `cpg_ingestion_rows` | Gauge | Row counts in DB (sales, products, regions) |

## Incremental Ingestion

The ETL uses `INSERT OR REPLACE` (UPSERT) keyed on `transaction_id`. Running ingestion multiple times is safe and idempotent — existing rows are updated, new rows are appended. Each run writes one row to the `ingestion_log` table (visible via `/health`).

## Project Structure

```
cpg-sales-intelligence/
├── data/raw/          # Source CSVs: sales_transactions (POS), sales_ecommerce, products, regions
├── src/
│   ├── ingestion/     # Multi-source ETL loader + SQLite schema
│   ├── forecasting/   # Linear regression model with seasonal features
│   ├── insights/      # LLM layer (Groq / Gemini)
│   ├── market/        # Live industry benchmarks via Yahoo Finance
│   └── api/           # FastAPI app + routes
├── ui/                # Streamlit dashboard (Overview, Forecasting, Sales Assistant, AI Insights)
├── tests/             # 69 pytest tests
├── docs/              # Architecture diagram, ADR, video script
└── .github/workflows/ # GitHub Actions CI
```

## Architecture

See [docs/architecture.md](docs/architecture.md) and [docs/adr/ADR-001.md](docs/adr/ADR-001.md).
