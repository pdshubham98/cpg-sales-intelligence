#!/usr/bin/env bash
set -euo pipefail

# Start Streamlit in the background on port 8501
streamlit run ui/app.py \
  --server.port=8501 \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --browser.gatherUsageStats=false &

# Start FastAPI (runs ingestion on startup) — foreground, keeps container alive
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000
