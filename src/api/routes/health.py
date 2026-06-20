from fastapi import APIRouter
from src.ingestion.schema import get_connection

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    """
    Returns service health, database row counts, and last ingestion timestamp.

    Example response:
    {"status": "ok", "db_rows": {"sales_transactions": 239, ...},
     "last_ingestion": "2026-06-20T06:00:00"}
    """
    try:
        with get_connection() as conn:
            sales_rows = conn.execute(
                "SELECT COUNT(*) FROM sales_transactions"
            ).fetchone()[0]
            product_rows = conn.execute(
                "SELECT COUNT(*) FROM products"
            ).fetchone()[0]
            region_rows = conn.execute(
                "SELECT COUNT(*) FROM regions"
            ).fetchone()[0]
            last_run = conn.execute(
                "SELECT run_at FROM ingestion_log ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return {
            "status": "ok",
            "db_rows": {
                "sales_transactions": sales_rows,
                "products": product_rows,
                "regions": region_rows,
            },
            "last_ingestion": last_run[0] if last_run else None,
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
