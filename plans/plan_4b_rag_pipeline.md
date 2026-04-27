# Plan 4B: RAG Pipeline

> **Project:** SG Job Market Intelligence Platform
> **Focus:** Core Retrieval-Augmented Generation pipeline — query embedding, vector search, document grading, answer generation, caching, and parallel grading
> **Status:** Active

---

## [Overview]

Single sentence: Production-grade RAG pipeline for semantic job search with caching, parallel document grading, and structured answer generation.

Multiple paragraphs:
The RAG pipeline is the central intelligence layer of the GenAI stack. It transforms user queries into vector embeddings, retrieves relevant job listings via hybrid search, grades each result for relevance using an LLM, and synthesizes a cited answer.

The pipeline is built around four core operations: `embed_query()` for query vectorization, `retrieve_jobs()` for semantic retrieval from Qdrant Cloud, `grade_documents()` for LLM-based relevance scoring, and `generate_answer()` for contextual response synthesis. A `rag_pipeline()` function orchestrates these steps into a single entry point.

Performance optimizations include an in-memory TTL cache for both query embeddings and full query results, plus parallelized document grading using a thread pool executor. These reduce redundant LLM calls and improve latency on repeated or similar queries.

The current pipeline uses SBERT `all-MiniLM-L6-v2` (384-dim) embeddings with Qdrant Cloud. Plan 4A will upgrade to bge-m3 (1024-dim) with cross-encoder re-ranking.

---

## [Architecture]

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          USER QUERY                                         │
│                    "Find data scientist jobs with Python"                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ EMBED QUERY (genai/rag.py)                                                  │
│ ─────────────────────────────────────────────────────────────────────────── │
│ • SBERT all-MiniLM-L6-v2 → 384-dim embedding                                │
│ • L2-normalized for cosine similarity                                       │
│ • Singleton pattern to avoid model reload                                   │
│ • Input validation: empty, short (<3 chars), long (>1000 chars)             │
│ • Check embedding cache first (QueryCache)                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ RETRIEVE JOBS (genai/rag.py)                                                │
│ ─────────────────────────────────────────────────────────────────────────── │
│ • Qdrant Cloud hybrid search (vector + BM25)                               │
│ • Hybrid scoring: 70% vector similarity + 30% keyword matching              │
│ • Filters: location (LIKE), min/max salary, work_type, classification       │
│ • Deduplication via ROW_NUMBER() on append-only cleaned_jobs                │
│ • Returns: job metadata + vector_distance, keyword_score, hybrid_score      │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ GRADE DOCUMENTS (genai/rag.py / genai/grading_parallel.py)                  │
│ ─────────────────────────────────────────────────────────────────────────── │
│ • Gemini 2.5 Flash scores each job 0-10 for relevance                       │
│ • Threshold filtering (default ≥ 5.0)                                       │
│ • JSON parsing with regex fallback for malformed responses                  │
│ • Average score computed on ALL retrieved docs (before filtering)           │
│ • Re-ranks by relevance score descending                                    │
│ • Parallel execution via ThreadPoolExecutor (configurable)                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ GENERATE ANSWER (genai/rag.py)                                              │
│ ─────────────────────────────────────────────────────────────────────────── │
│ │ Context + Query → Gemini 2.5 Flash → Response                             │
│ │ Structured output with citations [1], [2], etc.                           │
│ │ Empty context handling with graceful error message                        │
│ │ Response truncated to 4096 chars safety limit                             │
│ │ Cost and latency metadata returned                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ MODEL GATEWAY (genai/gateway.py)                                            │
│ ─────────────────────────────────────────────────────────────────────────── │
│ Vertex AI Gemini 2.5 Flash (default) → fallback → Ollama deepseek-r1:8b    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## [Files]

Single sentence: 2 new files, 1 modified file.

### New Files

| File | Purpose |
|------|---------|
| `genai/cache.py` | TTLCache wrapper for query results + embedding cache |
| `genai/grading_parallel.py` | Parallel document grading using asyncio/concurrent.futures |

