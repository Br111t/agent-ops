# Agent-Ops 🤖🚑

> Self-healing log-triage microservice built with multi-agent LLM orchestration.

## 🚀 Features
- **Planner Agent** outlines tasks by analyzing new log entries.
- **Retriever Agent** pulls relevant docs & runbooks (RAG via ElasticSearch).
- **Diagnoser Agent** pinpoints root cause and generates summary.
- **Jira-Bot Agent** auto-files incident tickets through the Jira REST API.

## 🛠️ Tech Stack
- **Orchestration:** Python + LangChain / Microsoft AutoGen  
- **Core Service:** Java 21 & Spring Boot 3  
- **Data Store:** ElasticSearch, FAISS for embeddings  
- **CI/CD:** GitHub Actions → Docker → GitHub Container Registry  
- **Deployment:** Kubernetes (Helm chart) + ArgoCD

## 🎯 Quick Start


# 1. Clone
```bash
git clone https://github.com/Br111t/agent-ops.git && cd agent-ops
```
# 2. Run locally
```bash
make dev-up    # spins up ES + service via Docker Compose
```
# 3. Diagnose sample
```bash
curl -X POST http://localhost:8080/api/diagnose \
  -H "Content-Type: application/json" \
  -d '{"logFile": "samples/payment_error.log"}'
```
