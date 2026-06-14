"""
Staff Optimization Agent
=========================
Analyses doctor schedules, detects understaffed shifts, and recommends reassignments.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any

from core.llm_connector import LLMConnector
from core.database import Database

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

SYSTEM_PROMPT = """You are a PulseCommand AI Staff Coordinator.
Given a specific ward, date, and shift, recommend specific on-call doctors who can be reassigned.
Use the provided schedule data to make grounded recommendations. Be concise and specific."""


class StaffOptimizerAgent:
    def __init__(self, llm: LLMConnector, db: Database, data_dir: str = DATA_DIR):
        self.llm = llm
        self.db = db
        self.data_dir = data_dir
        self._schedule_df = None
        self._bed_df = None

    @property
    def schedule_df(self) -> pd.DataFrame:
        if self._schedule_df is None:
            path = os.path.join(self.data_dir, "doctor_schedules.csv")
            self._schedule_df = pd.read_csv(path, parse_dates=["date"])
        return self._schedule_df

    @property
    def bed_df(self) -> pd.DataFrame:
        if self._bed_df is None:
            path = os.path.join(self.data_dir, "bed_occupancy.csv")
            self._bed_df = pd.read_csv(path, parse_dates=["timestamp"])
        return self._bed_df

    def load_schedules(self) -> pd.DataFrame:
        return self.schedule_df.copy()

    def detect_understaffing(self) -> pd.DataFrame:
        """Detect understaffed shifts (threshold: 1 per 10 occupied beds, min 2)"""
        df = self.schedule_df.copy()
        latest_bed = self.bed_df.groupby(["ward", "timestamp"])["occupied"].last().reset_index()
        latest_bed = latest_bed.groupby("ward")["occupied"].max().reset_index()
        ward_occupied = dict(zip(latest_bed["ward"], latest_bed["occupied"]))

        results = []
        for (ward, date, shift), group in df.groupby(["ward", "date", "shift"]):
            present = len(group[(group["leave"] == False)])
            occupied = ward_occupied.get(ward, 20)
            required = max(2, int(np.ceil(occupied / 10)))
            gap = required - present
            if gap > 0:
                results.append({
                    "ward": ward,
                    "date": date.strftime("%Y-%m-%d"),
                    "shift": shift,
                    "doctors_present": present,
                    "doctors_required": required,
                    "gap": gap
                })
        return pd.DataFrame(results)

    def get_overtime_risks(self) -> pd.DataFrame:
        """Find doctors with overtime_hours > 2 in last 7 days"""
        df = self.schedule_df.copy()
        cutoff_date = df["date"].max() - timedelta(days=7)
        recent = df[df["date"] >= cutoff_date]
        overtime = recent.groupby(["doctor_id", "doctor_name"]).agg({
            "overtime_hours": "sum",
            "ward": lambda x: x.mode()[0]
        }).reset_index()
        return overtime[overtime["overtime_hours"] > 2].sort_values("overtime_hours", ascending=False)

    def recommend_reassignment(self, ward: str, date: str, shift: str) -> str:
        """Recommend on-call doctors for reassignment"""
        df = self.schedule_df.copy()
        on_call = df[(df["ward"] == ward) & 
                     (df["date"] == pd.to_datetime(date)) & 
                     (df["on_call"] == True) & 
                     (df["leave"] == False)]
        
        if on_call.empty:
            return "⚠️ No on-call doctors available for this shift."
        
        user_msg = f"""
        Ward: {ward}
        Date: {date}
        Shift: {shift}
        Available on-call doctors:
        {on_call[["doctor_name", "specialization", "hours_worked"]].to_string(index=False)}
        Recommend which doctor(s) to reassign and why.
        """
        return self.llm.chat(SYSTEM_PROMPT, user_msg, max_tokens=300)

    def get_staffing_summary(self) -> Dict[str, Any]:
        """Get summary KPIs for dashboard"""
        df = self.schedule_df.copy()
        latest_date = df["date"].max()
        today = df[df["date"] == latest_date]
        
        understaffed = len(self.detect_understaffing())
        overtime = len(self.get_overtime_risks())
        total_doctors = df["doctor_id"].nunique()
        on_shift = len(today[(today["leave"] == False)])
        on_call = len(today[(today["on_call"] == True) & (today["leave"] == False)])
        on_leave = len(today[(today["leave"] == True)])
        
        return {
            "total_doctors": total_doctors,
            "on_shift": on_shift,
            "on_call": on_call,
            "on_leave": on_leave,
            "understaffed_shifts": understaffed,
            "overtime_risks": overtime,
            "latest_date": latest_date.strftime("%Y-%m-%d")
        }
