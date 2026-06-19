# CPG Sales Intelligence

AI-powered analytics platform for CPG revenue forecasting, data quality validation, and natural language business insights.

## Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| UI | Streamlit (4-page dashboard) |
| Storage | SQLite (WAL mode) |
| Ingestion | Pandas + 8 quality rules |
| Forecasting | scikit-learn LinearRegression |
| LLM | Groq `llama-3.3-70b-versatile` (primary) / Gemini `gemini-1.5-flash` (fallback) |
| Tests | pytest — 52 tests, all mocked |
| CI/CD | GitHub Actions (lint → test → Docker build) |
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
| GET | `/health` | Service health + DB row counts |
| GET | `/sales-summary` | Aggregated KPIs by region, category, channel, month |
| POST | `/forecast` | Revenue forecast by region or category |
| POST | `/ask` | Natural language Q&A against sales data |
| POST | `/insights` | 5 actionable AI-generated business insights |
| GET | `/trends` | LLM-generated trend summary |

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

## Project Structure

```
cpg-sales-intelligence/
├── data/raw/          # Source CSVs (sales, products, regions)
├── src/
│   ├── ingestion/     # ETL loader + SQLite schema
│   ├── forecasting/   # Linear regression model
│   ├── insights/      # LLM layer (Groq / Gemini)
│   └── api/           # FastAPI app + routes
├── ui/                # Streamlit dashboard
├── tests/             # 52 pytest tests
├── docs/              # Architecture diagram, ADR, video script
└── .github/workflows/ # GitHub Actions CI
```

## Architecture

See [docs/architecture.md](docs/architecture.md) and [docs/adr/ADR-001.md](docs/adr/ADR-001.md).
