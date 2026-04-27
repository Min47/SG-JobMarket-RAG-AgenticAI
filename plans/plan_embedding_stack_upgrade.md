# Implementation Plan: Embedding Stack Upgrade

> **Project:** SG Job Market Intelligence Platform  
> **Date:** April 2026  
> **Status:** Approved for Execution

---

## 1. Executive Summary

This document details the upgrade of the embedding stack for the SG Job Market platform. The current 384-dim SBERT (`all-MiniLM-L6-v2`) + BigQuery VECTOR_SEARCH architecture is being replaced with a multilingual-optimized, production-grade stack designed for Singapore's bilingual (English/Chinese/Malay) job market.

### Key Decisions

| Component | From | To | Rationale |
|-----------|------|-----|-----------|
| **Embedding Model** | `all-MiniLM-L6-v2` (384-dim) | `bge-m3` (1024-dim) | SOTA multilingual, MIT license, handles Chinese natively |
| **Vector Database** | BigQuery VECTOR_SEARCH | **Qdrant Cloud** | <50ms queries, hybrid search, domain collections |
| **Structured Storage** | BigQuery | **Cloud SQL PostgreSQL** | Metadata, filters, active listings 30-day window |
| **Compute** | GCP Cloud Run | **GCP Cloud Run** (retained) | Existing infrastructure, pay-per-use |
| **Preprocessing** | None (whole-job embedding) | **5-section semantic chunking** | Preserves structure, improves retrieval relevance |
| **Re-ranking** | None | **bge-reranker-v2-m3** | +15-25% NDCG@10, eliminates false positives |
| **Section Extraction** | N/A | **Gemini 2.5 Flash (all jobs)** | Handles messy HTML consistently, $1.60/month |
| **Query Standardization** | None | **Gemini 2.5 Flash (gated)** | Expands abbreviations, normalizes slang |
| **Query Rewrite** | Gemini 2.5 Flash | **Gemini 2.5 Flash** (retained) | Already optimal, no change |
| **Document Grading** | Gemini 2.5 Flash | **Gemini 2.5 Flash** (retained) | Already optimal, no change |
| **Answer Generation** | Gemini 2.5 Flash | **Gemini 2.5 Flash** (retained) | Already optimal, no change |

---

## 2. Architecture Overview

### 2.1 High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              SCRAPED JOB DATA                                       │
│                    (MCF + JobStreet raw HTML descriptions)                          │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ ETL: Section Extraction (Cloud Run Job, Daily)                                      │
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
│ ETL: Embedding Pipeline (Cloud Run Job, Daily Incremental)                          │
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
│ QUERY TIME: User Search                                                             │
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
│        │                                                                            │
│        ▼                                                                            │
│   User receives structured response with cited job listings                         │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Diagram

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

## 3. Detailed Specifications

### 3.1 Preprocessing: Section Extraction

**Model:** Gemini 2.5 Flash (Vertex AI)  
**Trigger:** Every job during ETL  
**Latency:** ~100-200ms per job  
**Cost:** ~$1.60/month (200 jobs/day)

**Prompt Template:**
```
You are a job description parser. Extract exactly these 5 sections from the HTML job description below.
Return ONLY a valid JSON object with these exact keys. Use empty string "" if a section is missing.

Sections:
1. summary - Brief overview of the role and company (1-2 sentences)
2. responsibilities - What the employee will do day-to-day (bullet points if available)
3. requirements - Skills, qualifications, experience needed (bullet points if available)
4. benefits - Compensation, perks, work arrangements, insurance, leave policy
5. metadata - Company info, application instructions, disclaimers, EA license numbers

Rules:
- Strip all HTML tags, return plain text only
- Preserve Chinese characters and Malay phrases as-is
- Do NOT paraphrase — extract verbatim where possible
- If a section spans multiple HTML sections, concatenate them

Return format (strictly valid JSON):
{"summary": "...", "responsibilities": "...", "requirements": "...", "benefits": "...", "metadata": "..."}

Job Description:
{description}
```

