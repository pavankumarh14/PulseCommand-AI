

PulseCommand AI
Real-time, multi-agent intelligence that turns raw hospital data into prioritised action

Theme: 04 — AI Meets Data  ·  Function: AI-Powered Operations & Insights

Suggested stack: LLM (any) · Streamlit · Pandas / NumPy · Plotly · SQLite  ·  Optional MS: Azure OpenAI · Azure
Functions · Azure SQL

## Problem Statement
## Problem Background
Hospitals generate enormous volumes of operational data every hour — bed states, patient
admissions, ICU readings, doctor schedules, ventilator usage — but lack systems capable of
surfacing the signal buried in that noise and recommending immediate action. Today’s hospital
operations teams rely on manual checks, siloed spreadsheets, and periodic reports that are
already stale by the time they are read. There is no unified intelligence layer that watches every
ward simultaneously, correlates anomalies across datasets, and tells the duty manager what to
do right now.
## Why It Matters
Delayed insight has direct clinical and financial consequences. A ward that tips into overflow
because nobody noticed the occupancy trend costs the hospital in diverted ambulances and
deteriorating patient outcomes. An understaffed night shift identified only after it starts means
reactive firefighting instead of planned reassignment. An ICU ventilator shortage spotted thirty
minutes late can be irreversible. Hospital operations are treated as a manual co-ordination
problem rather than a real-time analytics challenge — exactly the kind of legacy assumption an
AI-first data platform should overturn.
## Solution Summary
## Why This Problem Was Chosen
In an AI-first operations world, hospital intelligence should be maintained by the system, not by
whoever is on duty and happens to notice. Linking raw operational data to a multi-agent
reasoning layer makes risk measurable, visible, and actionable automatically — a high-leverage
change that does not require replacing any clinical system, only augmenting the data that
already exists.
## Proposed Solution
PulseCommand AI is a multi-agent AI platform with four specialised agents and a live
Streamlit dashboard. A Resource Monitor agent watches ward and ICU data continuously, firing
threshold-based anomaly alerts with AI-generated briefings. A Bed Allocator agent recommends
the optimal bed for each incoming patient using severity, diagnosis, and age, backed by an
LLM-generated clinical rationale. A Staff Optimizer agent detects understaffed shifts and
overtime risks and proposes named-doctor reassignments via the LLM. An Operational Planner
agent aggregates all three agents’ summaries into a unified hospital state and generates a
prioritised P1 / P2 / P3 action plan — cross-agent insight that no single data source could
provide alone.

## Expected Impact
- Bed overflows detected before they happen, not after ambulances are diverted.
- ICU ventilator and nursing shortfalls flagged with an hour’s lead time.
- Understaffed shifts identified the day before, enabling planned reassignment.
- A prioritised action plan generated in seconds, replacing manual morning handover
notes.
- A measurable hospital health score that makes operational risk visible to leadership.
## Technical Approach & Implementation
## Solution Workflow
- Four CSV datasets (admissions, bed_occupancy, doctor_schedules, icu_utilization) are
loaded and refreshed on each dashboard interaction.
- ResourceMonitorAgent scans ward occupancy and ICU readings against configurable
thresholds, flags WARNING / CRITICAL anomalies, and writes structured alerts to
SQLite.
- BedAllocationAgent ranks available beds by a priority score (patient severity × diagnosis
weight × age factor) and calls the LLM to generate a clinical rationale for the top
recommendation.
- StaffOptimizerAgent cross-joins schedule data with occupancy data to find ward/shift
combos below the staffing threshold (1 doctor per 10 occupied beds, minimum 2),
identifies overtime-risk doctors, and invokes the LLM to recommend specific on-call
reassignments.
- OperationalPlannerAgent calls every agent’s summary method, builds a unified hospital
state dict, and prompts the LLM to return a structured list of actions with priority,
department, ETA, and rationale. The plan is persisted to SQLite with a timestamp.
- The Streamlit dashboard presents all outputs across five pages: live KPI cards, ward
occupancy charts, ICU gauges, alert resolution workflows, staff heatmaps, and the
colour-coded action plan.
## Key Features
Real-Time Anomaly Detection.  Threshold-based alerting across ward occupancy and ICU
utilisation, with AI-generated explanatory briefings surfaced directly on the dashboard.
Priority-Driven Bed Allocation.  Scores every available bed against patient severity, diagnosis,
and age; presents the top recommendation with an LLM-generated clinical rationale and
one-click commit.
Staffing Gap Intelligence.  Detects understaffed shifts and overtime risks before they
materialise; the LLM suggests named on-call doctors for reassignment rather than generic
advice.
Cross-Agent Action Planning.  A single ‘Generate Plan’ button aggregates all agent states
and produces a P1 / P2 / P3 priority action plan — the kind of synthesis only possible when all
four data streams are seen together.

