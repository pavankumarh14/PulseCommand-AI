"""
Resource Monitor Agent
=======================
Continuously analyses bed occupancy and ICU utilisation.
Detects anomalies, raises alerts, and returns an AI-powered
plain-English summary of the current hospital state.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any

from core.llm_connector import LLMConnector
from core.database import Database

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# Per-ward thresholds (occupancy_rate) for WARNING and CRITICAL
THRESHOLDS: Dict[str, Dict[str, float]] = {
    "ICU":       {"warning": 0.80, "critical": 0.90},
    "Emergency": {"warning": 0.75, "critical": 0.88},
    "General":   {"warning": 0.82, "critical": 0.95},
    "Pediatric": {"warning": 0.75, "critical": 0.90},
    "Maternity": {"warning": 0.72, "critical": 0.88},
    "Surgical":  {"warning": 0.80, "critical": 0.93},
}

SYSTEM_PROMPT = """You are a PulseCommand AI.
Analyse the current hospital alert summary and provide a concise operational
briefing (3-4 sentences). Focus on the highest-priority issues and give
concrete, actionable recommendations. Be direct and clinical."""


class ResourceMonitorAgent:
    def __init__(self, llm: LLMConnector, db: Database, data_dir: str = DATA_DIR):
        self.llm      = llm
        self.db       = db
        self.data_dir = data_dir
        self._bed_df  = None
        self._icu_df  = None

    # ── Data loading (lazy + cached per session) ──────────────────────────────

    @property
    def bed_df(self) -> pd.DataFrame:
        if self._bed_df is None:
            path = os.path.join(self.data_dir, "bed_occupancy.csv")
            self._bed_df = pd.read_csv(path, parse_dates=["timestamp"])
        return self._bed_df

    @property
    def icu_df(self) -> pd.DataFrame:
        if self._icu_df is None:
            path = os.path.join(self.data_dir, "icu_utilization.csv")
            self._icu_df = pd.read_csv(path, parse_dates=["timestamp"])
        return self._icu_df

    # ── Current state ─────────────────────────────────────────────────────────

    def get_current_ward_status(self) -> pd.DataFrame:
        """Return the most-recent snapshot row per ward."""
        latest_ts = self.bed_df.groupby("ward")["timestamp"].max().reset_index()
        merged = pd.merge(self.bed_df, latest_ts, on=["ward", "timestamp"])
        return merged[[
            "ward", "total_beds", "occupied", "available", "maintenance", "occupancy_rate"
        ]].copy()

    def get_icu_summary(self) -> Dict[str, Any]:
        """Aggregated ICU metrics from the latest readings."""
        latest_ts = self.icu_df["timestamp"].max()
        window = self.icu_df[self.icu_df["timestamp"] >= latest_ts - timedelta(hours=2)]

        beds_total = int(window["beds_total"].sum())
        beds_occ   = int(window["beds_occupied"].sum())
        vents_tot  = int(window["ventilators_total"].sum())
        vents_use  = int(window["ventilators_in_use"].sum())
        nursing_req = int(window["nursing_staff_required"].sum())
        nursing_pres= int(window["nursing_staff_present"].sum())
        critical    = int(window["critical_patients"].sum())

        return {
            "beds_total":          beds_total,
            "beds_occupied":       beds_occ,
            "beds_available":      beds_total - beds_occ,
            "utilization_rate":    round(beds_occ / beds_total, 4) if beds_total else 0,
            "ventilators_total":   vents_tot,
            "ventilators_in_use":  vents_use,
            "vent_utilization":    round(vents_use / vents_tot, 4) if vents_tot else 0,
            "nursing_staff_present":  nursing_pres,
            "nursing_staff_required": nursing_req,
            "nursing_deficit":     max(0, nursing_req - nursing_pres),
            "critical_patients":   critical,
        }

    # ── Anomaly detection ─────────────────────────────────────────────────────

    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """
        Rule-based anomaly detection.
        Returns a list of alert dicts sorted by severity (CRITICAL first).
        """
        alerts: List[Dict[str, Any]] = []

        # Ward-level bed occupancy
        ward_status = self.get_current_ward_status()
        for _, row in ward_status.iterrows():
            ward  = row["ward"]
            rate  = float(row["occupancy_rate"])
            thr   = THRESHOLDS.get(ward, {"warning": 0.80, "critical": 0.92})

            if rate >= thr["critical"]:
                alerts.append({
                    "severity": "CRITICAL",
                    "ward":     ward,
                    "metric":   "bed_occupancy",
                    "value":    rate,
                    "message":  (
                        f"{ward} ward at {rate:.1%} capacity — "
                        f"{int(row['available'])} beds left, consider overflow protocol"
                    ),
                    "timestamp": datetime.now().isoformat(),
                })
            elif rate >= thr["warning"]:
                alerts.append({
                    "severity": "WARNING",
                    "ward":     ward,
                    "metric":   "bed_occupancy",
                    "value":    rate,
                    "message":  (
                        f"{ward} ward at {rate:.1%} capacity — "
                        f"monitor closely, {int(row['available'])} beds available"
                    ),
                    "timestamp": datetime.now().isoformat(),
                })

        # ICU-specific checks
        icu = self.get_icu_summary()

        if icu["utilization_rate"] >= 0.90:
            alerts.append({
                "severity": "CRITICAL",
                "ward":     "ICU",
                "metric":   "icu_beds",
                "value":    icu["utilization_rate"],
                "message":  (
                    f"ICU bed utilisation at {icu['utilization_rate']:.1%} — "
                    f"only {icu['beds_available']} beds available"
                ),
                "timestamp": datetime.now().isoformat(),
            })

        if icu["vent_utilization"] >= 0.85:
            alerts.append({
                "severity": "CRITICAL",
                "ward":     "ICU",
                "metric":   "ventilators",
                "value":    icu["vent_utilization"],
                "message":  (
                    f"Ventilator usage at {icu['ventilators_in_use']}/{icu['ventilators_total']} "
                    f"({icu['vent_utilization']:.1%}) — critical shortage risk"
                ),
                "timestamp": datetime.now().isoformat(),
            })

        if icu["nursing_deficit"] > 0:
            alerts.append({
                "severity": "WARNING",
                "ward":     "ICU",
                "metric":   "nursing_staff",
                "value":    icu["nursing_deficit"],
                "message":  (
                    f"ICU nursing deficit: {icu['nursing_staff_present']} present vs "
                    f"{icu['nursing_staff_required']} required "
                    f"(−{icu['nursing_deficit']})"
                ),
                "timestamp": datetime.now().isoformat(),
            })

        # Sort: CRITICAL first
        severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
        alerts.sort(key=lambda a: severity_order.get(a["severity"], 9))

        # Persist new alerts to DB
        for alert in alerts:
            self.db.add_alert(alert["ward"], alert["severity"], alert["message"])
        self.db.log_agent_action("ResourceMonitor", "detect_anomalies", f"{len(alerts)} alerts generated")

        return alerts

    # ── Trend data (for charts) ───────────────────────────────────────────────

    def get_occupancy_trend(self, hours: int = 24) -> pd.DataFrame:
        """Return hourly ward occupancy rates for the last `hours` hours."""
        cutoff = self.bed_df["timestamp"].max() - timedelta(hours=hours)
        df     = self.bed_df[self.bed_df["timestamp"] >= cutoff].copy()
        return df[["timestamp", "ward", "occupancy_rate"]].sort_values("timestamp")

    def get_icu_trend(self, hours: int = 24) -> pd.DataFrame:
        """Return hourly per-unit ICU utilization for the last `hours` hours."""
        cutoff = self.icu_df["timestamp"].max() - timedelta(hours=hours)
        df     = self.icu_df[self.icu_df["timestamp"] >= cutoff].copy()
        return df[["timestamp", "icu_unit", "utilization_rate",
                   "ventilators_in_use", "ventilators_total"]].sort_values("timestamp")

    # ── Summary metrics (dashboard KPIs) ─────────────────────────────────────

    def get_summary_metrics(self) -> Dict[str, Any]:
        ward_status = self.get_current_ward_status()
        icu         = self.get_icu_summary()
        alerts      = self.detect_anomalies()

        total_beds  = int(ward_status["total_beds"].sum())
        total_occ   = int(ward_status["occupied"].sum())
        total_avail = int(ward_status["available"].sum())

        return {
            "total_beds":        total_beds,
            "occupied":          total_occ,
            "available":         total_avail,
            "overall_occupancy": round(total_occ / total_beds, 4) if total_beds else 0,
            "icu":               icu,
            "critical_alerts":   sum(1 for a in alerts if a["severity"] == "CRITICAL"),
            "warning_alerts":    sum(1 for a in alerts if a["severity"] == "WARNING"),
            "total_alerts":      len(alerts),
            "alerts":            alerts,
            "ward_status":       ward_status,
        }

    # ── AI-powered analysis ───────────────────────────────────────────────────

    def get_ai_analysis(self, alerts: List[Dict[str, Any]]) -> str:
        if not alerts:
            return (
                "All hospital systems are operating within normal parameters. "
                "No immediate operational action required."
            )

        alert_lines = "\n".join(
            f"  [{a['severity']}] {a['ward']}: {a['message']}" for a in alerts
        )
        user_msg = f"Current hospital alerts:\n{alert_lines}\n\nProvide your operational briefing."
        return self.llm.chat(SYSTEM_PROMPT, user_msg, max_tokens=400)
