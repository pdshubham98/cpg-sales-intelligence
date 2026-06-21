# Video Demo Script — CPG Sales Intelligence

**Total time:** ~8 minutes  
**Format:** Screen recording with narration  
**Legend:** `[SHOW]` = what is visible on screen · `[SAY]` = exact narration

---

## [0:00–0:30] Section 1 — Introduction

---

**[SHOW]** GitHub repo page — `https://github.com/pdshubham98/cpg-sales-intelligence`  
Scroll slowly so the viewer can see the README preview, folder structure, and commit count.

**[SAY]**
> "Hi, I'm Shubham. This is CPG Sales Intelligence — an end-to-end AI analytics platform
> for Consumer Packaged Goods revenue analysis, built as part of the AI Acceleration
> Engineer assessment."

---

**[SHOW]** Scroll down the README to the Stack table — let the viewer read the tech stack row by row.

**[SAY]**
> "The business problem: CPG sales teams receive data from multiple systems — POS terminals,
> e-commerce platforms — with different schemas, currencies, and date formats. There's no
> unified view, no forecast, and no natural language interface for ad-hoc questions.
> I built this to solve that, end to end, in a single Docker container."

---

## [0:30–1:45] Section 2 — Architecture Overview

---

**[SHOW]** Open `docs/architecture.md` in the browser (GitHub renders the Mermaid diagram).  
Keep the diagram centred on screen. Point (hover mouse) to each layer as you describe it.

**[SAY]**
> "Let me walk through the architecture. Five layers, each cleanly separated."

---

**[SHOW]** Hover mouse over the `data/raw/` node at the bottom of the diagram.

**[SAY]**
> "At the bottom: raw CSV files from two sources — a POS system and an e-commerce platform.
> Different schemas, different date formats, different currencies."

---

**[SHOW]** Hover over the `ETL Ingestion` node.

**[SAY]**
> "Layer two: the ETL pipeline uses the adapter pattern. Each source has its own adapter
> that maps it to a canonical schema before nine quality rules run. All writes are atomic —
> the database never gets partial data."

---

**[SHOW]** Hover over the `SQLite WAL` database node.

**[SAY]**
> "Layer three: SQLite in WAL mode. WAL enables concurrent reads while writes happen —
> important when the dashboard and API are running simultaneously. There's also an
> ingestion_log table that records every run with timestamps and row counts."

---

**[SHOW]** Hover over the `FastAPI :8000` node. Then hover over `Prometheus /metrics`.

**[SAY]**
> "Layer four: FastAPI with eight endpoints, optional bearer-token auth, and a Prometheus
> metrics endpoint. FastAPI runs data ingestion automatically on startup — no separate
> cron job or script needed."

---

**[SHOW]** Hover over `LLM Layer` node, then the dashed auto-fallback arrow.

**[SAY]**
> "The AI layer uses Groq's Llama 3.3 70B as primary — free tier, no credit card.
> If Groq exhausts all retries, the system automatically falls back to Gemini 1.5 Flash.
> That's wired into the code, not a manual config switch."

---

**[SHOW]** Hover over `Streamlit :8501` node.

**[SAY]**
> "On top: a four-page Streamlit dashboard and the FastAPI docs. Both served from the
> same single Docker container."

---

## [1:45–3:15] Section 3 — Live Demo

---

### [1:45] Application Startup

**[SHOW]** Switch to terminal. Run:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```
The output shows `cpg-sales-intelligence-app-1` with status `Up ... (healthy)`.

**[SAY]**
> "The application is already running — one command, `docker compose up --build`,
> builds the image and starts both FastAPI on port 8000 and Streamlit on 8501.
> Let me confirm the health check."

---

**[SHOW]** In the same terminal, run:
```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```
The response appears:
```json
{
  "status": "ok",
  "db_rows": {
    "sales_transactions": 239,
    "products": 15,
    "regions": 5
  },
  "last_ingestion": "2026-06-20T..."
}
```

**[SAY]**
> "239 clean transactions loaded from two sources. The `last_ingestion` timestamp
> comes from the ingestion_log table — every run is audited. We have 15 products
> across 5 regions."

---

### [2:00] Data Quality

**[SHOW]** Open browser → `http://localhost:8000/docs`  
Scroll to the **health** section, expand `GET /data-quality`, click **Try it out**, then **Execute**.  
The response JSON appears on screen.

