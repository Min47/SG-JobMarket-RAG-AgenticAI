# Plan 4I: Performance & Cost Optimization

> **Project:** SG Job Market Intelligence Platform
> **Focus:** TTL caching, parallel grading, cost tracking, and Streamlit monitoring dashboard
> **Status:** Active

---

## [Overview]

Single sentence: Cost-efficient production RAG with TTL in-memory caching, parallel document grading, per-query cost tracking, and a real-time monitoring dashboard.

Multiple paragraphs:
Gemini API costs currently run approximately $88/month with no caching layer. This plan introduces performance and cost optimizations to reduce redundant LLM calls and improve response latency.

The primary optimization is an in-memory TTL cache for both query embeddings and full RAG results. Repeated queries hit the cache, bypassing embedding generation, vector search, document grading, and answer generation entirely. This is expected to reduce costs by 40-60% and latency by ~30% on repeated queries.

Parallel document grading uses a thread pool executor to score multiple jobs concurrently, reducing the grading phase latency. Cost tracking per query enables usage analysis and identification of expensive query patterns.

A Streamlit monitoring dashboard provides real-time visibility into query volume, latency trends, cost accumulation, cache hit rates, guardrail block events, and RAG quality scores.

---

## [Architecture]

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PERFORMANCE & COST LAYER                                                    │
│ ─────────────────────────────────────────────────────────────────────────── │
│                                                                             │
│  Caching (genai/cache.py)                                                   │
│  ├── Query result cache → TTLCache (maxsize=200, ttl=3600s)               │
│  ├── Embedding cache → TTLCache (maxsize=400, ttl=3600s)                  │
│  └── CacheMiddleware → FastAPI intercept for /v1/chat, /v1/search         │
│                                                                             │
│  Parallel Grading (genai/grading_parallel.py)                              │
│  └── ThreadPoolExecutor (max_workers=5) for concurrent doc scoring        │
│                                                                             │
│  Cost Tracking                                                              │
│  ├── Per-query cost in metadata (USD)                                       │
│  ├── COST_PER_QUERY Prometheus metric                                       │
│  └── Aggregate cost reporting                                               │
│                                                                             │
│  Dashboard (dashboard/app.py + metrics_fetcher.py)                         │
│  ├── Overview: queries, latency, cost, cache hit rate                      │
│  ├── Guardrails: blocks by type                                            │
│  ├── RAG Quality: relevance trends, failed queries                         │
│  └── Top Queries: most searched terms                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## [Files]

Single sentence: 4 new files, 2 modified files.

### New Files

| File | Purpose |
|------|---------|
| `genai/cache_middleware.py` | FastAPI middleware: intercept requests → cache hit → short-circuit response |
| `dashboard/app.py` | Streamlit monitoring dashboard (overwrites existing skeleton) |
| `dashboard/metrics_fetcher.py` | Fetch Prometheus metrics, Cloud Trace spans, PostgreSQL logs |

### Files from Plan 4B (RAG Pipeline)

| File | Source Plan | Purpose |
|------|-------------|---------|
| `genai/cache.py` | Plan 4B | TTLCache wrapper for query results + embedding cache |
| `genai/grading_parallel.py` | Plan 4B | Parallel document grading using asyncio/concurrent.futures |

### Modified Files

| File | Changes |
|------|---------|
| `genai/rag.py` | Add cache hit path; wrap `grade_documents()` with parallel executor; add cost tracking to metadata |
| `genai/observability.py` | Add CACHE_HIT_COUNT, CACHE_MISS_COUNT, COST_PER_QUERY metrics |

---

## [Cache Design]

### QueryCache Class

