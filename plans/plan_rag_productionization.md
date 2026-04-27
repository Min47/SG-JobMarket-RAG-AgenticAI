# Implementation Plan: RAG Productionization & Quality Assurance

> **Project:** SG Job Market Intelligence Platform
> **Date:** April 2026
> **Status:** Approved for Execution
> **Scope:** Testing & Evaluation, Performance & Cost Optimization, Guardrails Enhancement, Observability & Alerting

---

## [Overview]

Single sentence: Harden the production GenAI RAG pipeline with systematic evaluation, cost-efficient caching, future-proof guardrails, and a real-time monitoring dashboard.

Multiple paragraphs:
The current Phase 2 GenAI stack is functionally complete but lacks production-grade quality assurance. Agent performance is measured anecdotally ("13 tests passing") rather than systematically. Gemini API costs run ~$88/month with no caching layer. Guardrails are regex-only with no semantic fallback. Observability emits metrics but has no alerting or dashboard.

This plan addresses four areas:
1. **Testing & Evaluation** — Build a 50-query golden test set with LLM-as-judge scoring (threshold ≥ 8.0/10), retrieval metrics (Recall@10, NDCG@10), and CI/CD regression gates.
2. **Performance & Cost** — Add TTL in-memory caching (query + embedding cache), parallelize document grading, track cost per query.
3. **Guardrails Enhancement** — Add semantic guardrail hooks, output content moderation, and per-user rate limit framework.
4. **Observability & Alerting** — Build a Streamlit monitoring dashboard for queries, latency, cost, cache hit rate, guardrail blocks, and RAG quality trends.

This work is scoped to the existing Phase 2 architecture (SBERT + BigQuery + Gemini). It does NOT include the Phase 3 embedding stack upgrade (bge-m3, Qdrant, PostgreSQL).

---

## [Types]

Single sentence: Three new data structures are introduced for evaluation caching and dashboard metrics.

Detailed type definitions:

```python
# tests/evaluation/golden_test_set.py
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

class QueryLanguage(Enum):
    ENGLISH = "en"
    CHINESE = "zh"
    MALAY = "ms"

class QueryCategory(Enum):
    JOB_SPECIFIC = "job_specific"      # e.g., "software engineer python"
    SALARY_BASED = "salary_based"      # e.g., "$5000 data scientist"
    VAGUE = "vague"                    # e.g., "good job"
    FILTERED = "filtered"              # e.g., "remote marketing manager"
    EDGE_CASE = "edge_case"            # abbreviations, typos, slang

@dataclass
class GoldenQuery:
    """Single golden test query with expected relevance criteria."""
    query_id: str
    query_text: str
    language: QueryLanguage
    category: QueryCategory
    # Flexible relevance criteria — at least one must match
    must_contain_keywords: List[str] = field(default_factory=list)
    must_contain_classifications: List[str] = field(default_factory=list)
    must_not_contain_keywords: List[str] = field(default_factory=list)
    # Optional: exact job_ids known to be relevant (for Recall@N)
    expected_job_ids: List[str] = field(default_factory=list)
    # Optional: expected top-N classification distribution
    expected_classification: Optional[str] = None
    notes: str = ""

@dataclass
class EvaluationResult:
    """Result of evaluating a single golden query through the RAG pipeline."""
    query: GoldenQuery
    retrieved_jobs: List[Dict[str, Any]]
    graded_jobs: List[Dict[str, Any]]
    generated_answer: str
    # Metrics
    retrieval_recall_at_10: float        # What % of expected jobs are in top 10?
    ndcg_at_10: float                    # Normalized Discounted Cumulative Gain
    avg_relevance_score: float           # Average LLM grade of top 10
    answer_relevance_score: float        # LLM-as-judge: 0-10
    latency_ms: int
    cost_usd: float
    # Pass/Fail
    passed: bool
    failure_reasons: List[str] = field(default_factory=list)

@dataclass
class CacheEntry:
    """Entry in the in-memory TTL cache."""
    query: str
    result: Dict[str, Any]
    embedding: Optional[List[float]]
    created_at: float                    # Unix timestamp
    hit_count: int = 0
```

