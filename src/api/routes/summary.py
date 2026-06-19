from typing import Optional
from datetime import date as Date
from fastapi import APIRouter, HTTPException, Query
from src.ingestion.schema import get_connection

router = APIRouter(tags=["analytics"])


def _date_filter(col: str, start: Optional[Date], end: Optional[Date]) -> str:
    """Build a WHERE clause fragment for a date column."""
    parts = []
    if start:
        parts.append(f"{col} >= '{start.isoformat()}'")
    if end:
        parts.append(f"{col} <= '{end.isoformat()}'")
    return ("WHERE " + " AND ".join(parts)) if parts else ""


def _date_and(col: str, start: Optional[Date], end: Optional[Date]) -> str:
    """Same as _date_filter but uses AND prefix for queries with an existing WHERE."""
    parts = []
    if start:
        parts.append(f"{col} >= '{start.isoformat()}'")
    if end:
        parts.append(f"{col} <= '{end.isoformat()}'")
    return ("AND " + " AND ".join(parts)) if parts else ""


@router.get("/sales-summary")
def sales_summary(
    start_date: Optional[Date] = Query(default=None, description="Filter from date YYYY-MM-DD"),
    end_date: Optional[Date] = Query(default=None, description="Filter to date YYYY-MM-DD"),
):
    """
    Returns aggregated KPIs from the sales database.
    Optionally filtered by start_date and/or end_date (YYYY-MM-DD).

    Example response:
    {
      "total_revenue": 125430.20,
      "total_transactions": 198,
      "by_region": [{"region_id": "R001", "region_name": "North America",
                     "revenue": 28000.50, "transactions": 42}],
      "by_category": [{"category": "Beverages", "revenue": 35000.00, "transactions": 60}],
      "by_channel": [{"channel": "Retail", "revenue": 80000.00, "transactions": 120}],
      "monthly_trend": [{"month": "2024-01", "revenue": 8500.00}],
      "by_product": [{"product_name": "...", "sku": "...", "revenue": ..., ...}],
      "mom_delta": {"current_month": "2025-04", "revenue_delta_pct": 4.2, ...},
      "discount_analysis": [{"channel": "Retail", "avg_discount_pct": 4.2, ...}]
    }
    """
    w = _date_filter("date", start_date, end_date)
    sw = _date_and("s.date", start_date, end_date)

    try:
        with get_connection() as conn:
            total = conn.execute(
                f"SELECT ROUND(SUM(revenue),2), COUNT(*) FROM sales_transactions {w}"
            ).fetchone()

            by_region = conn.execute(f"""
                SELECT s.region_id,
                       COALESCE(r.region_name, s.region_id) AS region_name,
                       ROUND(SUM(s.revenue), 2) AS revenue,
                       COUNT(*) AS transactions
                FROM sales_transactions s
                LEFT JOIN regions r ON s.region_id = r.region_id
                WHERE 1=1 {sw}
                GROUP BY s.region_id, r.region_name
                ORDER BY revenue DESC
            """).fetchall()

            by_category = conn.execute(f"""
                SELECT p.category,
                       ROUND(SUM(s.revenue), 2) AS revenue,
                       COUNT(*) AS transactions
                FROM sales_transactions s
                JOIN products p ON s.product_id = p.product_id
                WHERE 1=1 {sw}
                GROUP BY p.category
                ORDER BY revenue DESC
            """).fetchall()

            by_channel = conn.execute(f"""
                SELECT channel,
                       ROUND(SUM(revenue), 2) AS revenue,
                       COUNT(*) AS transactions
                FROM sales_transactions {w}
                GROUP BY channel
                ORDER BY revenue DESC
            """).fetchall()

            monthly = conn.execute(f"""
                SELECT strftime('%Y-%m', date) AS month,
                       ROUND(SUM(revenue), 2)  AS revenue
                FROM sales_transactions {w}
                GROUP BY month
                ORDER BY month
            """).fetchall()

            by_product = conn.execute(f"""
                SELECT p.product_name, p.sku, p.category,
                       ROUND(SUM(s.revenue), 2)     AS revenue,
                       COUNT(*)                      AS transactions,
                       CAST(SUM(s.quantity) AS INT)  AS units_sold
                FROM sales_transactions s
                JOIN products p ON s.product_id = p.product_id
                WHERE 1=1 {sw}
                GROUP BY p.product_id, p.product_name, p.sku, p.category
                ORDER BY revenue DESC
            """).fetchall()

            discount = conn.execute(f"""
                SELECT channel,
                       ROUND(AVG(discount_pct) * 100, 2)                   AS avg_discount_pct,
                       ROUND(SUM(quantity * unit_price * discount_pct), 2)  AS revenue_foregone
                FROM sales_transactions {w}
                GROUP BY channel
                ORDER BY revenue_foregone DESC
            """).fetchall()

            # MoM always uses full dataset (not date-filtered) so the delta is always valid
            last_two = conn.execute("""
                SELECT strftime('%Y-%m', date) AS month,
                       ROUND(SUM(revenue), 2)  AS revenue,
                       COUNT(*)                AS transactions
                FROM sales_transactions
                GROUP BY month
                ORDER BY month DESC
                LIMIT 2
            """).fetchall()

        mom: dict = {}
        if len(last_two) == 2:
            curr, prev = last_two[0], last_two[1]
            rev_delta = round(curr[1] - prev[1], 2)
            rev_pct = round(rev_delta / prev[1] * 100, 1) if prev[1] else None
            tx_delta = curr[2] - prev[2]
            tx_pct = round(tx_delta / prev[2] * 100, 1) if prev[2] else None
            mom = {
                "current_month": curr[0],
                "prev_month": prev[0],
                "revenue_delta": rev_delta,
                "revenue_delta_pct": rev_pct,
                "transactions_delta": tx_delta,
                "transactions_delta_pct": tx_pct,
            }

        return {
            "total_revenue": round(total[0] or 0.0, 2),
            "total_transactions": total[1] or 0,
            "by_region": [dict(r) for r in by_region],
            "by_category": [dict(r) for r in by_category],
            "by_channel": [dict(r) for r in by_channel],
            "monthly_trend": [dict(r) for r in monthly],
            "by_product": [dict(r) for r in by_product],
            "mom_delta": mom,
            "discount_analysis": [dict(r) for r in discount],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