**[SAY]**
> "Here's the data quality report from startup ingestion. 245 raw rows came in."

---

**[SHOW]** Slowly scroll through the JSON response — pause on `quality_issues`.

**[SAY]**
> "Six rows were dropped: three duplicate transaction IDs, two null region IDs,
> one null product ID. Two mixed-case SKUs were normalised to uppercase but kept —
> that's a correction, not a drop. 40 rows went through EUR to USD currency
> conversion — that's the entire e-commerce source. Every quality rule is
> deterministic and documented. No silent data loss."

---

### [2:25] Forecast via API

**[SHOW]** Still in Swagger docs — scroll to **forecasting** section.  
Expand `POST /forecast`, click **Try it out**, replace the body with:
```json
{
  "dimension_type": "category",
  "periods": 6
}
```
Click **Execute**. Wait for response. Scroll to show the JSON output with predictions, r2_cv, rmse, mape.

**[SAY]**
> "Let me run a 6-month category forecast directly from the API."

---

**[SHOW]** Highlight the `model_note` field in the response: `"Linear regression + seasonal features on 16 monthly data points; CV R²=..."`.

**[SAY]**
> "The model uses three features: a trend index, and the sine and cosine of the
> calendar month. Cyclical encoding means the model knows December and January
> are adjacent — raw month numbers cannot express that. I use TimeSeriesSplit
> for cross-validation, which preserves temporal order. The original code used
> cross_val_score, which shuffles folds and lets future months leak into training.
> I identified and fixed that data leakage. Each result includes R², RMSE, and
> MAPE so model quality is transparent."

---

### [2:55] Streamlit Dashboard — Overview

**[SHOW]** Open new browser tab → `http://localhost:8501`  
The Overview page loads. Keep the full page visible.

**[SAY]**
> "The four-page dashboard. Starting with Overview."

---

**[SHOW]** Scroll to the top KPI cards row — show total revenue, total transactions, and the MoM delta badges (green or red arrows with percentage).

**[SAY]**
> "KPI cards with month-over-month percentage delta, colour-coded — green for growth,
> red for decline. These pull from the mom_delta field in the sales-summary API."

---

**[SHOW]** Use the date pickers at the top — set a start date a few months back — watch all charts update simultaneously.

**[SAY]**
> "The date range filter at the top applies to all charts at once. The filter is
> passed as query parameters to the API — not applied client-side — so the SQL
> aggregation changes, not just the display."

---

**[SHOW]** Scroll down slowly through: Revenue by Region chart → Revenue by Category → Monthly Trend → Top Products table → Discount Analysis.  
On any chart, click the **Download CSV** button to show it works.

**[SAY]**
> "Revenue by region, by category, monthly trend, top products by revenue, and
> discount analysis by channel — how much revenue was foregone through discounting.
> Every chart has a download CSV button."

---

### [3:20] Streamlit Dashboard — Forecasting

**[SHOW]** Click **Forecasting** in the left sidebar.  
Set: Forecast by = `region`, Region = `All regions`, Months ahead slider = `3`.  
Click **Run Forecast**.

**[SAY]**
> "Now the forecasting page. I'll forecast 3 months ahead for all regions."

---

**[SHOW]** Charts render — one per region. Show the first chart with grey historical bars and the dashed blue forecast line. Hover over forecast points to show the tooltip with month and revenue value.  
Point to the caption below the heading showing R², RMSE, MAPE values.

**[SAY]**
> "Each region gets its own seasonal model. Historical bars in grey, forecast
> overlay as a dashed line. CV R², RMSE, and MAPE are shown — so the evaluator
> can judge model quality, not just see a line."

---

### [3:35] Streamlit Dashboard — Sales Assistant

**[SHOW]** Click **Sales Assistant** in the sidebar.  
The chat interface appears. The sidebar shows a session list.

**[SAY]**
> "The Sales Assistant — a multi-turn chat powered by Llama 3.3 70B."

