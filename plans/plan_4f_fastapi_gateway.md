# Plan 4F: FastAPI & Model Gateway

> **Project:** SG Job Market Intelligence Platform
> **Focus:** FastAPI REST endpoints, request/response models, middleware, rate limiting, model gateway with fallback, and production deployment
> **Status:** Active

---

## [Overview]

Single sentence: Production FastAPI service with rate-limited REST endpoints, model gateway with automatic failover, and hardened Cloud Run deployment.

Multiple paragraphs:
The FastAPI layer exposes the GenAI stack as a REST API with endpoints for chat, search, job details, similar jobs, and statistics. Each endpoint has per-IP rate limits enforced via `slowapi`. Request logging uses UUID tracking with structured JSON and custom headers.

The Model Gateway (`genai/gateway.py`) provides a unified interface to multiple LLM providers. It defaults to Vertex AI Gemini 2.5 Flash with automatic fallback to Ollama `deepseek-r1:8b` when the primary provider fails. Cost tracking per call enables usage analysis and optimization.

Security hardening includes Trivy vulnerability scanning on all Docker builds, with builds failing if fixable HIGH/CRITICAL CVEs are detected in Python packages. The API service runs on Cloud Run with auto-scaling and IAM-bound service accounts.

---

## [Architecture]

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ FASTAPI GATEWAY (genai/api.py)                                              │
│ ─────────────────────────────────────────────────────────────────────────── │
│ POST /v1/chat      → Conversational RAG (10/min)                           │
│ POST /v1/search    → Direct vector search (50/min)                         │
│ GET  /v1/jobs/{id} → Job details (100/min)                                 │
│ GET  /v1/jobs/{id}/similar → Similar jobs (50/min)                         │
│ POST /v1/stats     → Aggregate statistics (30/min)                         │
│ GET  /health       → Health check (no limit)                               │
│ GET  /metrics      → Prometheus metrics (no limit)                         │
│ GET  /             → API navigation (no limit)                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ MIDDLEWARE                                                                  │
│ • Rate Limiting (slowapi): Per-endpoint limits by IP                       │
│ • CORS: localhost:3000, localhost:8501, production dashboard               │
│ • Request Logging: UUID tracking, structured JSON,                        │
│   X-Request-ID / X-Processing-Time-MS headers                              │
│ • Error Handling: HTTP exception handler + general exception handler       │
│ • CacheMiddleware: Query result caching (from Plan 4B)                     │
│ • Guardrails: Input validation before agent, output after generation       │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ MODEL GATEWAY (genai/gateway.py)                                            │
│ ─────────────────────────────────────────────────────────────────────────── │
│ Vertex AI Gemini 2.5 Flash (default)                                       │
│     │                                                                       │
│     └──► fallback → Ollama deepseek-r1:8b                                 │
│                                                                             │
│ Features:                                                                   │
│ • Automatic provider failover                                               │
│ • Cost tracking per call                                                    │
│ • Retry logic with exponential backoff                                      │
│ • Provider selection (auto or explicit)                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## [Endpoints]

| Method | Endpoint | Purpose | Rate Limit |
|--------|----------|---------|------------|
| POST | /v1/chat | Conversational agent | 10/min |
| POST | /v1/search | Direct vector search | 50/min |
| GET | /v1/jobs/{job_id} | Job details | 100/min |
| GET | /v1/jobs/{job_id}/similar | Similar jobs | 50/min |
| POST | /v1/stats | Aggregate statistics | 30/min |
| GET | /health | Health check | No limit |
| GET | /metrics | Prometheus metrics | No limit |
| GET | / | API navigation | No limit |

---

## [Pydantic Models]

- `ChatRequest` / `ChatResponse` — Agent conversations with conversation_id
- `SearchRequest` / `SearchResponse` — Vector search with filters
- `StatsRequest` / `StatsResponse` — Analytics grouping
- `HealthResponse` — Service + dependency status (PostgreSQL, Qdrant, Vertex AI, embeddings)
- `ErrorResponse` — Standardized errors with request_id