---

## [Files]

Single sentence: 12 new files, 7 modified files, 1 new config file.

### New Files

| File | Purpose |
|------|---------|
| `tests/evaluation/golden_queries.json` | 50 curated golden test queries with expected relevance criteria |
| `tests/evaluation/test_golden_set.py` | Pytest suite: run golden queries through RAG → output evaluation report |
| `tests/evaluation/evaluator.py` | Core evaluation logic: Recall@10, NDCG@10, LLM-as-judge scorer |
| `tests/evaluation/metrics.py` | Metric computation: recall, NDCG, precision, MAP |
| `genai/cache.py` | TTLCache wrapper for query results + embedding cache |
| `genai/cache_middleware.py` | FastAPI middleware: intercept requests → cache hit → short-circuit response |
| `genai/guardrails_semantic.py` | Semantic guardrail hooks + output content moderation |
| `genai/grading_parallel.py` | Parallel document grading using asyncio/concurrent.futures |
| `dashboard/app.py` | Streamlit monitoring dashboard (overwrites existing skeleton) |
| `dashboard/metrics_fetcher.py` | Fetch Prometheus metrics, Cloud Trace spans, BigQuery logs |
| `.github/workflows/ci.yml` | GitHub Actions: run golden tests + unit tests on PR |
| `docs/RAG_PRODUCTIONIZATION.md` | Architecture documentation for this upgrade |

### Modified Files

| File | Changes |
|------|---------|
| `genai/rag.py` | Add cache hit path via `genai.cache`; wrap `grade_documents()` with parallel executor; add cost tracking to metadata |
| `genai/api.py` | Add `CacheMiddleware`; add new `/v1/evaluate` admin endpoint for running golden tests; per-user rate limit framework |
| `genai/guardrails.py` | Call semantic guardrail hooks after regex checks; add output content moderation step |
| `genai/observability.py` | Add CACHE_HIT_COUNT, CACHE_MISS_COUNT, COST_PER_QUERY, RAG_AVG_RELEVANCE metrics; add cost tracking |
| `requirements.txt` | Add `cachetools>=5.3`, `streamlit>=1.30`, `pytest-asyncio>=0.21` |
| `requirements-api.txt` | Add `cachetools>=5.3` |
| `.github/agents/04_ml_engineer.agent.md` | Update Phase Status: mark new evaluation/performance work as IN PROGRESS |

### Deleted / Not touched
- Phase 3 embedding stack upgrade files remain unchanged
- ML training pipeline (`ml/`) remains deferred
- MCP server integration unchanged

---

## [Functions]

Single sentence: 10 new functions, 4 modified functions, 1 removed function.

### New Functions

```python
# tests/evaluation/evaluator.py
def run_golden_query(query: GoldenQuery, rag_pipeline) -> EvaluationResult:
    """Run a single golden query through the full RAG pipeline and compute metrics."""

def compute_recall_at_k(retrieved_jobs: List[Dict], expected_job_ids: List[str], k: int = 10) -> float:
    """Compute Recall@K: what fraction of expected jobs appear in top-K results."""

def compute_ndcg_at_k(relevance_scores: List[float], k: int = 10) -> float:
    """Compute Normalized Discounted Cumulative Gain at K."""

def llm_judge_answer_relevance(query: str, answer: str, context_jobs: List[Dict]) -> Dict[str, float]:
    """Use Gemini to score answer relevance 0-10 and flag hallucinations. Returns {score, explanation}."""

def generate_evaluation_report(results: List[EvaluationResult]) -> Dict[str, Any]:
    """Aggregate results into a pass/fail report with per-category breakdown."""

# genai/cache.py
def get_cached_result(query: str) -> Optional[Dict[str, Any]]:
    """Check TTL cache for query result. Returns cached response or None."""

def set_cached_result(query: str, result: Dict[str, Any], embedding: Optional[List[float]] = None) -> None:
    """Store query result in TTL cache with 60-minute expiry."""

def get_cached_embedding(query: str) -> Optional[List[float]]:
    """Check cache for pre-computed query embedding."""

# genai/grading_parallel.py
def grade_documents_parallel(
    query: str,
    documents: List[Dict[str, Any]],
    threshold: float = 5.0,
    max_workers: int = 5
) -> List[Dict[str, Any]]:
    """Grade documents concurrently using ThreadPoolExecutor. Returns sorted filtered docs."""

# genai/guardrails_semantic.py
def semantic_input_check(query: str) -> Optional[str]:
    """Placeholder semantic guardrail: checks intent beyond regex patterns. Returns violation type or None."""

def moderate_output(answer: str) -> Dict[str, Any]:
    """Lightweight keyword-based output moderation. Returns {safe: bool, flagged_categories: List[str]}."""

# dashboard/metrics_fetcher.py
def fetch_prometheus_metrics(url: str) -> Dict[str, float]:
    """Scrape /metrics endpoint for current request/latency/cost/guardrail metrics."""

def fetch_recent_queries(bq_client, limit: int = 100) -> List[Dict]:
    """Query BigQuery log table for recent requests with latency and cost."""
```

