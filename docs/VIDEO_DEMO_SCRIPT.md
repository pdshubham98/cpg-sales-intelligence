# Video Demo Script — CPG Sales Intelligence

**Total time:** ~7 minutes  
**Format:** Screen recording with narration

---

## [0:00–0:30] Introduction

> "Hi, I'm Pradeep. I'll walk you through the CPG Sales Intelligence platform —
> an end-to-end AI analytics system I built for CPG revenue forecasting and
> natural language business insights. Let me start with the architecture."

Show the `docs/architecture.md` diagram briefly.

> "The system has five layers: raw CSV ingestion with quality validation,
> SQLite storage, a scikit-learn forecasting engine, an AI insights layer
> powered by Groq's Llama 3, and a FastAPI backend with a Streamlit dashboard.
> Everything runs in a single Docker container."

---

## [0:30–1:30] Data Quality Demo

Open terminal. Run:
```bash
python3 -m src.ingestion.loader
```

> "The ingestion pipeline applies 8 quality rules. Watch what it finds in our
> raw dataset."

Point to the log output:
- Duplicate transaction T0001 and T0002 detected and dropped
- Mixed-case SKUs like `bev-003` normalised to `BEV-003`
- Row T0172 with missing `region_id` dropped
- Row T0187 with null `product_id` and quantity dropped
- Revenue derived as `quantity × unit_price × (1 − discount_pct)`

> "In production, this is where you'd swap pandas for PySpark — the loader
> module is the only file that changes. The quality rules and revenue
> derivation are identical."

---

## [1:30–2:30] API Demo

```bash
uvicorn src.api.main:app --reload
```

Open browser at `http://localhost:8000/docs`.

> "FastAPI gives us automatic OpenAPI docs. Let me hit a few endpoints."

1. **GET /health** — show `{"status": "ok", "db_rows": {...}}`
2. **GET /sales-summary** — scroll through by_region, by_category, monthly_trend
3. **POST /forecast** with `{"dimension_type": "region", "periods": 3}` — show predictions + R²

---

## [2:30–4:30] Streamlit Dashboard

Open new terminal:
```bash
streamlit run ui/app.py
```

Navigate to `http://localhost:8501`.

**Page 1: Overview**
> "The overview shows total revenue, transaction count, and average order value.
> Revenue by region, by category as a donut chart, and the full 16-month trend."

**Page 2: Forecasting**
> "I'll forecast 3 months ahead for all regions."
- Select: `region`, blank dimension, periods = 3
- Click **Run Forecast**
> "Each region gets its own linear regression model trained on historical monthly
> aggregates. The CV R² score tells us model quality."

**Page 3: Ask Data**
> "This is natural language Q&A powered by Groq's Llama 3."
- Type: "Which region has the highest revenue and why?"
- Click **Ask**
> "The LLM receives the full aggregated context — revenue by region, category,
> and monthly trend — and answers in plain English."

**Page 4: AI Insights**
- Click **Generate Trend Summary**
> "A paragraph summarising the key revenue patterns."
- Click **Generate Insights**
> "Five actionable business insights — each starting with an action verb."

---

## [4:30–5:30] Tests

```bash
pytest tests/ -v --tb=short
```

> "52 tests — all mocked, no live API key needed. We cover ingestion quality
> rules, forecasting edge cases, all 6 API endpoints, and LLM provider
> switching. 2 seconds to run the full suite."

---

## [5:30–6:30] Docker

```bash
docker-compose up --build
```

> "A single `docker-compose up` builds the image and starts both FastAPI on
> port 8000 and Streamlit on 8501. The entrypoint script starts Streamlit in
> the background, then runs uvicorn in the foreground. The healthcheck polls
> `/health` every 30 seconds."

---

## [6:30–7:00] CI/CD

Open `.github/workflows/ci.yml` in editor.

> "GitHub Actions runs three stages on every push: flake8 lint, pytest with
> coverage report, and on main branch a full Docker build plus a smoke test
> that hits `/health` and expects 200. The pipeline ensures the container
> actually runs before any merge."

---

## Close

> "To summarise: data quality with 8 rules, revenue forecasting with
> interpretable linear regression, AI Q&A and insights via Groq Llama 3,
> a 4-page Streamlit dashboard, 52 passing tests, and a single Docker
> container. Thank you."
