"""Staff Optimization Page"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.express as px

from agents.staff_optimizer import StaffOptimizerAgent
from core.database import Database
from core.llm_connector import LLMConnector

st.set_page_config(page_title="Staff Optimization · PulseCommand AI", layout="wide")

# ── Shared resources ────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def _load_resources():
    llm = LLMConnector()
    db = Database()
    optimizer = StaffOptimizerAgent(llm=llm, db=db)
    return optimizer, db, llm

optimizer, db, llm = _load_resources()

# ── Header ────────────────────────────────────────────────────────────────────

st.title("👨‍⚕️ Staff Optimization")
st.caption("Real-time staffing analytics and AI-powered reassignment recommendations")
st.divider()

# ── Summary KPIs ────────────────────────────────────────────────────────────────

summary = optimizer.get_staffing_summary()
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Doctors", summary["total_doctors"])
col2.metric("On Shift", summary["on_shift"])
col3.metric("On Call", summary["on_call"])
col4.metric("On Leave", summary["on_leave"])
col5.metric("Understaffed Shifts", summary["understaffed_shifts"], delta_color="inverse")

st.divider()

# ── Today's Staffing Overview ────────────────────────────────────────────────

st.subheader("Today's Staffing Overview")
df = optimizer.load_schedules()
latest_date = pd.to_datetime(summary["latest_date"])
today_df = df[df["date"] == latest_date]

# Group by ward and shift
ward_shift = today_df.groupby(["ward", "shift"]).agg({"doctor_name": "count", "leave": lambda x: (x == False).sum()}).reset_index()
ward_shift.columns = ["ward", "shift", "total_doctors", "doctors_present"]

fig = px.bar(
    ward_shift,
    x="ward",
    y="doctors_present",
    color="shift",
    barmode="group",
    title="Doctor Count by Ward and Shift",
    height=400
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Understaffed Shifts ──────────────────────────────────────────────────────

st.subheader("⚠️ Understaffed Shifts")
understaffed = optimizer.detect_understaffing()
if not understaffed.empty:
    st.dataframe(understaffed.style.highlight_max(axis=0, subset=["gap"], color="#ffcccc"), use_container_width=True)
else:
    st.success("✅ All shifts are adequately staffed!")

st.divider()

# ── Overtime Risks ───────────────────────────────────────────────────────────

st.subheader("🔥 Overtime Risks")
overtime = optimizer.get_overtime_risks()
if not overtime.empty:
    fig = px.bar(
        overtime,
        x="doctor_name",
        y="overtime_hours",
        color="ward",
        title="Doctors at Risk of Burnout (Overtime > 2 hours in last 7 days",
        height=350
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.success("✅ No doctors at high overtime risk!")

st.divider()

# ── AI Reassignment Panel ──────────────────────────────────────────────────────

st.subheader("🤖 AI Reassignment Recommendation")
wards = sorted(df["ward"].unique())
shifts = ["Morning", "Evening", "Night"]
dates = sorted(df["date"].dt.strftime("%Y-%m-%d").unique())

col_ward, col_date, col_shift = st.columns(3)
with col_ward:
    selected_ward = st.selectbox("Select Ward", wards)
with col_date:
    selected_date = st.selectbox("Select Date", dates, index=len(dates)-1)
with col_shift:
    selected_shift = st.selectbox("Select Shift", shifts)

if st.button("Get Reassignment Recommendation", type="primary"):
    with st.spinner("Analyzing staffing options..."):
        recommendation = optimizer.recommend_reassignment(selected_ward, selected_date, selected_shift)
        st.info(recommendation)

st.divider()

# ── 30-Day Staffing Heatmap ────────────────────────────────────────────────

st.subheader("📊 30-Day Staffing Heatmap")
heatmap_data = df.groupby(["ward", df["date"].dt.strftime("%Y-%m-%d")]).agg({"doctor_name": "count"}).reset_index()
heatmap_pivot = heatmap_data.pivot(index="ward", columns="date", values="doctor_name").fillna(0)
fig = px.imshow(
    heatmap_pivot,
    labels=dict(x="Date", y="Ward", color="Doctors"),
    aspect="auto",
    height=400,
    color_continuous_scale="Viridis"
)
st.plotly_chart(fig, use_container_width=True)
