"""
Operational Planner Agent
=========================
Aggregates data from all agents and generates prioritized action plans.
"""

import json
from datetime import datetime
from typing import List, Dict, Any

from core.llm_connector import LLMConnector
from core.database import Database
from agents.resource_monitor import ResourceMonitorAgent
from agents.bed_allocator import BedAllocationAgent
from agents.staff_optimizer import StaffOptimizerAgent

SYSTEM_PROMPT = """You are a PulseCommand AI Operations Chief.
Given the current hospital operational state, produce a prioritized action plan.
Format each action item as:
- PRIORITY (P1, P2, P3) | ACTION | DEPARTMENT | ETA
Prioritize patient safety first. Be specific and actionable."""


class OperationalPlannerAgent:
    def __init__(self, llm: LLMConnector, db: Database, 
                 monitor: ResourceMonitorAgent, 
                 allocator: BedAllocationAgent, 
                 optimizer: StaffOptimizerAgent):
        self.llm = llm
        self.db = db
        self.monitor = monitor
        self.allocator = allocator
        self.optimizer = optimizer

    def gather_hospital_state(self) -> Dict[str, Any]:
        """Gather state from all agents"""
        occupancy = self.monitor.get_summary_metrics()
        allocations = self.allocator.get_allocation_stats()
        staffing = self.optimizer.get_staffing_summary()
        
        return {
            "occupancy": occupancy,
            "allocations": allocations,
            "staffing": staffing,
            "timestamp": datetime.now().isoformat()
        }

    def generate_action_plan(self, state: Dict[str, Any]) -> str:
        """Generate action plan using LLM"""
        user_msg = f"""
        Current Hospital State:
        {json.dumps(state, indent=2)}
        
        Please generate a prioritized action plan.
        """
        return self.llm.chat(SYSTEM_PROMPT, user_msg, max_tokens=500)

    def save_plan(self, state: Dict[str, Any], plan: str) -> int:
        """Save plan to database"""
        state_str = json.dumps(state)
        plan_id = self.db.add_operational_plan(state_str, plan)
        self.db.log_agent_action("OperationalPlanner", "save_plan", f"Plan ID: {plan_id}")
        return plan_id

    def get_plan_history(self) -> List[Dict[str, Any]]:
        """Get historical plans"""
        return self.db.get_operational_plans()
