# Plan 4A: Embedding Stack Upgrade

> **Project:** SG Job Market Intelligence Platform
> **Focus:** Embedding stack using bge-m3 (1024-dim) + Qdrant Cloud + PostgreSQL with section extraction and cross-encoder re-ranking
> **Status:** Approved for Execution

---

## [Overview]

Single sentence: Upgrade the embedding stack to a multilingual-optimized, production-grade architecture with 5-section semantic chunking, hybrid search, and cross-encoder re-ranking.

Multiple paragraphs:
This plan establishes the embedding stack using `bge-m3` (1024-dim) with Qdrant Cloud for vector storage, Cloud SQL PostgreSQL for structured metadata, and `bge-reranker-v2-m3` for cross-encoder re-ranking.

Key changes:
- **Embedding model**: `bge-m3` (1024-dim)
- **Vector database**: Qdrant Cloud with hybrid search (vector + BM25)
- **Structured storage**: Cloud SQL PostgreSQL with 30-day active listings window
- **Preprocessing**: Whole-job embedding → 5-section semantic chunking via Gemini 2.5 Flash
- **Re-ranking**: None → `bge-reranker-v2-m3` cross-encoder before document grading
- **Query standardization**: None → gated query rephrasing via Gemini 2.5 Flash

Each job produces 5 vectors (one per section: summary, responsibilities, requirements, benefits, metadata). Qdrant stores these with payload metadata for filtering. PostgreSQL maintains the structured job data and 30-day active window.

---

## [Architecture]

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              SCRAPED JOB DATA                                       │
│                    (MCF + JobStreet raw HTML descriptions)                          │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ ETL: SECTION EXTRACTION (Cloud Run Job)                                             │
│ ─────────────────────────────────────────────────────────────────────────────────── │
│ Gemini 2.5 Flash → Extract 5 sections from raw HTML:                                │
│   • summary (role overview)                                                         │
│   • responsibilities (day-to-day tasks)                                             │
│   • requirements (skills, qualifications)                                           │
│   • benefits (compensation, perks)                                                  │
│   • metadata (company, application instructions)                                    │
│ Output: Clean JSON per job → stored in Cloud SQL PostgreSQL                         │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ ETL: EMBEDDING PIPELINE (Cloud Run Job, Daily Incremental)                          │
│ ─────────────────────────────────────────────────────────────────────────────────── │
│ bge-m3 (bi-encoder) → Embed each of 5 sections per job                              │
│   • 1024-dim vectors per section                                                    │
│   • L2 normalization for cosine similarity                                          │
│   • Batch size: 32 sections per forward pass                                        │
│ Output: Vectors + metadata → Qdrant Cloud                                           │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ QUERY TIME: USER SEARCH                                                             │
│ ─────────────────────────────────────────────────────────────────────────────────── │
│ User: "I want a gd data science job wfh"                                            │
│        │                                                                            │
│        ▼                                                                            │
│   [Gate] should_rephrase()? → YES (abbreviations detected)                          │
│        │                                                                            │
│        ▼                                                                            │
│   Gemini 2.5 Flash → "Remote data science jobs in Singapore"                        │
│        │                                                                            │
│        ▼                                                                            │
│   bge-m3 → Embed standardized query (1024-dim)                                    │
│        │                                                                            │
│        ▼                                                                            │
│   Qdrant → Hybrid Search (vector + keyword) → Top 50 candidates                     │
│        │                                                                            │
│        ▼                                                                            │
│   bge-reranker-v2-m3 → Score [query + section] pairs → Top 10                     │
│        │                                                                            │
│        ▼                                                                            │
│   Gemini 2.5 Flash → Grade documents (0-10 relevance) → Filter < 5.0                │
│        │                                                                            │
│        ▼ (if avg score < 5.0)                                                      │
│   Gemini 2.5 Flash → Rewrite query → Retry loop (max 2 retries)                     │
│        │                                                                            │
│        ▼                                                                            │
│   Gemini 2.5 Flash → Generate answer with citations [1], [2], ...                   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                    GCP CLOUD                                        │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────────────┐  │
│  │   Cloud Run     │    │   Cloud Run     │    │         Cloud SQL               │  │
│  │  (GenAI API)    │    │ (Embed Pipeline)│    │      (PostgreSQL)               │  │
│  │                 │    │                 │    │                                 │  │
│  │ • RAG endpoint  │    │ • bge-m3        │    │ • cleaned_jobs table            │  │
│  │ • Agent logic   │    │ • Section embed │    │ • 5 section columns             │  │
│  │ • Gateway       │    │ • Qdrant upload │    │ • Metadata + filters            │  │
│  │ • Guardrails    │    │                 │    │ • 30-day active window          │  │
│  └────────┬────────┘    └────────┬────────┘    └─────────────────────────────────┘  │
│           │                      │                                                    │
│           │                      │                                                    │
│           ▼                      ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────┐                     │
│  │                     QDRANT CLOUD (AWS)                      │                     │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │                     │
│  │  │ Collection:     │  │ Collection:     │  │ Collection: │ │                     │
│  │  │  sg_job_market  │  │  sg_healthcare  │  │  sg_finance │ │                     │
│  │  │  (production)   │  │  (future)       │  │  (future)   │ │                     │
│  │  │                 │  │                 │  │             │ │                     │
│  │  │ • 1024-dim      │  │ • 1024-dim      │  │ • 1024-dim  │ │                     │
│  │  │ • HNSW index    │  │ • HNSW index    │  │ • HNSW index│ │                     │
│  │  │ • BM25 payload  │  │ • BM25 payload  │  │ • BM25 payload│ │                   │
│  │  │ • COSINE dist   │  │ • COSINE dist   │  │ • COSINE dist│  │                   │
│  │  │ • 60-day TTL    │  │ • 60-day TTL    │  │ • 60-day TTL│ │                     │
│  │  └─────────────────┘  └─────────────────┘  └─────────────┘ │                     │
│  └─────────────────────────────────────────────────────────────┘                     │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐                     │
│  │              VERTEX AI (Google Cloud)                       │                     │
│  │         Gemini 2.5 Flash (all LLM tasks)                    │                     │
│  │  • Section extraction   • Query rephrase   • Grading        │                     │
│  │  • Query rewrite        • Answer generation                 │                     │
│  └─────────────────────────────────────────────────────────────┘                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## [Key Decisions]

