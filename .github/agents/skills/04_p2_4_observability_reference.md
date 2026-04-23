# Phase 2.6: Observability & Monitoring

> Reference this file when working on: metrics, tracing, Cloud Logging, or debugging production issues.

---

## OpenTelemetry Tracing

File: `genai/observability.py`

- Cloud Trace exporter (production)
- `@trace_function` decorator on all RAG functions
- `trace_span` context manager for code blocks
- `add_span_attributes()` for custom metadata
- Span attributes: query_length, result_count, duration_ms, relevance_scores
- Error tracking with exception details

## Prometheus Metrics (21 total)

| Category | Metrics | Description |
|----------|---------|-------------|
| **Request** | REQUEST_COUNT, REQUEST_LATENCY, ACTIVE_REQUESTS | Per-endpoint tracking |
| **LLM** | LLM_CALL_COUNT, LLM_TOKEN_COUNT, LLM_COST, LLM_LATENCY | Per provider/model |
| **RAG** | RETRIEVAL_LATENCY, RETRIEVAL_COUNT, GRADING_LATENCY, AVERAGE_RELEVANCE_SCORE, REWRITE_COUNT | Pipeline quality |
| **Agent** | AGENT_EXECUTION_LATENCY, AGENT_STEP_COUNT | Workflow performance |
| **Guardrails** | GUARDRAIL_BLOCKS | Security events by type |
| **System** | API_INFO | Version metadata |

## Cloud Integration

- Cloud Trace: Distributed tracing operational
- Cloud Monitoring: Metrics aggregation operational
- FastAPI auto-instrumentation via `instrument_fastapi(app)`
- Request ID tracking with `X-Request-ID` header
- IAM: roles/cloudtrace.agent + roles/monitoring.metricWriter

## Access

```bash
# Local
curl http://localhost:8000/metrics

# Production
curl $SERVICE_URL/metrics
```

## Dashboards

- Cloud Trace: https://console.cloud.google.com/traces?project=sg-job-market
- Cloud Monitoring: https://console.cloud.google.com/monitoring?project=sg-job-market