**Output Schema (Cloud SQL PostgreSQL):**
```sql
CREATE TABLE cleaned_jobs (
    job_id VARCHAR(255) PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    title VARCHAR(500) NOT NULL,
    company VARCHAR(500),
    location VARCHAR(255),
    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency VARCHAR(10),
    job_type VARCHAR(50),
    classification VARCHAR(100),
    work_type VARCHAR(50),
    
    -- 5 extracted sections (NEW)
    section_summary TEXT,
    section_responsibilities TEXT,
    section_requirements TEXT,
    section_benefits TEXT,
    section_metadata TEXT,
    
    -- For backward compatibility
    full_description TEXT,
    
    posted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    
    UNIQUE(source, job_id)
);

CREATE INDEX idx_cleaned_jobs_active ON cleaned_jobs(is_active, posted_at);
CREATE INDEX idx_cleaned_jobs_source ON cleaned_jobs(source, job_id);
```

### 3.2 Embedding Model: bge-m3

**Model:** `BAAI/bge-m3` (HuggingFace)  
**Dimensions:** 1024  
**License:** MIT  
**Languages:** 100+ (including Chinese Simplified/Traditional, English, Malay)  
**Max Sequence Length:** 8192 tokens  
**Batch Size:** 32 (Cloud Run 4GB RAM)

**Implementation (`nlp/embeddings.py` replacement):**
```python
from sentence_transformers import SentenceTransformer
import torch
import numpy as np

class EmbeddingGenerator:
    MODEL_NAME = "BAAI/bge-m3"
    DIMENSIONS = 1024
    MAX_SEQ_LENGTH = 8192
    
    def __init__(self):
        self._model = None
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
    
    def _load_model(self):
        if self._model is None:
            self._model = SentenceTransformer(
                self.MODEL_NAME,
                device=self._device,
                trust_remote_code=True
            )
            self._model.max_seq_length = self.MAX_SEQ_LENGTH
        return self._model
    
    def embed_texts(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        """Generate L2-normalized embeddings for a list of texts."""
        model = self._load_model()
        # bge-m3 expects instructions for retrieval tasks
        instruction = "Represent this sentence for searching relevant passages: "
        texts_with_instruction = [instruction + t for t in texts]
        embeddings = model.encode(
            texts_with_instruction,
            batch_size=batch_size,
            normalize_embeddings=True,  # L2 normalize for cosine similarity
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return embeddings
```

**Section Embedding Strategy:**
Each job produces **5 vectors** (one per section):  
- `job_id` + `section_name` as point ID  
- Payload: `{job_id, source, section_type, title, company, location, salary, ...}`

### 3.3 Vector Database: Qdrant Cloud

**Provider:** Qdrant Cloud (managed, AWS-based)  
**Plan:** Free tier (1GB) → Starter ($25/month) as data grows  
**Region:** Singapore (asia-southeast1) or nearest  
**Latency Target:** <50ms p99 for vector search

**Configuration:**
```yaml
# qdrant_config.yaml
collection_name: "sg_job_market"
vectors:
  size: 1024
  distance: Cosine
  hnsw_config:
    m: 16              # Number of edges per node
    ef_construct: 100  # Build-time search depth
    ef: 128            # Query-time search depth (higher = more accurate)
optimizers:
  default_segment_number: 2
  max_segment_size_kb: 200000
  memmap_threshold_kb: 200000
payload_schema:
  job_id: keyword      # For exact filtering
  source: keyword      # MCF / JobStreet
  section_type: keyword # summary / responsibilities / requirements / benefits / metadata
  title: text          # Full-text search (BM25)
  company: keyword
  location: keyword
  classification: keyword
  salary_min: integer
  salary_max: integer
  posted_at: datetime

ttl_rules:
  # Auto-delete vectors after 60 days (keep metadata in PostgreSQL)
  - field: posted_at
    expire_after: 60d
```

**Hybrid Search Setup:**
```python
from qdrant_client import QdrantClient, models

client = QdrantClient(
    url="https://your-cluster.qdrant.io",
    api_key="your-api-key"
)

# Create collection with sparse vectors for BM25
client.create_collection(
    collection_name="sg_job_market",
    vectors_config=models.VectorParams(size=1024, distance=models.Distance.COSINE),
    sparse_vectors_config={
        "bm25": models.SparseVectorParams(
            index=models.SparseIndexParams(
                on_disk=False,
            )
        )
    },
    hnsw_config=models.HnswConfigDiff(
        m=16,
        ef_construct=100,
    )
)
```

