"""
ETL loader: reads raw CSVs → applies 8 quality rules → writes to SQLite.
Quality issues in the dataset are intentional for demonstration.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.ingestion.schema import create_schema, get_connection

logger = logging.getLogger(__name__)

DATA_DIR = Path("data/raw")

# Quality rule labels (used in logging)
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


def _load_csv(name: str) -> pd.DataFrame:
    path = DATA_DIR / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Raw CSV not found: {path}")
    return pd.read_csv(path, dtype=str)


def _normalize_dates(series: pd.Series) -> pd.Series:
    """Parse dates in YYYY-MM-DD or MM/DD/YYYY format; return ISO strings."""
    parsed = pd.to_datetime(series, format="%Y-%m-%d", errors="coerce")
    fallback = pd.to_datetime(series, format="%m/%d/%Y", errors="coerce")
    return parsed.fillna(fallback).dt.strftime("%Y-%m-%d")


def run_ingestion() -> dict[str, int]:
    """
    Load raw CSVs, apply quality rules, and upsert into SQLite.
    Returns a summary dict with row counts.
    """
    create_schema()

    # --- Load CSVs ---
    regions = _load_csv("regions")
    products = _load_csv("products")

    # Clear in FK-safe order: transactions → products → regions
    with get_connection() as conn:
        conn.execute("DELETE FROM sales_transactions")
        conn.execute("DELETE FROM products")
        conn.execute("DELETE FROM regions")
        regions.to_sql("regions", conn, if_exists="append", index=False)
        products.to_sql("products", conn, if_exists="append", index=False)
    logger.info("Loaded %d regions, %d products", len(regions), len(products))

    # --- Sales transactions ---
    sales = _load_csv("sales_transactions")
    raw_count = len(sales)
    dropped: dict[str, int] = {}

    # Rule 1: drop duplicate transaction_id
    dupes = sales.duplicated(subset=["transaction_id"], keep="first")
    if dupes.sum():
        dropped[_QR[1]] = int(dupes.sum())
        sales = sales[~dupes]
    logger.info("Rule 1 — %s: dropped %d", _QR[1], dropped.get(_QR[1], 0))

    # Rule 2: drop null transaction_id
    mask = sales["transaction_id"].isna() | (sales["transaction_id"].str.strip() == "")
    if mask.sum():
        dropped[_QR[2]] = int(mask.sum())
        sales = sales[~mask]
    logger.info("Rule 2 — %s: dropped %d", _QR[2], dropped.get(_QR[2], 0))

    # Rule 3: drop null/empty region_id
    mask = sales["region_id"].isna() | (sales["region_id"].str.strip() == "")
    if mask.sum():
        dropped[_QR[3]] = int(mask.sum())
        sales = sales[~mask]
    logger.info("Rule 3 — %s: dropped %d", _QR[3], dropped.get(_QR[3], 0))

    # Rule 4: drop null product_id
    mask = sales["product_id"].isna() | (sales["product_id"].str.strip() == "")
    if mask.sum():
        dropped[_QR[4]] = int(mask.sum())
        sales = sales[~mask]
    logger.info("Rule 4 — %s: dropped %d", _QR[4], dropped.get(_QR[4], 0))

    # Rule 5: drop null or non-positive quantity
    sales["quantity"] = pd.to_numeric(sales["quantity"], errors="coerce")
    mask = sales["quantity"].isna() | (sales["quantity"] <= 0)
    if mask.sum():
        dropped[_QR[5]] = int(mask.sum())
        sales = sales[~mask]
    logger.info("Rule 5 — %s: dropped %d", _QR[5], dropped.get(_QR[5], 0))

    # Rule 6: drop null or non-positive unit_price
    sales["unit_price"] = pd.to_numeric(sales["unit_price"], errors="coerce")
    mask = sales["unit_price"].isna() | (sales["unit_price"] <= 0)
    if mask.sum():
        dropped[_QR[6]] = int(mask.sum())
        sales = sales[~mask]
    logger.info("Rule 6 — %s: dropped %d", _QR[6], dropped.get(_QR[6], 0))

    # Rule 7: drop rows with unparseable dates
    sales["date"] = _normalize_dates(sales["date"])
    mask = sales["date"].isna()
    if mask.sum():
        dropped[_QR[7]] = int(mask.sum())
        sales = sales[~mask]
    logger.info("Rule 7 — %s: dropped %d", _QR[7], dropped.get(_QR[7], 0))

    # Rule 8: normalise SKU to uppercase (non-destructive fix, not a drop)
    mixed_case = sales["sku"].str.upper() != sales["sku"]
    if mixed_case.sum():
        dropped[_QR[8]] = int(mixed_case.sum())
        sales["sku"] = sales["sku"].str.upper()
    logger.info("Rule 8 — %s: fixed %d", _QR[8], dropped.get(_QR[8], 0))

    # Derive revenue = quantity * unit_price * (1 - discount_pct)
    sales["discount_pct"] = pd.to_numeric(sales["discount_pct"], errors="coerce").fillna(0.0)
    sales["revenue"] = (
        sales["quantity"] * sales["unit_price"] * (1 - sales["discount_pct"])
    ).round(2)

    clean_count = len(sales)

    with get_connection() as conn:
        conn.execute("DELETE FROM sales_transactions")
        sales[
            [
                "transaction_id", "date", "region_id", "product_id",
                "sku", "quantity", "unit_price", "discount_pct", "channel", "revenue",
            ]
        ].to_sql("sales_transactions", conn, if_exists="append", index=False)

    summary = {
        "raw_rows": raw_count,
        "clean_rows": clean_count,
        "dropped_rows": raw_count - clean_count,
        "quality_issues": dropped,
    }
    logger.info("Ingestion complete: %s", summary)
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_ingestion()
    print(result)
