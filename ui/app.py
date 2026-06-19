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
import plotly.graph_objects as go

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="CPG Sales Intelligence",
    page_icon="📊",
    layout="wide",
)


def _get(endpoint: str, params: dict | None = None, timeout: int = 10) -> dict:
    try:
        resp = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error(
            f"Cannot reach the API at `{API_BASE}`. "
            "Make sure the backend is running and reload the page."
        )
        return {}
    except requests.exceptions.Timeout:
        st.error("The API took too long to respond. Please try again in a moment.")
        return {}
    except Exception as exc:
        st.error(f"Unexpected API error: {exc}")
        return {}


def _post(endpoint: str, payload: dict) -> dict:
    try:
        resp = requests.post(f"{API_BASE}{endpoint}", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error(
            f"Cannot reach the API at `{API_BASE}`. "
            "Make sure the backend is running and reload the page."
        )
        return {}
    except requests.exceptions.Timeout:
        st.error("The API took too long to respond. Please try again in a moment.")
        return {}
    except Exception as exc:
        st.error(f"Unexpected API error: {exc}")
        return {}


def _escape_md(text: str) -> str:
    """Escape $ so Streamlit does not render them as LaTeX math delimiters."""
    return text.replace("$", r"\$")


def _generate_html_report(
    data: dict, dq: dict, insights: dict | None = None,
    date_range: str = "", cpi_summary: dict | None = None,
) -> bytes:
    from datetime import datetime as _rdt

    generated_at = _rdt.now().strftime("%B %d, %Y at %I:%M %p")
    total_revenue = data.get("total_revenue", 0)
    total_tx = data.get("total_transactions", 0)
    avg_tx = total_revenue / total_tx if total_tx else 0
    mom = data.get("mom_delta", {})
    rev_delta = mom.get("revenue_delta_pct")
    tx_delta = mom.get("transactions_delta_pct")

    def _delta_html(val):
        if val is None:
            return ""
        color = "#16a34a" if val >= 0 else "#dc2626"
        arrow = "&#9650;" if val >= 0 else "&#9660;"
        return f'<div style="color:{color};font-size:13px;margin-top:6px">{arrow} {abs(val):.1f}% MoM</div>'

    def _prep_fig(fig):
        fig.update_layout(
            paper_bgcolor="white", plot_bgcolor="#f8fafc",
            margin=dict(t=50, b=30, l=20, r=20), height=320,
            font=dict(
                family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif",
                size=11,
            ),
        )
        return fig.to_html(include_plotlyjs=False, full_html=False)

    region_chart = cat_chart = monthly_chart = channel_chart = ""
    prod_chart = disc_chart1 = disc_chart2 = ""

    df_region = pd.DataFrame(data.get("by_region", []))
    if not df_region.empty:
        fig = px.bar(
            df_region, x="region_name", y="revenue",
            color="revenue", color_continuous_scale="Blues", text_auto=".2s",
            labels={"region_name": "Region", "revenue": "Revenue ($)"},
        )
        fig.update_layout(xaxis_tickangle=-20)
        fig.update_coloraxes(showscale=False)
        region_chart = _prep_fig(fig)

    df_cat = pd.DataFrame(data.get("by_category", []))
    if not df_cat.empty:
        fig = px.pie(df_cat, names="category", values="revenue", hole=0.45)
        cat_chart = _prep_fig(fig)

    df_monthly = pd.DataFrame(data.get("monthly_trend", []))
    if not df_monthly.empty:
        fig = px.line(
            df_monthly, x="month", y="revenue", markers=True,
            labels={"month": "Month", "revenue": "Revenue ($)"},
        )
        monthly_chart = _prep_fig(fig)

    df_channel = pd.DataFrame(data.get("by_channel", []))
    if not df_channel.empty:
        fig = px.bar(
            df_channel, x="channel", y="revenue", color="channel",
            text_auto=".2s", labels={"channel": "Channel", "revenue": "Revenue ($)"},
        )
        channel_chart = _prep_fig(fig)

    df_prod = pd.DataFrame(data.get("by_product", []))
    prod_table_html = ""
    if not df_prod.empty:
        fig = px.bar(
            df_prod.head(10), x="revenue", y="product_name",
            orientation="h", color="category", text_auto=".2s",
            labels={"revenue": "Revenue ($)", "product_name": "Product", "category": "Category"},
        )
        fig.update_layout(yaxis=dict(autorange="reversed"), height=380)
        prod_chart = _prep_fig(fig)
        avg_rev = df_prod["revenue"].mean()
        rows = ""
        for _, r in df_prod.head(10).iterrows():
            bg = "#f0fdf4" if r["revenue"] >= avg_rev else "#fffbeb"
            rows += (
                f'<tr style="background:{bg}">'
                f'<td>{r.get("product_name", "")}</td>'
                f'<td style="color:#64748b">{r.get("category", "")}</td>'
                f'<td style="text-align:right;font-weight:600">${r["revenue"]:,.2f}</td>'
                f"</tr>"
            )
        prod_table_html = (
            "<table>"
            "<thead><tr><th>Product</th><th>Category</th>"
            '<th style="text-align:right">Revenue</th></tr></thead>'
            f"<tbody>{rows}</tbody></table>"
            '<p style="font-size:11px;color:#94a3b8;margin-top:8px">'
            "Green = above average &nbsp;|&nbsp; Amber = below average</p>"
        )

    df_disc = pd.DataFrame(data.get("discount_analysis", []))
    if not df_disc.empty:
        fig = px.bar(
            df_disc, x="channel", y="avg_discount_pct", color="channel",
            text_auto=".1f",
            labels={"channel": "Channel", "avg_discount_pct": "Avg Discount (%)"},
        )
        disc_chart1 = _prep_fig(fig)
        fig = px.bar(
            df_disc, x="channel", y="revenue_foregone", color="channel",
            text_auto=".2s",
            labels={"channel": "Channel", "revenue_foregone": "Revenue Foregone ($)"},
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        disc_chart2 = _prep_fig(fig)

    insights_html = ""
    if insights and (insights.get("trend") or insights.get("insights")):
        trend_blk = ""
        if insights.get("trend"):
            trend_blk = (
                '<div style="padding:16px 20px;background:#f0fdf4;border-left:4px solid'
                ' #16a34a;border-radius:6px;margin-bottom:20px;color:#166534;'
                f'font-style:italic;line-height:1.6">{insights["trend"]}</div>'
            )
        icons = ["&#128269;", "&#128200;", "&#127919;", "&#128161;", "&#9889;"]
        items = "".join([
            f'<div style="padding:14px 18px;margin-bottom:10px;background:#eff6ff;'
            f'border-left:4px solid #2563eb;border-radius:6px;line-height:1.5">'
            f"{icons[i % 5]} &nbsp; {ins}</div>"
            for i, ins in enumerate(insights.get("insights", []))
        ])
        insights_html = (
            '<div class="section"><h2 class="section-title">AI Insights</h2>'
            f"{trend_blk}{items}</div>"
        )

    dq_html = ""
    if dq:
        raw = dq.get("raw_rows", 0)
        clean = dq.get("clean_rows", 0)
        dropped = dq.get("dropped_rows", 0)
        issues = dq.get("quality_issues", {})
        issues_rows = (
            "".join([
                f'<div style="font-size:13px;color:#475569;margin-top:6px">'
                f'&#8226; <code style="background:#f1f5f9;padding:2px 6px;'
                f'border-radius:3px;font-size:12px">{rule}</code>: {cnt} row(s)</div>'
                for rule, cnt in issues.items()
            ])
            if issues
            else '<div style="color:#16a34a;font-size:13px;margin-top:8px">&#10003; No quality issues detected</div>'
        )
        dq_html = (
            '<div class="section" style="background:#f8fafc">'
            '<h2 class="section-title">Data Quality</h2>'
            '<div style="display:flex;gap:56px;margin-bottom:20px">'
            f'<div><div style="font-size:32px;font-weight:700;color:#0f172a">{raw:,}</div>'
            '<div style="font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#94a3b8;margin-top:4px">Raw Rows</div></div>'
            f'<div><div style="font-size:32px;font-weight:700;color:#16a34a">{clean:,}</div>'
            '<div style="font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#94a3b8;margin-top:4px">Clean Rows</div></div>'
            f'<div><div style="font-size:32px;font-weight:700;color:#dc2626">{dropped:,}</div>'
            '<div style="font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#94a3b8;margin-top:4px">Dropped</div></div>'
            '</div>'
            '<div style="border-top:1px solid #e2e8f0;padding-top:16px">'
            '<div style="font-size:12px;font-weight:600;color:#374151;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">Quality Rules Applied</div>'
            f"{issues_rows}</div></div>"
        )

    # Macro Health section — rendered only when CPI data is available
    macro_html = ""
    if cpi_summary and rev_delta is not None:
        all_items = cpi_summary.get("All Items", {})
        cpi_mom = all_items.get("mom_pct")
        cpi_month = all_items.get("latest_month", "")
        if cpi_mom is not None:
            real_growth = round(rev_delta - cpi_mom, 1)
            beating = real_growth >= 0
            badge_bg    = "#dcfce7" if beating else "#fee2e2"
            badge_color = "#166534" if beating else "#991b1b"
            badge_text  = "Beating inflation ✅" if beating else "Lagging inflation ⚠️"
            cpi_rows = ""
            for cname, cv in cpi_summary.items():
                mom_v = cv.get("mom_pct")
                yoy_v = cv.get("yoy_pct")
                mom_s = f"{mom_v:+.2f}%" if mom_v is not None else "—"
                yoy_s = f"{yoy_v:+.1f}%" if yoy_v is not None else "—"
                cpi_rows += (
                    f"<tr><td style='padding:7px 12px'>{cname}</td>"
                    f"<td style='padding:7px 12px;text-align:right'>{mom_s}</td>"
                    f"<td style='padding:7px 12px;text-align:right'>{yoy_s}</td></tr>"
                )
            macro_html = (
                '<div class="section">'
                '<h2 class="section-title">Macro Health Check</h2>'
                '<div style="display:flex;gap:48px;flex-wrap:wrap;align-items:flex-start">'
                "<div>"
                '<div style="font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#94a3b8;margin-bottom:8px">Real Revenue Growth (MoM)</div>'
                f'<div style="font-size:36px;font-weight:700;color:#0f172a">{real_growth:+.1f}%</div>'
                f'<div style="display:inline-block;margin-top:10px;padding:6px 16px;background:{badge_bg};color:{badge_color};border-radius:20px;font-size:13px;font-weight:600">{badge_text}</div>'
                f'<div style="font-size:12px;color:#94a3b8;margin-top:8px">Revenue MoM ({rev_delta:+.1f}%) &minus; CPI ({cpi_mom:+.2f}%)</div>'
                "</div>"
                "<div>"
                f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#94a3b8;margin-bottom:8px">US CPI by Category &nbsp;({cpi_month})</div>'
                '<table style="font-size:13px;border-collapse:collapse;min-width:280px">'
                '<thead><tr style="background:#0f2952;color:white">'
                '<th style="padding:8px 12px;text-align:left">Category</th>'
                '<th style="padding:8px 12px;text-align:right">MoM</th>'
                '<th style="padding:8px 12px;text-align:right">YoY</th>'
                f"</tr></thead><tbody>{cpi_rows}</tbody></table>"
                "</div></div>"
                '<p style="font-size:11px;color:#94a3b8;margin-top:14px">'
                "Source: US Bureau of Labor Statistics (BLS) CPI-U. "
                "Real growth = your revenue MoM growth minus current CPI inflation rate.</p>"
                "</div>"
            )

    date_label = f"Period: {date_range}" if date_range else "All available data"
    no_insights_note = (
        "" if insights
        else ' &nbsp;|&nbsp; <span style="opacity:.6;font-size:12px">AI Insights not included — generate them on the Insights page first</span>'
    )

    top_products_section = (
        '<div class="section"><div class="section-title">Top 10 Products — Detail</div>'
        + prod_table_html
        + "</div>"
    ) if prod_table_html else ""

    discount_section = (
        '<div class="grid2">'
        '<div class="section" style="padding-bottom:8px"><div class="section-title">Avg Discount % by Channel</div>'
        + disc_chart1
        + '</div><div class="section" style="padding-bottom:8px"><div class="section-title">Revenue Foregone to Discounts</div>'
        + disc_chart2
        + "</div></div>"
    ) if disc_chart1 else ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>CPG Sales Intelligence Report</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f1f5f9;color:#1e293b}}
    .wrap{{max-width:1200px;margin:0 auto;padding:36px 28px}}
    .header{{background:linear-gradient(135deg,#0f2952 0%,#2563eb 100%);color:white;padding:44px 52px;border-radius:16px;margin-bottom:32px}}
    .header h1{{font-size:28px;font-weight:700;letter-spacing:-.5px;margin-bottom:10px}}
    .header p{{font-size:14px;opacity:.75;line-height:1.6}}
    .kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-bottom:28px}}
    .kpi{{background:white;border-radius:12px;padding:26px 28px;box-shadow:0 1px 4px rgba(0,0,0,.07);border-top:4px solid #2563eb}}
    .kpi-label{{font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px}}
    .kpi-value{{font-size:30px;font-weight:700;color:#0f172a;line-height:1}}
    .grid2{{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:24px}}
    .section{{background:white;border-radius:12px;padding:28px;box-shadow:0 1px 4px rgba(0,0,0,.07);margin-bottom:24px}}
    .section-title{{font-size:11px;font-weight:700;color:#64748b;margin-bottom:18px;padding-bottom:12px;border-bottom:1px solid #f1f5f9;text-transform:uppercase;letter-spacing:.08em}}
    table{{width:100%;border-collapse:collapse;font-size:14px}}
    thead tr{{background:#0f2952;color:white}}
    th{{padding:12px 16px;text-align:left;font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase}}
    td{{padding:10px 16px;border-bottom:1px solid #f8fafc}}
    .footer{{text-align:center;color:#94a3b8;font-size:12px;margin-top:40px;padding:24px;border-top:1px solid #e2e8f0}}
    @media print{{body{{background:white}}.wrap{{max-width:100%;padding:16px}}.section,.kpi{{box-shadow:none;border:1px solid #e2e8f0!important}}.grid2{{grid-template-columns:1fr}}}}
  </style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>CPG Sales Intelligence Report</h1>
    <p>{date_label} &nbsp;&bull;&nbsp; Generated {generated_at}{no_insights_note}</p>
  </div>

  <div class="kpis">
    <div class="kpi"><div class="kpi-label">Total Revenue</div><div class="kpi-value">${total_revenue:,.0f}</div>{_delta_html(rev_delta)}</div>
    <div class="kpi"><div class="kpi-label">Total Transactions</div><div class="kpi-value">{total_tx:,}</div>{_delta_html(tx_delta)}</div>
    <div class="kpi"><div class="kpi-label">Avg Revenue / Transaction</div><div class="kpi-value">${avg_tx:,.2f}</div></div>
  </div>

  {macro_html}

  <div class="grid2">
    <div class="section" style="padding-bottom:8px"><div class="section-title">Revenue by Region</div>{region_chart}</div>
    <div class="section" style="padding-bottom:8px"><div class="section-title">Revenue by Category</div>{cat_chart}</div>
  </div>

  <div class="section" style="padding-bottom:8px;margin-bottom:24px">
    <div class="section-title">Monthly Revenue Trend</div>{monthly_chart}
  </div>

  <div class="grid2">
    <div class="section" style="padding-bottom:8px"><div class="section-title">Revenue by Channel</div>{channel_chart}</div>
    <div class="section" style="padding-bottom:8px"><div class="section-title">Top 10 Products</div>{prod_chart}</div>
  </div>

  {top_products_section}
  {discount_section}
  {insights_html}
  {dq_html}

  <div class="footer">
    <p><strong>CPG Sales Intelligence</strong> &nbsp;&bull;&nbsp; v4.0 &nbsp;&bull;&nbsp; {generated_at}</p>
    <p style="margin-top:6px">Auto-generated from live sales data &nbsp;&bull;&nbsp; All figures in USD &nbsp;&bull;&nbsp; For internal use only</p>
  </div>
</div>
</body>
</html>"""
    return html.encode("utf-8")


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
    ["Overview", "Forecasting", "Ask Data", "AI Insights", "Market Intelligence"],
    index=0,
)

# ── Page: Overview ────────────────────────────────────────────────────────────
if page == "Overview":
    import datetime as _dt
    st.title("Sales Overview")

    # Date range filter
    with st.expander("Date Range Filter", expanded=False):
        _fc1, _fc2, _fc3 = st.columns([2, 2, 1])
        with _fc1:
            _start = st.date_input(
                "From", value=_dt.date(2024, 1, 1), min_value=_dt.date(2024, 1, 1),
                key="ov_start",
            )
        with _fc2:
            _end = st.date_input(
                "To", value=_dt.date(2025, 12, 31), max_value=_dt.date(2025, 12, 31),
                key="ov_end",
            )
        with _fc3:
            st.markdown(" ")
            if st.button("Reset", use_container_width=True):
                st.session_state.ov_start = _dt.date(2024, 1, 1)
                st.session_state.ov_end = _dt.date(2025, 12, 31)
                st.rerun()
    _params = {
        "start_date": str(_start) if "_start" in dir() else None,
        "end_date": str(_end) if "_end" in dir() else None,
    }

    data = _get("/sales-summary", params=_params)
    if not data:
        st.warning(
            "No data available. The API may still be starting up — "
            "wait a few seconds and reload the page."
        )
        st.stop()

    # Cache data quality once per session for use in the report
    if "dq_data" not in st.session_state:
        _dq_fetched = _get("/data-quality")
        if _dq_fetched:
            st.session_state.dq_data = _dq_fetched

    # Cache CPI once per session — 24-hour TTL handled on the backend
    if "cpi_data" not in st.session_state:
        _cpi_fetched = _get("/market/cpi", timeout=20)
        if _cpi_fetched and not _cpi_fetched.get("error"):
            st.session_state.cpi_data = _cpi_fetched

    mom = data.get("mom_delta", {})
    _rev_pct = mom.get("revenue_delta_pct")
    _tx_pct = mom.get("transactions_delta_pct")
    _mom_label = (
        f"vs {mom['prev_month']}" if mom.get("prev_month") else ""
    )

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Total Revenue", f"${data['total_revenue']:,.2f}",
        delta=f"{_rev_pct:+.1f}% MoM {_mom_label}" if _rev_pct is not None else None,
    )
    col2.metric(
        "Total Transactions", f"{data['total_transactions']:,}",
        delta=f"{_tx_pct:+.1f}% MoM {_mom_label}" if _tx_pct is not None else None,
    )
    avg = (
        data["total_revenue"] / data["total_transactions"]
        if data["total_transactions"] else 0
    )
    col3.metric("Avg Revenue / Transaction", f"${avg:,.2f}")

    st.markdown("---")

    # ── Macro Health Check ────────────────────────────────────────────────────
    _cpi = st.session_state.get("cpi_data", {})
    _cpi_summary = _cpi.get("summary", {})
    _all_items = _cpi_summary.get("All Items", {})
    _cpi_mom = _all_items.get("mom_pct")
    _cpi_month = _all_items.get("latest_month", "")

    if _cpi_mom is not None and _rev_pct is not None:
        _real_growth = round(_rev_pct - _cpi_mom, 1)
        _beating = _real_growth >= 0
        st.subheader("Macro Health Check")
        _mh1, _mh2, _mh3, _mh4 = st.columns(4)
        _mh1.metric(
            f"US CPI — All Items ({_cpi_month})",
            f"{_cpi_mom:+.2f}% MoM",
            help="Bureau of Labor Statistics CPI-U. General US inflation rate.",
        )
        _mh2.metric(
            "Real Revenue Growth (MoM)",
            f"{_real_growth:+.1f}%",
            delta="Beating inflation" if _beating else "Lagging inflation",
            delta_color="normal" if _beating else "inverse",
            help="Your MoM revenue growth minus current CPI. Positive = outpacing inflation.",
        )
        _food_yoy = _cpi_summary.get("Food at Home", {}).get("yoy_pct")
        if _food_yoy is not None:
            _mh3.metric(
                "Food at Home CPI (YoY)",
                f"{_food_yoy:+.1f}%",
                help="Year-over-year grocery inflation — key COGS driver for food/bev CPG.",
            )
        _hpc_yoy = _cpi_summary.get("Personal Care", {}).get("yoy_pct")
        if _hpc_yoy is not None:
            _mh4.metric(
                "Personal Care CPI (YoY)",
                f"{_hpc_yoy:+.1f}%",
                help="Year-over-year HPC inflation. Benchmark for your personal care SKUs.",
            )
        st.caption(
            f"Source: US Bureau of Labor Statistics (BLS) CPI-U · Latest: {_cpi_month} · "
            "Real growth = your revenue MoM − CPI MoM"
        )
        st.markdown("---")

    # Single HTML report download — replaces all individual CSV exports
    _insights_cache = st.session_state.get("insights_cache")
    _dq_report = st.session_state.get("dq_data", {})
    _cpi_report = st.session_state.get("cpi_data", {}).get("summary")
    _date_range_str = f"{_start} to {_end}"
    _report_bytes = _generate_html_report(
        data, _dq_report, _insights_cache, _date_range_str, _cpi_report
    )
    _rc1, _rc2 = st.columns([1, 4])
    with _rc1:
        st.download_button(
            label="📊 Download Report",
            data=_report_bytes,
            file_name=f"cpg_report_{_start}_{_end}.html",
            mime="text/html",
            type="primary",
            use_container_width=True,
        )
    with _rc2:
        if not _insights_cache:
            st.caption(
                "💡 Tip: Go to **AI Insights** and click **Generate All Insights** "
                "to include the AI analysis section in the report."
            )

    st.markdown("---")

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Revenue by Region")
        df_region = pd.DataFrame(data["by_region"])
        if not df_region.empty:
            fig = px.bar(
                df_region, x="region_name", y="revenue",
                labels={"region_name": "Region", "revenue": "Revenue ($)"},
                color="revenue", color_continuous_scale="Blues",
                text_auto=".2s",
            )
            fig.update_layout(xaxis_tickangle=-20)
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
            text_auto=".2s",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Top Products by Revenue")
    df_prod = pd.DataFrame(data.get("by_product", []))
    if not df_prod.empty:
        fig = px.bar(
            df_prod.head(10), x="revenue", y="product_name",
            orientation="h",
            color="category",
            labels={"revenue": "Revenue ($)", "product_name": "Product", "category": "Category"},
            text_auto=".2s",
        )
        fig.update_layout(yaxis=dict(autorange="reversed"), height=380)
        st.plotly_chart(fig, use_container_width=True)

    # Discount analysis
    df_discount = pd.DataFrame(data.get("discount_analysis", []))
    if not df_discount.empty:
        st.markdown("---")
        st.subheader("Discount Analysis by Channel")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            fig = px.bar(
                df_discount, x="channel", y="avg_discount_pct",
                labels={"channel": "Channel", "avg_discount_pct": "Avg Discount (%)"},
                color="channel", text_auto=".1f",
                title="Average Discount %",
            )
            st.plotly_chart(fig, use_container_width=True)
        with col_d2:
            fig = px.bar(
                df_discount, x="channel", y="revenue_foregone",
                labels={"channel": "Channel", "revenue_foregone": "Revenue Foregone ($)"},
                color="channel", text_auto=".2s",
                title="Revenue Foregone to Discounts",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            st.plotly_chart(fig, use_container_width=True)

    # Data quality report
    st.markdown("---")
    with st.expander("Data Quality Report", expanded=False):
        dq = st.session_state.get("dq_data") or _get("/data-quality")
        if dq:
            c1, c2, c3 = st.columns(3)
            c1.metric("Raw Rows Ingested", dq.get("raw_rows", "—"))
            c2.metric("Clean Rows Loaded", dq.get("clean_rows", "—"))
            c3.metric("Rows Dropped", dq.get("dropped_rows", "—"))
            issues = dq.get("quality_issues", {})
            if issues:
                st.markdown("**Quality rules applied:**")
                for rule, count in issues.items():
                    st.markdown(f"- `{rule}`: **{count}** row(s) affected")
            else:
                st.success("No quality issues detected.")
        else:
            st.info("Quality report not yet available (API may be starting up).")

# ── Page: Forecasting ─────────────────────────────────────────────────────────
elif page == "Forecasting":
    st.title("Revenue Forecasting")
    st.caption("Linear regression on historical monthly data. CV R² shown where available.")

    # Load valid dimension values for the dropdowns
    _summary = _get("/sales-summary")
    _region_options = {
        r["region_name"]: r["region_id"]
        for r in _summary.get("by_region", [])
    }
    _category_options = [c["category"] for c in _summary.get("by_category", [])]

    _product_options = [p["product_name"] for p in _summary.get("by_product", [])]

    col1, col2, col3 = st.columns(3)
    with col1:
        dim_type = st.selectbox("Forecast by", ["region", "category", "product"])
    with col2:
        if dim_type == "region":
            _region_choices = ["All regions"] + list(_region_options.keys())
            _sel_region = st.selectbox("Region", _region_choices)
            dim_val = None if _sel_region == "All regions" else _region_options[_sel_region]
        elif dim_type == "category":
            _cat_choices = ["All categories"] + _category_options
            _sel_cat = st.selectbox("Category", _cat_choices)
            dim_val = None if _sel_cat == "All categories" else _sel_cat
        else:
            _prod_choices = ["All products"] + _product_options
            _sel_prod = st.selectbox("Product", _prod_choices)
            dim_val = None if _sel_prod == "All products" else _sel_prod
    with col3:
        periods = st.slider("Months ahead", 1, 12, 3)

    if st.button("Run Forecast", type="primary"):
        payload = {
            "dimension_type": dim_type,
            "dimension_value": dim_val,
            "periods": periods,
        }
        results = _post("/forecast", payload)
        if isinstance(results, list) and results:
            for result in results:
                st.subheader(f"{result['dimension']} ({result['dimension_type']})")
                r2 = result.get("r2_cv")
                quality = (
                    f"Model fit: R² = {r2:.3f} "
                    + ("(good)" if r2 and r2 >= 0.7 else "(low — interpret with caution)")
                    if r2 is not None else "Model fit: insufficient data for R²"
                )
                st.caption(f"{result['model_note']}  |  {quality}")

                hist = result.get("historical", [])
                preds = result.get("predictions", [])

                if preds:
                    fig = go.Figure()
                    if hist:
                        df_h = pd.DataFrame(hist)
                        fig.add_trace(go.Bar(
                            x=df_h["month"], y=df_h["revenue"],
                            name="Historical",
                            marker_color="#94A3B8",
                        ))
                    df_p = pd.DataFrame(preds)
                    fig.add_trace(go.Scatter(
                        x=df_p["month"], y=df_p["revenue"],
                        mode="lines+markers",
                        name="Forecast",
                        line=dict(color="#2563EB", dash="dash", width=2),
                        marker=dict(size=8),
                    ))
                    fig.update_layout(
                        xaxis_title="Month",
                        yaxis_title="Revenue ($)",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02),
                        hovermode="x unified",
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

    # Suggested questions — shown only when the conversation is empty
    _SUGGESTED = [
        "Which region has the highest revenue?",
        "What are the top 3 products by sales?",
        "Which channel drives the most transactions?",
        "How has monthly revenue trended this year?",
    ]
    _quick_fire: str | None = None
    if not history:
        st.markdown("**Try asking:**")
        _cols = st.columns(len(_SUGGESTED))
        for _col, _q in zip(_cols, _SUGGESTED):
            with _col:
                if st.button(_q, use_container_width=True, key=f"suggest_{_q[:20]}"):
                    _quick_fire = _q

    # Chat input — sticks to the bottom
    user_input = st.chat_input("Ask a question about your sales data…") or _quick_fire

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
    st.caption(
        "AI-generated analysis of your current sales data. Results are cached for this session."
    )

    _INSIGHT_ICONS = ["🔍", "📈", "🎯", "💡", "⚡"]

    col_gen, col_clear = st.columns([3, 1])
    with col_gen:
        _generate = st.button("Generate All Insights", type="primary", use_container_width=True)
    with col_clear:
        if st.button("Clear cache", use_container_width=True):
            st.session_state.pop("insights_cache", None)
            st.rerun()

    if _generate:
        with st.spinner("Generating insights and trend summary…"):
            _trend_res = _get("/trends")
            _insights_res = _post("/insights", {})
        if _trend_res or _insights_res:
            st.session_state.insights_cache = {
                "trend": _trend_res.get("summary", ""),
                "insights": _insights_res.get("insights", []),
            }
        else:
            st.error("Could not generate insights. Check your LLM API key.")

    _cache = st.session_state.get("insights_cache")
    if _cache:
        st.markdown("---")

        # Trend summary block
        if _cache.get("trend"):
            st.subheader("Trend Summary")
            st.info(_cache["trend"])
            st.markdown("")

        # Insight cards
        if _cache.get("insights"):
            st.subheader("Business Insights")
            for i, insight in enumerate(_cache["insights"]):
                icon = _INSIGHT_ICONS[i % len(_INSIGHT_ICONS)]
                with st.container(border=True):
                    st.markdown(f"{icon} &nbsp; {insight}")
    else:
        st.markdown(
            "> Click **Generate All Insights** to get an AI-powered trend analysis "
            "and 5 actionable business insights from your current sales data."
        )

# ── Page: Market Intelligence ─────────────────────────────────────────────────
elif page == "Market Intelligence":
    st.title("Market Intelligence")
    st.caption(
        "Real market data from Yahoo Finance and Open Food Facts — "
        "benchmark your sales against the broader CPG industry."
    )

    # ── CPG Sector Benchmark ──────────────────────────────────────────────────
    st.subheader("CPG Sector Performance")
    st.markdown(
        "Top CPG companies indexed to **100** at the start of the period. "
        "Values above 100 mean the stock has risen — use this to gauge whether "
        "your sales growth is ahead of or behind broader market momentum."
    )

    _period_labels = {"3 Months": "3mo", "6 Months": "6mo", "1 Year": "1y"}
    _period_label = st.radio(
        "Timeframe",
        list(_period_labels.keys()),
        horizontal=True,
        index=2,
        label_visibility="collapsed",
    )
    _period = _period_labels[_period_label]

    with st.spinner("Fetching sector data from Yahoo Finance… (cached after first load)"):
        _sector_raw = _get("/market/sector", params={"period": _period}, timeout=60)

    if _sector_raw and isinstance(_sector_raw, list) and len(_sector_raw) > 0:
        df_sector = pd.DataFrame(_sector_raw)

        fig = px.line(
            df_sector, x="date", y="value", color="company",
            labels={
                "value":   "Indexed Return (Base = 100)",
                "date":    "Date",
                "company": "Company",
            },
            color_discrete_sequence=px.colors.qualitative.Set1,
        )
        fig.add_hline(
            y=100, line_dash="dash", line_color="#94a3b8", opacity=0.6,
            annotation_text="Baseline", annotation_position="bottom right",
        )
        fig.update_layout(
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Compact summary table — one row per company
        _summary_df = (
            df_sector.sort_values("date")
            .groupby("ticker", as_index=False)
            .agg(
                Company=("company", "last"),
                period_return=("period_return", "last"),
                current_price=("current_price", "last"),
            )
            .sort_values("period_return", ascending=False)
        )
        _summary_df["Period Return"] = _summary_df["period_return"].apply(
            lambda v: f"{'▲' if v >= 0 else '▼'} {abs(v):.1f}%"
        )
        _summary_df["Current Price (USD)"] = _summary_df["current_price"].apply(
            lambda v: f"${v:,.2f}"
        )
        st.dataframe(
            _summary_df[["ticker", "Company", "Period Return", "Current Price (USD)"]].rename(
                columns={"ticker": "Ticker"}
            ),
            use_container_width=True,
            hide_index=True,
        )
        st.caption("Source: Yahoo Finance via yfinance. Prices shown in USD (ADR for non-US companies).")
    else:
        st.info(
            "Sector data is unavailable right now. "
            "This requires an internet connection and may take ~10 s on first load."
        )

    st.markdown("---")

    # ── Inflation & Macro Context ─────────────────────────────────────────────
    st.subheader("Inflation & Macro Context")
    st.markdown(
        "US Consumer Price Index (BLS) across CPG categories — "
        "see whether your portfolio is growing in **real terms** or simply tracking inflation."
    )

    _cpi_raw = st.session_state.get("cpi_data") or _get("/market/cpi", timeout=20)
    if _cpi_raw and not _cpi_raw.get("error") and not st.session_state.get("cpi_data"):
        st.session_state.cpi_data = _cpi_raw

    if _cpi_raw and _cpi_raw.get("series"):
        _series = _cpi_raw["series"]
        _cpi_sum = _cpi_raw.get("summary", {})

        # Trend chart — all four CPI series
        _cpi_rows = []
        for _sname, _spts in _series.items():
            for _pt in _spts:
                _cpi_rows.append({
                    "Month": _pt["month"],
                    "CPI Value": _pt["value"],
                    "Category": _sname,
                })
        if _cpi_rows:
            df_cpi = pd.DataFrame(_cpi_rows)
            fig = px.line(
                df_cpi, x="Month", y="CPI Value", color="Category",
                markers=False,
                labels={"CPI Value": "CPI (1982–84 = 100)", "Month": "Month"},
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_layout(
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig, use_container_width=True)

        # Summary table — MoM + YoY per category
        if _cpi_sum:
            _sum_rows = [
                {
                    "Category": name,
                    "Latest Month": v.get("latest_month", "—"),
                    "CPI Value": f"{v['latest_value']:.3f}" if v.get("latest_value") else "—",
                    "MoM Change": (
                        f"{'▲' if v['mom_pct'] >= 0 else '▼'} {abs(v['mom_pct']):.2f}%"
                        if v.get("mom_pct") is not None else "—"
                    ),
                    "YoY Change": (
                        f"{'▲' if v['yoy_pct'] >= 0 else '▼'} {abs(v['yoy_pct']):.1f}%"
                        if v.get("yoy_pct") is not None else "—"
                    ),
                }
                for name, v in _cpi_sum.items()
            ]
            st.dataframe(
                pd.DataFrame(_sum_rows),
                use_container_width=True,
                hide_index=True,
            )

        # Inflation vs revenue growth callout
        _all_cpi = _cpi_sum.get("All Items", {})
        _cpi_yoy = _all_cpi.get("yoy_pct")
        if _cpi_yoy is not None:
            _rev_data = _get("/sales-summary")
            _rev_mom = _rev_data.get("mom_delta", {}).get("revenue_delta_pct") if _rev_data else None
            if _rev_mom is not None:
                _real = round(_rev_mom - (_all_cpi.get("mom_pct") or 0), 1)
                _color = "normal" if _real >= 0 else "inverse"
                st.metric(
                    label=f"Portfolio Real Revenue Growth (MoM vs CPI {_all_cpi.get('latest_month','')})",
                    value=f"{_real:+.1f}%",
                    delta="Outpacing inflation ✅" if _real >= 0 else "Below inflation ⚠️",
                    delta_color=_color,
                    help="Revenue MoM % − CPI All Items MoM %. Positive means you are growing faster than inflation.",
                )

        st.caption(
            "Source: Bureau of Labor Statistics CPI-U (not seasonally adjusted). "
            "Series: CUUR0000SA0 · CUUR0000SAF11 · CUUR0000SEHF · CUUR0000SAP. "
            "Cached 24 hours."
        )

    elif _cpi_raw and _cpi_raw.get("error"):
        st.warning(
            f"BLS CPI data unavailable: {_cpi_raw['error']}. "
            "The public BLS API allows 25 requests/day — try again later or check your connection."
        )
    else:
        st.info("CPI data is loading. Reload the page if this persists.")

    st.markdown("---")

    # ── Product Discovery ─────────────────────────────────────────────────────
    st.subheader("Real Product Discovery")
    st.markdown(
        "Browse real products from **Open Food Facts** — a free, open database of 3M+ "
        "CPG products globally. Nutri-Score and Eco-Score are standardised ratings used "
        "across major retailers in Europe and increasingly worldwide."
    )

    _OFF_CATS = ["Beverages", "Snacks", "Dry Goods", "Chilled", "HPC", "All"]
    _NUTRI_ICON = {"A": "🟢 A", "B": "🟡 B", "C": "🟠 C", "D": "🔴 D", "E": "⚫ E", "—": "—"}
    _ECO_ICON   = {"A": "🌿 A", "B": "🌱 B", "C": "🍂 C", "D": "💨 D", "E": "🔥 E", "—": "—"}

    _off_c1, _off_c2, _off_c3 = st.columns([2, 1, 1])
    with _off_c1:
        _off_cat = st.selectbox(
            "Category", _OFF_CATS,
            index=0, label_visibility="visible",
        )
    with _off_c2:
        _off_limit = st.select_slider(
            "Results", options=[12, 24, 50, 100], value=24,
            label_visibility="visible",
        )
    with _off_c3:
        st.markdown(" ")
        _load_off = st.button("Load Products", type="primary", use_container_width=True)

    if _load_off:
        with st.spinner("Fetching products from Open Food Facts…"):
            _off_data = _get(
                "/market/products",
                params={"category": _off_cat, "limit": _off_limit},
                timeout=25,
            )
        if _off_data:
            st.session_state.off_data    = _off_data
            st.session_state.off_cat_sel = _off_cat

    _off = st.session_state.get("off_data")
    _off_cat_sel = st.session_state.get("off_cat_sel", _off_cat)

    if _off:
        if _off.get("error"):
            st.warning(
                f"Open Food Facts returned an error: {_off['error']}. "
                "Check your internet connection and try again."
            )
        elif _off.get("products"):
            total_in_mkt = _off.get("total_in_market", 0)
            returned     = _off.get("returned", 0)

            _mk1, _mk2 = st.columns(2)
            _mk1.metric(f"'{_off_cat_sel}' products globally", f"{total_in_mkt:,}")
            _mk2.metric("Showing", f"{returned:,} products")

            # Product table
            df_off = pd.DataFrame(_off["products"])
            df_off["Nutri-Score"] = df_off["nutriscore"].map(
                lambda g: _NUTRI_ICON.get(g, "—")
            )
            df_off["Eco-Score"] = df_off["ecoscore"].map(
                lambda g: _ECO_ICON.get(g, "—")
            )
            df_off = df_off.rename(columns={
                "name": "Product", "brand": "Brand",
                "quantity": "Pack Size", "categories": "Category",
            })
            st.dataframe(
                df_off[["Product", "Brand", "Pack Size", "Nutri-Score", "Eco-Score", "Category"]],
                use_container_width=True,
                hide_index=True,
                height=420,
            )

            # Brand landscape
            top_brands = _off.get("top_brands", [])
            if top_brands:
                st.markdown("---")
                st.subheader("Brand Landscape")
                st.caption(
                    f"How often each brand appears in the top {returned} most popular "
                    f"'{_off_cat_sel}' products — a proxy for shelf presence."
                )
                df_brands = pd.DataFrame(top_brands)
                fig = px.bar(
                    df_brands, x="count", y="brand",
                    orientation="h",
                    labels={"count": "Products in Sample", "brand": "Brand"},
                    color="count", color_continuous_scale="Blues",
                    text_auto=True,
                )
                fig.update_layout(yaxis=dict(autorange="reversed"))
                fig.update_coloraxes(showscale=False)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(
                f"No products found for **{_off_cat_sel}**. "
                "Try a different category or increase the result count."
            )
    else:
        with st.container(border=True):
            st.markdown(
                "**How to use this section**\n\n"
                "1. Select a category matching your internal product mix\n"
                "2. Click **Load Products** to pull live data from Open Food Facts\n"
                "3. Compare real market products — brands, pack sizes, Nutri/Eco scores — "
                "against your own SKU portfolio\n\n"
                "_Data is cached for 6 hours after first load._"
            )

    st.markdown("---")
    st.caption(
        "Product data: [Open Food Facts](https://world.openfoodfacts.org) — "
        "open database, CC BY-SA 4.0 license. &nbsp;|&nbsp; "
        "Stock data: Yahoo Finance (yfinance). &nbsp;|&nbsp; "
        "Nutri-Score: A (best) → E (worst). &nbsp;|&nbsp; "
        "Eco-Score: A (lowest impact) → E (highest impact)."
    )

# ── Sidebar footer ────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.caption("CPG Sales Intelligence v4.0")
