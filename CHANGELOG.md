# Changelog

All notable changes to this project are documented here.

## [3.1.0] — 2026-06-20

### Added
- **Prometheus observability** — `/metrics` endpoint exposing request counts, request latency, LLM call latency, LLM errors, LLM fallback count, and ingestion row gauges
- **Optional API key auth** — `SECRET_KEY` env var enables `X-Api-Key` bearer-token protection on all AI endpoints; disabled when unset (dev/demo mode)
- **Auto Groq→Gemini fallback** — if Groq exhausts 3 retry attempts, automatically falls back to Gemini when `GEMINI_API_KEY` is set
- **Exponential backoff on Groq** — 3 attempts with 1 s / 2 s / 4 s delays before raising
- **Incremental ingestion (UPSERT)** — `INSERT OR REPLACE` keyed on `transaction_id`; re-running ingestion is idempotent and new rows are appended without wiping existing data
- **`ingestion_log` table** — each ingestion run writes raw/clean/dropped row counts and per-source stats; surfaced in `/health` as `last_ingestion`
- **`source` column on `sales_transactions`** — data lineage: records which source adapter loaded each row
- **Schema migration guard** — `ALTER TABLE ADD COLUMN` protected by `PRAGMA table_info()` check so existing Docker volumes upgrade without data loss
- **Secrets scanning in CI** — `gitleaks/gitleaks-action@v2` runs as the first CI job before lint or tests
- **Coverage gate** — pytest enforces `--cov-fail-under=70`
- **9 tests for new functionality** — `TestMetricsEndpoint` (4), `TestAutoFallback` (2), `TestIncrementalIngestion` (3)

### Changed
- **Cross-validation fix** — replaced `cross_val_score` (shuffles data, causes data leakage) with `TimeSeriesSplit` to enforce temporal ordering in CV folds
- **Additional forecast metrics** — `ForecastResult` now includes RMSE and MAPE alongside R²
- **Structured error responses** — all 500 paths use `detail="Internal server error"` + `logger.exception()` instead of leaking stack traces
- **LLM prompts use `json.dumps`** — context dicts serialised with `json.dumps(..., default=str)` instead of raw `str()` for safe, readable prompts
- **Test client raises exceptions** — `raise_server_exceptions=True` in conftest so server errors surface immediately in tests
- **`/health` returns `last_ingestion`** — queries `ingestion_log` for the most recent run timestamp
- **`AskRequest` validation** — `question` field has `max_length=2000`
- **README** updated to document `/metrics`, `SECRET_KEY`, auto-fallback, incremental ingestion, and `ingestion_log`
- **Architecture diagram** replaced ASCII art with Mermaid in `docs/architecture.md`

### Fixed
- **FK constraint on second ingestion run** — `DELETE FROM sales_transactions` now runs before `DELETE FROM products`/`regions` to satisfy SQLite FK constraints
- **Python 3.9 compatibility** — `str | None` union syntax replaced with `Optional[str]` from `typing` in `auth.py`

## [3.0.0] — 2026-06-19

### Added
- Multi-source ingestion with source adapter registry (`POS` + `E-Commerce`)
- E-Commerce adapter with EUR→USD currency conversion and date normalisation
- Late-arriving record detection (>60 days before batch max date)
- Cross-source deduplication keyed on `transaction_id`
- Product-level revenue forecasting (in addition to region and category)
- Date range filter on Overview page
- Structured error and empty states throughout the UI

### Changed
- `quantity` column changed from `INTEGER` to `REAL` to support fractional units
- LLM clients use lazy singleton pattern to avoid import-time side effects

## [2.0.0] — initial production-ready release

- FastAPI backend with 7 endpoints
- Streamlit 4-page dashboard
- SQLite with WAL mode
- Groq (primary) / Gemini (secondary) LLM routing
- Linear regression forecasting with cyclical seasonal features (sin/cos month encoding)
- 8 data quality rules with drop reporting
- Docker + docker-compose
- GitHub Actions CI (lint → test → Docker build)
