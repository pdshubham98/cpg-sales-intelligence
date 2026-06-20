"""
Revenue forecasting using monthly-aggregated linear regression with seasonal features.
Features: period_index (trend) + sin/cos of month-of-year (seasonality).
Supports forecasting by region, product category, or product.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import TimeSeriesSplit

from src.ingestion.schema import get_connection


@dataclass
class ForecastResult:
    dimension: str          # region_id or category name
    dimension_type: str     # "region" or "category"
    periods: int
    predictions: list[dict]  # [{month: "YYYY-MM", revenue: float}]
    historical: list[dict]   # [{month: "YYYY-MM", revenue: float}]
    r2_cv: float | None
    rmse: float | None
    mape: float | None
    model_note: str


def _load_monthly_revenue(
    dimension_type: Literal["region", "category", "product"]
) -> pd.DataFrame:
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
    elif dimension_type == "category":
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
    else:  # product
        query = """
            SELECT
                strftime('%Y-%m', s.date) AS month,
                p.product_name            AS dimension,
                SUM(s.revenue)            AS revenue
            FROM sales_transactions s
            JOIN products p ON s.product_id = p.product_id
            GROUP BY month, p.product_name
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

    # Cyclical seasonal features: sin/cos of month-of-year so Dec→Jan wraps correctly
    df["month_num"] = pd.to_datetime(df["month"] + "-01").dt.month
    df["month_sin"] = df["month_num"].apply(lambda m: math.sin(2 * math.pi * m / 12))
    df["month_cos"] = df["month_num"].apply(lambda m: math.cos(2 * math.pi * m / 12))
    return df


def _seasonal_features(month_num: int) -> list[float]:
    """Return [sin, cos] cyclical encoding for a calendar month (1–12)."""
    return [
        math.sin(2 * math.pi * month_num / 12),
        math.cos(2 * math.pi * month_num / 12),
    ]


def _forecast_one(
    group: pd.DataFrame,
    periods_ahead: int,
    min_cv_samples: int = 3,
) -> tuple[list[dict], list[dict], float | None, float | None, float | None]:
    """
    Fit LinearRegression on (period_index, month_sin, month_cos → revenue).
    Seasonal features capture within-year patterns; period_index captures trend.
    Returns (predictions_list, historical_list, r2_cv, rmse, mape).
    """
    feature_cols = ["period_index", "month_sin", "month_cos"]
    X = group[feature_cols].values
    y = group["revenue"].values

    # Historical actuals for overlay chart
    historical = [
        {"month": row["month"], "revenue": round(float(row["revenue"]), 2)}
        for _, row in group.sort_values("month").iterrows()
    ]

    model = LinearRegression()
    model.fit(X, y)

    # Cross-validated metrics using time-ordered splits to prevent future leakage
    r2_cv: float | None = None
    rmse: float | None = None
    mape: float | None = None
    if len(X) >= min_cv_samples:
        tscv = TimeSeriesSplit(n_splits=min(3, len(X) - 1))
        r2_scores, rmse_scores, mape_scores = [], [], []
        for train_idx, test_idx in tscv.split(X):
            m = LinearRegression().fit(X[train_idx], y[train_idx])
            y_pred = m.predict(X[test_idx])
            y_true = y[test_idx]
            ss_res = ((y_true - y_pred) ** 2).sum()
            ss_tot = ((y_true - y_true.mean()) ** 2).sum()
            r2_scores.append(1 - ss_res / ss_tot if ss_tot > 0 else 0.0)
            rmse_scores.append(float(np.sqrt(((y_true - y_pred) ** 2).mean())))
            nonzero = y_true != 0
            if nonzero.any():
                mape_scores.append(
                    float(np.mean(np.abs((y_true[nonzero] - y_pred[nonzero]) / y_true[nonzero])) * 100)
                )
        finite_r2 = [s for s in r2_scores if np.isfinite(s)]
        r2_cv = round(float(np.mean(finite_r2)), 3) if finite_r2 else None
        rmse = round(float(np.mean(rmse_scores)), 2) if rmse_scores else None
        mape = round(float(np.mean(mape_scores)), 1) if mape_scores else None

    # Predict future months
    last_period = int(group["period_index"].max())
    last_month = group.loc[group["period_index"] == last_period, "month"].iloc[0]
    last_dt = pd.Timestamp(last_month + "-01")

    predictions = []
    for i in range(1, periods_ahead + 1):
        future_dt = last_dt + pd.DateOffset(months=i)
        future_period = last_period + i
        future_month = future_dt.strftime("%Y-%m")
        sin_cos = _seasonal_features(future_dt.month)
        features = [[future_period] + sin_cos]
        predicted_revenue = float(model.predict(features)[0])
        predictions.append(
            {
                "month": future_month,
                "revenue": round(max(predicted_revenue, 0.0), 2),
            }
        )

    return predictions, historical, r2_cv, rmse, mape


def forecast(
    dimension_type: Literal["region", "category", "product"],
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
                    rmse=None,
                    mape=None,
                    model_note="Insufficient data (< 2 months)",
                )
            )
            continue

        predictions, historical, r2_cv, rmse, mape = _forecast_one(group.copy(), periods)
        note = f"Linear regression + seasonal features on {len(group)} monthly data points"
        if r2_cv is not None:
            note += f"; CV R²={r2_cv:.3f}"
        if rmse is not None:
            note += f"; RMSE={rmse:.2f}"
        if mape is not None:
            note += f"; MAPE={mape:.1f}%"

        results.append(
            ForecastResult(
                dimension=str(dim),
                dimension_type=dimension_type,
                periods=periods,
                predictions=predictions,
                historical=historical,
                r2_cv=r2_cv,
                rmse=rmse,
                mape=mape,
                model_note=note,
            )
        )

    return results
