"""Bed Management — AI-powered bed recommendation and allocation for incoming patients."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import plotly.express as px
import pandas as pd

from agents.bed_allocator import BedAllocationAgent
from core.database import Database
from core.llm_connector import LLMConnector

st.set_page_config(page_title="Bed Management · Hospital Ops Chief", layout="wide")

DIAGNOSES = [
    "Pneumonia", "Cardiac Arrest", "Appendicitis", "Fracture", "Stroke",
    "Diabetes Complication", "Respiratory Failure", "Sepsis", "COVID-19",
    "Hypertension Crisis", "Kidney Failure", "Liver Disease", "Cancer Treatment",
    "Trauma Injury", "Burns", "Normal Delivery", "Complicated Delivery",
    "Pediatric Infection", "Meningitis", "Post-Op Recovery",
    "Gastrointestinal Bleeding", "Asthma Attack", "Anemia", "COPD",
    "Hip Replacement", "Cardiac Catheterization",
]

# ── Shared resources ──────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def _load_resources():
    llm       = LLMConnector()
    db        = Database()
    allocator = BedAllocationAgent(llm=llm, db=db)
    return allocator, db, llm

allocator, db, llm = _load_resources()

# ── Header ────────────────────────────────────────────────────────────────────

st.title("Bed Management")
st.caption("AI-assisted bed allocation for incoming patients")
st.divider()

# ── Row 1: Ward availability snapshot ────────────────────────────────────────

st.subheader("Current Ward Availability")
occ_df = allocator.get_ward_occupancy()

col_chart, col_table = st.columns([3, 2])

with col_chart:
    fig = px.bar(
        occ_df,
        x="ward",
        y=["occupied", "available", "maintenance"] if "maintenance" in occ_df.columns else ["occupied", "available"],
        barmode="stack",
        color_discrete_map={"occupied": "#e74c3c", "available": "#2ecc71", "maintenance": "#95a5a6"},
        labels={"ward": "Ward", "value": "Beds", "variable": "Status"},
        height=300,
    )
    fig.update_layout(margin=dict(t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)

with col_table:
    display_df = occ_df[["ward", "total_beds", "occupied", "available", "occupancy_rate"]].copy()
    display_df["occupancy_rate"] = (display_df["occupancy_rate"] * 100).round(1).astype(str) + "%"
    display_df.columns = ["Ward", "Total", "Occupied", "Available", "Occupancy"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

st.divider()

# ── Row 2: Patient intake + recommendation ────────────────────────────────────

left_form, right_rec = st.columns([1, 1])

with left_form:
    st.subheader("🏥 New Patient Intake")

    with st.form("patient_intake"):
        patient_id   = st.text_input("Patient ID", placeholder="e.g. P99001", value="P99001")
        age          = st.number_input("Age", min_value=1, max_value=110, value=45)
        gender       = st.selectbox("Gender", ["M", "F", "Other"])
        diagnosis    = st.selectbox("Diagnosis", DIAGNOSES)
        severity     = st.slider(
            "Severity (1 = mild, 5 = critical)", min_value=1, max_value=5, value=3
        )
        adm_type     = st.selectbox("Admission Type", ["Emergency", "Elective", "Transfer"])

        severity_map = {
            1: "🟢 Mild",
            2: "🔵 Moderate",
            3: "🟡 Serious",
            4: "🟠 Severe",
            5: "🔴 Critical",
        }
        st.caption(f"Severity: {severity_map[severity]}")

        submitted = st.form_submit_button("🔍 Get Bed Recommendation", type="primary", use_container_width=True)

with right_rec:
    st.subheader("🤖 AI Recommendation")

    if submitted:
        with st.spinner("Analysing patient profile and ward capacity …"):
            rec, reasoning = allocator.recommend_bed(
                severity=severity,
                diagnosis=diagnosis,
                age=age,
                admission_type=adm_type,
            )
            st.session_state["last_rec"]       = rec
            st.session_state["last_reasoning"] = reasoning
            st.session_state["last_patient"]   = {
                "id": patient_id, "age": age, "diagnosis": diagnosis,
                "severity": severity, "adm_type": adm_type,
            }

    if "last_rec" in st.session_state and st.session_state["last_rec"]:
        rec = st.session_state["last_rec"]
        pt  = st.session_state["last_patient"]

        st.success(f"**Recommended Ward: {rec['ward']}**")

        cols = st.columns(3)
        cols[0].metric("Bed Label",     rec["bed_label"])
        cols[1].metric("Available Beds",rec["available_beds"])
        cols[2].metric("Ward Occupancy",f"{rec['occupancy_rate']:.1%}")

        st.markdown("**AI Reasoning:**")
        st.info(st.session_state["last_reasoning"])

        # Confirm allocation button
        if st.button("✅ Confirm Allocation", type="primary", use_container_width=True):
            allocator.allocate_bed(
                patient_id=pt["id"],
                ward=rec["ward"],
                bed_label=rec["bed_label"],
                severity=pt["severity"],
                diagnosis=pt["diagnosis"],
            )
            st.success(
                f"✅ Bed **{rec['bed_label']}** allocated to patient **{pt['id']}** "
                f"in **{rec['ward']}** ward."
            )
            del st.session_state["last_rec"]
            del st.session_state["last_reasoning"]
            del st.session_state["last_patient"]

    elif "last_rec" in st.session_state and st.session_state["last_rec"] is None:
        st.error("⚠️ No beds available. Escalate immediately.")
    else:
        st.caption("Fill in the patient form and click **Get Bed Recommendation**.")

st.divider()

# ── Row 3: Allocation history + analytics ────────────────────────────────────

st.subheader("📋 Allocation History")

stats   = allocator.get_allocation_stats()
history = db.get_allocations(limit=50)

if not history:
    st.info("No allocations recorded yet. Use the form above to allocate a bed.")
else:
    hist_df = pd.DataFrame(history)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Allocations", stats["total"])
    c2.metric("Wards Used",        len(stats["by_ward"]))
    c3.metric("Most Common Ward",  max(stats["by_ward"], key=stats["by_ward"].get) if stats["by_ward"] else "—")

    tab_table, tab_charts = st.tabs(["📋 Table", "📊 Charts"])

    with tab_table:
        display_cols = ["timestamp", "patient_id", "bed_id", "ward", "severity", "diagnosis", "status"]
        st.dataframe(hist_df[display_cols], use_container_width=True, hide_index=True)

    with tab_charts:
        if stats["by_ward"]:
            ward_series = pd.Series(stats["by_ward"]).reset_index()
            ward_series.columns = ["Ward", "Allocations"]
            fig = px.pie(ward_series, names="Ward", values="Allocations",
                         title="Allocations by Ward", height=300)
            st.plotly_chart(fig, use_container_width=True)

# ── Admission trend ───────────────────────────────────────────────────────────

st.subheader("📈 Admission Trends (Last 30 Days)")
trend_df = allocator.get_admission_trends()

if not trend_df.empty:
    fig = px.line(
        trend_df, x="date", y="admissions", color="ward",
        labels={"date": "Date", "admissions": "Daily Admissions", "ward": "Ward"},
        height=280,
    )
    fig.update_layout(margin=dict(t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)
