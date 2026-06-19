from fastapi import APIRouter, HTTPException
from src.market.benchmarks import get_quarterly_revenue

router = APIRouter(tags=["market intelligence"])


@router.get("/market-benchmarks")
def market_benchmarks():
    """
    Quarterly revenue (USD millions) for major public CPG companies.
    Sourced live from Yahoo Finance — no API key required.
    """
    try:
        data = get_quarterly_revenue()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if not data:
        raise HTTPException(status_code=503, detail="Could not fetch market data.")
    return {"benchmarks": data}
