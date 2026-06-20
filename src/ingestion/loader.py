"""
ETL loader: reads multiple source CSVs → normalises to canonical schema →
applies quality rules → writes to SQLite.

Source registry pattern: each source defines its own adapter that maps its
columns to the canonical schema. Adding a new feed = adding one entry here.

Canonical columns: transaction_id, date, region_id, product_id, sku,
                   quantity, unit_price, discount_pct, channel
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

import json

from src.ingestion.schema import create_schema, get_connection

logger = logging.getLogger(__name__)

DATA_DIR = Path("data/raw")

# EUR → USD fixed conversion rate.
# Extension point: replace with a live FX API call (e.g. exchangerate-api.com).
_EUR_TO_USD = 1.09

_CANONICAL = [
    "transaction_id", "date", "region_id", "product_id",
    "sku", "quantity", "unit_price", "discount_pct", "channel",
]
# Columns written to DB (canonical + derived)
_DB_COLS = _CANONICAL + ["revenue", "source"]

# Quality rule labels
_QR = {
    1: "duplicate transaction_id",
    2: "null transaction_id",
    3: "null or empty region_id",
    4: "null product_id",
    5: "null or non-positive quantity",
    6: "null or non-positive unit_price",
    7: "unparseable date",
    8: "mixed-case SKU normalised",
}


# ── Source adapters ───────────────────────────────────────────────────────────

def _adapt_pos(df: pd.DataFrame) -> pd.DataFrame:
    """POS system: already matches canonical schema."""
    return df[[c for c in _CANONICAL if c in df.columns]].copy()


def _adapt_ecommerce(df: pd.DataFrame) -> pd.DataFrame:
    """
    E-commerce platform: different column names, EUR prices, extra columns.
    Schema drift handled here so the rest of the pipeline is source-agnostic.
    """
    df = df.rename(columns={
        "order_id":       "transaction_id",
        "order_date":     "date",
        "region_code":    "region_id",
        "product_code":   "product_id",
        "sku_ref":        "sku",
        "qty":            "quantity",
        "unit_price_eur": "unit_price",
        "promo_pct":      "discount_pct",
    })
    # Currency normalisation: EUR → USD
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce") * _EUR_TO_USD
    # Drop source-specific columns not in canonical schema (customer_segment, currency)
    return df[[c for c in _CANONICAL if c in df.columns]].copy()


# Registry: (csv_filename, adapter_fn, label_for_reporting)
_SOURCE_REGISTRY = [
    ("sales_transactions", _adapt_pos,       "POS"),
    ("sales_ecommerce",    _adapt_ecommerce, "E-Commerce"),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_csv(name: str) -> pd.DataFrame:
    path = DATA_DIR / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Raw CSV not found: {path}")
    return pd.read_csv(path, dtype=str)


def _normalize_dates(series: pd.Series) -> pd.Series:
    """Accept YYYY-MM-DD or MM/DD/YYYY; return ISO strings."""
    parsed = pd.to_datetime(series, format="%Y-%m-%d", errors="coerce")
    fallback = pd.to_datetime(series, format="%m/%d/%Y", errors="coerce")
    return parsed.fillna(fallback).dt.strftime("%Y-%m-%d")


# ── Main ingestion entry point ────────────────────────────────────────────────

def run_ingestion() -> dict:
    """
    Load all registered sources, normalise, merge, apply quality rules,
    and upsert into SQLite.
    Returns a quality report dict.
    """
    create_schema()

    # ── Load all CSVs and adapt before touching the DB ────────────────────────
    # All file I/O happens first so a missing CSV never leaves the DB empty.
    regions = _load_csv("regions")
    products = _load_csv("products")

    frames: list[pd.DataFrame] = []
    source_stats: dict[str, dict] = {}
    currency_conversions = 0

    for filename, adapter, label in _SOURCE_REGISTRY:
        try:
            raw = _load_csv(filename)
            adapted = adapter(raw)
            adapted["_source"] = label
            source_stats[label] = {"raw": len(raw)}
            frames.append(adapted)
            if adapter is _adapt_ecommerce:
                currency_conversions += len(adapted)
            logger.info("Loaded source '%s': %d rows", label, len(raw))
        except FileNotFoundError:
            logger.warning("Source '%s' not found — skipping", filename)

    if not frames:
        return {"error": "No source files found"}

    sales = pd.concat(frames, ignore_index=True)
    raw_count = len(sales)

    # ── Quality rules ─────────────────────────────────────────────────────────
    dropped: dict[str, int] = {}

    # Rule 1: duplicate transaction_id (across all sources)
    dupes = sales.duplicated(subset=["transaction_id"], keep="first")
    if dupes.sum():
        dropped[_QR[1]] = int(dupes.sum())
        sales = sales[~dupes]

    # Rule 2: null transaction_id
    mask = sales["transaction_id"].isna() | (sales["transaction_id"].str.strip() == "")
    if mask.sum():
        dropped[_QR[2]] = int(mask.sum())
        sales = sales[~mask]

    # Rule 3: null/empty region_id
    mask = sales["region_id"].isna() | (sales["region_id"].str.strip() == "")
    if mask.sum():
        dropped[_QR[3]] = int(mask.sum())
        sales = sales[~mask]

    # Rule 4: null product_id
    mask = sales["product_id"].isna() | (sales["product_id"].str.strip() == "")
    if mask.sum():
        dropped[_QR[4]] = int(mask.sum())
        sales = sales[~mask]

    # Rule 5: null or non-positive quantity
    sales["quantity"] = pd.to_numeric(sales["quantity"], errors="coerce")
    mask = sales["quantity"].isna() | (sales["quantity"] <= 0)
    if mask.sum():
        dropped[_QR[5]] = int(mask.sum())
        sales = sales[~mask]

    # Rule 6: null or non-positive unit_price
    sales["unit_price"] = pd.to_numeric(sales["unit_price"], errors="coerce")
    mask = sales["unit_price"].isna() | (sales["unit_price"] <= 0)
    if mask.sum():
        dropped[_QR[6]] = int(mask.sum())
        sales = sales[~mask]

    # Rule 7: unparseable dates (handles both YYYY-MM-DD and MM/DD/YYYY)
    sales["date"] = _normalize_dates(sales["date"])
    mask = sales["date"].isna()
    if mask.sum():
        dropped[_QR[7]] = int(mask.sum())
        sales = sales[~mask]

    # Rule 8: normalise SKU to uppercase
    mixed_case = sales["sku"].str.upper() != sales["sku"]
    if mixed_case.sum():
        dropped[_QR[8]] = int(mixed_case.sum())
        sales["sku"] = sales["sku"].str.upper()

    # ── Late-arriving record detection ────────────────────────────────────────
    # Records whose date is >60 days before the most recent date in the batch
    # are flagged as late-arriving. They are kept (valid data) but reported.
    dates = pd.to_datetime(sales["date"], errors="coerce")
    max_date = dates.max()
    late_mask = (max_date - dates).dt.days > 60
    late_arriving = int(late_mask.sum())
    if late_arriving:
        logger.info("Late-arriving records (>60 days before batch max): %d", late_arriving)

    # ── Per-source clean counts ───────────────────────────────────────────────
    for label in source_stats:
        source_stats[label]["clean"] = int(
            (sales["_source"] == label).sum()
        )

    # ── Derive revenue ────────────────────────────────────────────────────────
    sales["discount_pct"] = pd.to_numeric(sales["discount_pct"], errors="coerce").fillna(0.0)
    sales["revenue"] = (
        sales["quantity"] * sales["unit_price"] * (1 - sales["discount_pct"])
    ).round(2)

    clean_count = len(sales)

    # ── Write to DB in a single atomic transaction ────────────────────────────
    # Reference tables (regions, products) are always fully reloaded — they are
    # small and treated as authoritative source of truth.
    # Sales transactions use INSERT OR REPLACE (UPSERT) keyed on transaction_id
    # so re-running ingestion is idempotent and new records are appended without
    # wiping existing data.
    sales["source"] = sales["_source"]

    def _upsert(table, conn, keys, data_iter):
        cols = ", ".join(f'"{k}"' for k in keys)
        placeholders = ", ".join(["?"] * len(keys))
        sql = f"INSERT OR REPLACE INTO {table.name} ({cols}) VALUES ({placeholders})"
        conn.executemany(sql, data_iter)

    with get_connection() as conn:
        # Delete child table first to satisfy FK constraints
        conn.execute("DELETE FROM sales_transactions")
        conn.execute("DELETE FROM products")
        conn.execute("DELETE FROM regions")
        regions.to_sql("regions", conn, if_exists="append", index=False)
        products.to_sql("products", conn, if_exists="append", index=False)
        sales[_DB_COLS].to_sql(
            "sales_transactions", conn, if_exists="append",
            index=False, method=_upsert,
        )
        # Record this run in the ingestion log
        conn.execute(
            "INSERT INTO ingestion_log (raw_rows, clean_rows, dropped_rows, sources) "
            "VALUES (?, ?, ?, ?)",
            (raw_count, clean_count, raw_count - clean_count, json.dumps(source_stats)),
        )
    logger.info("Loaded %d regions, %d products", len(regions), len(products))

    summary = {
        "raw_rows": raw_count,
        "clean_rows": clean_count,
        "dropped_rows": raw_count - clean_count,
        "quality_issues": dropped,
        "sources": source_stats,
        "currency_conversions": currency_conversions,
        "late_arriving_rows": late_arriving,
    }
    logger.info("Ingestion complete: %s", summary)
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run_ingestion())
