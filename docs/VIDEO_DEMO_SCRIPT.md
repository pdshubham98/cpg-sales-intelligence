# Video Demo Script — CPG Sales Intelligence
# Every line: SAY (what to speak) + SHOW (exact screen action)

**Total time:** ~8 minutes
**Recording tool:** QuickTime / OBS / Loom
**Before recording:** Pre-open tabs — localhost:8501, localhost:8000/docs, GitHub repo, terminal

---

## [0:00 – 0:30] SECTION 1 — Introduction

**SAY:** "Hi, I'm Shubham."
**SHOW:** Keep terminal or GitHub tab visible. Start talking naturally.

**SAY:** "This is CPG Sales Intelligence — an end-to-end AI analytics platform I built for CPG revenue forecasting and natural language business insights."
**SHOW:** Switch to browser → GitHub repo tab (github.com/pdshubham98/cpg-sales-intelligence). Scroll slowly so the README title and Stack table are visible.

**SAY:** "The business problem: CPG sales teams receive data from multiple systems — POS terminals and e-commerce platforms — with different schemas, currencies, and date formats. There is no unified view, no forecast, and no natural language interface."
**SHOW:** Stay on GitHub README. Scroll down slowly past the Stack table.

**SAY:** "I'll walk you through the full system in about eight minutes — architecture, live data, API, dashboard, AI tools, and roadmap."
**SHOW:** Scroll back to top of README.

---

## [0:30 – 1:45] SECTION 2 — Architecture

**SAY:** "Let me start with the architecture."
**SHOW:** Open docs/architecture.md on GitHub (click docs/ folder → architecture.md). The Mermaid diagram renders.

**SAY:** "The system has five layers. At the bottom: raw CSV files — a POS system and an e-commerce platform with different schemas."
**SHOW:** Move mouse to the bottom of the Mermaid diagram — the `data/raw/ CSVs` node.

**SAY:** "Layer two is the ETL pipeline built on the adapter pattern. Each source has its own adapter that maps it to a canonical schema before nine quality rules run. All writes are atomic."
**SHOW:** Move mouse up to the `ETL Ingestion` node.

**SAY:** "Layer three is SQLite in WAL mode — zero ops, concurrent reads, foreign key constraints, and an ingestion_log table that audits every run."
**SHOW:** Move mouse to the `SQLite WAL` database node.

**SAY:** "Layer four is the FastAPI backend — eight endpoints, optional API key auth, and a Prometheus metrics endpoint."
**SHOW:** Move mouse to the `FastAPI :8000` node.

**SAY:** "On top: a Streamlit dashboard and the FastAPI docs page — both served from a single Docker container."
**SHOW:** Move mouse to the `Streamlit :8501` node.

**SAY:** "AI sits between the API and the data. Groq's Llama 3.3 70B is the primary provider — free tier, no credit card, 14,400 requests per day. If Groq fails after three retries, the system automatically falls back to Gemini 1.5 Flash."
**SHOW:** Move mouse to the `LLM Layer` node. Point at the dashed auto-fallback arrow.

---

## [1:45 – 4:30] SECTION 3 — Live Demo

### [1:45] Startup

**SAY:** "The application is already running. One command — docker compose up — builds the image and starts both services."
**SHOW:** Switch to terminal. Type and run:
```
docker ps --format "table {{.Names}}\t{{.Status}}"
```
Output: cpg-sales-intelligence-app-1   Up X hours (healthy)

**SAY:** "Let me confirm the health check."
**SHOW:** In terminal, type and run:
```
curl -s http://localhost:8000/health | python3 -m json.tool
```
Output appears:
{
    "status": "ok",
    "db_rows": { "sales_transactions": 239, "products": 15, "regions": 5 },
    "last_ingestion": "2026-06-20T07:17:49"
}

**SAY:** "239 clean transactions loaded. The last_ingestion timestamp comes from the ingestion_log table — every run is audited automatically."
**SHOW:** Keep terminal output visible. Point cursor at last_ingestion field.

