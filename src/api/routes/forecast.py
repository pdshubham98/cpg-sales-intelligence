from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.forecasting.model import forecast, ForecastResult

router = APIRouter(tags=["forecasting"])


class ForecastRequest(BaseModel):
    dimension_type: Literal["region", "category"] = Field(
        default="region",
        description="Forecast by 'region' or 'category'",
    )
    dimension_value: Optional[str] = Field(
        default=None,
        description="Specific region ID or category name; omit for all",
    )
    periods: int = Field(
        default=3,
        ge=1,
        le=12,
        description="Number of months ahead to forecast (1–12)",
    )


class ForecastResponse(BaseModel):
    dimension: str
    dimension_type: str
    periods: int
    predictions: list[dict]
    r2_cv: Optional[float]
    model_note: str


@router.post("/forecast", response_model=list[ForecastResponse])
def run_forecast(req: ForecastRequest):
    """
    Revenue forecast using linear regression on historical monthly data.

    Example request:
    {"dimension_type": "region", "dimension_value": "R001", "periods": 3}

    Example response:
    [{"dimension": "R001", "dimension_type": "region", "periods": 3,
      "predictions": [{"month": "2025-05", "revenue": 1240.50}, ...],
      "r2_cv": 0.91, "model_note": "Linear regression on 16 monthly data points; CV R²=0.910"}]
    """
    try:
        results: list[ForecastResult] = forecast(
            dimension_type=req.dimension_type,
            dimension_value=req.dimension_value,
            periods=req.periods,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if not results:
        raise HTTPException(status_code=404, detail="No data found for the given parameters.")

    return [
        ForecastResponse(
            dimension=r.dimension,
            dimension_type=r.dimension_type,
            periods=r.periods,
            predictions=r.predictions,
            r2_cv=r.r2_cv,
            model_note=r.model_note,
        )
        for r in results
    ]