| Component | From | To | Rationale |
|-----------|------|-----|-----------|
| **Embedding Model** | `bge-m3` (1024-dim) | SOTA multilingual, MIT license, handles Chinese natively |
| **Vector Database** | **Qdrant Cloud** | <50ms queries, hybrid search, domain collections |
| **Structured Storage** | **Cloud SQL PostgreSQL** | Metadata, filters, active listings 30-day window |
| **Compute** | GCP Cloud Run | **GCP Cloud Run** (retained) | Existing infrastructure, pay-per-use |
| **Preprocessing** | None (whole-job embedding) | **5-section semantic chunking** | Preserves structure, improves retrieval relevance |
| **Re-ranking** | None | **bge-reranker-v2-m3** | +15-25% NDCG@10, eliminates false positives |
| **Section Extraction** | N/A | **Gemini 2.5 Flash (all jobs)** | Handles messy HTML consistently |
| **Query Standardization** | None | **Gemini 2.5 Flash (gated)** | Expands abbreviations, normalizes slang |
| **Query Rewrite** | Gemini 2.5 Flash | **Gemini 2.5 Flash** (retained) | Already optimal, no change |
| **Document Grading** | Gemini 2.5 Flash | **Gemini 2.5 Flash** (retained) | Already optimal, no change |
| **Answer Generation** | Gemini 2.5 Flash | **Gemini 2.5 Flash** (retained) | Already optimal, no change |

---

## [Files]

Single sentence: 5 new files, 5 modified files, 2 new deployment configs.

### New Files

| File | Purpose |
|------|---------|
| `nlp/section_extractor.py` | Section extraction with Gemini 2.5 Flash |
| `utils/qdrant_client.py` | Qdrant connection and operations wrapper |
| `nlp/chunking.py` | 5-section chunking logic |
| `nlp/reranker.py` | Cross-encoder re-ranking module with bge-reranker-v2-m3 |
| `tests/integration/test_end_to_end.py` | Full pipeline integration tests |

### Modified Files

| File | Changes |
|------|---------|
| `nlp/embeddings.py` | Swap `all-MiniLM-L6-v2` → `bge-m3` |
| `nlp/generate_embeddings.py` | Update pipeline for Qdrant target |
| `etl/transform.py` | Integrate section extraction into ETL pipeline |
| `utils/schemas.py` | Add `CleanedJob` fields for 5 sections |
| `genai/rag.py` | Insert `rerank_documents()` between retrieve and grade; update `retrieve_jobs()` for Qdrant |

### Deployment Files

| File | Purpose |
|------|---------|
| `Dockerfile.embeddings` | Add bge-m3 + reranker dependencies |
| `cloudbuild.embeddings.yaml` | Updated build pipeline with new packages |

---

## [Functions]

Single sentence: 4 new functions, 2 modified functions.

### New Functions