Provider-Agnostic LLM Layer.  One LLMConnector interface supports OpenAI, Groq,
DeepSeek, Gemini, and Anthropic Claude — swap provider via .env with zero code changes.
## Technology Stack
## Frontend
- Streamlit — multi-page app with live KPI cards, interactive forms, and tabbed views
- Plotly Express + Graph Objects — bar charts, occupancy gauges, heatmaps, trend lines
- Pandas / NumPy — schedule analysis, occupancy aggregation, anomaly scoring
## Backend
- Python 3.10+ — agent layer and Streamlit page controllers
- SQLite (via sqlite3) — alerts, bed allocations, agent logs, operation plans
- python-dotenv — .env-based provider and credential configuration
## AI / ML
- LLM for clinical rationale, staffing reassignment, and action plan generation
## (provider-agnostic)
- Rule-based anomaly scoring with configurable thresholds (no ML training required)
- Priority scoring model — weighted blend of severity, diagnosis criticality, and patient age
## Data & Integrations
- Four synthetic CSV datasets (~10 000 rows total) — admissions, bed occupancy, doctor
schedules, ICU utilisation
- SQLite persistence for alerts, allocations, agent logs, and operational plans
- Provider API integrations: OpenAI, Groq, DeepSeek, Google Gemini, Anthropic
## Models & Algorithms
Anomaly Detection.  Ward and ICU metrics are compared against configurable occupancy and
utilisation thresholds. Breaches are classified as WARNING or CRITICAL and persisted to
SQLite with a timestamp and affected unit.
Bed Priority Score.  Each available bed is scored as severity_weight × diagnosis_criticality ×
age_factor. The top-scoring bed is passed to the LLM alongside patient context to generate a
clinical allocation rationale.
Staffing Gap Calculation.  The agent cross-joins daily schedule data with hourly occupancy
snapshots to compute the required doctor count per ward per shift (ceil(occupied_beds / 10),
min 2). Shortfalls trigger an LLM reassignment recommendation using named on-call doctors.
Overtime Risk Flagging.  Doctors with overtime_hours > 2 accumulated over the prior seven
days are surfaced as burnout risks, independently of whether their shift is understaffed.
Unified State Action Plan.  The Operational Planner merges resource, bed, and staffing
summaries into a single state dict and prompts the LLM to return a structured action list with
priority (P1 / P2 / P3), department, estimated resolution time, and rationale.

## Innovation
Multi-agent, single-truth orchestration.  Four specialist agents each own one domain; the
Operational Planner is the only component that sees all four — so its output is structurally
cross-functional, not a single-model generalisation.
Priority plan, not raw alerts.  The system does not just surface numbers; it tells the duty
manager what to do first, second, and third, with department and ETA attached to each action.
Named-doctor reassignment.  Staff suggestions name specific on-call doctors from the
schedule data rather than generic role labels — the LLM has grounded context, not hypothetical
advice.
Provider-agnostic intelligence.  The same production application runs on a hosted model, a
private Azure OpenAI endpoint, or a self-hosted model — data-residency requirements do not
require re-architecting the system.
## Future Scope
## Near-term
- Real-time data ingestion via hospital EMR / HL7 FHIR feeds replacing CSV polling
- Slack / Teams alert push when a ward breaches CRITICAL threshold
- Per-ward and per-doctor performance scorecards for nursing and medical leads
## Medium-term
- Predictive occupancy modelling — forecast bed demand 4–8 hours ahead from
admission trends
- Automated discharge planning recommendations to free beds before overflow
- Pharmacy and supply-chain agent — surface medication and equipment shortfalls
alongside staffing alerts
## Long-term
- Org-wide hospital network view — aggregate occupancy and staffing across multiple
sites
- Confidence-gated auto-execution for low-risk operational decisions (e.g. routine bed
re-assignments)
- Clinical outcome feedback loop — correlate operational decisions with patient outcome
data to improve scoring weights
## Scalability & Larger Vision
## How It Scales
PulseCommand AI is built to grow along three independent axes without
re-architecting the core.
Technically, the agent layer is stateless and data-driven: each agent reads from a shared data
layer and writes to a shared SQLite store. Replacing CSV polling with a streaming data source
(Kafka, Azure Event Hubs) requires changing only the data loader — the agents, LLM calls, and

UI are unaffected. The LLM layer is provider-agnostic, so the same system runs on a hosted
model, a private Azure OpenAI endpoint, or a self-hosted model depending on data-residency
needs.
Across hospitals and networks, the platform moves naturally from a single facility to an entire
hospital group. The occupancy and staffing scores are defined per ward but aggregate cleanly
to hospital, region, and network level, so the same primitives that help one duty manager
become a leadership-level risk dashboard without new machinery.
Organisationally, the unit of value — an agent that watches one domain and publishes a
structured summary — is identical whether the hospital has five wards or fifty. Onboarding a
new ward requires no manual configuration; the agents bootstrap from the data schema
automatically.
## How It Expands
The roadmap deepens the same core idea rather than bolting on unrelated features. Near term,
real EMR data replaces synthetic CSVs and push alerts reach the duty team in Slack. In the
medium term, predictive occupancy modelling gives the team a four-to-eight-hour window to act
before overflow rather than reacting to it. Long term, PulseCommand AI becomes the
backbone of a hospital network intelligence layer, with confidence-gated auto-execution
handling routine reassignments without requiring human approval for every decision.
## The Larger Vision
Hospital operations stop being a manual co-ordination problem and become a living intelligence
layer the system maintains. The end state is a facility where no shift starts understaffed, no ward
tips into overflow unannounced, and no ICU ventilator shortage is discovered too late —
because the system watched the data, correlated the signals, and told the right person what to
do before the window closed.
## Potential Impact
At one hospital’s scale, PulseCommand AI prevents one overflow event per week —
averting ambulance diversions, improving patient outcomes, and saving nursing hours
previously spent on manual status checks. Understaffed shifts caught the day before become
planned reassignments rather than crisis responses. Bed allocation decisions backed by clinical
reasoning reduce inappropriate placements and readmissions.
At network scale, the compounding effect is larger: a measurable operational health benchmark
across sites, sharply fewer reactive incidents, and a leadership-level dashboard that surfaces
systemic risk before it reaches clinical severity. The intervention is architectural — a reasoning
layer over data that already exists — but it shifts an entire operations culture from reactive
firefighting to proactive, intelligence-led hospital management.