---

**[SHOW]** Type in the chat box:
```
How does our Beverages revenue compare to Coca-Cola's latest quarter?
```
Press Enter. Wait for the response to appear.

**[SAY]**
> "The LLM has both internal sales data AND live competitor revenue from Yahoo Finance
> as context. No API key needed for Yahoo Finance — it's fetched via the yfinance
> library. So it can answer competitive questions."

---

**[SHOW]** The response appears. Then click **＋ New Chat** in the sidebar. A new session appears. Show both sessions in the sidebar.

**[SAY]**
> "Each conversation is independent. You can run multiple sessions from the sidebar
> and switch between them. Session history is preserved per session."

---

### [3:50] Streamlit Dashboard — AI Insights

**[SHOW]** Click **AI Insights** in the sidebar. The page shows two sections: Trend Summary and Business Insights.  
Click the **Generate All Insights** button. Wait for the response.

**[SAY]**
> "AI Insights generates two things in one click."

---

**[SHOW]** The trend summary paragraph appears first, then 5 insight cards below it. Scroll slowly so each insight is visible.

**[SAY]**
> "A 3 to 5 sentence trend analysis, then five actionable business insights — each
> starting with an action verb: Expand, Reduce, Invest, Focus. These are generated
> by the LLM with the full sales context as input."

---

## [4:00–5:30] Section 4 — AI Tool Usage & Engineering Decisions

---

### Where AI Was Used

**[SHOW]** Switch to terminal. Run:
```bash
git log --oneline
```
Scroll through the list slowly so timestamps and commit messages are readable.

**[SAY]**
> "I used Claude Code throughout. It's visible in the Co-Authored-By line
> on every commit. Let me show two specific moments — one where I accepted
> AI output, and two where I explicitly overrode it."

---

### Decision 1 — CV Data Leakage (Override)

**[SHOW]** Open `src/forecasting/model.py` in the IDE or terminal:
```bash
grep -n "TimeSeriesSplit\|cross_val" src/forecasting/model.py
```
Output shows `TimeSeriesSplit` on line 127.

**[SAY]**
> "The original AI-generated code used cross_val_score from scikit-learn.
> cross_val_score shuffles data before splitting into folds by default.
> For a time series that's wrong — a validation fold can see training data
> from the future. That's data leakage. I identified it and replaced it
> with TimeSeriesSplit, which enforces that training data always comes
> before validation data chronologically."

---

**[SHOW]** Open `src/forecasting/model.py`, scroll to line 127. Show the `TimeSeriesSplit` call and the `tscv.split(X)` loop (lines 127–142).

**[SAY]**
> "The n_splits is also capped to min(3, len(X) minus 1) to handle edge cases
> when there are fewer data points than splits. That guard was also not in
> the original AI output."

---

### Decision 2 — Market Data Architecture (Override)

**[SHOW]** In the terminal, run:
```bash
git log --oneline | grep -E "market|intel"
```
Shows two commits: `feat(v4): market intelligence with real CPG data` and `improve(v3): enrich Sales Assistant with live market data`.

**[SAY]**
> "Here you can see two commits close together. The first one created a new
> Market Intelligence dashboard page with charts and a metrics table — that
> was the AI output."

---

**[SHOW]** Run:
```bash
git show 8e282e6 --stat
```
Shows files added/changed — including a new UI page.

**[SAY]**
> "I rejected it. My design principle: improve existing pages, never add new ones
> without explicit requirement. A fifth page for market data adds friction —
> the user has to navigate to it. Instead I fed the Yahoo Finance data silently
> into the LLM context."

---

**[SHOW]** Open `src/api/routes/ask.py`, scroll to lines 44–58. Show the `industry_benchmarks` block inside `_get_summary_context()`.

**[SAY]**
> "Now the Sales Assistant can answer competitive questions — 'how does our
> Beverages revenue compare to Coca-Cola?' — with zero extra pages and zero
> extra clicks. The result is more useful and the interface stays focused."

---

### Decision 3 — Prometheus Layer (Developer Initiative)

**[SHOW]** Open `src/api/metrics.py`. Show the full file — six metric definitions.

