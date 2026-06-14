"""Operational Planner Page"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import json

from agents.operational_planner import OperationalPlannerAgent
from agents.resource_monitor import ResourceMonitorAgent
from agents.bed_allocator import BedAllocationAgent
from agents.staff_optimizer import StaffOptimizerAgent
from core.llm_connector import LLMConnector
from core.database import Database

st.set_page_config(page_title="Operational Planner · PulseCommand AI", layout="wide")

# ── Shared resources ────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def _load_resources():
    llm = LLMConnector()
    db = Database()
    monitor = ResourceMonitorAgent(llm=llm, db=db)
    allocator = BedAllocationAgent(llm=llm, db=db)
    optimizer = StaffOptimizerAgent(llm=llm, db=db)
    planner = OperationalPlannerAgent(
        llm=llm, db=db,
        monitor=monitor,
        allocator=allocator,
        optimizer=optimizer
    )
    return planner, db, llm

planner, db, llm = _load_resources()

# ── Header ────────────────────────────────────────────────────────────────────

st.title("📋 Operational Planner")
st.caption("AI-powered prioritized action plans for hospital operations")
st.divider()

# ── Generate Plan Button ────────────────────────────────────────────────────────

if st.button("Generate Action Plan", type="primary", use_container_width=True):
    with st.spinner("Gathering hospital state and generating plan..."):
        state = planner.gather_hospital_state()
        plan = planner.generate_action_plan(state)
        planner.save_plan(state, plan)
        st.session_state["current_state"] = state
        st.session_state["current_plan"] = plan

st.divider()

# ── Display Current State & Plan ────────────────────────────────────────────────

if "current_state" in st.session_state and "current_plan" in st.session_state:
    state_col, plan_col = st.columns([1, 2])
    
    with state_col:
        st.subheader("🏥 Hospital State Snapshot")
        st.json(st.session_state["current_state"])
    
    with plan_col:
        st.subheader("📋 Action Plan")
        plan_text = st.session_state["current_plan"]
        st.info(plan_text)
        
        # Color-code priorities
        lines = plan_text.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if "P1" in line:
                st.error(line)
            elif "P2" in line:
                st.warning(line)
            elif "P3" in line:
                st.info(line)
            else:
                st.write(line)

st.divider()

# ── Plan History ────────────────────────────────────────────────────────────────

st.subheader("📜 Plan History")
history = planner.get_plan_history()
if history:
    for plan in history:
        with st.expander(f"Plan from {plan['timestamp']}"):
            st.write("**Action Plan:**")
            st.info(plan["action_plan"])
            st.write("**Hospital State:**")
            st.json(json.loads(plan["hospital_state"]))
else:
    st.info("No plans generated yet. Click the button above to generate your first plan!")
