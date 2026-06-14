# PulseCommand AI

> **Hackathon Prototype · Theme: AI Meets Data**
> Turning raw hospital operational data into real-time, actionable intelligence.

---

## Problem Statement

Hospitals generate enormous volumes of operational data every hour — bed states, patient admissions, ICU readings, doctor schedules — but lack systems that can **surface the signal buried in the noise** and recommend immediate action. Delayed insight leads to bed shortages, understaffed shifts, and avoidable patient risk.

**PulseCommand AI** is a multi-agent AI platform that monitors, allocates, optimises, and plans hospital operations in real time using synthetic hospital data and LLM-powered reasoning.

---

## Technology Stack

| Layer | Technology |
|---|---|
| **UI Framework** | [Streamlit](https://streamlit.io) — multi-page app with live KPI cards, Plotly charts, interactive forms |
| **Data Processing** | Pandas, NumPy — schedule analysis, occupancy aggregation, anomaly detection |
| **Visualisation** | Plotly Express + Graph Objects — bar charts, gauges, heatmaps, trend lines |
| **AI / LLM** | Provider-agnostic via `LLMConnector` — OpenAI, Groq, DeepSeek, Gemini, Anthropic |
| **Persistence** | SQLite (via Python `sqlite3`) — alerts, bed allocations, agent logs, action plans |
| **Config** | `python-dotenv` — `.env` file for API keys and provider selection |
| **Language** | Python 3.10+ |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Streamlit UI  (app.py + pages/)              │
│                                                                      │
│  Dashboard      Bed Management    Alerts &       Staff        Operational │
│  (app.py)       (built)           Monitoring     Optimization  Planner   │
│                                   (built)        (candidate)  (candidate)│
└──────────┬──────────────┬─────────────┬──────────────┬───────────────┘
           │              │             │              │
           ▼              ▼             ▼              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                          Agent Layer                                 │
│                                                                      │
│  ResourceMonitorAgent     BedAllocationAgent      [candidate builds] │
│  ─────────────────────    ──────────────────       StaffOptimizer    │
│  • Bed/ICU anomaly        • Priority-based         OperationalPlanner│
│    detection                bed recommendation                       │
│  • Threshold alerts       • LLM allocation                          │
│  • AI briefings             rationale                                │
└──────────────────────────┬───────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
┌─────────────────┐ ┌────────────┐ ┌─────────────────────────────────┐
│ LLMConnector    │ │  Database  │ │  Data Layer (CSV files)         │
│                 │ │ (SQLite)   │ │                                 │
│ openai          │ │            │ │  admissions.csv     (~2 000 rows)│
│ groq            │ │ alerts     │ │  bed_occupancy.csv  (~2 016 rows)│
│ deepseek        │ │ allocations│ │  doctor_schedules.csv (~1 500)  │
│ gemini          │ │ agent_logs │ │  icu_utilization.csv (~2 880)   │
│ anthropic       │ │ op_plans   │ │                                 │
└─────────────────┘ └────────────┘ └─────────────────────────────────┘
```

### Data Flow

```
CSV files
   │
   ├─── ResourceMonitorAgent  →  occupancy metrics, anomaly alerts
   │
   ├─── BedAllocationAgent    →  available beds, allocation recommendation
   │
   ├─── StaffOptimizerAgent   →  understaffed shifts, overtime risks, reassignments
   │         [candidate]
   │
   └─── OperationalPlannerAgent  →  unified state + LLM action plan (P1/P2/P3)
             [candidate]                    │
                                            ▼
                                    SQLite (persisted plans)
                                            │
                                            ▼
                                    Streamlit UI (colour-coded plan)
```

---

## Project Structure

```
PulseCommand AI/
│
├── app.py                          # Entry point — opens directly on Dashboard
├── requirements.txt
├── .env                            # Your LLM credentials (not committed)
├── .env.example                    # Credentials template
├── Dockerfile                      # For Render deployment
├── .dockerignore                   # Exclude unnecessary files from Docker
├── hospital.db                     # SQLite database (auto-created on first run)
│
├── data/
│   ├── admissions.csv              # Patient admissions (30 days)
│   ├── bed_occupancy.csv           # Hourly ward occupancy snapshots
│   ├── doctor_schedules.csv        # Doctor shifts and on-call data
│   └── icu_utilization.csv         # Hourly ICU unit readings
│
├── core/
│   ├── database.py                 # SQLite abstraction (alerts, allocations, logs, plans)
│   └── llm_connector.py            # Provider-agnostic LLM interface
│
├── agents/
│   ├── resource_monitor.py         # Anomaly detection, alerts, AI briefings
│   ├── bed_allocator.py            # Bed recommendation + allocation tracking
│   ├── staff_optimizer.py          # Staff schedule analysis, reassignments
│   └── operational_planner.py      # Cross-agent action plans
│
└── pages/
    ├── Bed_Management.py           # Patient intake + AI bed recommendation
    ├── Alerts_&_Monitoring.py      # Live alerts, resolution, ICU tracking
    ├── Staff_Optimization.py       # Staff analytics + AI reassignments
    └── Operational_Planner.py      # Action plans + history
```

---

## What is Implemented (100%)

### Core Infrastructure

| Module | File | Description |
|---|---|---|
| LLM Connector | `core/llm_connector.py` | Single `llm.chat(system_prompt, user_message)` call — switch provider via `.env` with no code changes |
| Database | `core/database.py` | SQLite wrapper with tables for alerts, bed allocations, agent action logs, operation plans |

### Agents

| Agent | File | Capabilities |
|---|---|---|
| **Resource Monitor** | `agents/resource_monitor.py` | Real-time ward and ICU anomaly detection, threshold-based alerting (WARNING / CRITICAL), occupancy trend analysis, AI-powered operational briefings |
| **Bed Allocator** | `agents/bed_allocator.py` | Priority-based bed recommendation engine (severity + diagnosis + patient age), LLM-generated clinical allocation rationale, allocation history and analytics |
| **Staff Optimizer** | `agents/staff_optimizer.py` | Schedule analysis, understaffing detection, overtime risk flagging, AI-powered reassignment recommendations |
| **Operational Planner** | `agents/operational_planner.py` | Cross-agent state aggregation, LLM-generated prioritized action plans, plan history tracking |

### Streamlit Pages

| Page | File | What it shows |
|---|---|---|
| **Dashboard** | `app.py` | 5 live KPI cards, ward occupancy bar chart (with critical/warning thresholds), ICU utilisation gauge, 24-hour occupancy trend, active alert list, AI operational briefing |
| **Bed Management** | `pages/Bed_Management.py` | Patient intake form (severity, diagnosis, age), AI-powered bed recommendation with rationale, one-click allocation commit, allocation history table, severity distribution charts |
| **Alerts & Monitoring** | `pages/Alerts_&_Monitoring.py` | Live alert scan, per-alert resolution workflow, AI-powered alert analysis, ICU ventilator and nursing level tracking |
| **Staff Optimization** | `pages/Staff_Optimization.py` | Staff KPIs, today's shift overview, understaffed shifts, overtime risks, AI reassignment panel, 30-day staffing heatmap |
| **Operational Planner** | `pages/Operational_Planner.py` | One-click action plan generation, color-coded priorities, hospital state snapshot, plan history |

---

## How the LLM Connector Works

All AI calls across every agent go through one interface:

```python
from core.llm_connector import LLMConnector

llm = LLMConnector()   # reads LLM_PROVIDER + LLM_API_KEY from .env

response = llm.chat(
    system_prompt="You are a hospital staffing coordinator.",
    user_message="Which on-call doctors should cover the Night shift in ICU?",
    max_tokens=350,     # optional, default 512
)
# returns a plain string — handles all providers transparently
print(response)
```

Switch the provider in `.env` — zero code changes needed anywhere in the application.

---

## Dataset Schema Reference

### `admissions.csv`
| Column | Type | Description |
|---|---|---|
| patient_id | string | Unique patient identifier |
| admission_datetime | datetime | Date and time of admission |
| discharge_datetime | datetime | Date and time of discharge |
| ward | string | Assigned ward |
| diagnosis | string | Primary diagnosis |
| severity | int | 1 (low) – 5 (critical) |
| age | int | Patient age |
| admission_type | string | Emergency / Elective / Transfer |

### `bed_occupancy.csv`
| Column | Type | Description |
|---|---|---|
| timestamp | datetime | Hourly snapshot time |
| ward | string | Ward name |
| total_beds | int | Total beds in ward |
| occupied | int | Currently occupied beds |
| available | int | Available beds |
| maintenance | int | Beds out of service |
| occupancy_rate | float | occupied / total_beds |

### `doctor_schedules.csv`
| Column | Type | Description |
|---|---|---|
| schedule_id | string | Unique schedule entry ID |
| doctor_id | string | Doctor identifier |
| doctor_name | string | Full name |
| specialization | string | Medical specialization |
| ward | string | Assigned ward |
| date | date | Shift date |
| shift | string | Morning / Evening / Night |
| shift_start / shift_end | string | HH:MM times |
| hours_worked | float | Total hours on shift |
| overtime_hours | float | Hours beyond standard shift |
| patients_seen | int | Patients seen during shift |
| on_call | bool | Whether doctor is on call |
| leave | bool | Whether doctor is on leave |

### `icu_utilization.csv`
| Column | Type | Description |
|---|---|---|
| timestamp | datetime | Hourly reading time |
| icu_unit | string | ICU unit name |
| beds_total / beds_occupied | int | Bed counts |
| ventilators_total / ventilators_in_use | int | Ventilator counts |
| nursing_staff_required / present | int | Nursing staffing |
| critical_patients | int | Patients in critical state |
| utilization_rate | float | beds_occupied / beds_total |

---

## Theme Alignment — AI Meets Data

> *"If your solution makes someone say 'I had no idea that was in our data,' you're on the right track."*

This platform takes four raw hospital CSV files and surfaces:

- Which wards are **approaching overflow** before they get there
- Which ICU units face a **ventilator shortage** in the coming hour
- Which **specific bed** to allocate to each incoming patient, with clinical reasoning
- Which doctors are at **burnout risk** from accumulated overtime
- A cross-agent **prioritised action plan** — insight that no single data source could provide alone

---

## Deploy to Render

### 1. Create a Dockerfile

We already created a `Dockerfile` in the root directory for you!

### 2. Push your code to GitHub/GitLab

Make sure your code is committed and pushed to a Git repository.

### 3. Create a new Web Service on Render

1. Go to [Render.com](https://render.com) and sign in
2. Click **New +** → **Web Service**
3. Connect your Git repository
4. Configure the service:
   - **Name**: pulsecommand-ai (or your preferred name)
   - **Region**: choose the one closest to you
   - **Branch**: main (or your deployment branch)
   - **Runtime**: Docker
   - **Dockerfile Path**: ./Dockerfile (default)
   - **Instance Type**: Free (or higher if you need more resources)

### 4. Add Environment Variables

In the **Environment** section of your Render service, add:
```
LLM_PROVIDER=groq
LLM_API_KEY=your_groq_api_key_here
LLM_MODEL=llama-3.3-70b-versatile  # optional
```

### 5. Deploy!

Click **Create Web Service** and Render will build and deploy your app! 🚀
