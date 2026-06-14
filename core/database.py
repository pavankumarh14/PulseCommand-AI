import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hospital.db")


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   TEXT    NOT NULL,
                    ward        TEXT    NOT NULL,
                    severity    TEXT    NOT NULL,
                    message     TEXT    NOT NULL,
                    resolved    INTEGER NOT NULL DEFAULT 0,
                    resolved_at TEXT
                );

                CREATE TABLE IF NOT EXISTS bed_allocations (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   TEXT    NOT NULL,
                    patient_id  TEXT    NOT NULL,
                    bed_id      TEXT    NOT NULL,
                    ward        TEXT    NOT NULL,
                    severity    INTEGER NOT NULL,
                    diagnosis   TEXT    NOT NULL,
                    status      TEXT    NOT NULL DEFAULT 'allocated'
                );

                CREATE TABLE IF NOT EXISTS agent_logs (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   TEXT    NOT NULL,
                    agent_name  TEXT    NOT NULL,
                    action      TEXT    NOT NULL,
                    details     TEXT
                );

                CREATE TABLE IF NOT EXISTS operational_plans (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   TEXT    NOT NULL,
                    hospital_state TEXT NOT NULL,
                    action_plan TEXT NOT NULL
                );
            """)

    # ── Alerts ───────────────────────────────────────────────────────────────

    def add_alert(self, ward: str, severity: str, message: str) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO alerts (timestamp, ward, severity, message) VALUES (?, ?, ?, ?)",
                (datetime.now().isoformat(), ward, severity, message),
            )
            return cur.lastrowid

    def get_alerts(self, resolved: bool = False, limit: int = 100):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM alerts WHERE resolved = ? ORDER BY timestamp DESC LIMIT ?",
                (1 if resolved else 0, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def resolve_alert(self, alert_id: int):
        with self._connect() as conn:
            conn.execute(
                "UPDATE alerts SET resolved = 1, resolved_at = ? WHERE id = ?",
                (datetime.now().isoformat(), alert_id),
            )

    def get_alert_history(self, limit: int = 200):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Bed Allocations ───────────────────────────────────────────────────────

    def add_allocation(
        self,
        patient_id: str,
        bed_id: str,
        ward: str,
        severity: int,
        diagnosis: str,
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO bed_allocations
                   (timestamp, patient_id, bed_id, ward, severity, diagnosis)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (datetime.now().isoformat(), patient_id, bed_id, ward, severity, diagnosis),
            )
            return cur.lastrowid

    def get_allocations(self, limit: int = 100):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM bed_allocations ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Agent Logs ────────────────────────────────────────────────────────────

    def log_agent_action(self, agent_name: str, action: str, details: str = ""):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO agent_logs (timestamp, agent_name, action, details) VALUES (?, ?, ?, ?)",
                (datetime.now().isoformat(), agent_name, action, details),
            )

    # ── Operational Plans ───────────────────────────────────────────────────────

    def add_operational_plan(self, hospital_state: str, action_plan: str) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO operational_plans (timestamp, hospital_state, action_plan) VALUES (?, ?, ?)",
                (datetime.now().isoformat(), hospital_state, action_plan),
            )
            return cur.lastrowid

    def get_operational_plans(self, limit: int = 50):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM operational_plans ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