**Query Pattern:**
```python
async def search_jobs(
    query_embedding: list[float],
    query_text: str,
    top_k: int = 50,
    filters: dict = None,
    hybrid_weight: float = 0.7  # 70% vector + 30% BM25
) -> list[dict]:
    """
    Hybrid search: dense vector similarity + sparse BM25 keyword matching.
    """
    # Dense vector search
    dense_results = client.search(
        collection_name="sg_job_market",
        vector=query_embedding,
        limit=top_k,
        query_filter=build_qdrant_filter(filters),
        with_payload=True,
    )
    
    # Sparse BM25 search (requires indexing text fields)
    sparse_results = client.search(
        collection_name="sg_job_market",
        vector=models.NamedVector(
            name="bm25",
            vector=query_text,  # Qdrant computes BM25 internally
        ),
        limit=top_k,
        query_filter=build_qdrant_filter(filters),
        with_payload=True,
    )
    
    # Reciprocal Rank Fusion (RRF) for hybrid scoring
    return reciprocal_rank_fusion(dense_results, sparse_results, weight=hybrid_weight)
```

### 3.4 Cross-Encoder Re-ranker: bge-reranker-v2-m3

**Model:** `BAAI/bge-reranker-v2-m3`  
**Parameters:** ~550M  
**License:** MIT  
**Input:** `[query_text, section_text]` pair  
**Output:** Relevance score (0.0 - 1.0)  
**Latency:** ~150ms for 50 documents (CPU, Cloud Run 4GB)

**Implementation:**
```python
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

class Reranker:
    MODEL_NAME = "BAAI/bge-reranker-v2-m3"
    
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.MODEL_NAME)
        self.model.eval()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = self.model.to(self.device)
    
    def rerank(
        self, 
        query: str, 
        documents: list[dict], 
        top_k: int = 10
    ) -> list[dict]:
        """Score and re-rank documents by relevance."""
        pairs = [
            [query, doc["section_text"]] 
            for doc in documents
        ]
        
        with torch.no_grad():
            inputs = self.tokenizer(
                pairs, 
                padding=True, 
                truncation=True, 
                return_tensors="pt", 
                max_length=512
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            scores = self.model(**inputs).logits.view(-1).float()
            scores = torch.sigmoid(scores).cpu().numpy()
        
        # Attach scores and sort
        for doc, score in zip(documents, scores):
            doc["rerank_score"] = float(score)
        
        documents.sort(key=lambda x: x["rerank_score"], reverse=True)
        return documents[:top_k]
```

**Integration in RAG Pipeline:**
```
1. Qdrant hybrid search → Top 50 candidates
2. bge-reranker-v2-m3 → Score each [query, section] pair → Top 10
3. Gemini 2.5 Flash → Grade top 10 (0-10) → Filter < 5.0
4. If avg grade < 5.0 → Rewrite query → Retry (max 2)
5. Gemini 2.5 Flash → Generate answer with citations
```

### 3.5 Query Standardization (Gated)

**Model:** Gemini 2.5 Flash  
**Trigger:** Only when `should_rephrase(query)` returns True

**Gate Logic:**
```python
ABBREVIATIONS = {"wfh", "ft", "pt", "exp", "yr", "yrs", "min", "max", "sgd", "rm"}
SLANG_TERMS = {"gd", "gud", "nice", "shiok", "chiong", "sian"}

def should_rephrase(query: str) -> bool:
    """Determine if query needs standardization before embedding."""
    q = query.lower().strip()
    return (
        len(q.split()) < 5                    # Too short/vague
        or any(abbr in q.split() for abbr in ABBREVIATIONS)
        or any(slang in q for slang in SLANG_TERMS)
        or q.count("?") > 1                   # Multiple questions
        or not any(c.isalpha() for c in q)    # No real words
    )
```

**Standardization Prompt:**
```
Rephrase the following job search query into clear, professional language suitable for semantic search.
Expand abbreviations, normalize slang, and clarify intent.

Rules:
- Keep the original language (English/Chinese/Malay)
- Do NOT add location unless specified (default: Singapore)
- Do NOT add salary unless specified
- Output ONLY the rephrased query, no explanations

Query: "{query}"

Rephrased:
```

**Estimated trigger rate:** ~30% of queries  
**Cost:** ~$10.50/month

### 3.6 Unified LLM Budget

