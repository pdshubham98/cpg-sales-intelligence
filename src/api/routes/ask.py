import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.insights.llm import ask_question, generate_insights, summarize_trends
from src.ingestion.schema import get_connection
from src.market.benchmarks import get_quarterly_revenue

router = APIRouter(tags=["AI insights"])
logger = logging.getLogger(__name__)


def _get_summary_context() -> dict:
    """Pull aggregated sales data to provide as LLM context."""
    with get_connection() as conn:
        total = conn.execute(
            "SELECT ROUND(SUM(revenue),2), COUNT(*) FROM sales_transactions"
        ).fetchone()

        by_region = conn.execute("""
            SELECT COALESCE(r.region_name, s.region_id) AS region_name,
                   ROUND(SUM(s.revenue),2) AS revenue, COUNT(*) AS tx
            FROM sales_transactions s
            LEFT JOIN regions r ON s.region_id = r.region_id
            GROUP BY s.region_id, r.region_name ORDER BY revenue DESC
        """).fetchall()

        by_category = conn.execute("""
            SELECT p.category, ROUND(SUM(s.revenue),2) AS revenue, COUNT(*) AS tx
            FROM sales_transactions s
            JOIN products p ON s.product_id = p.product_id
            GROUP BY p.category ORDER BY revenue DESC
        """).fetchall()

        monthly = conn.execute("""
            SELECT strftime('%Y-%m', date) AS month, ROUND(SUM(revenue),2) AS revenue
            FROM sales_transactions GROUP BY month ORDER BY month
        """).fetchall()

    # Summarise industry benchmarks: latest quarter revenue per company
    industry: list[dict] = []
    try:
        raw = get_quarterly_revenue()
        seen: set[str] = set()
        for rec in sorted(raw, key=lambda r: r["quarter"], reverse=True):
            if rec["ticker"] not in seen:
                industry.append({
                    "company": rec["company"],
                    "quarter": rec["quarter"],
                    "revenue_usd_m": rec["revenue_m"],
                })
                seen.add(rec["ticker"])
    except Exception:
        pass  # market data is best-effort; don't fail the whole context

    return {
        "total_revenue": total[0],
        "total_transactions": total[1],
        "by_region": [dict(r) for r in by_region],
        "by_category": [dict(r) for r in by_category],
        "monthly_trend": [dict(r) for r in monthly],
        "industry_benchmarks": industry,
    }


class ChatMessage(BaseModel):
    role: str   # "user" or "assistant"
    content: str


class AskRequest(BaseModel):
    question: str
    history: Optional[list[ChatMessage]] = None


class AskResponse(BaseModel):
    question: str
    answer: str


class InsightsResponse(BaseModel):
    insights: list[str]


class TrendsResponse(BaseModel):
    summary: str


@router.post("/ask", response_model=AskResponse)
def ask_data(req: AskRequest):
    """
    Natural language Q&A against the sales data.

    Example request:  {"question": "Which region has the highest revenue?"}
    Example response: {"question": "...", "answer": "Region R001 leads with $28,000."}
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty.")
    try:
        context = _get_summary_context()
        history = (
            [{"role": m.role, "content": m.content} for m in req.history]
            if req.history else []
        )
        answer = ask_question(req.question, context, history=history)
        return AskResponse(question=req.question, answer=answer)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in /ask: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/insights", response_model=InsightsResponse)
def get_insights():
    """
    Generate 5 actionable business insights from current sales data.

    Example response:
    {"insights": ["Expand distribution in North America...", "Reduce inventory for..."]}
    """
    try:
        context = _get_summary_context()
        insights = generate_insights(context)
        return InsightsResponse(insights=insights)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in /insights: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/trends", response_model=TrendsResponse)
def get_trends():
    """
    LLM-generated trend summary from current sales data.

    Example response:
    {"summary": "Revenue has grown 12% month-over-month in North America..."}
    """
    try:
        context = _get_summary_context()
        summary = summarize_trends(context)
        return TrendsResponse(summary=summary)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in /trends: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")
