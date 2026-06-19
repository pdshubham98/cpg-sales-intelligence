"""
Market intelligence endpoints.

Data sources
------------
- Open Food Facts (https://world.openfoodfacts.org)  — 3M+ real CPG products, no key required
- Yahoo Finance via yfinance                          — CPG sector stock performance

Namespace: /market/*
  GET /market/products   — product catalog by category (Open Food Facts)
  GET /market/sector     — CPG stock benchmark (Yahoo Finance, normalized)

Phase 3 extension: add /market/cpi (BLS) and /market/macro (FRED) in the same namespace.
"""
import time
import logging
from collections import Counter
from typing import Any, Optional

import requests
from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/market", tags=["market"])

# ── Simple TTL cache (shared across requests, no external dependency) ──────────
_cache: dict[str, tuple[float, Any]] = {}
_TTL: dict[str, int] = {
    "products": 6 * 3600,   # Open Food Facts: stable data, 6-hour TTL
    "sector":   1 * 3600,   # Yahoo Finance:  refresh hourly
    "cpi":     24 * 3600,   # BLS public API: 25 req/day limit — cache aggressively
}


def _cached(key: str) -> Any | None:
    if key in _cache:
        ts, data = _cache[key]
        ttl = next((v for k, v in _TTL.items() if key.startswith(k)), 3600)
        if time.time() - ts < ttl:
            return data
    return None


def _store(key: str, data: Any) -> Any:
    _cache[key] = (time.time(), data)
    return data


# ── Open Food Facts ────────────────────────────────────────────────────────────
_OFF_URL = "https://world.openfoodfacts.org/api/v2/search"
_OFF_HEADERS = {
    "User-Agent": "CPGSalesIntelligence/4.0 (https://github.com/cpg-sales-intelligence; contact@example.com)"
}

# Maps our internal category names to Open Food Facts category tags
_CATEGORY_MAP: dict[str, Optional[str]] = {
    "Beverages": "beverages",
    "Snacks":    "snacks",
    "Dry Goods": "cereals-and-potatoes",
    "Chilled":   "dairies",
    "HPC":       "beauty",  # limited coverage in OFF; returns cosmetics/personal care
    "All":       None,      # no filter — cross-category
}

_GRADE = {"a": "A", "b": "B", "c": "C", "d": "D", "e": "E"}


def _fetch_products(category: str, limit: int) -> dict:
    off_cat = _CATEGORY_MAP.get(category)
    params: dict = {
        "fields": "product_name,brands,categories_tags_en,nutriscore_grade,ecoscore_grade,quantity",
        "page_size": limit,
        "sort_by":   "popularity",
        "json":      "1",
    }
    if off_cat:
        params["categories_tags_en"] = off_cat

    resp = requests.get(_OFF_URL, params=params, headers=_OFF_HEADERS, timeout=15)
    resp.raise_for_status()
    raw = resp.json()

    products: list[dict] = []
    for p in raw.get("products", []):
        name = (p.get("product_name") or "").strip()
        if not name:
            continue
        brand = (p.get("brands") or "").split(",")[0].strip()
        cats = [
            c.replace("en:", "").replace("-", " ").title()
            for c in (p.get("categories_tags_en") or [])
            if c.startswith("en:")
        ][:2]
        products.append({
            "name":       name,
            "brand":      brand,
            "nutriscore": _GRADE.get((p.get("nutriscore_grade") or "").lower(), "—"),
            "ecoscore":   _GRADE.get((p.get("ecoscore_grade") or "").lower(), "—"),
            "quantity":   (p.get("quantity") or "").strip(),
            "categories": ", ".join(cats) if cats else category,
        })

    brand_counts = Counter(p["brand"] for p in products if p["brand"])
    top_brands = [{"brand": b, "count": c} for b, c in brand_counts.most_common(15)]

    return {
        "total_in_market": raw.get("count", 0),
        "returned":        len(products),
        "products":        products,
        "top_brands":      top_brands,
    }


@router.get("/products")
def market_products(
    category: str = Query(default="Beverages", description="CPG category name"),
    limit: int    = Query(default=30, ge=5, le=100),
):
    """
    Real CPG product catalog from Open Food Facts filtered by category.

    Returns product name, brand, Nutri-Score, Eco-Score, and a brand frequency
    distribution useful for market share analysis.
    """
    key = f"products:{category}:{limit}"
    cached = _cached(key)
    if cached is not None:
        return cached
    try:
        return _store(key, _fetch_products(category, limit))
    except Exception as exc:
        logger.warning("Open Food Facts error: %s", exc)
        return {
            "total_in_market": 0,
            "returned":        0,
            "products":        [],
            "top_brands":      [],
            "error":           str(exc),
        }


# ── Yahoo Finance — CPG Sector Benchmark ───────────────────────────────────────
_CPG_COMPANIES: dict[str, str] = {
    "PG":   "Procter & Gamble",
    "KO":   "Coca-Cola",
    "PEP":  "PepsiCo",
    "UL":   "Unilever",
    "CL":   "Colgate-Palmolive",
    "MDLZ": "Mondelez",
}