```python
# nlp/section_extractor.py
def extract_sections(description: str, max_retries: int = 3) -> Dict[str, str]:
    """Extract 5 sections from raw HTML job description using Gemini 2.5 Flash.
    Returns {summary, responsibilities, requirements, benefits, metadata}."""

# utils/qdrant_client.py
def search_hybrid(
    query_embedding: List[float],
    query_text: str,
    top_k: int = 50,
    filters: Optional[Dict] = None,
    hybrid_weight: float = 0.7
) -> List[Dict]:
    """Hybrid search: dense vector similarity + sparse BM25 keyword matching.
    Returns fused and ranked results."""

# nlp/reranker.py
def rerank_documents(
    query: str,
    documents: List[Dict],
    top_k: int = 10
) -> List[Dict]:
    """Score and re-rank documents using bge-reranker-v2-m3 cross-encoder.
    Returns top-k documents with rerank_score attached."""

# nlp/embeddings.py (bge-m3)
def embed_texts(texts: List[str], batch_size: int = 32) -> np.ndarray:
    """Generate L2-normalized bge-m3 embeddings with retrieval instruction prefix."""
```

### Modified Functions

```python
# genai/rag.py — retrieve_jobs()
def retrieve_jobs(
    query: str,
    top_k: int = 50,
    filters: Optional[Dict[str, Any]] = None,
    settings: Optional[Settings] = None,
) -> List[Dict[str, Any]]:
    """Qdrant hybrid search for semantic retrieval."""

# genai/rag.py — rag_pipeline()
def rag_pipeline(
    query: str,
    top_k: int = 10,
    filters: Optional[Dict[str, Any]] = None,
    settings: Optional[Settings] = None,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """Insert rerank_documents() between retrieve and grade."""
```

---

## [Classes]

Single sentence: 3 new classes.

### New Classes

```python
# nlp/section_extractor.py
class SectionExtractor:
    """Extracts 5 structured sections from raw job descriptions."""
    
    def extract(self, description: str) -> Dict[str, str]
    def validate_json(self, output: str) -> Dict[str, str]

# nlp/reranker.py
class Reranker:
    """Cross-encoder re-ranking with bge-reranker-v2-m3."""
    
    def __init__(self)
    def rerank(self, query: str, documents: List[Dict], top_k: int = 10) -> List[Dict]

# utils/qdrant_client.py
class QdrantClientWrapper:
    """Wrapper for Qdrant Cloud CRUD and search operations."""
    
    def search_dense(self, vector: List[float], limit: int, filters: Dict) -> List[Dict]
    def search_sparse(self, text: str, limit: int, filters: Dict) -> List[Dict]
    def upsert_batch(self, points: List[Dict]) -> None
```

---

## [Data Schemas]

### Cloud SQL PostgreSQL

```sql
CREATE TABLE cleaned_jobs (
    job_id VARCHAR(255) NOT NULL,
    source VARCHAR(50) NOT NULL,
    title VARCHAR(500) NOT NULL,
    company VARCHAR(500),
    location VARCHAR(255),
    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency VARCHAR(10) DEFAULT 'SGD',
    job_type VARCHAR(50),
    classification VARCHAR(100),
    work_type VARCHAR(50),
    employment_type VARCHAR(50),
    
    -- 5 extracted sections
    section_summary TEXT,
    section_responsibilities TEXT,
    section_requirements TEXT,
    section_benefits TEXT,
    section_metadata TEXT,
    
    -- Full description for fallback
    full_description TEXT,
    
    posted_at TIMESTAMP,
    scraped_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    
    PRIMARY KEY (source, job_id)
);

CREATE INDEX idx_cleaned_jobs_active_posted 
    ON cleaned_jobs(is_active, posted_at DESC);
CREATE INDEX idx_cleaned_jobs_classification 
    ON cleaned_jobs(classification) WHERE is_active = TRUE;
CREATE INDEX idx_cleaned_jobs_salary 
    ON cleaned_jobs(salary_min, salary_max) WHERE is_active = TRUE;

CREATE VIEW cleaned_jobs_active AS
SELECT * FROM cleaned_jobs
WHERE is_active = TRUE
  AND posted_at >= NOW() - INTERVAL '30 days';
```

### Qdrant Payload Schema

```python
# Each point represents ONE section of ONE job
qdrant_point = {
    "id": f"{source}:{job_id}:{section_type}",
    "vector": [0.123, -0.456, ...],  # 1024-dimensional float array
    "payload": {
        "job_id": "abc123",
        "source": "MCF",
        "section_type": "requirements",
        "title": "Data Scientist",
        "company": "GovTech",
        "location": "Singapore",
        "classification": "Information Technology",
        "salary_min": 6000,
        "salary_max": 9000,
        "work_type": "Full Time",
        "posted_at": "2026-04-15T00:00:00Z",
        "section_text": "Minimum 3 years experience in Python...",
    }
}
```

