"""
Streamlit dashboard — 4 pages:
  1. Overview      — KPI cards + revenue charts
  2. Forecasting   — region/category revenue forecast
  3. Ask Data      — multi-session natural language chat
  4. AI Insights   — generated business insights + trend summary
"""
import time
import os
import requests
import streamlit as st
import pandas as pd
import plotly.express as px

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="CPG Sales Intelligence",
    page_icon="📊",
    layout="wide",
)


def _get(endpoint: str) -> dict:
    try:
        resp = requests.get(f"{API_BASE}{endpoint}", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        st.error(f"API error: {exc}")
        return {}


def _post(endpoint: str, payload: dict) -> dict:
    try:
        resp = requests.post(f"{API_BASE}{endpoint}", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        st.error(f"API error: {exc}")
        return {}


def _escape_md(text: str) -> str:
    """Escape $ so Streamlit does not render them as LaTeX math delimiters."""
    return text.replace("$", r"\$")


# ── Chat session helpers ──────────────────────────────────────────────────────

def _create_session() -> str:
    sid = f"chat_{int(time.time() * 1000)}"
    if "chat_sessions" not in st.session_state:
        st.session_state.chat_sessions = {}
    st.session_state.chat_sessions[sid] = {"name": "New Chat", "history": []}
    st.session_state.active_session_id = sid
    return sid


def _init_sessions():
    if "chat_sessions" not in st.session_state or not st.session_state.chat_sessions:
        _create_session()
    if (
        "active_session_id" not in st.session_state
        or st.session_state.active_session_id not in st.session_state.chat_sessions
    ):
        st.session_state.active_session_id = next(iter(st.session_state.chat_sessions))


def _delete_session(sid: str):
    sessions = st.session_state.chat_sessions
    sessions.pop(sid, None)
    if not sessions:
        _create_session()
    elif st.session_state.active_session_id == sid:
        st.session_state.active_session_id = next(iter(sessions))


def _session_label(session: dict) -> str:
    user_msgs = [m for m in session["history"] if m["role"] == "user"]
    if not user_msgs:
        return "New Chat"
    first = user_msgs[0]["content"]
    return first[:28] + "…" if len(first) > 28 else first


# ── Sidebar navigation ───────────────────────────────────────────────────────
page = st.sidebar.radio(
    "Navigation",
    ["Overview", "Forecasting", "Ask Data", "AI Insights"],
    index=0,
)

# ── Page: Overview ────────────────────────────────────────────────────────────
if page == "Overview":
    st.title("Sales Overview")
    data = _get("/sales-summary")
    if not data:
        st.stop()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Revenue", f"${data['total_revenue']:,.2f}")
    col2.metric("Total Transactions", f"{data['total_transactions']:,}")
    avg = (
        data["total_revenue"] / data["total_transactions"]
        if data["total_transactions"] else 0
    )
    col3.metric("Avg Revenue / Transaction", f"${avg:,.2f}")

    st.markdown("---")

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Revenue by Region")
        df_region = pd.DataFrame(data["by_region"])
        if not df_region.empty:
            fig = px.bar(
                df_region, x="region_id", y="revenue",
                labels={"region_id": "Region", "revenue": "Revenue ($)"},
                color="revenue", color_continuous_scale="Blues",
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Revenue by Category")
        df_cat = pd.DataFrame(data["by_category"])
        if not df_cat.empty:
            fig = px.pie(
                df_cat, names="category", values="revenue",
                hole=0.4,
            )
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Monthly Revenue Trend")
    df_monthly = pd.DataFrame(data["monthly_trend"])
    if not df_monthly.empty:
        fig = px.line(
            df_monthly, x="month", y="revenue",
            markers=True,
            labels={"month": "Month", "revenue": "Revenue ($)"},
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Revenue by Channel")
    df_channel = pd.DataFrame(data["by_channel"])
    if not df_channel.empty:
        fig = px.bar(
            df_channel, x="channel", y="revenue",
            color="channel",
            labels={"channel": "Channel", "revenue": "Revenue ($)"},
        )
        st.plotly_chart(fig, use_container_width=True)

# ── Page: Forecasting ─────────────────────────────────────────────────────────
elif page == "Forecasting":
    st.title("Revenue Forecasting")
    st.caption("Linear regression on historical monthly data. CV R² shown where available.")

    col1, col2, col3 = st.columns(3)
    with col1:
        dim_type = st.selectbox("Forecast by", ["region", "category"])
    with col2:
        dim_val = st.text_input("Specific value (leave blank for all)", value="")
    with col3:
        periods = st.slider("Months ahead", 1, 12, 3)

    if st.button("Run Forecast", type="primary"):
        payload = {
            "dimension_type": dim_type,
            "dimension_value": dim_val.strip() or None,
            "periods": periods,
        }
        results = _post("/forecast", payload)
        if isinstance(results, list) and results:
            for result in results:
                st.subheader(f"{result['dimension']} ({result['dimension_type']})")
                st.caption(result["model_note"])
                if result["predictions"]:
                    df = pd.DataFrame(result["predictions"])
                    fig = px.bar(
                        df, x="month", y="revenue",
                        labels={"month": "Month", "revenue": "Predicted Revenue ($)"},
                        color_discrete_sequence=["#2563EB"],
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Insufficient data for forecast.")
        else:
            st.warning("No forecast results returned.")

# ── Page: Ask Data (Multi-session chat) ───────────────────────────────────────
elif page == "Ask Data":
    _init_sessions()

    # Sidebar — conversation session list
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Conversations**")

    if st.sidebar.button("＋ New Chat", use_container_width=True):
        _create_session()
        st.rerun()

    for sid, session in list(st.session_state.chat_sessions.items()):
        is_active = sid == st.session_state.active_session_id
        label = _session_label(session)
        c1, c2 = st.sidebar.columns([5, 1])
        with c1:
            if st.button(
                label,
                key=f"sess_{sid}",
                type="primary" if is_active else "secondary",
                use_container_width=True,
            ):
                st.session_state.active_session_id = sid
                st.rerun()
        with c2:
            if st.button("✕", key=f"del_{sid}", use_container_width=True):
                _delete_session(sid)
                st.rerun()

    # Main area — active session
    active_sid = st.session_state.active_session_id
    session = st.session_state.chat_sessions[active_sid]
    history = session["history"]

    st.title("Ask Data")
    st.caption(
        "Chat with your sales data. Each conversation in the sidebar is independent."
    )

    # Render existing messages
    for msg in history:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                st.markdown(_escape_md(msg["content"]))
            else:
                st.markdown(msg["content"])

    # Chat input — sticks to the bottom
    user_input = st.chat_input("Ask a question about your sales data…")

    if user_input and user_input.strip():
        with st.chat_message("user"):
            st.markdown(user_input)
        history.append({"role": "user", "content": user_input})

        # Auto-name the session from the first user message
        if session["name"] == "New Chat" and len(history) == 1:
            session["name"] = (
                user_input[:28] + "…" if len(user_input) > 28 else user_input
            )

        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                result = _post(
                    "/ask",
                    {"question": user_input, "history": history[:-1]},
                )
            if result and "answer" in result:
                st.markdown(_escape_md(result["answer"]))
                history.append({"role": "assistant", "content": result["answer"]})
            else:
                error_msg = (
                    "Sorry, I could not get an answer. Please check your LLM API key."
                )
                st.error(error_msg)
                history.append({"role": "assistant", "content": error_msg})

# ── Page: AI Insights ─────────────────────────────────────────────────────────
elif page == "AI Insights":
    st.title("AI Insights")

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Trend Summary")
        if st.button("Generate Trend Summary"):
            with st.spinner("Analysing trends..."):
                result = _get("/trends")
            if result and "summary" in result:
                st.info(result["summary"])
            else:
                st.error("Could not generate summary. Check your LLM API key.")

    with col_b:
        st.subheader("Business Insights")
        if st.button("Generate Insights"):
            with st.spinner("Generating insights..."):
                result = _post("/insights", {})
            if result and "insights" in result:
                for i, insight in enumerate(result["insights"], 1):
                    st.markdown(f"**{i}.** {insight}")
            else:
                st.error("Could not generate insights. Check your LLM API key.")

# ── Sidebar footer ────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.caption("CPG Sales Intelligence v2.0")
