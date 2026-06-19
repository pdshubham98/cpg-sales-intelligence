"""
API integration tests using FastAPI TestClient.
LLM calls are mocked; DB is a seeded temp SQLite file.
"""
from unittest.mock import patch


class TestHealthEndpoint:
    def test_returns_ok(self, api_client):
        resp = api_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_db_rows_present(self, api_client):
        resp = api_client.get("/health")
        data = resp.json()
        assert "db_rows" in data
        assert data["db_rows"]["sales_transactions"] > 0
        assert data["db_rows"]["products"] == 1
        assert data["db_rows"]["regions"] == 1


class TestSalesSummaryEndpoint:
    def test_returns_200(self, api_client):
        resp = api_client.get("/sales-summary")
        assert resp.status_code == 200

    def test_has_expected_keys(self, api_client):
        resp = api_client.get("/sales-summary")
        data = resp.json()
        expected = (
            "total_revenue", "total_transactions", "by_region", "by_category", "monthly_trend"
        )
        for key in expected:
            assert key in data

    def test_total_revenue_is_positive(self, api_client):
        resp = api_client.get("/sales-summary")
        assert resp.json()["total_revenue"] > 0

    def test_monthly_trend_is_list(self, api_client):
        resp = api_client.get("/sales-summary")
        assert isinstance(resp.json()["monthly_trend"], list)


class TestForecastEndpoint:
    def test_region_forecast_returns_200(self, api_client):
        resp = api_client.post(
            "/forecast",
            json={"dimension_type": "region", "periods": 3},
        )
        assert resp.status_code == 200

    def test_category_forecast_returns_200(self, api_client):
        resp = api_client.post(
            "/forecast",
            json={"dimension_type": "category", "periods": 2},
        )
        assert resp.status_code == 200

    def test_forecast_result_has_predictions(self, api_client):
        resp = api_client.post(
            "/forecast",
            json={"dimension_type": "region", "periods": 3},
        )
        data = resp.json()
        assert isinstance(data, list)
        for item in data:
            assert "predictions" in item

    def test_invalid_periods_rejected(self, api_client):
        resp = api_client.post(
            "/forecast",
            json={"dimension_type": "region", "periods": 99},
        )
        assert resp.status_code == 422

    def test_unknown_dimension_returns_404(self, api_client):
        resp = api_client.post(
            "/forecast",
            json={"dimension_type": "region", "dimension_value": "RZZZ", "periods": 3},
        )
        assert resp.status_code == 404


class TestAskEndpoint:
    def test_returns_answer(self, api_client):
        with patch("src.api.routes.ask.ask_question", return_value="R001 leads."):
            resp = api_client.post("/ask", json={"question": "Which region leads?"})
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert data["answer"] == "R001 leads."

    def test_empty_question_returns_400(self, api_client):
        resp = api_client.post("/ask", json={"question": "   "})
        assert resp.status_code == 400

    def test_missing_api_key_returns_503(self, api_client):
        err = ValueError("GROQ_API_KEY environment variable is not set.")
        with patch("src.api.routes.ask.ask_question", side_effect=err):
            resp = api_client.post("/ask", json={"question": "test"})
        assert resp.status_code == 503


class TestInsightsEndpoint:
    def test_returns_list_of_insights(self, api_client):
        insights = [
            "Expand North America.", "Reduce costs.", "Focus on Beverages.",
            "Invest in Q4.", "Monitor HPC.",
        ]
        with patch("src.api.routes.ask.generate_insights", return_value=insights):
            resp = api_client.post("/insights", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert "insights" in data
        assert len(data["insights"]) == 5

    def test_missing_api_key_returns_503(self, api_client):
        err = ValueError("GROQ_API_KEY environment variable is not set.")
        with patch("src.api.routes.ask.generate_insights", side_effect=err):
            resp = api_client.post("/insights", json={})
        assert resp.status_code == 503


class TestTrendsEndpoint:
    def test_returns_summary(self, api_client):
        with patch("src.api.routes.ask.summarize_trends", return_value="Revenue is growing."):
            resp = api_client.get("/trends")
        assert resp.status_code == 200
        assert resp.json()["summary"] == "Revenue is growing."

    def test_missing_api_key_returns_503(self, api_client):
        err = ValueError("GROQ_API_KEY environment variable is not set.")
        with patch("src.api.routes.ask.summarize_trends", side_effect=err):
            resp = api_client.get("/trends")
        assert resp.status_code == 503
