# Agent-Ops 🤖🚑

> Self-healing log triage with an Angular ops console backed by agent-driven diagnostics.

## What’s in this repo

- `frontend/agent-ops-console` — Angular UI (incident inbox, triage runs, audit trail)
- `backend/` — API service powering the console (mock-first, extensible to full agent orchestration)
- `infra/` — Docker Compose and deployment resources

## 🚀 Features

### Console (Angular)
- Incident inbox with filters (service / environment / severity)
- Incident detail view with raw logs and triage run trace
- Run triage and inspect agent steps + recommendations
- Audit trail of diagnostic actions

### Agent Orchestration
- **Planner Agent** — outlines triage steps based on log context
- **Retriever Agent** — pulls relevant docs & runbooks (RAG via ElasticSearch)
- **Diagnoser Agent** — synthesizes root cause and remediation summary
- **Jira Bot Agent** — optionally files incident tickets via Jira REST API

## 🛠️ Tech Stack

**Frontend**
- Angular
- TypeScript
- RxJS

**Backend**
- Python (FastAPI) and/or Java 21 (Spring Boot)
- LangChain / Microsoft AutoGen

**Data**
- ElasticSearch
- FAISS (embeddings)

**Infra**
- Docker, GitHub Actions
- Kubernetes (Helm) + ArgoCD (planned)

> Note: Some components are stubbed or mocked initially to support frontend development and Angular learning.

## 🎯 Quick Start

### 1. Clone
```bash
git clone https://github.com/Br111t/agent-ops.git
cd agent-ops
```
### 2. Backend (API)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 3. Frontend (Angular)
```bash
cd ../frontend/agent-ops-console
npm install
npm start
```

The Angular console will be available at `http://localhost:4200`

