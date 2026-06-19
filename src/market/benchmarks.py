"""
Fetch quarterly revenue for major CPG companies via yfinance (no API key needed).
Revenue values are in USD millions for display comparability.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

CPG_TICKERS = {
    "PG":  "Procter & Gamble",
    "KO":  "Coca-Cola",
    "PEP": "PepsiCo",
    "KHC": "Kraft Heinz",
    "GIS": "General Mills",
    "UL":  "Unilever",
}


def get_quarterly_revenue() -> list[dict]:
    """
    Return last 4 quarters of total revenue for each CPG company.
    Each record: {company, ticker, quarter, revenue_m}
    """
    import yfinance as yf  # lazy import — optional dependency

    records = []
    for ticker, name in CPG_TICKERS.items():
        try:
            df = yf.Ticker(ticker).quarterly_financials
            if df is None or df.empty or "Total Revenue" not in df.index:
                continue
            row = df.loc["Total Revenue"].dropna().sort_index(ascending=False).head(4)
            for ts, val in row.items():
                records.append({
                    "company": name,
                    "ticker": ticker,
                    "quarter": ts.strftime("%Y-Q%q") if hasattr(ts, "strftime") else str(ts)[:7],
                    "revenue_m": round(float(val) / 1_000_000, 1),
                })
        except Exception as exc:
            logger.warning("yfinance fetch failed for %s: %s", ticker, exc)
    return records