---

### [2:00] Data Quality

**SAY:** "Let me show the data quality report. FastAPI automatically generates interactive API documentation."
**SHOW:** Switch to browser → localhost:8000/docs. Swagger UI loads. Scroll slowly so all 8 endpoints are visible.

**SAY:** "Let me hit the data-quality endpoint."
**SHOW:** Click GET /data-quality → Try it out → Execute.

**SAY:** "245 raw rows came in. Six were dropped: three duplicate transaction IDs, two null region IDs, one null product ID. Mixed-case SKUs were normalised and kept. 40 rows went through EUR to USD currency conversion — that is the e-commerce source."
**SHOW:** Scroll to the Response Body. Point cursor at each quality_issues key as you name it.

---

### [2:25] Forecast API

**SAY:** "Now let me run a revenue forecast."
**SHOW:** Scroll up in Swagger → click POST /forecast → Try it out. Replace body with:
{ "dimension_type": "category", "periods": 6 }
Click Execute.

**SAY:** "Six months ahead by product category. The model uses three features: a trend index, plus sine and cosine of the calendar month. Cyclical encoding means the model knows December and January are adjacent — raw month numbers cannot express that."
**SHOW:** Scroll to Response Body. Point at predictions array and dimension field.

**SAY:** "R-squared, RMSE, and MAPE are returned for every dimension — full model quality transparency in the API response."
**SHOW:** Point cursor at r2_cv, rmse, mape fields in the response.

---

### [2:55] Overview Page

**SAY:** "Now the dashboard."
**SHOW:** Switch to browser → localhost:8501. Overview page loads.

**SAY:** "Four KPI cards at the top. Each shows a month-over-month percentage delta — green for growth, red for decline."
**SHOW:** Point at the 4 KPI cards and the MoM delta badges below each number.

**SAY:** "The date pickers filter all charts simultaneously."
**SHOW:** Click the start date picker. Select a date 3 months back. Charts re-render. Clear the filter.

**SAY:** "Revenue by region, by category, by channel, monthly trend, top products, and discount analysis — all on one page."
**SHOW:** Scroll down slowly through each chart section. Pause 1 second on each chart.

---

### [3:20] Forecasting Page

**SAY:** "Forecasting page."
**SHOW:** Click Forecasting in the left sidebar.

**SAY:** "I will forecast 3 months ahead for all regions."
**SHOW:**
- Forecast by dropdown → region
- Region dropdown → All regions
- Months ahead slider → 3
- Click the red Run Forecast button

**SAY:** "Each region gets its own seasonal model. Historical bars on the left, dashed blue forecast line extending to the right."
**SHOW:** Scroll down as charts render. Let first chart be fully visible.

**SAY:** "CV R-squared, RMSE, and MAPE are shown directly below each heading."
**SHOW:** Point cursor at the metric caption line below the first chart heading.

**SAY:** "There is a CSV export button under every chart."
**SHOW:** Click Download CSV below the first chart. A file downloads.

---

### [3:45] Sales Assistant

**SAY:** "Sales Assistant page."
**SHOW:** Click Sales Assistant in the left sidebar.

**SAY:** "Multi-turn chat powered by Groq's Llama 3.3 70B. Multiple independent sessions from the sidebar."
**SHOW:** Point at the Conversations section in the left sidebar and the + New Chat button.

**SAY:** "I will ask a competitive question."
**SHOW:** Click the chat input box. Type:
How does our Beverages revenue compare to Coca-Cola's latest quarter?
Press Enter. Wait for the LLM response to appear.

**SAY:** "The LLM has both our internal sales data AND live competitor revenue from Yahoo Finance as context — so it can answer competitive questions without any extra page or clicks."
**SHOW:** Let the full answer render. Keep both the question and response visible.

**SAY:** "Let me ask a follow-up in the same conversation."
**SHOW:** In the same chat, type:
Which region is growing fastest month over month?
Press Enter. Wait for response.