### Modified Functions

```python
# genai/rag.py — grade_documents()
def grade_documents(
    query: str,
    documents: List[Dict[str, Any]],
    threshold: float = 5.0,
    settings: Optional[Settings] = None,
    use_parallel: bool = True,          # NEW parameter
) -> List[Dict[str, Any]]:
    """Add use_parallel flag. If True, delegate to grade_documents_parallel()."""

# genai/rag.py — embed_query()
def embed_query(
    query: str,
    settings: Optional[Settings] = None,
) -> List[float]:
    """Before generating, check get_cached_embedding(). If hit, return cached embedding."""

# genai/rag.py — rag_pipeline()
def rag_pipeline(
    query: str,
    top_k: int = 10,
    filters: Optional[Dict[str, Any]] = None,
    settings: Optional[Settings] = None,
    use_cache: bool = True,             # NEW parameter
) -> Dict[str, Any]:
    """Before retrieve → check get_cached_result(). If hit, return cached response + mark in metadata.
    After generate → call set_cached_result() for cache miss."""

# genai/api.py — app initialization
# Add CacheMiddleware to FastAPI app:
app.add_middleware(CacheMiddleware)
# Add admin evaluate endpoint:
@app.post("/admin/evaluate", tags=["Admin"])
async def run_evaluation(admin_key: str = Header(...)) -> Dict[str, Any]:
    """Run full golden test suite. Protected by admin API key."""
```

### Removed Functions

None.

---

## [Classes]

Single sentence: 4 new classes, 2 modified classes.

### New Classes

```python
# genai/cache.py
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

# genai/cache_middleware.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class CacheMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware: intercept /v1/chat and /v1/search requests.
    Cache hit → returns cached JSONResponse immediately.
    Cache miss → proceeds to endpoint, caches response on way out."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip cache for non-GET/POST or admin endpoints
        # Normalize query text for cache key
        # On miss: capture response, cache valid 200 responses only

# genai/guardrails_semantic.py
class SemanticGuardrails:
    """Future-proof semantic guardrail layer.
    Currently uses lightweight heuristics + keyword fallback.
    Can be swapped for LLM-based or enterprise guardrail API later."""
    
    def check_input_intent(self, query: str) -> Optional[str]
    def check_output_safety(self, text: str) -> Dict[str, Any]
    def check_rate_limit(self, user_id: str, endpoint: str) -> bool

# tests/evaluation/evaluator.py
class RAGEvaluator:
    """Orchestrates golden test evaluation: runs queries, computes metrics, judges answers."""
    
    def __init__(self, golden_queries: List[GoldenQuery])
    def evaluate_single(self, query: GoldenQuery) -> EvaluationResult
    def evaluate_all(self) -> List[EvaluationResult]
    def generate_report(self) -> Dict[str, Any]
```

### Modified Classes

