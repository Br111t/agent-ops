# Agent-Ops Architecture

Agent-Ops is an operations console + backend service for log triage and incident response. The system is designed “mock-first” so the Angular UI can be built and tested before full agent orchestration is wired up.

## Goals
- Provide an **Ops Console** to review incidents, inspect logs, and run triage.
- Produce **traceable diagnostics** (run steps, inputs/outputs, audit trail).
- Support progressive enhancement:
  1) mocked data → 2) real API → 3) agent orchestration → 4) integrations (Jira)

## High-level Components

### 1) Angular Ops Console (`frontend/agent-ops-console`)
Primary UI for:
- Incident inbox (filter by service/env/severity/time)
- Incident detail (raw logs, metadata, tags)
- Triage runs (start run, view status, inspect step trace)
- Audit trail (who/what triggered actions)

Key Angular concepts used:
- Routing: `/incidents`, `/incidents/:id`
- Services: `IncidentsApiService`, `TriageApiService`
- Reactive Forms: filter/search panel
- RxJS: polling triage run status, debounced search, combining filters

### 2) API Backend (`backend/`)
The backend exposes REST endpoints used by the console:
- Incident query and detail retrieval
- Triage run initiation
- Run status + trace retrieval
- Persistence of run results and audit events

Implementation can start as:
- FastAPI mock endpoints returning static JSON
Then evolve into:
- real ingestion + storage
- agent execution and trace persistence

### 3) Agent Orchestration (Backend subsystem)
Triage is performed by cooperative agents that generate a structured output and a trace of intermediate steps.

Agents:
- **Planner**: determines a triage plan based on log context
- **Retriever**: fetches relevant runbooks/docs and similar incidents (RAG)
- **Diagnoser**: synthesizes root cause + recommended fix
- **Jira Bot** (optional): files ticket via Jira REST API

The UI does not call agents directly — it calls the backend, which runs agents and returns:
- `runId`
- `status`
- `steps[]` (trace)
- `result` (when completed)

## Data Flow

### A) Browse incidents
1. UI requests `GET /api/incidents?filters…`
2. Backend returns summary list
3. UI renders table + filter/search UI

### B) View incident detail
1. UI requests `GET /api/incidents/{id}`
2. Backend returns logs + metadata + last run summary (if exists)

### C) Run triage
1. User clicks “Run triage”
2. UI calls `POST /api/incidents/{id}/triage`
3. Backend creates a run record and returns `{ runId }`
4. UI polls `GET /api/runs/{runId}` every N seconds
5. Backend updates run status and step trace as agents complete work
6. When finished, backend returns the final `result` and UI displays it

## API Contract (Minimal)

### Incidents
- `GET /api/incidents`
  - Query params: `service`, `environment`, `severity`, `q`, `from`, `to`
  - Returns: `Incident[]` (summary)

- `GET /api/incidents/{id}`
  - Returns: `IncidentDetail`

### Triage Runs
- `POST /api/incidents/{id}/triage`
  - Body: optional config (e.g., strategy, retriever scope)
  - Returns: `{ runId: string }`

- `GET /api/runs/{runId}`
  - Returns:
    - `status` (queued/running/succeeded/failed)
    - `steps[]` (trace)
    - `result` (only when finished)

## Data Model (Conceptual)

### Incident
- `id`, `title`, `service`, `environment`, `severity`
- `createdAt`, `updatedAt`
- `errorSignature` (optional)
- `rawLogs[]`

### TriageRun
- `runId`, `incidentId`
- `status`, `startedAt`, `finishedAt`
- `steps[]` (trace)
- `result` (summary/root cause/fix/confidence)
