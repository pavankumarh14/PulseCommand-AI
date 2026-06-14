"""Alerts & Monitoring — live anomaly feed, resolution workflow, AI briefings."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime

from agents.resource_monitor import ResourceMonitorAgent
from core.database import Database
from core.llm_connector import LLMConnector

st.set_page_config(page_title="Alerts · Hospital Ops Chief", layout="wide")

# ── Shared resources ──────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def _load_resources():
    llm     = LLMConnector()
    db      = Database()
    monitor = ResourceMonitorAgent(llm=llm, db=db)
    return monitor, db, llm

monitor, db, llm = _load_resources()

# ── Header ────────────────────────────────────────────────────────────────────

st.title("Alerts & Monitoring")
st.caption("Real-time anomaly detection · threshold-based AI alerting system")
st.divider()

# ── Live alert scan ───────────────────────────────────────────────────────────

st.subheader("Live System Scan")

scan_col, info_col = st.columns([1, 2])

with scan_col:
    if st.button("🔄 Run Alert Scan Now", type="primary", use_container_width=True):
        with st.spinner("Scanning all wards and ICU units …"):
            fresh_alerts = monitor.detect_anomalies()
            st.session_state["scan_alerts"] = fresh_alerts
            st.session_state["scan_time"]   = datetime.now().strftime("%H:%M:%S")

with info_col:
    if "scan_time" in st.session_state:
        st.caption(f"Last scan: {st.session_state['scan_time']}")

# Show scan results
if "scan_alerts" in st.session_state:
    alerts = st.session_state["scan_alerts"]

    if not alerts:
        st.success("✅ All systems normal — no anomalies detected.")
    else:
        crit = [a for a in alerts if a["severity"] == "CRITICAL"]
        warn = [a for a in alerts if a["severity"] == "WARNING"]

        m1, m2 = st.columns(2)
        m1.metric("🔴 Critical", len(crit), delta_color="inverse")
        m2.metric("🟡 Warning",  len(warn), delta_color="inverse")

        for a in alerts:
            badge = "🔴" if a["severity"] == "CRITICAL" else "🟡"
            fn    = st.error if a["severity"] == "CRITICAL" else st.warning
            fn(f"{badge} **[{a['severity']}] {a['ward']}** — {a['message']}")

st.divider()

# ── AI analysis of current alerts ────────────────────────────────────────────

st.subheader("🤖 AI Alert Analysis")

tab_current, tab_history = st.tabs(["Current Alerts", "Alert History"])

with tab_current:
    col_btn, col_out = st.columns([1, 2])

    with col_btn:
        if st.button("Analyse with AI", type="primary", use_container_width=True):
            active_alerts = monitor.detect_anomalies()
            with st.spinner("AI is reviewing hospital state …"):
                analysis = monitor.get_ai_analysis(active_alerts)
                st.session_state["alert_analysis"] = analysis

    with col_out:
        if "alert_analysis" in st.session_state:
            st.info(st.session_state["alert_analysis"])
        else:
            st.caption("Click **Analyse with AI** to get a clinical briefing.")

with tab_history:
    # ── Alert log from DB ─────────────────────────────────────────────────────
    all_alerts = db.get_alert_history(limit=200)

    if not all_alerts:
        st.info("No alert history yet. Run a scan to generate alerts.")
    else:
        df = pd.DataFrame(all_alerts)

        # Summary stats
        s1, s2, s3, s4 = st.columns(4)
        total   = len(df)
        crit_n  = (df["severity"] == "CRITICAL").sum()
        warn_n  = (df["severity"] == "WARNING").sum()
        res_n   = df["resolved"].sum()

        s1.metric("Total Alerts",    total)
        s2.metric("Critical",        int(crit_n))
        s3.metric("Warning",         int(warn_n))
        s4.metric("Resolved",        int(res_n))

        # Alerts over time chart
        if len(df) > 1:
            df["ts"]   = pd.to_datetime(df["timestamp"])
            df["date"] = df["ts"].dt.date
            daily      = df.groupby(["date", "severity"]).size().reset_index(name="count")

            fig = px.bar(
                daily, x="date", y="count", color="severity",
                color_discrete_map={"CRITICAL": "#e74c3c", "WARNING": "#f39c12", "INFO": "#3498db"},
                labels={"date": "Date", "count": "Alerts", "severity": "Severity"},
                title="Alert Volume Over Time",
                height=280,
            )
            fig.update_layout(margin=dict(t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)

        # Table with resolve buttons
        st.markdown("#### Alert Log")
        active_df = df[df["resolved"] == 0].head(50)

        if active_df.empty:
            st.success("All logged alerts have been resolved.")
        else:
            for _, row in active_df.iterrows():
                badge = "🔴" if row["severity"] == "CRITICAL" else "🟡"
                r1, r2 = st.columns([4, 1])
                r1.markdown(
                    f"{badge} `{row['timestamp'][:16]}` · **{row['ward']}** · {row['message']}"
                )
                if r2.button("Resolve", key=f"res_{row['id']}"):
                    db.resolve_alert(int(row["id"]))
                    st.success(f"Alert #{row['id']} resolved.")
                    st.rerun()

st.divider()

# ── ICU deep-dive ─────────────────────────────────────────────────────────────

st.subheader("🏥 ICU Utilisation Trend (Last 24 hours)")
icu_trend = monitor.get_icu_trend(hours=24)

if not icu_trend.empty:
    fig = px.line(
        icu_trend, x="timestamp", y="utilization_rate", color="icu_unit",
        labels={"timestamp": "Time", "utilization_rate": "Utilisation", "icu_unit": "ICU Unit"},
        height=280,
    )
    fig.add_hline(y=0.90, line_dash="dash", line_color="red",    annotation_text="Critical 90%")
    fig.add_hline(y=0.80, line_dash="dot",  line_color="orange", annotation_text="Warning 80%")
    fig.update_layout(margin=dict(t=20, b=10), yaxis_tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)

    # Ventilator usage
    st.markdown("#### Ventilator Usage by ICU Unit")
    latest_icu = icu_trend.sort_values("timestamp").groupby("icu_unit").last().reset_index()
    vent_df    = latest_icu[["icu_unit", "ventilators_in_use", "ventilators_total"]].copy()
    vent_df["vent_pct"] = (vent_df["ventilators_in_use"] / vent_df["ventilators_total"] * 100).round(1)
    vent_df.columns = ["ICU Unit", "In Use", "Total", "Usage %"]
    st.dataframe(vent_df, use_container_width=True, hide_index=True)