```python
# genai/guardrails.py — InputGuardrails
class InputGuardrails:
    """Add semantic check after existing regex checks."""
    
    def validate(self, query: str) -> ValidationResult:
        # Existing: regex PII, injection, length checks
        # NEW: call SemanticGuardrails.check_input_intent()
        # NEW: call SemanticGuardrails.check_rate_limit()

# genai/guardrails.py — OutputGuardrails
class OutputGuardrails:
    """Add output moderation after hallucination check."""
    
    def validate(self, answer: str, context_jobs: List[Dict]) -> ValidationResult:
        # Existing: hallucination, empty, length checks
        # NEW: call SemanticGuardrails.check_output_safety()
```

---

## [Dependencies]

Single sentence: Add 3 new Python packages; no version conflicts expected.

| Package | Version | Purpose |
|---------|---------|---------|
| `cachetools` | `>=5.3.0` | In-memory TTLCache for query + embedding caching |
| `streamlit` | `>=1.30.0` | Monitoring dashboard |
| `pytest-asyncio` | `>=0.21.0` | Async test support for parallel grading tests |

No dependency conflicts:
- `cachetools` is lightweight (pure Python), does not conflict with FastAPI/LangGraph
- `streamlit` is self-contained for dashboard only
- `pytest-asyncio` is dev-only dependency

Installation:
```bash
pip install cachetools==5.3.3 streamlit==1.32.0 pytest-asyncio==0.23.5
```

---

## [Testing]

Single sentence: Three test layers: unit tests for cache/metrics, integration tests for evaluation, CI gate.

### Unit Tests (new)

| File | Tests |
|------|-------|
| `tests/test_cache.py` | TTL expiry, hit/miss, embedding cache, thread safety, maxsize eviction |
| `tests/test_metrics.py` | Recall@K, NDCG@K computation with known inputs |
| `tests/test_guardrails_semantic.py` | Intent check, output moderation, rate limit |
| `tests/test_grading_parallel.py` | Parallel vs sequential grading produces same results |

### Integration / Evaluation Tests

| File | Tests |
|------|-------|
| `tests/evaluation/test_golden_set.py` | Run all 50 golden queries, assert ≥ 80% pass rate (40/50) |
| `tests/evaluation/test_evaluator.py` | LLM judge scoring consistency, metric computation |

### Manual / Smoke Tests

| Test | How |
|------|-----|
| Cache effectiveness | Run same query 3 times → 1st miss, 2nd/3rd hit; check /metrics for CACHE_HIT_COUNT |
| Cost tracking | Run benchmark query → check metadata.cost_usd is populated |
| Dashboard | `streamlit run dashboard/app.py` → verify all widgets load with live data |
| CI | Open a PR → verify GitHub Actions runs all tests, blocks merge if golden tests fail |

### Regression Tests

Run existing test suite to ensure no breakage:
```bash
pytest tests/genai/ --tb=short -q
```
Expected: All 13 existing tests still pass (12 fully + 1 minor JSON parse issue unchanged).

---

## [Implementation Order]

Single sentence: Sequential phases to minimize conflicts and validate each layer before the next.

### Phase A: Testing & Evaluation Framework

1. **Design golden test set**
   - Create `tests/evaluation/golden_queries.json` with 50 queries
   - Categories: 30 English job-specific, 10 Chinese, 5 Malay, 5 edge cases
   - Define `GoldenQuery` schema and relevance criteria

2. **Build evaluation engine**
   - Create `tests/evaluation/metrics.py` — Recall@K, NDCG@K, MAP
   - Create `tests/evaluation/evaluator.py` — `RAGEvaluator` class
   - Implement `llm_judge_answer_relevance()` using Gemini via ModelGateway
   - Set PASS threshold: avg_relevance_score ≥ 8.0

3. **Write evaluation tests**
   - Create `tests/evaluation/test_evaluator.py`
   - Create `tests/evaluation/test_golden_set.py`
   - Run manually, tune queries until ≥ 80% (40/50) pass rate

### Phase B: Performance & Cost Optimization

