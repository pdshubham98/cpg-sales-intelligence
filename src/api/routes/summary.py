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
                SELECT region_id,
                       ROUND(SUM(revenue), 2) AS revenue,
                       COUNT(*) AS transactions
                FROM sales_transactions
                GROUP BY region_id
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

        return {
            "total_revenue": round(total[0] or 0.0, 2),
            "total_transactions": total[1] or 0,
            "by_region": [dict(r) for r in by_region],
            "by_category": [dict(r) for r in by_category],
            "by_channel": [dict(r) for r in by_channel],
            "monthly_trend": [dict(r) for r in monthly],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