```python
from cachetools import TTLCache

class QueryCache:
    """Thread-safe TTL cache for RAG query results and embeddings."""
    
    def __init__(self, maxsize: int = 200, ttl_seconds: int = 3600):
        self._result_cache = TTLCache(maxsize=maxsize, ttl=ttl_seconds)
        self._embedding_cache = TTLCache(maxsize=maxsize * 2, ttl=ttl_seconds)
    
    def get_result(self, query: str) -> Optional[Dict[str, Any]]
    def set_result(self, query: str, result: Dict[str, Any], cost_usd: float)
    def get_embedding(self, query: str) -> Optional[List[float]]
    def set_embedding(self, query: str, embedding: List[float])
    def get_stats(self) -> Dict[str, int]  # hits, misses, size
```

### CacheMiddleware

- Intercepts `/v1/chat` and `/v1/search` requests
- Normalizes query text for consistent cache keys
- Cache hit → returns cached JSONResponse immediately
- Cache miss → proceeds to endpoint, caches valid 200 responses on way out
- Skips cache for admin endpoints and non-standard methods

---

## [Parallel Grading]

```python
def grade_documents_parallel(
    query: str,
    documents: List[Dict[str, Any]],
    threshold: float = 5.0,
    max_workers: int = 5
) -> List[Dict[str, Any]]:
    """Grade documents concurrently using ThreadPoolExecutor.
    Returns sorted filtered docs."""
```

- Configurable via `use_parallel` flag in `grade_documents()`
- Falls back to sequential if parallel fails
- Produces identical results to sequential grading

---

## [Cost Tracking]

- Each LLM call records cost in USD
- `COST_PER_QUERY` metric aggregates per RAG pipeline execution
- Metadata returned with every response includes:
  - `cost_usd`: Total cost for this query
  - `latency_ms`: Total execution time
  - `provider`: Which LLM provider was used

---

## [Dashboard]

### Pages

| Page | Widgets |
|------|---------|
| **Overview** | Queries today, avg latency, cost today, cache hit rate |
| **Guardrails** | Blocks by type (PII, injection, semantic) |
| **RAG Quality** | Avg relevance score trend, top failed queries |
| **Top Queries** | Most searched terms, repeated queries |

### Data Sources

| Source | Data |
|--------|------|
| `/metrics` endpoint | Prometheus metrics (requests, latency, cost, cache) |
| Cloud Trace | Distributed trace spans |
| PostgreSQL logs | Recent requests with latency and cost |

---

## [Dependencies]

| Package | Version | Purpose |
|---------|---------|---------|
| `cachetools` | `>=5.3.0` | In-memory TTLCache |
| `streamlit` | `>=1.30.0` | Monitoring dashboard |

---

## [Testing]

### Unit Tests

| File | Tests |
|------|-------|
| `tests/test_cache.py` | TTL expiry, hit/miss, embedding cache, thread safety, maxsize eviction |
| `tests/test_grading_parallel.py` | Parallel vs sequential grading produces same results |

### Manual / Smoke Tests

| Test | How |
|------|-----|
| Cache effectiveness | Run same query 3 times → 1st miss, 2nd/3rd hit; check /metrics for CACHE_HIT_COUNT |
| Cost tracking | Run benchmark query → check metadata.cost_usd is populated |
| Dashboard | `streamlit run dashboard/app.py` → verify all widgets load with live data |

---

## [Acceptance Criteria]

| Criterion | Target | How to Measure |
|-----------|--------|----------------|
| Cost reduction | ~40-60% vs baseline | Compare metadata.cost_usd before/after cache |
| Latency improvement | ~30% on repeated queries | Compare metadata.latency_ms |
| Cache hit rate | ≥ 20% on representative workload | Prometheus `CACHE_HIT_COUNT / (HIT + MISS)` |
| Parallel correctness | Identical results to sequential | `pytest tests/test_grading_parallel.py` |
| Dashboard loads | Live metrics in < 5 seconds | Manual `streamlit run dashboard/app.py` |
| Cache metrics accurate | HIT/MISS counts match actual behavior | Cache test + metrics check |

---

*Document version: 1.0*
