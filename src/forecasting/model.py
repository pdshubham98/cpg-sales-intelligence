"""
Revenue forecasting using monthly-aggregated linear regression.
Supports forecasting by region or by product category.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import cross_val_score

from src.ingestion.schema import get_connection


@dataclass
class ForecastResult:
    dimension: str          # region_id or category name
    dimension_type: str     # "region" or "category"
    periods: int
    predictions: list[dict]  # [{month: "YYYY-MM", revenue: float}]
    historical: list[dict]   # [{month: "YYYY-MM", revenue: float}]
    r2_cv: float | None
    model_note: str


def _load_monthly_revenue(dimension_type: Literal["region", "category"]) -> pd.DataFrame:
    """
    Query SQLite and return monthly revenue aggregated by the chosen dimension.
    Returns columns: [period_index, dimension, revenue]
    """
    if dimension_type == "region":
        query = """
            SELECT
                strftime('%Y-%m', date) AS month,
                region_id              AS dimension,
                SUM(revenue)           AS revenue
            FROM sales_transactions
            GROUP BY month, region_id
            ORDER BY month
        """
    else:
        query = """
            SELECT
                strftime('%Y-%m', s.date) AS month,
                p.category                AS dimension,
                SUM(s.revenue)            AS revenue
            FROM sales_transactions s
            JOIN products p ON s.product_id = p.product_id
            GROUP BY month, p.category
            ORDER BY month
        """

    with get_connection() as conn:
        df = pd.read_sql_query(query, conn)

    if df.empty:
        return df

    # Encode month as integer period index (0, 1, 2, …)
    months = sorted(df["month"].unique())
    month_index = {m: i for i, m in enumerate(months)}
    df["period_index"] = df["month"].map(month_index)
    return df


def _forecast_one(
    group: pd.DataFrame,
    periods_ahead: int,
    min_cv_samples: int = 3,
) -> tuple[list[dict], list[dict], float | None]:
    """
    Fit LinearRegression on (period_index → revenue) for one dimension group.
    Returns (predictions_list, historical_list, r2_cv).
    """
    X = group["period_index"].values.reshape(-1, 1)
    y = group["revenue"].values

    # Historical actuals for overlay chart
    historical = [
        {"month": row["month"], "revenue": round(float(row["revenue"]), 2)}
        for _, row in group.sort_values("month").iterrows()
    ]

    model = LinearRegression()
    model.fit(X, y)

    # Cross-validated R² only when there are enough samples
    r2_cv: float | None = None
    if len(X) >= min_cv_samples:
        scores = cross_val_score(model, X, y, cv=min(3, len(X)), scoring="r2")
        finite = scores[np.isfinite(scores)]
        r2_cv = float(finite.mean()) if len(finite) > 0 else None

    # Predict future months
    last_period = int(group["period_index"].max())
    last_month = group.loc[group["period_index"] == last_period, "month"].iloc[0]
    last_dt = pd.Timestamp(last_month + "-01")

    predictions = []
    for i in range(1, periods_ahead + 1):
        future_period = last_period + i
        future_month = (last_dt + pd.DateOffset(months=i)).strftime("%Y-%m")
        predicted_revenue = float(model.predict([[future_period]])[0])
        predictions.append(
            {
                "month": future_month,
                "revenue": round(max(predicted_revenue, 0.0), 2),
            }
        )

    return predictions, historical, r2_cv


def forecast(
    dimension_type: Literal["region", "category"],
    dimension_value: str | None = None,
    periods: int = 3,
) -> list[ForecastResult]:
    """
    Run revenue forecast.

    Args:
        dimension_type: "region" or "category"
        dimension_value: specific region/category to forecast; None = all
        periods: months ahead to predict (1–12)

    Returns:
        List of ForecastResult, one per dimension value.
    """
    periods = max(1, min(periods, 12))
    df = _load_monthly_revenue(dimension_type)

    if df.empty:
        return []

    if dimension_value:
        df = df[df["dimension"] == dimension_value]
        if df.empty:
            return []

    results: list[ForecastResult] = []
    for dim, group in df.groupby("dimension"):
        if len(group) < 2:
            results.append(
                ForecastResult(
                    dimension=dim,
                    dimension_type=dimension_type,
                    periods=periods,
                    predictions=[],
                    historical=[],
                    r2_cv=None,
                    model_note="Insufficient data (< 2 months)",
                )
            )
            continue

        predictions, historical, r2_cv = _forecast_one(group.copy(), periods)
        note = f"Linear regression on {len(group)} monthly data points"
        if r2_cv is not None:
            note += f"; CV R²={r2_cv:.3f}"

        results.append(
            ForecastResult(
                dimension=str(dim),
                dimension_type=dimension_type,
                periods=periods,
                predictions=predictions,
                historical=historical,
                r2_cv=r2_cv,
                model_note=note,
            )
        )

    return results
