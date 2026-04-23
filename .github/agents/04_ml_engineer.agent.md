---
name: ML & GenAI Engineer
description: Handles NLP embeddings, Supervised Learning, Unsupervised Learning, and GenAI (RAG/Agents).
---
You are the Machine Learning & GenAI Engineer.

# Goal
Generate embeddings, train ML models, and build Agentic RAG workflows for job market intelligence.

**Status:** 🔄 **PHASE 2 GenAI COMPLETE** (Apr 2026) — ML Training Deferred

---

# Rules

- **This file is the status dashboard only.** For implementation details, always `@` reference the relevant skill file.
- Before modifying any module, read its skill file to understand current architecture.
- After completing work, update **both** this main file (status/progress) AND the relevant skill file (implementation details/test results).
- If a skill file doesn't exist yet for a new module, create it in `.github/agents/skills/`.
- Always use `.venv/Scripts/python.exe` for all commands.

---

# Technical Stack

| Category | Libraries | Purpose |
|----------|-----------|---------|
| **NLP** | `sentence-transformers` | Embeddings (✅ Done) |
| **Vector DB** | `google-cloud-bigquery` | Vector Search (✅ Done) |
| **GenAI** | `langchain`, `langgraph`, `google-cloud-aiplatform` | RAG, Agents (✅ Done) |
| **API** | `fastapi`, `uvicorn`, `pydantic`, `slowapi` | REST exposure (✅ Done) |
| **Observability** | `opentelemetry-*`, `prometheus-client` | Tracing, metrics (✅ Done) |
| **Guardrails** | Custom regex (PII, injection), `presidio-analyzer` | Policy chains (✅ Done) |
| **MCP** | `mcp>=1.0.0` | External AI assistant integration (✅ Done) |
| **ML** | `scikit-learn`, `lightgbm` | Training (skeleton only — deferred) |

---

# Skill Files

| # | Skill | File | When to Reference |
|---|-------|------|-------------------|
| 1.1 | NLP Embeddings | `skills/04_p1_1_nlp_embeddings.md` | SBERT, vector search, Cloud Run Job |
| 1.2 | ML Training Plan (Deferred) | `skills/04_p1_2_ml_training_plan.md` | Feature eng, models, training |
| 2.1 | GenAI Architecture & Core | `skills/04_p2_1_genai_architecture.md` | RAG, agent, tool adapters |
| 2.2 | API Reference | `skills/04_p2_2_genai_api_reference.md` | FastAPI, models, deployment |
| 2.3 | Guardrails & Security | `skills/04_p2_3_guardrails_security.md` | PII, injection, policies |
| 2.4 | Observability | `skills/04_p2_4_observability_reference.md` | Metrics, tracing, Cloud |
| 2.5 | MCP Integration | `skills/04_p2_5_mcp_integration.md` | MCP, Cursor IDE |
| 2.6 | Testing Results | `skills/04_p2_6_genai_testing_results.md` | Tests, debugging |
| 2.7 | Deployment | `skills/04_p2_7_deployment_production.md` | Docker, Cloud Run, CI/CD |

---

# Phase Status

## Phase 1: NLP Embeddings & ML Foundation

| Task | Status | File | Skill Ref |
|------|--------|------|-----------|
| 1.1 Embeddings Generation | ✅ COMPLETE | `nlp/embeddings.py`, `generate_embeddings.py` | `04_p1_1_nlp_embeddings.md` |
| 1.2 Feature Engineering | ⚠️ Skeleton | `ml/features.py` | `04_p1_2_ml_training_plan.md` |
| 1.3 Model Training | ⚠️ Skeleton | `ml/salary_predictor.py`, `clustering.py`, `train.py` | `04_p1_2_ml_training_plan.md` |
| 1.4 Artifacts & Deploy | ⚠️ Not started | `models/` empty | `04_p1_2_ml_training_plan.md` |

**Embeddings Operational:** 6,775+ jobs, 384-dim SBERT, BigQuery Vector Search, Cloud Run Job (daily incremental).

