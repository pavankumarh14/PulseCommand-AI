"""
Bed Allocation Agent
======================
Recommends and records the best available bed for an incoming patient
based on clinical severity, diagnosis, age, and real-time ward capacity.
Uses the LLM to generate a human-readable allocation rationale.
"""

import os
import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict, Any, List

from core.llm_connector import LLMConnector
from core.database import Database

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# Severity → preferred ward priority lists  (highest first)
SEVERITY_WARD_PRIORITY: Dict[int, List[str]] = {
    5: ["ICU", "Emergency"],
    4: ["ICU", "Emergency", "Surgical"],
    3: ["Emergency", "Surgical", "General"],
    2: ["General", "Pediatric", "Maternity", "Surgical"],
    1: ["General", "Pediatric", "Maternity"],
}

# Diagnosis → specific ward override
DIAGNOSIS_WARD: Dict[str, str] = {
    "Cardiac Arrest":      "ICU",
    "Respiratory Failure": "ICU",
    "Sepsis":              "ICU",
    "Stroke":              "ICU",
    "Normal Delivery":     "Maternity",
    "Complicated Delivery":"Maternity",
    "Pediatric Infection": "Pediatric",
    "Meningitis":          "Pediatric",
    "Hip Replacement":     "Surgical",
    "Appendicitis":        "Surgical",
    "Burns":               "Surgical",
    "Post-Op Recovery":    "Surgical",
    "Trauma Injury":       "Emergency",
}

ALLOC_SYSTEM_PROMPT = """You are an AI Hospital Bed Allocation Specialist.
Explain the bed allocation decision in 2-3 concise sentences.
Be specific about why this ward and bed type is medically appropriate for this patient."""