| Task | Model | Monthly Queries | Cost/Query | Monthly Cost |
|------|-------|----------------|------------|--------------|
| Section extraction | Gemini 2.5 Flash | 6,000 (200/day avg) | $0.0003 | ~$1.80 |
| Query standardization | Gemini 2.5 Flash | 18,000 (30% of ~2K/day) | $0.0005 | ~$9.00 |
| Document grading | Gemini 2.5 Flash | 60,000 (all queries) | $0.0004 | ~$24.00 |
| Query rewrite | Gemini 2.5 Flash | 12,000 (20% retry rate) | $0.0005 | ~$6.00 |
| Answer generation | Gemini 2.5 Flash | 60,000 (all queries) | $0.0008 | ~$48.00 |
| **TOTAL** | | | | **~$88.80/month** |

*Note: Actual costs may be 30-40% lower if many queries are cached or below token thresholds.*

---

## 4. Implementation Phases

### Phase 1: Preprocessing Module (Week 1)

**Goal:** Build section extraction pipeline with Gemini 2.5 Flash

**Files to Create:**
- `nlp/section_extractor.py` — Section extraction with Gemini 2.5 Flash
- `tests/nlp/test_section_extractor.py` — Unit tests

**Files to Modify:**
- `etl/transform.py` — Integrate section extraction into ETL pipeline
- `utils/schemas.py` — Add `CleanedJob` fields for 5 sections
- `utils/bq_schemas.py` — Update BigQuery schema (or switch to PostgreSQL migration)

**Tasks:**
1. [ ] Create section extraction module with Gemini 2.5 Flash integration
2. [ ] Implement JSON validation and error handling for malformed LLM outputs
3. [ ] Add retry logic (3 attempts, exponential backoff)
4. [ ] Write unit tests with sample MCF + JobStreet descriptions
5. [ ] Integrate into ETL pipeline (`etl/transform.py`)
6. [ ] Update database schema (PostgreSQL migration)

**Acceptance Criteria:**
- [ ] 100% of jobs have 5 sections extracted
- [ ] Average extraction time < 200ms per job
- [ ] JSON parse success rate > 99%
- [ ] All tests passing

---

### Phase 2: bge-m3 Integration + Qdrant Migration (Week 2)

**Goal:** Replace SBERT with bge-m3, migrate from BigQuery to Qdrant Cloud

**Files to Create:**
- `utils/qdrant_client.py` — Qdrant connection and operations wrapper
- `nlp/chunking.py` — 5-section chunking logic
- `tests/nlp/test_bge_m3.py` — Embedding model tests

**Files to Modify:**
- `nlp/embeddings.py` — Swap `all-MiniLM-L6-v2` → `bge-m3`
- `nlp/generate_embeddings.py` — Update pipeline for Qdrant target
- `requirements.txt` — Add `qdrant-client`, `transformers>=4.36`

**Tasks:**
1. [ ] Update `nlp/embeddings.py` to use `BAAI/bge-m3`
2. [ ] Implement instruction-based embedding (retrieval task prefix)
3. [ ] Create `utils/qdrant_client.py` with CRUD operations
4. [ ] Set up Qdrant Cloud collection with hybrid search config
5. [ ] Update `nlp/generate_embeddings.py` to write to Qdrant instead of BigQuery
6. [ ] Implement batch upsert for 5 sections per job
7. [ ] Add section type filtering in Qdrant payload

**Acceptance Criteria:**
- [ ] bge-m3 loads and embeds correctly (1024 dims)
- [ ] Qdrant collection created with proper schema
- [ ] All 6,775+ jobs migrated to Qdrant with 5 sections each
- [ ] Hybrid search (vector + BM25) returns results
- [ ] Query latency < 100ms p99

---

### Phase 3: Cross-Encoder Re-ranker + RAG Update (Week 3)

**Goal:** Add bge-reranker-v2-m3, update RAG pipeline for new architecture

**Files to Create:**
- `nlp/reranker.py` — Cross-encoder re-ranking module
- `tests/nlp/test_reranker.py` — Re-ranker tests

**Files to Modify:**
- `genai/rag.py` — Update retrieve → rerank → grade → generate flow
- `genai/agent.py` — Update LangGraph nodes for new pipeline
- `genai/tools/search.py` — Update tool adapters for Qdrant

**Tasks:**
1. [ ] Implement `nlp/reranker.py` with bge-reranker-v2-m3
2. [ ] Add rerank step between Qdrant retrieval and document grading
3. [ ] Update `genai/rag.py` orchestration:
   - `retrieve_jobs()` → hybrid search (Qdrant)
   - `rerank_documents()` → cross-encoder scoring
   - `grade_documents()` → Gemini 2.5 Flash (existing)
   - `generate_answer()` → Gemini 2.5 Flash (existing)