---

## [Files]

Single sentence: 2 core files, 1 Dockerfile, 1 Cloud Build config.

### Core Files

| File | Purpose |
|------|---------|
| `genai/api.py` | FastAPI app with all endpoints, middleware, models |
| `genai/gateway.py` | ModelGateway with VertexAIProvider and OllamaProvider |

### Deployment Files

| File | Purpose |
|------|---------|
| `Dockerfile.api` | Optimized to ~1.8GB (CPU-only PyTorch, down from 5GB) |
| `cloudbuild.api.yaml` | Trivy vulnerability scanning before deployment |

### Deployment Scripts

| File | Purpose |
|------|---------|
| `deployment/API_01_Deploy_FastAPI.ps1` | PowerShell deployment script |

---

## [Model Gateway]

### Providers

| Provider | Model | Role |
|----------|-------|------|
| Vertex AI | Gemini 2.5 Flash | Primary — fast, cost-effective |
| Ollama | deepseek-r1:8b | Fallback — local, no API cost |

### Features

- Automatic provider failover on error or timeout
- Cost tracking per call (USD)
- Retry logic with exponential backoff
- Explicit provider selection via request parameter
- Configuration-driven provider priority

---

## [Middleware]

- **Rate Limiting** (`slowapi`): Per-endpoint limits by IP
- **CORS**: localhost:3000, localhost:8501, production dashboard
- **Request Logging**: UUID tracking, structured JSON, X-Request-ID / X-Processing-Time-MS headers
- **Error Handling**: HTTP exception handler + general exception handler with logging
- **CacheMiddleware**: Query result caching (from Plan 4B)
- **Guardrails Integration**: Input validation before agent execution (PII, injection); output validation after generation (hallucination check)
  - `BLOCKED` severity → HTTP 400/500
  - `WARNING` severity → logged but allowed through

---

## [Deployment]

### Cloud Run

- Region: asia-southeast1
- Instances: 0-10 (auto-scaling)
- CPU: 2 vCPU
- RAM: 4GB
- IAM: roles/aiplatform.user for Vertex AI

### Security

- Trivy vulnerability scanning on all cloudbuild pipelines
- Scans Python packages for HIGH/CRITICAL CVEs
- Ignores unfixed OS vulnerabilities
- Build fails on fixable vulnerabilities

### Service URL

```
https://genai-api-[hash]-as.a.run.app
```

---

## [Testing]

### API Tests (8 tests)

| Test | Endpoint | Target |
|------|----------|--------|
| Chat endpoint | POST /v1/chat | Agent conversation |
| Search endpoint | POST /v1/search | Vector search results |
| Job details | GET /v1/jobs/{id} | Full job info |
| Similar jobs | GET /v1/jobs/{id}/similar | Similarity results |
| Stats | POST /v1/stats | Aggregated statistics |
| Health | GET /health | Service status |
| Metrics | GET /metrics | Prometheus metrics |
| Rate limiting | All endpoints | Limits enforced |

### Gateway Tests (6 tests)

| Test | Target |
|------|--------|
| 1 | Provider detection |
| 2 | Simple generation |
| 3 | Specific provider selection |
| 4 | Fallback logic |
| 5 | Cost tracking |
| 6 | Configuration options |

---

## [Acceptance Criteria]

| Criterion | Target | How to Measure |
|-----------|--------|----------------|
| All endpoints respond | 200/201 for valid requests | API tests |
| Rate limits enforced | 429 when exceeded | API tests |
| CORS working | Cross-origin requests allowed | Manual test |
| Request IDs present | X-Request-ID in all responses | API tests |
| Fallback works | Ollama used when Vertex AI fails | Gateway tests |
| Cost tracked | metadata.cost_usd populated | Gateway tests |
| Build secure | No fixable HIGH/CRITICAL CVEs | Trivy scan |
| Health check | Returns dependency status | Health endpoint |
| Metrics endpoint | Prometheus format | /metrics test |

---

*Document version: 1.0*
