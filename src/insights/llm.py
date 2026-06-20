"""
LLM integration layer.
Primary: Groq (llama-3.3-70b-versatile) — free tier.
Fallback: Gemini (gemini-1.5-flash) — controlled by LLM_PROVIDER env var.
"""
from __future__ import annotations

import json
import os
import time
import logging
from typing import Any

logger = logging.getLogger(__name__)


# Lazy import of metrics to avoid circular imports and allow tests without prometheus
def _metrics():
    try:
        from src.api.metrics import LLM_LATENCY, LLM_ERRORS, LLM_FALLBACKS
        return LLM_LATENCY, LLM_ERRORS, LLM_FALLBACKS
    except Exception:
        return None, None, None


_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0  # seconds; doubles each attempt

_GROQ_MODEL = "llama-3.3-70b-versatile"
_GEMINI_MODEL = "gemini-1.5-flash"

_groq_client = None
_gemini_client = None


def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set.")
        from groq import Groq  # type: ignore
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
        from google import genai  # type: ignore
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def _call_llm(prompt: str) -> str:
    """Route to Groq or Gemini based on LLM_PROVIDER env var.

    If primary provider is Groq and all retries fail, automatically falls
    back to Gemini when GEMINI_API_KEY is set — no manual intervention needed.
    """
    _, _, llm_fallbacks = _metrics()
    provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()
    if provider == "groq":
        try:
            return _call_groq(prompt)
        except Exception as exc:
            gemini_key = os.getenv("GEMINI_API_KEY", "")
            if gemini_key:
                logger.warning(
                    "Groq failed (%s) — falling back to Gemini automatically", exc
                )
                if llm_fallbacks:
                    llm_fallbacks.inc()
                return _call_gemini(prompt)
            raise
    elif provider == "gemini":
        return _call_gemini(prompt)
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER='{provider}'. Must be 'groq' or 'gemini'."
        )


def _call_groq(prompt: str) -> str:
    client = _get_groq_client()
    llm_latency, llm_errors, _ = _metrics()
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        t0 = time.time()
        try:
            response = client.chat.completions.create(
                model=_GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1024,
            )
            if llm_latency:
                llm_latency.labels(provider="groq").observe(time.time() - t0)
            return response.choices[0].message.content.strip()
        except Exception as exc:
            last_exc = exc
            if llm_errors:
                llm_errors.labels(provider="groq").inc()
            # Bail immediately on auth errors; retry on rate limit / transient
            if "401" in str(exc) or "invalid_api_key" in str(exc).lower():
                raise
            delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
            logger.warning(
                "Groq call failed (attempt %d/%d): %s. Retrying in %.1fs",
                attempt, _MAX_RETRIES, exc, delay,
            )
            if attempt < _MAX_RETRIES:
                time.sleep(delay)
    raise RuntimeError(f"Groq failed after {_MAX_RETRIES} attempts") from last_exc


def _call_gemini(prompt: str) -> str:
    from google.genai import types  # type: ignore

    client = _get_gemini_client()
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
{json.dumps(sales_summary, indent=2, default=str)}

Provide only the analysis, no preamble."""
    return _call_llm(prompt)


def ask_question(
    question: str,
    context: dict[str, Any],
    history: list[dict] | None = None,
) -> str:
    """
    Answer a natural language question about the sales data.
    Accepts optional conversation history to support multi-turn chat.
    """
    history_block = ""
    if history:
        # Include up to the last 6 turns (3 exchanges) as context
        recent = history[-6:]
        lines = []
        for msg in recent:
            prefix = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{prefix}: {msg['content']}")
        history_block = "\nConversation so far:\n" + "\n".join(lines) + "\n"

    prompt = (
        "You are a CPG sales data analyst assistant. "
        "Answer the following question using only the provided sales data context.\n\n"
        "Formatting rules:\n"
        "- Use bullet points or numbered lists when presenting multiple items or data points\n"
        "- Write currency as plain dollar amounts (e.g. $2,878.20)\n"
        "- Use clear, plain English — no LaTeX or math notation\n"
        "- Keep your answer concise and well-structured\n"
        f"{history_block}\n"
        f"Sales Data Context:\n{json.dumps(context, indent=2, default=str)}\n\n"
        f"Question: {question}\n\nAnswer:"
    )
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
{json.dumps(sales_summary, indent=2, default=str)}

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