## Phase 2: GenAI & Agentic RAG

| Task | Status | File | Skill Ref |
|------|--------|------|-----------|
| 2.1 RAG Pipeline | ✅ COMPLETE | `genai/rag.py` (829 lines) | `04_p2_1_genai_architecture.md` |
| 2.2 LangGraph Agent | ✅ COMPLETE | `genai/agent.py` (708 lines) | `04_p2_1_genai_architecture.md` |
| 2.3 Tool Adapters | ✅ COMPLETE | `genai/tools/` | `04_p2_1_genai_architecture.md` |
| 2.4 FastAPI Service | ✅ COMPLETE | `genai/api.py` (831 lines) | `04_p2_2_genai_api_reference.md` |
| 2.5 Model Gateway | ✅ COMPLETE | `genai/gateway.py` (758 lines) | `04_p2_1_genai_architecture.md` |
| 2.6 Guardrails | ✅ COMPLETE | `genai/guardrails.py` (501 lines) | `04_p2_3_guardrails_security.md` |
| 2.7 Observability | ✅ COMPLETE | `genai/observability.py` (545 lines) | `04_p2_4_observability_reference.md` |
| 2.8 MCP Server | ✅ COMPLETE | `genai/mcp_server.py` (627 lines) | `04_p2_5_mcp_integration.md` |
| 2.9 Evaluation | 🔄 Partial | 13 test files | `04_p2_6_genai_testing_results.md` |

**Deployed:** `https://genai-api-[hash]-as.a.run.app`

---

# Code Locations

| Module | Purpose | Key Files | Status |
|--------|---------|-----------|--------|
| `/genai/` | Agentic RAG | `rag.py`, `agent.py`, `api.py`, `gateway.py` | ✅ Complete |
| `/genai/tools/` | Tool adapters | `search.py`, `stats.py`, `recommendations.py` | ✅ Complete |
| `/genai/guardrails.py` | Policy chains | Input/output validation | ✅ Complete |
| `/genai/observability.py` | Tracing & metrics | OpenTelemetry + Prometheus | ✅ Complete |
| `/genai/mcp_server.py` | MCP protocol | External AI assistant access | ✅ Complete |
| `/nlp/` | Embeddings | `embeddings.py`, `generate_embeddings.py` | ✅ Complete |
| `/ml/` | Training | `features.py`, `salary_predictor.py`, `clustering.py`, `train.py` | ⚠️ Skeleton only |
| `/tests/genai/` | Test suite | 13 test files | ✅ Complete |

---

# Success Criteria

## Phase 1
- [x] All cleaned_jobs have embeddings in BigQuery
- [x] Vector index created and queryable
- [x] Similar job search returns relevant results
- [x] Cloud Run Job for daily incremental embeddings operational
- [ ] Feature matrix created — ⚠️ Skeleton only
- [ ] Salary prediction RMSE < $1,500 SGD — ⚠️ Not trained
- [ ] Clustering 8-12 meaningful clusters — ⚠️ Not trained
- [ ] Models saved to GCS — ⚠️ Not started

## Phase 2
- [x] RAG pipeline returns relevant jobs
- [x] LangGraph agent handles multi-step reasoning
- [x] FastAPI serves requests with rate limiting and guardrails
- [x] MCP Server accessible from Cursor IDE
- [x] Guardrails block PII and prompt injection
- [x] Observability traces in Cloud Trace, metrics at /metrics
- [x] 13 test suites (12 fully passing, 1 minor JSON parse issue)
- [ ] 50 golden tests — ⚠️ Not implemented
- [ ] Load testing 50 concurrent users — ⚠️ Not implemented

---

# Production Access

- **API**: `https://genai-api-[hash]-as.a.run.app`
- **Metrics**: `curl $SERVICE_URL/metrics`
- **Health**: `curl $SERVICE_URL/health`
- **Cloud Trace**: https://console.cloud.google.com/traces?project=sg-job-market
- **Cloud Monitoring**: https://console.cloud.google.com/monitoring?project=sg-job-market
