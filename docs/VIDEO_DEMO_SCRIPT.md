# Video Demo Script — CPG Sales Intelligence

**Total time:** ~8 minutes
**Format:** Screen recording with narration

---

## [0:00–0:30] Introduction

> "Hi, I'm Shubham. I'll walk you through the CPG Sales Intelligence platform —
> an end-to-end AI analytics system I built for CPG revenue forecasting and
> natural language business insights. Let me start with the architecture."

Show the `docs/architecture.md` diagram.

> "The system has five layers: multi-source CSV ingestion with quality validation,
> SQLite storage, a scikit-learn forecasting engine with seasonal features,
> an AI insights layer powered by Groq's Llama 3, and a FastAPI backend with
> a Streamlit dashboard. Everything runs in a single Docker container."

---

## [0:30–1:30] Data Quality & Multi-Source Ingestion

Open terminal. Run:
```bash
python3 -m src.ingestion.loader
```

> "The ingestion pipeline loads two sources — a POS system and an e-commerce
> platform. Each has a different schema: different column names, date formats,
> even currency. The adapter pattern normalises both to the same canonical
> schema before any quality rules run."

Point to the log output:
- POS source: 205 raw rows, YYYY-MM-DD dates, USD prices
- E-commerce source: 39 rows, MM/DD/YYYY dates, EUR prices converted to USD
- Cross-source duplicate detected and dropped
- 1 null region_id dropped
- Mixed-case SKUs normalised to uppercase
- Late-arriving records flagged (records >60 days before batch max date)
- Revenue derived as `quantity × unit_price × (1 − discount_pct)`

> "In production this is where you'd swap pandas for PySpark — only `loader.py`
> changes. Adding a new feed is one adapter function and one registry entry."

---

## [1:30–2:30] API Demo

Open browser at `http://localhost:8000/docs`.

> "FastAPI gives us automatic OpenAPI docs. Let me hit a few endpoints."

1. **GET /health** — show `{"status": "ok", "db_rows": {...}}`
2. **GET /sales-summary** — scroll through by_region, by_category, monthly_trend, discount_analysis
3. **POST /forecast** with `{"dimension_type": "region", "periods": 3}`

> "The forecast now uses three features: a trend index plus sin and cos of the
> calendar month. That's cyclical seasonal encoding — it means the model knows
> December and January are adjacent, which raw month numbers can't express."

4. **GET /market-benchmarks** — show live quarterly revenue for P&G, Coca-Cola, PepsiCo

---

## [2:30–4:30] Streamlit Dashboard

Open `http://localhost:8501`.

**Page 1: Overview**
> "KPI cards with month-over-month delta, revenue by region and category,
> monthly trend, channel breakdown, top products, and discount analysis.
> Date range filter at the top filters all charts simultaneously."

**Page 2: Forecasting**
> "I'll forecast 6 months ahead for all categories."
- Select: `category`, all categories, periods = 6, click Run Forecast
> "Each category gets its own seasonal model. CV R² tells us fit quality.
> The chart overlays historical bars with the forecast line."

**Page 3: Sales Assistant**
> "Multi-session chat powered by Groq's Llama 3. Each conversation is
> independent — you can run multiple sessions from the sidebar."
- Ask: "How does our Beverages revenue compare to Coca-Cola's latest quarter?"
> "The LLM has both our internal sales data AND live competitor revenue from
> Yahoo Finance as context — so it can answer competitive questions."
- Ask: "Which region is growing fastest month over month?"

**Page 4: AI Insights**
- Click **Generate All Insights**
> "A trend summary paragraph and five actionable business insights, each
> starting with an action verb like Expand, Reduce, or Invest."

---

## [4:30–5:30] AI Tool Usage — Override Example

> "I'll show one moment where I explicitly overrode the AI output."

Show the git log — point to the market benchmarks commits.

> "When I asked Claude Code to integrate Yahoo Finance data, it created a whole
> new Market Intelligence page with charts and metrics — a new feature.
> That contradicted my design principle of improving existing pages, not
> adding new ones. I overrode it: I stripped the UI entirely and instead fed
> the Yahoo Finance data silently into the LLM context. Now the Sales Assistant
> can answer competitive questions with no extra page, no extra clicks.
> The result is more useful and the interface stays focused."

---

## [5:30–6:30] Tests

```bash
pytest tests/ -v --tb=short
```

> "60 tests across four modules — all mocked, no live API key needed.
> We cover ingestion quality rules, multi-source merging, currency conversion,
> late-arriving detection, seasonal feature math, all 7 API endpoints,
> and LLM provider routing. Under 3 seconds."

---

## [6:30–7:00] Docker & CI

```bash
docker-compose up --build
```

> "One command builds the image and starts both FastAPI on 8000 and
> Streamlit on 8501. The entrypoint script starts Streamlit in the background
> then runs uvicorn in the foreground. Healthcheck polls /health every 30 seconds."

Open `.github/workflows/ci.yml`.

> "GitHub Actions runs three stages on every push: flake8 lint, pytest with
> coverage, and on main a full Docker build plus a smoke test that hits /health
> and expects 200 before the pipeline passes."

---

## [7:00–8:00] What I'd Build Next

> "Four things in priority order.

> First — Prophet for forecasting. It handles seasonality, holidays, and
> missing data natively. The interface in model.py is already designed for
> that swap.

> Second — PostgreSQL. One line change in schema.py gives you concurrent
> writes and proper production ops.

> Third — promo and campaign data as a third source in the adapter registry.
> One new adapter function, one registry entry in loader.py. Demand spikes
> become explainable.

> Fourth — streaming LLM responses in the Sales Assistant. Right now users
> wait for the full answer. Token streaming makes it feel instant.

> The skeleton is designed so all four are isolated changes — no rewrites."

---

## Close

> "To summarise: multi-source ingestion with schema drift and currency
> normalisation, seasonal revenue forecasting, AI Q&A enriched with live
> market data, a 4-page Streamlit dashboard, 60 passing tests, and a
> single Docker container. Thank you."
