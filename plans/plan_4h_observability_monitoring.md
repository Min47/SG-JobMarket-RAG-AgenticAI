# Plan 4H: Observability & Monitoring

> **Project:** SG Job Market Intelligence Platform
> **Focus:** OpenTelemetry distributed tracing, Prometheus metrics, Cloud Logging integration, and monitoring dashboard
> **Status:** Active

---

## [Overview]

Single sentence: Full-stack observability with 21 Prometheus metrics, OpenTelemetry tracing, Cloud Trace integration, and a Streamlit monitoring dashboard.

Multiple paragraphs:
The observability layer provides production visibility into every layer of the GenAI stack. OpenTelemetry traces follow requests from the FastAPI layer through the LangGraph agent, RAG pipeline, and Model Gateway. Prometheus metrics expose quantitative data for alerting and trend analysis.

19 metrics are tracked across 6 categories (16 core + 3 cache metrics from Plan 4B): Request (count, latency, active requests), LLM (calls, tokens, cost, latency), RAG (retrieval latency, count, grading latency, relevance scores, rewrites), Agent (execution latency, step count), Guardrails (blocks by type), and System (version metadata).

Cloud Trace and Cloud Monitoring provide centralized aggregation in GCP. The FastAPI `/metrics` endpoint serves Prometheus-format data for scraping. A Streamlit dashboard (see Plan 4I for dashboard details) visualizes live metrics for operations teams.

Additional metrics for caching and cost tracking are added as part of Plan 4B (RAG Pipeline) integration: `CACHE_HIT_COUNT`, `CACHE_MISS_COUNT`, and `COST_PER_QUERY`.

---

## [Architecture]

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ OBSERVABILITY STACK                                                         │
│ ─────────────────────────────────────────────────────────────────────────── │
│                                                                             │
│  OpenTelemetry Tracing                                                      │
│  ├── @trace_function decorator on all RAG functions                        │
│  ├── trace_span context manager for code blocks                            │
│  ├── add_span_attributes() for custom metadata                             │
│  └── Cloud Trace exporter (production)                                      │
│                                                                             │
│  Prometheus Metrics (19 total)                                              │
│  ├── Request: REQUEST_COUNT, REQUEST_LATENCY, ACTIVE_REQUESTS              │
│  ├── LLM: LLM_CALL_COUNT, LLM_TOKEN_COUNT, LLM_COST, LLM_LATENCY         │
│  ├── RAG: RETRIEVAL_LATENCY, RETRIEVAL_COUNT, GRADING_LATENCY,            │
│  │         AVERAGE_RELEVANCE_SCORE, REWRITE_COUNT                          │
│  ├── Agent: AGENT_EXECUTION_LATENCY, AGENT_STEP_COUNT                     │
│  ├── Guardrails: GUARDRAIL_BLOCKS                                          │
│  └── System: API_INFO                                                      │
│                                                                             │
│  Cloud Integration                                                          │
│  ├── Cloud Trace: Distributed tracing operational                          │
│  ├── Cloud Monitoring: Metrics aggregation operational                     │
│  └── IAM: roles/cloudtrace.agent + roles/monitoring.metricWriter          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## [Files]

Single sentence: 1 core observability file, 1 dashboard file.

### Core File

| File | Purpose |
|------|---------|
| `genai/observability.py` | OpenTelemetry tracing, Prometheus metrics, Cloud integration |

### Dashboard Files

| File | Purpose |
|------|---------|
| `dashboard/app.py` | Streamlit monitoring dashboard (overwrites existing skeleton) |
| `dashboard/metrics_fetcher.py` | Fetch Prometheus metrics, Cloud Trace spans, PostgreSQL logs |

---

## [Prometheus Metrics]

### Request Metrics

| Metric | Description |
|--------|-------------|
| `REQUEST_COUNT` | Total requests per endpoint |
| `REQUEST_LATENCY` | Request duration in milliseconds |
| `ACTIVE_REQUESTS` | Currently in-flight requests |