**SAY:** "The conversation history is included in the prompt — the model remembers what we discussed."
**SHOW:** Scroll up slightly so both exchanges are visible as a thread.

---

### [4:10] AI Insights

**SAY:** "AI Insights page."
**SHOW:** Click AI Insights in the left sidebar.

**SAY:** "One click — a trend summary and five actionable business insights."
**SHOW:** Click Generate All Insights button. Wait for response.

**SAY:** "The trend summary is a 3 to 5 sentence plain-English analysis."
**SHOW:** Point at the trend summary paragraph.

**SAY:** "Five insights below — each starting with an action verb: Expand, Reduce, Invest, Focus, Monitor."
**SHOW:** Scroll to show all five insight cards.

---

## [4:30 – 5:45] SECTION 4 — AI Tool Usage

**SAY:** "I will show where AI tools were used and where I overrode the output."
**SHOW:** Switch to terminal. Run:
git log --oneline
Let the full commit list print.

**SAY:** "I used Claude Code throughout — visible in the Co-Authored-By line on every commit."
**SHOW:** Run:
git log --format="%h %s" | head -15
Point cursor at several commit messages.

**SAY:** "First override — the CV data leakage fix. Claude generated cross_val_score, which shuffles data by default. For a time series that means the model trains on future months to predict the past — data leakage."
**SHOW:** Run in terminal:
grep -n "TimeSeriesSplit" src/forecasting/model.py
Output shows line 127.

**SAY:** "I replaced it with TimeSeriesSplit, which enforces chronological ordering. That was my engineering decision, not the AI's."
**SHOW:** Open src/forecasting/model.py in editor. Scroll to line 127. Let TimeSeriesSplit(n_splits=min(3, len(X)-1)) be visible.

**SAY:** "Second override — the market data architecture. Claude created an entirely new Market Intelligence dashboard page."
**SHOW:** In terminal, run:
git show 8e282e6 --stat
Output shows new market page files created.

**SAY:** "I rejected that. My principle: improve existing pages, never add new ones. I stripped the entire UI and fed the Yahoo Finance data silently into the LLM context instead. The Sales Assistant now answers competitive questions with zero extra UI."
**SHOW:** Run:
git show d2c6faf --stat
Output shows the new page removed; ask.py modified.

**SAY:** "Third — the Prometheus metrics layer. AI never suggested this. I added it myself: request count, latency histograms, LLM call latency, fallback counter, ingestion row gauges."
**SHOW:** Run in terminal:
cat src/api/metrics.py
All 6 metric definitions scroll past.

**SAY:** "About 60 to 65 percent of the code was AI-generated. The remaining 35 to 40 percent required engineering judgment — the CV fix, market data redirect, Prometheus layer, FK constraint ordering, and Python 3.9 compatibility."
**SHOW:** Return to terminal. Keep git log visible.

---

## [5:45 – 6:30] SECTION 5 — Tests and CI

**SAY:** "69 tests. All mocked — no API key required in CI."
**SHOW:** Run in terminal:
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -20
Wait. Final line: 69 passed in X.XXs

**SAY:** "I cover ingestion quality rules, UPSERT idempotency, all eight API endpoints, Prometheus metrics content, and LLM auto-fallback behaviour."
**SHOW:** Scroll up in pytest output so test names are visible.

**SAY:** "CI has four stages on every push."
**SHOW:** Open .github/workflows/ci.yml in editor or run:
cat .github/workflows/ci.yml

**SAY:** "First: gitleaks scans the full git history for secrets — blocking everything downstream. Then flake8 lint. Then pytest with a 70 percent coverage gate. On main — a full Docker build plus a live smoke test against the health endpoint."
**SHOW:** Scroll through the YAML. Point at secrets-scan job, then lint, then test (highlight --cov-fail-under=70), then docker-build job.

---