4. **Add in-memory caching**
   - Create `genai/cache.py` with `QueryCache` (TTLCache)
   - Modify `genai/rag.py` — `embed_query()` checks embedding cache
   - Modify `genai/rag.py` — `rag_pipeline()` checks result cache, stores on miss
   - Create `genai/cache_middleware.py` — `CacheMiddleware` for FastAPI
   - Modify `genai/api.py` — register middleware; skip cache for admin endpoints
   - Add metrics: `CACHE_HIT_COUNT`, `CACHE_MISS_COUNT`, `COST_PER_QUERY`

5. **Parallelize document grading**
   - Create `genai/grading_parallel.py` with `grade_documents_parallel()`
   - Modify `genai/rag.py` — `grade_documents()` delegates to parallel when `use_parallel=True`
   - Test: parallel vs sequential produce identical results

6. **Validate cost reduction**
   - Before benchmark: run 20 repeated queries, record cost/latency
   - After benchmark: same 20 queries, verify ~40-60% cost reduction, ~30% latency reduction

### Phase C: Guardrails Enhancement

7. **Add semantic guardrail hooks**
   - Create `genai/guardrails_semantic.py` with `SemanticGuardrails` class
   - Implement placeholder `check_input_intent()` — lightweight keyword fallback
   - Implement `check_output_safety()` — toxicity keyword list
   - Implement `check_rate_limit()` — per-user token bucket (in-memory)

8. **Integrate into existing guardrails**
   - Modify `genai/guardrails.py` — `InputGuardrails.validate()` calls semantic checks after regex
   - Modify `genai/guardrails.py` — `OutputGuardrails.validate()` calls output moderation
   - Add `GUARDRAIL_SEMANTIC_BLOCKS` metric

### Phase D: Observability & Alerting Dashboard

9. **Build Streamlit dashboard**
   - Create `dashboard/app.py` — multi-page Streamlit app
   - Create `dashboard/metrics_fetcher.py` — fetch from /metrics, BigQuery logs
   - Pages:
     - Overview: queries today, avg latency, cost today, cache hit rate
     - Guardrails: blocks by type (PII, injection, semantic)
     - RAG Quality: avg relevance score trend, top failed queries
     - Top Queries: most searched terms, repeated queries

10. **Add CI/CD regression gate**
    - Create `.github/workflows/ci.yml`
    - Steps: checkout → install deps → run `pytest tests/genai/` → run `pytest tests/evaluation/`
    - Block merge if any test fails or if golden test pass rate < 80%

11. **Documentation & agent file updates**
    - Create `docs/RAG_PRODUCTIONIZATION.md`
    - Update `.github/agents/04_ml_engineer.agent.md` with new Phase 2.x status
    - Update `.github/agents/skills/04_p2_6_genai_testing_results.md` with testing docs
    - Update `.github/agents/skills/04_p2_4_observability_reference.md` with dashboard docs

### Final Validation

12. **Run full regression suite**
    ```bash
    pytest tests/ --tb=short -q
    ```
    Expected: All existing 13 genai tests pass + new cache/performance tests pass + golden tests ≥ 80% pass.

---

## Acceptance Criteria

| Criterion | Target | How to Measure |
|-----------|--------|----------------|
| Golden test pass rate | ≥ 80% (40/50 queries) | `pytest tests/evaluation/test_golden_set.py` |
| LLM judge threshold | Avg ≥ 8.0/10 | Report from evaluator |
| Cost reduction | ~40-60% vs baseline | Compare metadata.cost_usd before/after cache |
| Latency improvement | ~30% on repeated queries | Compare metadata.latency_ms |
| Cache hit rate | ≥ 20% on representative workload | Prometheus `CACHE_HIT_COUNT / (HIT + MISS)` |
| Regression | Zero breakage of existing 13 tests | `pytest tests/genai/` all green |
| Dashboard | Loads with live metrics in < 5s | Manual `streamlit run dashboard/app.py` |
| CI gate | Blocks merge on test failure | Open test PR with failing golden test |

---

*Document version: 1.0*
*Last updated: 2026-04-27*
*Next review: Post-Phase D completion*