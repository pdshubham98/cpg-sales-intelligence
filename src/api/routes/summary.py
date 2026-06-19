from fastapi import APIRouter, HTTPException
from src.ingestion.schema import get_connection

router = APIRouter(tags=["analytics"])


@router.get("/sales-summary")
def sales_summary():
    """
    Returns aggregated KPIs from the sales database.

    Example response:
    {
      "total_revenue": 125430.20,
      "total_transactions": 198,
      "by_region": [{"region_id": "R001", "revenue": 28000.50, "transactions": 42}],
      "by_category": [{"category": "Beverages", "revenue": 35000.00, "transactions": 60}],
      "by_channel": [{"channel": "Retail", "revenue": 80000.00, "transactions": 120}],
      "monthly_trend": [{"month": "2024-01", "revenue": 8500.00}]
    }
    """
    try:
        with get_connection() as conn:
            total = conn.execute(
                "SELECT SUM(revenue), COUNT(*) FROM sales_transactions"
            ).fetchone()

            by_region = conn.execute("""
                SELECT s.region_id,
                       COALESCE(r.region_name, s.region_id) AS region_name,
                       ROUND(SUM(s.revenue), 2) AS revenue,
                       COUNT(*) AS transactions
                FROM sales_transactions s
                LEFT JOIN regions r ON s.region_id = r.region_id
                GROUP BY s.region_id, r.region_name
                ORDER BY revenue DESC
            """).fetchall()

            by_category = conn.execute("""
                SELECT p.category,
                       ROUND(SUM(s.revenue), 2) AS revenue,
                       COUNT(*) AS transactions
                FROM sales_transactions s
                JOIN products p ON s.product_id = p.product_id
                GROUP BY p.category
                ORDER BY revenue DESC
            """).fetchall()

            by_channel = conn.execute("""
                SELECT channel,
                       ROUND(SUM(revenue), 2) AS revenue,
                       COUNT(*) AS transactions
                FROM sales_transactions
                GROUP BY channel
                ORDER BY revenue DESC
            """).fetchall()

            monthly = conn.execute("""
                SELECT strftime('%Y-%m', date) AS month,
                       ROUND(SUM(revenue), 2)  AS revenue
                FROM sales_transactions
                GROUP BY month
                ORDER BY month
            """).fetchall()

            by_product = conn.execute("""
                SELECT p.product_name, p.sku, p.category,
                       ROUND(SUM(s.revenue), 2)     AS revenue,
                       COUNT(*)                      AS transactions,
                       CAST(SUM(s.quantity) AS INT)  AS units_sold
                FROM sales_transactions s
                JOIN products p ON s.product_id = p.product_id
                GROUP BY p.product_id, p.product_name, p.sku, p.category
                ORDER BY revenue DESC
            """).fetchall()

            # Discount analysis by channel
            discount = conn.execute("""
                SELECT channel,
                       ROUND(AVG(discount_pct) * 100, 2)          AS avg_discount_pct,
                       ROUND(SUM(quantity * unit_price * discount_pct), 2) AS revenue_foregone
                FROM sales_transactions
                GROUP BY channel
                ORDER BY revenue_foregone DESC
            """).fetchall()

            # Month-over-month: last two complete months in the dataset
            last_two = conn.execute("""
                SELECT strftime('%Y-%m', date) AS month,
                       ROUND(SUM(revenue), 2)  AS revenue,
                       COUNT(*)                AS transactions
                FROM sales_transactions
                GROUP BY month
                ORDER BY month DESC
                LIMIT 2
            """).fetchall()

        # Build MoM delta dict
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