4. [ ] Update `genai/tools/search.py` to use Qdrant instead of BigQuery VECTOR_SEARCH
5. [ ] Add query standardization gate in API layer
6. [ ] Update FastAPI models for new response format

**Acceptance Criteria:**
- [ ] Re-ranker scores documents accurately (manual spot-check 20 queries)
- [ ] End-to-end RAG pipeline completes in < 3 seconds
- [ ] Reranker improves relevance vs. no reranking (A/B test 50 queries)
- [ ] All API endpoints functional with Qdrant backend

---

### Phase 4: Testing, Validation, Fallback Removal (Week 4)

**Goal:** Validate new stack, remove BigQuery fallback, update documentation

**Files to Create:**
- `tests/integration/test_end_to_end.py` — Full pipeline integration tests
- `docs/EMBEDDING_UPGRADE.md` — Architecture documentation

**Files to Modify:**
- `.github/agents/skills/04_p1_1_nlp_embeddings.md` — Update skill documentation
- `.github/agents/04_ml_engineer.agent.md` — Update status dashboard
- `Dockerfile.embeddings` — Add bge-m3 + reranker dependencies
- `cloudbuild.embeddings.yaml` — Update build pipeline

**Tasks:**
1. [ ] Run golden test set (50 representative queries) — compare old vs new stack
2. [ ] Measure metrics: latency, recall@10, user satisfaction (if available)
3. [ ] Stress test: 100 concurrent queries
4. [ ] Remove BigQuery vector index dependencies (keep for historical data)
5. [ ] Update agent.md and skill files with new architecture
6. [ ] Update deployment scripts (Dockerfile, Cloud Build)
7. [ ] Run full regression test suite (13 genai tests)

**Acceptance Criteria:**
- [ ] Golden test set: new stack outperforms old stack on > 80% of queries
- [ ] End-to-end latency < 3 seconds at p95
- [ ] All 13 genai tests passing
- [ ] Integration tests passing
- [ ] Agent.md and skill files updated
- [ ] Deployment scripts validated

---

## 5. Data Schema Changes

### 5.1 Cloud SQL PostgreSQL (New)

```sql
-- Main jobs table with sections
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
    
    -- Metadata
    posted_at TIMESTAMP,
    scraped_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    
    PRIMARY KEY (source, job_id)
);

-- Index for active jobs (RAG only queries active listings)
CREATE INDEX idx_cleaned_jobs_active_posted 
    ON cleaned_jobs(is_active, posted_at DESC);

-- Index for lookups
CREATE INDEX idx_cleaned_jobs_classification 
    ON cleaned_jobs(classification) WHERE is_active = TRUE;

-- Index for salary range queries
CREATE INDEX idx_cleaned_jobs_salary 
    ON cleaned_jobs(salary_min, salary_max) WHERE is_active = TRUE;

-- 30-day active window view
CREATE VIEW cleaned_jobs_active AS
SELECT * FROM cleaned_jobs
WHERE is_active = TRUE
  AND posted_at >= NOW() - INTERVAL '30 days';
```

### 5.2 Qdrant Payload Schema

```python
# Each point in Qdrant represents ONE section of ONE job
qdrant_point = {
    "id": f"{source}:{job_id}:{section_type}",  # e.g., "MCF:abc123:requirements"
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

## 6. Deployment Plan

### 6.1 Infrastructure Setup

```bash
# 1. Qdrant Cloud (manual setup via UI or Terraform)
#    - Create cluster in Singapore region
#    - Create collection "sg_job_market"
#    - Configure API key

# 2. Cloud SQL PostgreSQL
gcloud sql instances create sg-job-market-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=asia-southeast1 \
  --storage-size=10GB \
  --storage-auto-increase

# 3. Create database and user
gcloud sql databases create jobmarket --instance=sg-job-market-db
gcloud sql users create embedding_service \
  --instance=sg-job-market-db \
  --password=[GENERATED_PASSWORD]
```

### 6.2 Service Configuration

**Environment Variables (Cloud Run):**
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

### 6.3 Migration Strategy

```
Phase A: Dual-Write (Week 2)
  • Old pipeline continues writing to BigQuery (384-dim SBERT)
  • New pipeline writes to Qdrant (1024-dim bge-m3)
  • PostgreSQL receives new schema with 5 sections