class BedAllocationAgent:
    def __init__(self, llm: LLMConnector, db: Database, data_dir: str = DATA_DIR):
        self.llm      = llm
        self.db       = db
        self.data_dir = data_dir
        self._bed_df  = None
        self._adm_df  = None

    # ── Data (lazy) ───────────────────────────────────────────────────────────

    @property
    def bed_df(self) -> pd.DataFrame:
        if self._bed_df is None:
            path = os.path.join(self.data_dir, "bed_occupancy.csv")
            self._bed_df = pd.read_csv(path, parse_dates=["timestamp"])
        return self._bed_df

    @property
    def admissions_df(self) -> pd.DataFrame:
        if self._adm_df is None:
            path = os.path.join(self.data_dir, "admissions.csv")
            self._adm_df = pd.read_csv(path, parse_dates=["admission_datetime", "discharge_datetime"], low_memory=False)
        return self._adm_df

    # ── Available beds ────────────────────────────────────────────────────────

    def get_available_beds_by_ward(self) -> Dict[str, int]:
        """Return {ward: available_bed_count} from the latest snapshot."""
        latest_ts = self.bed_df.groupby("ward")["timestamp"].max().reset_index()
        latest    = pd.merge(self.bed_df, latest_ts, on=["ward", "timestamp"])
        return latest.set_index("ward")["available"].to_dict()

    def get_ward_occupancy(self) -> pd.DataFrame:
        """Return latest occupancy rate per ward."""
        latest_ts = self.bed_df.groupby("ward")["timestamp"].max().reset_index()
        return pd.merge(self.bed_df, latest_ts, on=["ward", "timestamp"])[
            ["ward", "total_beds", "occupied", "available", "occupancy_rate"]
        ]

    # ── Recommendation logic ──────────────────────────────────────────────────

    def recommend_bed(
        self,
        severity: int,
        diagnosis: str,
        age: int,
        admission_type: str,
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Returns (recommendation_dict | None, reasoning_text).
        recommendation_dict keys: ward, available_beds, occupancy_rate, bed_label
        """
        available = self.get_available_beds_by_ward()
        occupancy = self.get_ward_occupancy().set_index("ward")

        # Build ordered ward preference list
        preferred: List[str] = []

        # 1. Diagnosis-specific override
        if diagnosis in DIAGNOSIS_WARD:
            preferred.append(DIAGNOSIS_WARD[diagnosis])

        # 2. Age-specific
        if age < 16:
            preferred.insert(0, "Pediatric")
        elif 18 <= age <= 45 and diagnosis in ("Normal Delivery", "Complicated Delivery"):
            preferred.insert(0, "Maternity")

        # 3. Severity-based
        preferred += SEVERITY_WARD_PRIORITY.get(severity, ["General"])

        # Deduplicate while preserving order
        seen: set = set()
        ordered: List[str] = []
        for w in preferred:
            if w not in seen:
                seen.add(w)
                ordered.append(w)

        # Pick first ward that has available beds
        chosen_ward: Optional[str] = None
        for ward in ordered:
            if available.get(ward, 0) > 0:
                chosen_ward = ward
                break

        # Fallback: any ward with available beds
        if chosen_ward is None:
            for ward, cnt in available.items():
                if cnt > 0:
                    chosen_ward = ward
                    break

        if chosen_ward is None:
            return None, "⚠️ No beds are currently available across any ward. Please escalate immediately."

        row      = occupancy.loc[chosen_ward]
        avail_n  = int(available[chosen_ward])
        occ_rate = float(row["occupancy_rate"])

        recommendation = {
            "ward":            chosen_ward,
            "available_beds":  avail_n,
            "occupancy_rate":  occ_rate,
            "bed_label":       f"{chosen_ward}-B{int(row['occupied']) + 1:03d}",
            "preferred_order": ordered,
        }

        reasoning = self._get_allocation_reasoning(
            recommendation, severity, diagnosis, age, admission_type, ordered
        )
        self.db.log_agent_action(
            "BedAllocator",
            "recommend_bed",
            f"Patient age={age} sev={severity} diag={diagnosis} → {chosen_ward}",
        )
        return recommendation, reasoning

    def _get_allocation_reasoning(
        self,
        rec: Dict[str, Any],
        severity: int,
        diagnosis: str,
        age: int,
        admission_type: str,
        preferred_order: List[str],
    ) -> str:
        user_msg = (
            f"Patient: age {age}, diagnosis '{diagnosis}', severity {severity}/5, "
            f"admission type '{admission_type}'.\n"
            f"Recommended ward: {rec['ward']} "
            f"({rec['available_beds']} beds available, {rec['occupancy_rate']:.1%} occupied).\n"
            f"Ward priority evaluated: {', '.join(preferred_order)}.\n\n"
            "Explain why this allocation is medically appropriate."
        )
        return self.llm.chat(ALLOC_SYSTEM_PROMPT, user_msg, max_tokens=256)

    # ── Commit allocation ─────────────────────────────────────────────────────

    def allocate_bed(
        self,
        patient_id: str,
        ward: str,
        bed_label: str,
        severity: int,
        diagnosis: str,
    ) -> int:
        """Persist allocation to DB and return the new record ID."""
        record_id = self.db.add_allocation(
            patient_id=patient_id,
            bed_id=bed_label,
            ward=ward,
            severity=severity,
            diagnosis=diagnosis,
        )
        self.db.log_agent_action(
            "BedAllocator",
            "allocate_bed",
            f"Allocated {bed_label} ({ward}) to patient {patient_id}",
        )
        return record_id

    # ── Stats for dashboard ───────────────────────────────────────────────────

    def get_allocation_stats(self) -> Dict[str, Any]:
        history = self.db.get_allocations(limit=500)
        if not history:
            return {"total": 0, "by_ward": {}, "by_severity": {}, "recent": []}

        df = pd.DataFrame(history)
        return {
            "total":       len(df),
            "by_ward":     df.groupby("ward").size().sort_values(ascending=False).to_dict(),
            "by_severity": df.groupby("severity").size().sort_values().to_dict(),
            "recent":      history[:10],
        }

    # ── Admission analytics ───────────────────────────────────────────────────

    def get_admission_trends(self) -> pd.DataFrame:
        """Daily admission count per ward for the last 30 days."""
        df = self.admissions_df.copy()
        df["date"] = df["admission_datetime"].dt.date
        return (
            df.groupby(["date", "ward"])
            .size()
            .reset_index(name="admissions")
            .sort_values("date")
        )

    def get_severity_distribution(self) -> pd.DataFrame:
        return (
            self.admissions_df.groupby(["ward", "severity"])
            .size()
            .reset_index(name="count")
        )
