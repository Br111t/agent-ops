# Agent-Ops 🤖🚑

> **Self-healing log-triage service built with multi-agent LLM orchestration.**  
> Detects anomalies in application logs, summarizes root-cause, and auto-opens Jira tickets.

## ✨ Features
- **AutoGen–powered agent swarm**: Planner, Retriever, Diagnoser, Jira-Bot
- **Java Spring Boot** REST wrapper → scalable deployment on Kubernetes
- **Python micro-agents** run via FastAPI + LangChain
- Retrieval-Augmented Generation (RAG) over ElasticSearch logs
- CI/CD: GitHub Actions → Docker → GHCR → ArgoCD
- Unit & integration tests (JUnit 5 + PyTest)

## 🚀 Quick start

```bash
# 1. clone
git clone https://github.com/Br111t/agent-ops.git && cd agent-ops

# 2. spin up containers
make dev-up          # or: docker compose up -d

# 3. run sample workflow
curl -X POST http://localhost:8080/api/diagnose \
     -d '{"logFile": "samples/payment_error.log"}'