def _fetch_sector(period: str) -> list[dict]:
    try:
        import yfinance as yf  # optional dependency
    except ImportError:
        logger.warning("yfinance not installed — sector data unavailable")
        return []

    rows: list[dict] = []
    for ticker, company in _CPG_COMPANIES.items():
        try:
            hist = yf.Ticker(ticker).history(period=period)
            if hist.empty:
                continue
            close = hist["Close"].dropna()
            if len(close) < 2:
                continue
            base = float(close.iloc[0])
            if base == 0:
                continue
            current     = float(close.iloc[-1])
            period_ret  = round((current - base) / base * 100, 2)
            for dt, val in close.items():
                rows.append({
                    "date":          dt.strftime("%Y-%m-%d"),
                    "company":       company,
                    "ticker":        ticker,
                    "value":         round(float(val) / base * 100, 2),
                    "period_return": period_ret,
                    "current_price": round(current, 2),
                })
        except Exception as exc:
            logger.warning("yfinance %s: %s", ticker, exc)

    return rows


@router.get("/sector")
def market_sector(
    period: str = Query(default="1y", pattern="^(3mo|6mo|1y)$"),
):
    """
    CPG sector stock performance from Yahoo Finance.

    Returns daily close prices normalized to 100 at the start of the selected
    period so different-priced stocks are directly comparable.
    """
    key = f"sector:{period}"
    cached = _cached(key)
    if cached is not None:
        return cached
    rows = _fetch_sector(period)
    return _store(key, rows)


# ── BLS Consumer Price Index ───────────────────────────────────────────────────
_BLS_URL = "https://api.bls.gov/publicAPI/v1/timeseries/data/"

# CPI-U (All Urban Consumers, not seasonally adjusted) series relevant to CPG
_BLS_SERIES: dict[str, str] = {
    "CUUR0000SA0":   "All Items",       # general inflation benchmark
    "CUUR0000SAF11": "Food at Home",    # grocery / dry goods / beverages
    "CUUR0000SEHF":  "Beverages",       # non-alcoholic beverages
    "CUUR0000SAP":   "Personal Care",   # HPC category proxy
}


def _fetch_cpi() -> dict:
    from datetime import datetime as _now
    cur_year = str(_now.now().year)
    prv_year = str(_now.now().year - 1)

    resp = requests.post(
        _BLS_URL,
        json={"seriesid": list(_BLS_SERIES.keys()), "startyear": prv_year, "endyear": cur_year},
        headers={"Content-type": "application/json"},
        timeout=15,
    )
    resp.raise_for_status()
    raw = resp.json()

    if raw.get("status") != "REQUEST_SUCCEEDED":
        raise ValueError(f"BLS API error: {raw.get('message', 'unknown')}")

    series_out: dict[str, list[dict]] = {}
    for s in raw.get("Results", {}).get("series", []):
        name = _BLS_SERIES.get(s["seriesID"], s["seriesID"])
        points: list[dict] = []
        for item in s.get("data", []):
            period = item.get("period", "")
            if not period.startswith("M") or period == "M13":
                continue
            month_num = int(period[1:])
            try:
                points.append({
                    "month": f"{item['year']}-{month_num:02d}",
                    "value": float(item["value"]),
                })
            except (KeyError, ValueError):
                continue
        points.sort(key=lambda x: x["month"])
        series_out[name] = points

    # Compute MoM and YoY change rates
    summary: dict[str, dict] = {}
    for name, pts in series_out.items():
        if len(pts) < 2:
            continue
        curr = pts[-1]["value"]
        prev = pts[-2]["value"]
        mom = round((curr - prev) / prev * 100, 2) if prev else None
        yoy = None
        if len(pts) >= 13:
            base = pts[-13]["value"]
            yoy = round((curr - base) / base * 100, 2) if base else None
        summary[name] = {
            "latest_month": pts[-1]["month"],
            "latest_value": curr,
            "mom_pct":      mom,
            "yoy_pct":      yoy,
        }

    return {"series": series_out, "summary": summary}


@router.get("/cpi")
def market_cpi():
    """
    US Consumer Price Index for CPG-relevant categories (BLS CPI-U, not seasonally adjusted).

    Series tracked:
      CUUR0000SA0   — All Items        (general inflation benchmark)
      CUUR0000SAF11 — Food at Home     (grocery / dry goods / beverages)
      CUUR0000SEHF  — Beverages        (non-alcoholic beverages category)
      CUUR0000SAP   — Personal Care    (HPC category proxy)

    Returns both raw monthly series and a summary with MoM and YoY % changes.
    Cached for 24 hours to respect the BLS v1 public API rate limit (25 req/day).

    Phase 3 note: set BLS_API_KEY env var to upgrade to BLS v2 (500 req/day, more series).
    """
    key = "cpi:latest"
    cached = _cached(key)
    if cached is not None:
        return cached
    try:
        return _store(key, _fetch_cpi())
    except Exception as exc:
        logger.warning("BLS CPI error: %s", exc)
        return {"series": {}, "summary": {}, "error": str(exc)}