### LLM Metrics

| Metric | Description |
|--------|-------------|
| `LLM_CALL_COUNT` | Total LLM calls per provider/model |
| `LLM_TOKEN_COUNT` | Tokens consumed per call |
| `LLM_COST` | Cost per call in USD |
| `LLM_LATENCY` | LLM call duration in milliseconds |

### RAG Metrics

| Metric | Description |
|--------|-------------|
| `RETRIEVAL_LATENCY` | Vector search duration |
| `RETRIEVAL_COUNT` | Number of documents retrieved |
| `GRADING_LATENCY` | Document grading duration |
| `AVERAGE_RELEVANCE_SCORE` | Mean relevance score across graded docs |
| `REWRITE_COUNT` | Number of query rewrites triggered |

### Agent Metrics

| Metric | Description |
|--------|-------------|
| `AGENT_EXECUTION_LATENCY` | Total agent workflow duration |
| `AGENT_STEP_COUNT` | Number of graph steps executed |

### Guardrail Metrics

| Metric | Description |
|--------|-------------|
| `GUARDRAIL_BLOCKS` | Security events by type (PII, injection, semantic) |

### System Metrics

| Metric | Description |
|--------|-------------|
| `API_INFO` | Version metadata |

### Cache Metrics (from Plan 4B)

| Metric | Description |
|--------|-------------|
| `CACHE_HIT_COUNT` | Query result cache hits |
| `CACHE_MISS_COUNT` | Query result cache misses |
| `COST_PER_QUERY` | Total cost per RAG query |

---

## [OpenTelemetry Tracing]

- `@trace_function` decorator on all RAG functions
- `trace_span` context manager for arbitrary code blocks
- `add_span_attributes()` for custom metadata
- Span attributes include:
  - `query_length`
  - `result_count`
  - `duration_ms`
  - `relevance_scores`
- Error tracking with full exception details

### Cloud Integration

- Cloud Trace exporter (production mode)
- Cloud Monitoring metrics aggregation
- FastAPI auto-instrumentation via `instrument_fastapi(app)`
- Request ID tracking with `X-Request-ID` header

---

## [Dashboard Pages]

The Streamlit dashboard (detailed in Plan 4I) includes:

- **Overview**: queries today, avg latency, cost today, cache hit rate
- **Guardrails**: blocks by type (PII, injection, semantic)
- **RAG Quality**: avg relevance score trend, top failed queries
- **Top Queries**: most searched terms, repeated queries

---

## [Access]

```bash
# Local
curl http://localhost:8000/metrics

# Production
curl $SERVICE_URL/metrics
```

### GCP Console Links

- Cloud Trace: `https://console.cloud.google.com/traces?project=sg-job-market`
- Cloud Monitoring: `https://console.cloud.google.com/monitoring?project=sg-job-market`

---

## [Testing]

### Observability Tests (7 tests)

| Test | Target |
|------|--------|
| 1 | Initialization (local mode) |
| 2 | Tracing decorators & span attributes |
| 3 | All 21 Prometheus metrics tracked |
| 4 | RAG pipeline integration (retrieve + grade) |
| 5 | Gateway LLM tracking |
| 6 | FastAPI /metrics endpoint |
| 7 | Error handling in traces |

---

## [Acceptance Criteria]

| Criterion | Target | How to Measure |
|-----------|--------|----------------|
| All 21+ metrics emitted | Each metric has non-zero values | `/metrics` endpoint |
| Tracing operational | Spans visible in Cloud Trace | Cloud Trace console |
| Request IDs | X-Request-ID in all responses | API tests |
| Error tracking | Exceptions logged with spans | Error injection test |
| Dashboard loads | Live metrics in < 5 seconds | Manual `streamlit run` |
| Cache metrics | HIT/MISS counts accurate | Cache test + metrics check |

---

*Document version: 1.0*