### Modified Files

| File | Changes |
|------|---------|
| `genai/rag.py` | Add cache hit path via `genai.cache`; wrap `grade_documents()` with parallel executor; add cost tracking to metadata |

---

## [Functions]

Single sentence: 7 new functions, 3 modified functions.

### Modified Functions

```python
# genai/rag.py — embed_query()
def embed_query(
    query: str,
    settings: Optional[Settings] = None,
) -> List[float]:
    """Before generating, check get_cached_embedding(). If hit, return cached embedding."""

# genai/rag.py — grade_documents()
def grade_documents(
    query: str,
    documents: List[Dict[str, Any]],
    threshold: float = 5.0,
    settings: Optional[Settings] = None,
    use_parallel: bool = True,          # NEW parameter
) -> List[Dict[str, Any]]:
    """Add use_parallel flag. If True, delegate to grade_documents_parallel()."""

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
```

### New Functions

```python
# genai/cache.py
def get_cached_result(query: str) -> Optional[Dict[str, Any]]:
    """Check TTL cache for query result. Returns cached response or None."""

def set_cached_result(query: str, result: Dict[str, Any], embedding: Optional[List[float]] = None) -> None:
    """Store query result in TTL cache with configurable expiry."""

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
```

---

## [Classes]

Single sentence: 1 new class.

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
```

---

## [Dependencies]

Single sentence: Add 1 new Python package.

| Package | Version | Purpose |
|---------|---------|---------|
| `cachetools` | `>=5.3.0` | In-memory TTLCache for query + embedding caching |

Installation:
```bash
pip install cachetools==5.3.3
```

---

## [Integration with Plan 4A]

When the embedding stack is upgraded (see `plan_4a_embedding_stack.md`), the RAG pipeline will incorporate the following changes:

| Component | Current | After 4A Upgrade |
|-----------|---------|------------------|
| **Vector Search** | Qdrant Cloud hybrid search | Qdrant Cloud hybrid search |
| **Re-ranking** | None (grading only) | `bge-reranker-v2-m3` cross-encoder before grading |
| **Query Preprocessing** | None | Gated query standardization (Gemini 2.5 Flash) |
| **Document Context** | Whole job description | 5 extracted sections per job |
| **Filters** | Qdrant payload filters + PostgreSQL metadata | Qdrant payload filters + PostgreSQL metadata |
| **Embedding Dimensions** | 384 | 1024 |

Modified files for 4A integration:
- `genai/rag.py` — Insert `rerank_documents()` between retrieve and grade; update `retrieve_jobs()` for Qdrant
- `genai/agent.py` — Add query standardization gate node; update LangGraph edges
- `genai/api.py` — Add query standardization trigger; update response models

---

## [Testing]

Single sentence: Unit tests for cache behavior and parallel grading correctness.

### Unit Tests

| File | Tests |
|------|-------|
| `tests/test_cache.py` | TTL expiry, hit/miss, embedding cache, thread safety, maxsize eviction |
| `tests/test_grading_parallel.py` | Parallel vs sequential grading produces same results |

### Regression Tests

Run existing test suite to ensure no breakage:
```bash
pytest tests/genai/ --tb=short -q
```
Expected: All 13 existing tests still pass.

---

## [Acceptance Criteria]

| Criterion | Target | How to Measure |
|-----------|--------|----------------|
| Cache hit rate | ≥ 20% on representative workload | Prometheus `CACHE_HIT_COUNT / (HIT + MISS)` |
| Parallel grading correctness | Identical results to sequential | `pytest tests/test_grading_parallel.py` |
| Regression | Zero breakage of existing 13 tests | `pytest tests/genai/` all green |
| Embedding cache | Query embeddings cached and reused | Manual verification via cache stats |
| Result cache | Full RAG results cached and returned | Manual verification via cache stats |

---

*Document version: 1.0*
