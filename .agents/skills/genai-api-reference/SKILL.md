---
name: genai-api-reference
description: Reference this file when working on FastAPI endpoints, request/response models, middleware, rate limits, or deployment.
---

# Phase 2.4: GenAI API Reference

## Endpoints

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

## Pydantic Models

- `ChatRequest` / `ChatResponse` — Agent conversations with conversation_id
- `SearchRequest` / `SearchResponse` — Vector search with filters
- `StatsRequest` / `StatsResponse` — Analytics grouping
- `HealthResponse` — Service + dependency status (BigQuery, Vertex AI, embeddings)
- `ErrorResponse` — Standardized errors with request_id

## Middleware

- **Rate Limiting** (`slowapi`): Per-endpoint limits by IP
- **CORS**: localhost:3000, localhost:8501, production dashboard
- **Request Logging**: UUID tracking, structured JSON, X-Request-ID / X-Processing-Time-MS headers
- **Error Handling**: HTTP exception handler + general exception handler with logging

## Guardrails Integration

- Input validation before agent execution (PII, injection)
- Output validation after generation (hallucination check)
- `BLOCKED` severity → HTTP 400/500
- `WARNING` severity → logged but allowed through

## Deployment

- **File:** `genai/api.py`
- **Dockerfile.api**: Optimized to ~1.8GB (CPU-only PyTorch, down from 5GB)
- **Cloud Build:** `cloudbuild.api.yaml` with Trivy vulnerability scanning
- **Cloud Run**: asia-southeast1, 0-10 instances, 2 vCPU, 4GB RAM
- **IAM**: roles/aiplatform.user for Vertex AI
- **Security**: Trivy scans Python packages for HIGH/CRITICAL CVEs; build fails on fixable vulnerabilities
- Service URL: `https://genai-api-[hash]-as.a.run.app`