**[SAY]**
> "The Prometheus observability layer was entirely my initiative — the AI never
> suggested it. I added request count and latency for every endpoint, LLM call
> latency per provider, an error counter, a fallback counter, and ingestion row
> gauges. Production systems need metrics. The endpoint is already ready for
> any Prometheus-compatible scraper."

---

**[SHOW]** In browser, open `http://localhost:8000/metrics`. Show the raw Prometheus text output scrolling down — metric names visible including `cpg_http_requests_total`, `cpg_llm_call_duration_seconds`.

**[SAY]**
> "You can see all metrics live here — request counts, latency histograms,
> and ingestion row gauges, all in Prometheus text format."

---

## [5:30–6:30] Section 5 — Future Roadmap

---

**[SHOW]** Open `docs/adr/ADR-001.md` in the browser (GitHub renders it nicely).  
Scroll slowly to show the decisions table — 8 rows visible.

**[SAY]**
> "The ADR documents why every technology was chosen and what the upgrade path is.
> Four things I'd build next, in priority order."

---

**[SHOW]** Scroll to §6 in the ADR — `scikit-learn LinearRegression over Prophet / XGBoost`.

**[SAY]**
> "First — Prophet for forecasting. It handles seasonality, holidays, and missing
> data natively, scales to years of history, and needs no feature engineering.
> The swap requires changing only model.py — the ForecastResult interface stays
> the same."

---

**[SHOW]** Scroll to §3 — `SQLite over PostgreSQL`.

**[SAY]**
> "Second — PostgreSQL. One function change in schema.py — swap sqlite3.connect
> for psycopg2.connect. Unlocks concurrent writes, connection pooling, and managed
> cloud database services. The schema is already compatible."

---

**[SHOW]** Scroll back to `loader.py` — show `_SOURCE_REGISTRY` (lines 79–82).

**[SAY]**
> "Third — a third source in the adapter registry. Promotional and campaign data
> would make demand spikes explainable in the LLM context. One new adapter function,
> one registry entry. The pipeline handles the rest."

---

**[SHOW]** Open `src/insights/llm.py` — show `_call_groq()` function.

**[SAY]**
> "Fourth — streaming LLM responses in the Sales Assistant. Right now users wait
> for the full response. Groq's streaming API plus Streamlit's write_stream()
> makes it feel instant. All four of these are isolated changes — no rewrites."

---

## [6:30–7:30] Section 6 — Tests & CI

---

### Tests

**[SHOW]** Switch to terminal. Run:
```bash
python3 -m pytest tests/ -v --tb=short 2>&1 | head -80
```
Show tests running — green dots appearing, test names scrolling.

**[SAY]**
> "69 tests across four modules. All LLM calls mocked — no API key needed in CI.
> Under 3 seconds."

---

**[SHOW]** Let the test run complete. Show the final summary line:
```
69 passed, 5 warnings in 3.04s
```

**[SAY]**
> "Nine quality rule tests, multi-source merging, EUR to USD conversion,
> UPSERT idempotency, ingestion_log writes, all eight API endpoints,
> Prometheus metrics content, LLM provider routing, auto-fallback behaviour,
> and seasonal feature math. All green."

---

### CI Pipeline

**[SHOW]** Open `.github/workflows/ci.yml` in the IDE or browser.  
Scroll through to show all four jobs: `secrets-scan`, `lint`, `test`, `docker-build`.

**[SAY]**
> "GitHub Actions runs four stages in order."

---

**[SHOW]** Highlight `secrets-scan` job (lines 9–21) — point to `gitleaks-action@v2` and `fetch-depth: 0`.

**[SAY]**
> "First: secrets scanning with gitleaks on the full git history — not just the
> latest commit. Every job downstream is blocked if secrets are found."

---

**[SHOW]** Highlight `lint` job's `needs: secrets-scan` line.

**[SAY]**
> "Second: flake8 lint, max 100 characters per line. Runs only after secrets
> scan passes."

---

**[SHOW]** Highlight `test` job — point to `--cov-fail-under=70` in the pytest command.

**[SAY]**
> "Third: pytest with coverage enforcement at 70%. Coverage XML uploaded as
> a GitHub Actions artifact."