## [6:30 – 7:30] SECTION 6 — Future Roadmap

**SAY:** "Four things I would build next."
**SHOW:** Switch to browser. Open docs/SUBMISSION.md on GitHub. Scroll to Extension Points table.

**SAY:** "First — Prophet for forecasting. Handles seasonality, holidays, and missing data natively. The swap requires changing only model.py."
**SHOW:** Point at Upgrade forecasting model row in the table.

**SAY:** "Second — PostgreSQL. One function change in schema.py. The SQL schema is fully compatible — concurrent writes and managed cloud backup."
**SHOW:** Point at Scale storage row.

**SAY:** "Third — a third source in the adapter registry. Promotional campaign data would make demand spikes explainable."
**SHOW:** Run in terminal:
grep -n "_SOURCE_REGISTRY" src/ingestion/loader.py
Show the two-entry registry.

**SAY:** "Fourth — streaming LLM responses in the Sales Assistant. Token streaming makes it feel instant. Streamlit's write_stream supports it natively."
**SHOW:** Switch to localhost:8501. Show the Sales Assistant chat input briefly.

**SAY:** "Every one of those changes touches a single file. No rewrites."
**SHOW:** Stay on Sales Assistant page.

---

## [7:30 – 8:00] Close

**SAY:** "To summarise."
**SHOW:** Switch to Overview page (localhost:8501).

**SAY:** "Multi-source ETL with schema drift handling and currency normalisation. Nine data quality rules. Idempotent UPSERT ingestion with audit logging."
**SHOW:** Point at the revenue by region chart and the KPI cards.

**SAY:** "Seasonal revenue forecasting with time-series cross-validation."
**SHOW:** Click Forecasting sidebar item. A forecast chart is visible.

**SAY:** "AI-powered natural language Q&A enriched with live competitor data."
**SHOW:** Click Sales Assistant. The chat interface is visible.

**SAY:** "A four-page Streamlit dashboard. 69 passing tests. Prometheus observability. Optional API auth. All in a single Docker container. Thank you."
**SHOW:** Click through: Overview → Forecasting → Sales Assistant → AI Insights — one second each. Land on AI Insights page. Stop recording.

---

## Pre-Recording Checklist

- [ ] docker ps shows container (healthy)
- [ ] curl http://localhost:8000/health returns "status": "ok"
- [ ] localhost:8501 loads Overview page with data visible
- [ ] localhost:8000/docs loads Swagger UI
- [ ] GitHub repo tab open (github.com/pdshubham98/cpg-sales-intelligence)
- [ ] docs/architecture.md Mermaid diagram visible on GitHub
- [ ] Terminal font size 18pt minimum
- [ ] Browser zoom 100%
- [ ] Notifications silenced / Do Not Disturb on
- [ ] Valid GROQ_API_KEY in .env for live LLM demo
- [ ] Screen resolution 1920x1080 or higher
- [ ] Microphone tested

## Timestamp Guide

| Time  | What is on screen                                          |
|-------|------------------------------------------------------------|
| 0:00  | GitHub repo README                                         |
| 0:30  | docs/architecture.md Mermaid diagram                       |
| 1:45  | Terminal — docker ps + curl /health                        |
| 2:00  | localhost:8000/docs — GET /data-quality executed           |
| 2:25  | localhost:8000/docs — POST /forecast executed              |
| 2:55  | localhost:8501 — Overview page                             |
| 3:20  | localhost:8501 — Forecasting page, run forecast            |
| 3:45  | localhost:8501 — Sales Assistant, ask question             |
| 4:10  | localhost:8501 — AI Insights, generate                     |
| 4:30  | Terminal — git log, model.py line 127, git show commits    |
| 5:45  | Terminal — pytest output, ci.yml                           |
| 6:30  | GitHub docs/SUBMISSION.md Extension Points table           |
| 7:30  | localhost:8501 — click through all 4 pages                 |
| 8:00  | Stop recording on AI Insights page                         |
