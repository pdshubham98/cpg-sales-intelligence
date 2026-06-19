"""
LLM integration layer.
Primary: Groq (llama-3.3-70b-versatile) — free tier.
Fallback: Gemini (gemini-1.5-flash) — controlled by LLM_PROVIDER env var.
"""
from __future__ import annotations

import os
import logging
from typing import Any

logger = logging.getLogger(__name__)

_PROVIDER = os.getenv("LLM_PROVIDER", "groq").strip().lower()
_GROQ_MODEL = "llama-3.3-70b-versatile"
_GEMINI_MODEL = "gemini-1.5-flash"


def _call_llm(prompt: str) -> str:
    """Route to Groq or Gemini based on LLM_PROVIDER env var."""
    if _PROVIDER == "groq":
        return _call_groq(prompt)
    elif _PROVIDER == "gemini":
        return _call_gemini(prompt)
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER='{_PROVIDER}'. Must be 'groq' or 'gemini'."
        )


def _call_groq(prompt: str) -> str:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set.")

    from groq import Groq  # type: ignore

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=_GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1024,
    )
    return response.choices[0].message.content.strip()


def _call_gemini(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")

    from google import genai  # type: ignore
    from google.genai import types  # type: ignore

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=_GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=1024,
        ),
    )
    return response.text.strip()


# ---------------------------------------------------------------------------
# Public functions called by FastAPI routes
# ---------------------------------------------------------------------------

def summarize_trends(sales_summary: dict[str, Any]) -> str:
    """
    Given a sales summary dict, return a plain-English trend analysis.
    """
    prompt = f"""You are a senior CPG sales analyst. Analyze the following sales data
summary and provide a concise 3–5 sentence trend analysis. Focus on top-performing
regions, revenue growth patterns, and any notable anomalies.

Sales Summary:
{sales_summary}

Provide only the analysis, no preamble."""
    return _call_llm(prompt)


def ask_question(question: str, context: dict[str, Any]) -> str:
    """
    Answer a natural language question about the sales data.
    """
    prompt = f"""You are a CPG sales data analyst assistant. Answer the following
question using only the provided sales data context. Be concise and specific.

Sales Data Context:
{context}

Question: {question}

Answer:"""
    return _call_llm(prompt)


def generate_insights(sales_summary: dict[str, Any]) -> list[str]:
    """
    Generate 5 actionable business insights from sales data.
    Returns a list of insight strings.
    """
    prompt = f"""You are a CPG sales strategist. Based on the following sales data,
generate exactly 5 actionable business insights. Each insight should be a single
sentence starting with an action verb (e.g., "Expand", "Reduce", "Invest", "Focus").
Return each insight on its own line, numbered 1–5.

Sales Data:
{sales_summary}

Insights:"""
    raw = _call_llm(prompt)
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    # Strip leading numbering like "1." or "1)"
    cleaned = []
    for line in lines:
        if line and line[0].isdigit() and len(line) > 2 and line[1] in (".", ")"):
            cleaned.append(line[2:].strip())
        else:
            cleaned.append(line)
    return cleaned[:5]