---

**[SHOW]** Highlight `docker-build` job — point to `if: github.ref == 'refs/heads/main'` and the smoke test curl command.

**[SAY]**
> "Fourth: on main only — full Docker build, container start, and a live smoke
> test that calls /health and expects HTTP 200 before the pipeline passes."

---

## [7:30–8:00] Close

---

**[SHOW]** Return to the Streamlit dashboard Overview page. Scroll slowly through the full page one final time — KPIs, charts, download buttons all visible.

**[SAY]**
> "To summarise: multi-source ETL with schema drift handling and currency
> normalisation, nine data quality rules, idempotent UPSERT ingestion with
> audit logging, seasonal revenue forecasting with time-series cross-validation,
> AI-powered Q&A enriched with live competitor market data, a four-page Streamlit
> dashboard, 69 passing tests, Prometheus observability, optional API auth, and
> a single Docker container with four-stage CI. Thank you."

---

**[SHOW]** End on the GitHub repo page — let the viewer see the repo URL one final time.

---

## Recording Checklist

### Before you start

- [ ] `docker ps` shows container status as `(healthy)`
- [ ] `curl -s http://localhost:8000/health` returns `"status": "ok"`
- [ ] `http://localhost:8501` loads Overview page with data visible
- [ ] `http://localhost:8000/docs` loads Swagger UI
- [ ] Terminal font size ≥ 18pt, browser zoom = 100%
- [ ] Notifications silenced (Focus / Do Not Disturb on)
- [ ] `.env` has a valid `GROQ_API_KEY` so Sales Assistant responds live
- [ ] Browser tabs pre-opened: GitHub repo, `localhost:8501`, `localhost:8000/docs`, `docs/architecture.md` on GitHub, `docs/adr/ADR-001.md` on GitHub
- [ ] IDE open with `src/forecasting/model.py`, `src/api/routes/ask.py`, `src/api/metrics.py`, `.github/workflows/ci.yml` ready to switch to

### Screen sequence (in order)

| Time | Screen |
|---|---|
| 0:00 | GitHub repo — README |
| 0:30 | GitHub — `docs/architecture.md` Mermaid diagram |
| 1:45 | Terminal — `docker ps` then `curl /health` |
| 2:00 | Browser — `localhost:8000/docs` → `/data-quality` |
| 2:25 | Browser — Swagger `POST /forecast` |
| 2:55 | Browser — `localhost:8501` Overview page |
| 3:05 | Overview — date picker interaction |
| 3:10 | Overview — scroll charts; click CSV download |
| 3:20 | Streamlit — Forecasting page, run forecast |
| 3:35 | Streamlit — Sales Assistant, type question |
| 3:50 | Streamlit — AI Insights, click Generate |
| 4:00 | Terminal — `git log --oneline` |
| 4:10 | Terminal — `grep TimeSeriesSplit src/forecasting/model.py` |
| 4:20 | IDE — `model.py` lines 127–142 |
| 4:30 | Terminal — `git log --oneline | grep market` |
| 4:40 | IDE — `ask.py` lines 44–58 (`industry_benchmarks`) |
| 4:55 | IDE — `metrics.py` full file |
| 5:05 | Browser — `localhost:8000/metrics` raw output |
| 5:30 | GitHub — `docs/adr/ADR-001.md` |
| 6:30 | Terminal — `pytest tests/ -v --tb=short` |
| 7:00 | IDE or GitHub — `.github/workflows/ci.yml` |
| 7:30 | Browser — `localhost:8501` Overview page (final) |
| 7:55 | GitHub repo — URL visible |

---

## Evaluator Q&A Guide

**Q: Why SQLite instead of PostgreSQL?**
> SQLite with WAL mode handles concurrent reads from Streamlit and the API simultaneously while a single writer runs ingestion. For ~250 rows, adding PostgreSQL adds a second container, init scripts, health checks, and volume coordination with zero functional benefit. The swap is one function — `get_connection()` in `schema.py`. Extension to PostgreSQL is documented in ADR-001 §3 with explicit rationale.

