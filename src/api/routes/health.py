from fastapi import APIRouter
from src.ingestion.schema import get_connection

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    """
    Returns service health and database row count.

    Example response:
    {"status": "ok", "db_rows": {"sales_transactions": 198, "products": 15, "regions": 5}}
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
        return {
            "status": "ok",
            "db_rows": {
                "sales_transactions": sales_rows,
                "products": product_rows,
                "regions": region_rows,
            },
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
