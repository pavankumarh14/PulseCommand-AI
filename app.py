"""Dashboard — live hospital KPIs, occupancy charts, ICU gauges, AI briefing."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from agents.resource_monitor import ResourceMonitorAgent
from core.database import Database
from core.llm_connector import LLMConnector

st.set_page_config(
    page_title="PulseCommand AI",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Shared resources (cached for session) ────────────────────────────────────

@st.cache_resource(show_spinner=False)
def _load_resources():
    llm     = LLMConnector()
    db      = Database()
    monitor = ResourceMonitorAgent(llm=llm, db=db)
    return monitor, db, llm

monitor, db, llm = _load_resources()

# ── Header ────────────────────────────────────────────────────────────────────

st.title("📊 Operations Dashboard")
st.caption(f"Real-time hospital resource monitoring · LLM: {llm.provider_info()}")
st.divider()

# ── KPI cards ─────────────────────────────────────────────────────────────────

with st.spinner("Loading metrics …"):
    metrics = monitor.get_summary_metrics()

col1, col2, col3, col4, col5 = st.columns(5)

occ_pct = f"{metrics['overall_occupancy']:.1%}"
icu_pct = f"{metrics['icu']['utilization_rate']:.1%}"

col1.metric("🛏️ Total Beds",      metrics["total_beds"])
col2.metric("📈 Occupancy",        occ_pct,
            delta="▲ High"   if metrics["overall_occupancy"] > 0.85 else "Normal",
            delta_color="inverse" if metrics["overall_occupancy"] > 0.85 else "normal")
col3.metric("✅ Available",         metrics["available"])
col4.metric("🏥 ICU Utilisation",   icu_pct,
            delta="▲ Critical" if metrics["icu"]["utilization_rate"] > 0.90 else "Normal",
            delta_color="inverse" if metrics["icu"]["utilization_rate"] > 0.90 else "normal")
col5.metric("🚨 Active Alerts",     metrics["total_alerts"],
            delta=f"{metrics['critical_alerts']} critical",
            delta_color="inverse" if metrics["critical_alerts"] > 0 else "normal")

st.divider()

# ── Row 1: Ward occupancy bar + ICU gauge ─────────────────────────────────────

left, right = st.columns([2, 1])

with left:
    st.subheader("Ward Bed Occupancy")
    ward_df = metrics["ward_status"].copy()
    ward_df["pct"] = (ward_df["occupancy_rate"] * 100).round(1)

    fig = px.bar(
        ward_df,
        x="ward",
        y="pct",
        color="pct",
        color_continuous_scale=["#2ecc71", "#f39c12", "#e74c3c"],
        range_color=[50, 100],
        text="pct",
        labels={"ward": "Ward", "pct": "Occupancy (%)"},
        height=360,
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.add_hline(y=85, line_dash="dash", line_color="red",   annotation_text="Critical 85%")
    fig.add_hline(y=75, line_dash="dot",  line_color="orange",annotation_text="Warning 75%")
    fig.update_layout(coloraxis_showscale=False, margin=dict(t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("ICU Utilisation")
    icu = metrics["icu"]
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=round(icu["utilization_rate"] * 100, 1),
        delta={"reference": 80},
        number={"suffix": "%"},
        title={"text": "ICU Beds in Use"},
        gauge={
            "axis":  {"range": [0, 100], "tickwidth": 1},
            "bar":   {"color": "#c0392b"},
            "steps": [
                {"range": [0,  75], "color": "#d5f5e3"},
                {"range": [75, 88], "color": "#fdebd0"},
                {"range": [88, 100],"color": "#fadbd8"},
            ],
            "threshold": {
                "line":      {"color": "red", "width": 4},
                "thickness": 0.75,
                "value":     90,
            },
        },
    ))
    fig.update_layout(height=200, margin=dict(t=30, b=10, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        f"""
| Metric | Value |
|---|---|
| Beds Occupied | {icu['beds_occupied']} / {icu['beds_total']} |
| Ventilators | {icu['ventilators_in_use']} / {icu['ventilators_total']} |
| Critical Patients | {icu['critical_patients']} |
| Nursing Deficit | {icu['nursing_deficit']} |
        """
    )

# ── Row 2: 24-hour trend ──────────────────────────────────────────────────────

st.subheader("24-Hour Occupancy Trend by Ward")
trend_df = monitor.get_occupancy_trend(hours=24)

fig = px.line(
    trend_df,
    x="timestamp",
    y="occupancy_rate",
    color="ward",
    labels={"timestamp": "Time", "occupancy_rate": "Occupancy Rate", "ward": "Ward"},
    height=280,
)
fig.add_hline(y=0.85, line_dash="dash", line_color="red",    annotation_text="Critical")
fig.add_hline(y=0.75, line_dash="dot",  line_color="orange", annotation_text="Warning")
fig.update_layout(margin=dict(t=20, b=10), yaxis_tickformat=".0%")
st.plotly_chart(fig, use_container_width=True)

# ── Row 3: Active alerts + AI briefing ───────────────────────────────────────

st.divider()
alert_col, ai_col = st.columns([1, 1])

with alert_col:
    st.subheader("🚨 Active Alerts")
    alerts = metrics["alerts"]
    if not alerts:
        st.success("✅ All wards operating within normal parameters.")
    else:
        for a in alerts:
            if a["severity"] == "CRITICAL":
                st.error(f"🔴 **[{a['ward']}]** {a['message']}")
            elif a["severity"] == "WARNING":
                st.warning(f"🟡 **[{a['ward']}]** {a['message']}")
            else:
                st.info(f"🔵 {a['message']}")

with ai_col:
    st.subheader("🤖 AI Operational Briefing")
    if st.button("Generate AI Briefing", type="primary", use_container_width=True):
        with st.spinner("Analysing hospital state …"):
            analysis = monitor.get_ai_analysis(alerts)
            st.session_state["dashboard_analysis"] = analysis

    if "dashboard_analysis" in st.session_state:
        st.info(st.session_state["dashboard_analysis"])
    else:
        st.caption("Click the button above to get an AI-powered analysis of current conditions.")
