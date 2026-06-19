from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.insights.llm import ask_question, generate_insights, summarize_trends
from src.ingestion.schema import get_connection

router = APIRouter(tags=["AI insights"])


def _get_summary_context() -> dict:
    """Pull aggregated sales data to provide as LLM context."""
    with get_connection() as conn:
        total = conn.execute(
            "SELECT ROUND(SUM(revenue),2), COUNT(*) FROM sales_transactions"
        ).fetchone()

        by_region = conn.execute("""
            SELECT region_id, ROUND(SUM(revenue),2) AS revenue, COUNT(*) AS tx
            FROM sales_transactions GROUP BY region_id ORDER BY revenue DESC
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

    return {
        "total_revenue": total[0],
        "total_transactions": total[1],
        "by_region": [dict(r) for r in by_region],
        "by_category": [dict(r) for r in by_category],
        "monthly_trend": [dict(r) for r in monthly],
    }


class AskRequest(BaseModel):
    question: str


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
    Example response: {"question": "...", "answer": "Region R001 (North America) leads with $28,000."}
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty.")
    try:
        context = _get_summary_context()
        answer = ask_question(req.question, context)
        return AskResponse(question=req.question, answer=answer)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


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
        raise HTTPException(status_code=500, detail=str(exc))


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
        raise HTTPException(status_code=500, detail=str(exc))
