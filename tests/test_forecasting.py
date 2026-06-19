"""
Unit tests for the forecasting module.
"""
import os
from unittest.mock import patch

import pytest


@pytest.fixture()
def forecast_env(populated_db):
    with patch.dict(os.environ, {"DB_PATH": str(populated_db)}):
        yield


class TestForecastByRegion:
    def test_returns_results(self, forecast_env):
        from src.forecasting.model import forecast
        results = forecast("region", periods=3)
        assert len(results) > 0

    def test_prediction_count_matches_periods(self, forecast_env):
        from src.forecasting.model import forecast
        results = forecast("region", periods=3)
        for r in results:
            if r.predictions:
                assert len(r.predictions) == 3

    def test_predictions_have_positive_revenue(self, forecast_env):
        from src.forecasting.model import forecast
        results = forecast("region", periods=3)
        for r in results:
            for pred in r.predictions:
                assert pred["revenue"] >= 0.0

    def test_dimension_type_is_region(self, forecast_env):
        from src.forecasting.model import forecast
        results = forecast("region", periods=2)
        for r in results:
            assert r.dimension_type == "region"

    def test_specific_region_filter(self, forecast_env):
        from src.forecasting.model import forecast
        results = forecast("region", dimension_value="R001", periods=3)
        assert len(results) == 1
        assert results[0].dimension == "R001"

    def test_unknown_region_returns_empty(self, forecast_env):
        from src.forecasting.model import forecast
        results = forecast("region", dimension_value="RZZZ", periods=3)
        assert results == []


class TestForecastByCategory:
    def test_returns_results(self, forecast_env):
        from src.forecasting.model import forecast
        results = forecast("category", periods=3)
        assert len(results) > 0

    def test_category_values_present(self, forecast_env):
        from src.forecasting.model import forecast
        results = forecast("category", periods=3)
        for r in results:
            assert r.dimension_type == "category"
            assert r.dimension != ""


class TestForecastEdgeCases:
    def test_periods_clamped_to_max_12(self, forecast_env):
        from src.forecasting.model import forecast
        results = forecast("region", periods=99)
        for r in results:
            if r.predictions:
                assert len(r.predictions) == 12

    def test_periods_clamped_to_min_1(self, forecast_env):
        from src.forecasting.model import forecast
        results = forecast("region", periods=0)
        for r in results:
            if r.predictions:
                assert len(r.predictions) == 1

    def test_r2_is_float_or_none(self, forecast_env):
        from src.forecasting.model import forecast
        results = forecast("region", periods=3)
        for r in results:
            assert r.r2_cv is None or isinstance(r.r2_cv, float)

    def test_model_note_is_non_empty(self, forecast_env):
        from src.forecasting.model import forecast
        results = forecast("region", periods=3)
        for r in results:
            assert r.model_note != ""
