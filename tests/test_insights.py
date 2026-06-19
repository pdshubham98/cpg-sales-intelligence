"""
Unit tests for the LLM insights layer.
All LLM calls are mocked — no API key required.
"""
import os
from unittest.mock import MagicMock, patch

import pytest


MOCK_SUMMARY = {
    "total_revenue": 50000.0,
    "total_transactions": 100,
    "by_region": [{"region_id": "R001", "revenue": 30000.0, "tx": 60}],
    "by_category": [{"category": "Beverages", "revenue": 20000.0, "tx": 40}],
    "monthly_trend": [{"month": "2024-01", "revenue": 4000.0}],
}


class TestProviderRouting:
    def test_defaults_to_groq(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "groq", "GROQ_API_KEY": "test"}):
            import importlib
            import src.insights.llm as llm_module
            importlib.reload(llm_module)
            assert llm_module._PROVIDER == "groq"

    def test_switches_to_gemini(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "gemini", "GEMINI_API_KEY": "test"}):
            import importlib
            import src.insights.llm as llm_module
            importlib.reload(llm_module)
            assert llm_module._PROVIDER == "gemini"

    def test_unknown_provider_raises(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "unknown"}):
            import importlib
            import src.insights.llm as llm_module
            importlib.reload(llm_module)
            with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
                llm_module._call_llm("test")

    def test_missing_groq_key_raises(self):
        env = {"LLM_PROVIDER": "groq", "GROQ_API_KEY": ""}
        with patch.dict(os.environ, env, clear=False):
            import importlib
            import src.insights.llm as llm_module
            importlib.reload(llm_module)
            with pytest.raises(ValueError, match="GROQ_API_KEY"):
                llm_module._call_groq("test")

    def test_missing_gemini_key_raises(self):
        env = {"LLM_PROVIDER": "gemini", "GEMINI_API_KEY": ""}
        with patch.dict(os.environ, env, clear=False):
            import importlib
            import src.insights.llm as llm_module
            importlib.reload(llm_module)
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                llm_module._call_gemini("test")


class TestSummarizeTrends:
    def test_returns_string(self):
        with patch("src.insights.llm._call_llm", return_value="Strong growth in Q1."):
            from src.insights.llm import summarize_trends
            result = summarize_trends(MOCK_SUMMARY)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_passes_summary_in_prompt(self):
        with patch("src.insights.llm._call_llm", return_value="ok") as mock:
            from src.insights.llm import summarize_trends
            summarize_trends(MOCK_SUMMARY)
            call_args = mock.call_args[0][0]
            assert "50000" in call_args or "total_revenue" in call_args


class TestAskQuestion:
    def test_returns_string_answer(self):
        with patch("src.insights.llm._call_llm", return_value="R001 leads."):
            from src.insights.llm import ask_question
            result = ask_question("Which region leads?", MOCK_SUMMARY)
            assert isinstance(result, str)
            assert "R001" in result

    def test_question_included_in_prompt(self):
        with patch("src.insights.llm._call_llm", return_value="answer") as mock:
            from src.insights.llm import ask_question
            ask_question("What is revenue?", MOCK_SUMMARY)
            prompt = mock.call_args[0][0]
            assert "What is revenue?" in prompt


class TestGenerateInsights:
    def test_returns_list(self):
        raw = "1. Expand North America.\n2. Reduce Snacks inventory.\n3. Focus on Beverages.\n4. Invest in digital.\n5. Monitor Q4."
        with patch("src.insights.llm._call_llm", return_value=raw):
            from src.insights.llm import generate_insights
            result = generate_insights(MOCK_SUMMARY)
            assert isinstance(result, list)
            assert len(result) == 5

    def test_strips_numbering(self):
        raw = "1. Expand North America.\n2. Reduce costs."
        with patch("src.insights.llm._call_llm", return_value=raw):
            from src.insights.llm import generate_insights
            result = generate_insights(MOCK_SUMMARY)
            for item in result:
                assert not item[0].isdigit()

    def test_returns_at_most_5(self):
        raw = "\n".join(f"{i}. Insight {i}." for i in range(1, 10))
        with patch("src.insights.llm._call_llm", return_value=raw):
            from src.insights.llm import generate_insights
            result = generate_insights(MOCK_SUMMARY)
            assert len(result) <= 5