Phase B: Shadow Testing (Week 3)
  • RAG queries run against BOTH systems
  • Compare results, measure metrics
  • Log discrepancies for analysis

Phase C: Cutover (Week 4)
  • Switch RAG to read from Qdrant only
  • Stop BigQuery vector writes (keep table for history)
  • Monitor for 1 week, rollback if issues
```

---

## 7. Testing Strategy

### 7.1 Unit Tests

| Module | File | Coverage |
|--------|------|----------|
| Section extractor | `tests/nlp/test_section_extractor.py` | JSON parsing, error handling, retry logic |
| Embedding generator | `tests/nlp/test_bge_m3.py` | 1024-dim output, L2 norm, batch processing |
| Qdrant client | `tests/utils/test_qdrant_client.py` | CRUD, search, filtering |
| Reranker | `tests/nlp/test_reranker.py` | Score range, sorting, top-k |

### 7.2 Integration Tests

| Flow | File | Validates |
|------|------|-----------|
| E2E RAG | `tests/integration/test_end_to_end.py` | Query → standardize → embed → search → rerank → grade → generate |
| Embed pipeline | `tests/integration/test_embedding_pipeline.py` | Raw job → sections → Qdrant |
| API backward compat | `tests/genai/test_api_compat.py` | Old endpoints work with new backend |

### 7.3 Golden Test Set

Create 50 representative queries covering:
- English queries (35): "software engineer Python", "marketing manager", "$5000 salary"
- Chinese queries (10): "数据科学家", "薪金优厚的工作"
- Malay queries (5): "kerja jurutera", "gaji tinggi"
- Edge cases (10): abbreviations, typos, vague requests, combined filters

Measure:
- Recall@10 (are relevant jobs in top 10?)
- NDCG@10 (are they ranked correctly?)
- Latency (p50, p95, p99)

---

## 8. Rollback Plan

If critical issues arise post-deployment:

1. **Immediate (0-5 min):**
   - Switch `genai/rag.py` config to read from BigQuery VECTOR_SEARCH
   - Environment variable: `VECTOR_BACKEND=bigquery`
   - No code deployment needed

2. **Short-term (5-60 min):**
   - Revert Cloud Run deployment to previous revision
   - `gcloud run services update-traffic genai-api --to-revisions=PREVIOUS=100`

3. **Long-term (1-7 days):**
   - Keep Qdrant collection but stop writes
   - Debug issue, fix code, redeploy
   - Resume Qdrant writes once validated

---

## 9. Post-Implementation Monitoring

### 9.1 Metrics to Track

| Metric | Tool | Alert Threshold |
|--------|------|-----------------|
| Qdrant query latency | Prometheus | p99 > 100ms |
| Embedding generation time | Prometheus | p99 > 2s |
| Re-ranker latency | Prometheus | p99 > 500ms |
| LLM API errors | Prometheus | > 1% error rate |
| Vector store size | Qdrant dashboard | > 80% of free tier |
| PostgreSQL connections | Cloud Monitoring | > 80% of max |
| RAG end-to-end latency | Prometheus | p95 > 3s |

### 9.2 Dashboards

- **Grafana:** RAG pipeline latency breakdown per stage
- **Qdrant Console:** Collection health, query performance
- **Cloud Monitoring:** Cloud Run, Cloud SQL, Vertex AI metrics

---

## 10. Future Enhancements (Post-MVP)

| Feature | Description | Effort |
|---------|-------------|--------|
| Domain branching | Create Qdrant collections per industry (healthcare, finance) | 1 day |
| Late chunking | Experiment with Jina v3 late chunking for long descriptions | 2-3 days |
| Sparse embeddings | Add SPLADE or BGE-M3 sparse vectors for keyword-heavy queries | 2 days |
| Embedding compression | Use Matryoshka to store 256-dim + 512-dim + 1024-dim | 1 day |
| A/B testing framework | Route 10% traffic to new model variants | 2 days |
| Multi-vector per section | Store multiple embeddings per section (mean, max, CLS) | 3 days |

---

## 11. Approval

| Stakeholder | Role | Status |
|-------------|------|--------|
| ML & GenAI Engineer | Architecture & Implementation | ✅ Approved |
| User | Product Owner | ✅ Approved |

---

*Document version: 1.0*  
*Last updated: 2026-04-27*  
*Next review: Post-Phase 4 completion*