**Q: How does the seasonal forecasting work?**
> I encode the calendar month as two cyclical features: `sin(2π·month/12)` and `cos(2π·month/12)`. This means December (12) and January (1) are geometrically adjacent in feature space. Raw integer month numbers can't express that — month 12 and month 1 would look maximally distant. The period index captures linear trend. Together, three features give the model enough signal to separate trend from seasonal pattern on ~15 monthly data points per dimension.

**Q: What is TimeSeriesSplit and why did you replace cross_val_score?**
> `cross_val_score` shuffles data before splitting into folds by default. For a time series, that means a validation fold can see training data from the future — the model gets to "know" Q4 while predicting Q2. That's data leakage; it makes CV scores optimistically biased. `TimeSeriesSplit` enforces that training data always comes chronologically before validation data. I also capped `n_splits` to `min(3, len(X)-1)` to prevent an edge case where the number of splits exceeds the number of samples.

**Q: How does the Groq–Gemini fallback work exactly?**
> `_call_llm()` calls `_call_groq()` first. `_call_groq()` retries up to 3 times with exponential backoff — 1 second, 2 seconds, 4 seconds — before raising. Auth errors (401, invalid_api_key) bail immediately without retrying. If all 3 retries fail and `GEMINI_API_KEY` is set, `_call_llm()` automatically calls `_call_gemini()` and increments a Prometheus fallback counter. The user never sees an error. If `GEMINI_API_KEY` is not set, the exception propagates and the API returns 503.

**Q: How do you prevent SQL injection in the date filter?**
> The `start_date` and `end_date` query parameters in `/sales-summary` are typed as `datetime.date` in the FastAPI route signature. FastAPI and Pydantic validate and parse them before my code runs — a malformed string returns 422 before reaching SQL. The values reach the query only via `.isoformat()`, which produces only `YYYY-MM-DD`. No user-controlled string is interpolated raw into SQL.

**Q: Why Groq over OpenAI or Anthropic?**
> The constraint was no paid service. Groq's free tier requires no credit card and provides 14,400 requests per day against Llama 3.3 70B — a 70 billion parameter model that produces high-quality CPG analysis. Gemini's free tier (1 million tokens per day) is the automatic fallback. OpenAI and Anthropic both require paid accounts. The provider is a single `LLM_PROVIDER` environment variable — switching requires zero code changes. Documented in ADR-001 §5.

**Q: Why did you put Yahoo Finance data into the LLM context instead of a separate page?**
> The AI generated a new Market Intelligence page. I rejected it because my design principle was: improve existing features, never add new pages without an explicit requirement. A fifth page adds navigation friction — users have to go there to see it. Injecting the data into the LLM context means the Sales Assistant can answer competitive questions — "how does our Beverages revenue compare to Coca-Cola's latest quarter?" — with no extra pages and no extra clicks. The data is more accessible and the interface stays focused.

**Q: How much of the code is AI-generated?**
> Roughly 60–65% of implementation lines. The remaining 35–40% required engineering judgment: identifying and fixing the TimeSeriesSplit data leakage issue, overriding the Market Intelligence page decision, designing the Prometheus metrics layer (the AI never suggested it), fixing FK constraint delete ordering in ingestion (AI had it reversed), and the Python 3.9 compatibility fixes for union type syntax. Every AI output was read, understood, and validated before commit.

**Q: What would you build next?**
> Four things in priority order: (1) Prophet for forecasting — it handles seasonality and holidays natively; the `model.py` interface is already designed for the swap. (2) PostgreSQL — one `get_connection()` change. (3) A third data source in the adapter registry — promotional data to explain demand spikes. (4) Streaming LLM responses in the Sales Assistant — Groq supports token streaming; Streamlit's `write_stream()` supports it; currently users wait for the full response.

**Q: What does the ingestion_log table do?**
> Every call to `run_ingestion()` writes one row to `ingestion_log` with a timestamp, raw row count, clean row count, dropped row count, and per-source JSON stats. The `/health` endpoint surfaces the `last_ingestion` timestamp from this table. This provides an audit trail for every ETL run — you can answer "when was data last refreshed and how many rows were dropped" without reading application logs. It's also used by the Prometheus `cpg_ingestion_rows` gauge.