---

## [Dependencies]

Single sentence: Add 2 new Python packages.

| Package | Version | Purpose |
|---------|---------|---------|
| `qdrant-client` | `>=1.7.0` | Qdrant Cloud vector database client |
| `transformers` | `>=4.36.0` | bge-m3 and bge-reranker-v2-m3 models |

Installation:
```bash
pip install qdrant-client==1.7.0 transformers==4.36.0
```

---

## [Environment Variables]

```bash
# Qdrant
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-api-key
QDRANT_COLLECTION=sg_job_market

# PostgreSQL
POSTGRES_HOST=/cloudsql/sg-job-market:asia-southeast1:sg-job-market-db
POSTGRES_DB=jobmarket
POSTGRES_USER=embedding_service
POSTGRES_PASSWORD=[SECRET]

# Models
EMBEDDING_MODEL=BAAI/bge-m3
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
EMBEDDING_DIMENSIONS=1024

# GCP (existing)
GCP_PROJECT_ID=sg-job-market
GCP_REGION=asia-southeast1

# Vertex AI (existing)
VERTEX_AI_PROJECT=$GCP_PROJECT_ID
VERTEX_AI_LOCATION=asia-southeast1
```

---

## [Integration with Other Plans]

| Plan | Integration |
|------|-------------|
| **4B RAG Pipeline** | `retrieve_jobs()` uses Qdrant hybrid search; `rerank_documents()` inserted before grading |
| **4C LangGraph Agent** | Query standardization gate added as new node; LangGraph edges updated |
| **4F FastAPI/Gateway** | New endpoints for query standardization trigger; response models updated |
| **4G Testing** | Golden test set validates retrieval quality and answer relevance |

---

## [Testing]

Single sentence: Unit tests for each new module, integration tests for end-to-end flow, and golden test A/B comparison.

### Unit Tests

| File | Tests |
|------|-------|
| `tests/nlp/test_section_extractor.py` | JSON parsing, error handling, retry logic |
| `tests/nlp/test_bge_m3.py` | 1024-dim output, L2 norm, batch processing |
| `tests/utils/test_qdrant_client.py` | CRUD, search, filtering |
| `tests/nlp/test_reranker.py` | Score range, sorting, top-k |

### Integration Tests

| File | Validates |
|------|-----------|
| `tests/integration/test_end_to_end.py` | Query → standardize → embed → search → rerank → grade → generate |
| `tests/integration/test_embedding_pipeline.py` | Raw job → sections → Qdrant |
| `tests/genai/test_api_compat.py` | Old endpoints work with new backend |

### Golden Test Set

Create 50 representative queries:
- English queries (35): "software engineer Python", "marketing manager", "$5000 salary"
- Chinese queries (10): "数据科学家", "薪金优厚的工作"
- Malay queries (5): "kerja jurutera", "gaji tinggi"
- Edge cases (10): abbreviations, typos, vague requests, combined filters

Measure:
- Recall@10 (are relevant jobs in top 10?)
- NDCG@10 (are they ranked correctly?)
- Latency (p50, p95, p99)

---

## [Acceptance Criteria]

| Criterion | Target | How to Measure |
|-----------|--------|----------------|
| bge-m3 embedding | 1024-dim, L2-normalized | `tests/nlp/test_bge_m3.py` |
| Qdrant collection | Created with proper schema | `tests/utils/test_qdrant_client.py` |
| All jobs indexed | 5 sections each in Qdrant | Integration test |
| Hybrid search | Vector + BM25 returns results | Integration test |
| Re-ranker scores | Accurate on spot-check 20 queries | Manual verification |
| E2E latency | < 3 seconds | Integration test |
| Golden test pass | >= 80% pass rate | Golden test evaluation |
| Regression | All 13 genai tests passing | `pytest tests/genai/` |

---

## [Future Enhancements]

| Feature | Description |
|---------|-------------|
| Domain branching | Qdrant collections per industry (healthcare, finance) |
| Late chunking | Jina v3 late chunking for long descriptions |
| Sparse embeddings | SPLADE or BGE-M3 sparse vectors for keyword-heavy queries |
| Embedding compression | Matryoshka to store 256-dim + 512-dim + 1024-dim |
| A/B testing | Route 10% traffic to new model variants |
| Multi-vector per section | Multiple embeddings per section (mean, max, CLS) |

---

*Document version: 1.0*
