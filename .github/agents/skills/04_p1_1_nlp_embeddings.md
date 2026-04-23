# Phase 1.1: NLP Embeddings Generation

> Reference this file when working on: embeddings, vector search, SBERT model, Cloud Run Job pipeline, or BigQuery vector index.

---

## Status: ✅ COMPLETE

**Operational:** 6,775+ jobs embedded, 384-dim SBERT, BigQuery Vector Search, daily incremental Cloud Run Job.

---

## Model Selection

| Model | Dimensions | Speed | Quality | Use Case |
|-------|------------|-------|---------|----------|
| `all-MiniLM-L6-v2` ✅ | 384 | Fast | Good | **CHOSEN** — Best balance |
| `all-mpnet-base-v2` | 768 | Medium | Better | If quality is critical |
| `text-embedding-004` (Vertex AI) | 768 | API call | Best | Production with budget |

**Decision:** Use `all-MiniLM-L6-v2` for initial implementation (free, local, fast).
Can upgrade to Vertex AI embeddings later for production.


### [Concept] BigQuery Vector Index
- [ ] Create vector index for similarity search:
  ```sql
  CREATE VECTOR INDEX job_embedding_idx
  ON `sg-job-market.sg_job_market.job_embeddings`(embedding)
  OPTIONS(distance_type='COSINE', index_type='IVF', ivf_options='{"num_lists": 100}');
  ```
- [ ] Create similarity search function:
  ```python
  def find_similar_jobs(query_embedding: List[float], top_k: int = 10) -> List[Dict]
  ```
- [ ] Test with sample queries

### [Concept] Acceptance Criteria
- [ ] All cleaned_jobs have embeddings in BigQuery
- [ ] Vector index created and queryable
- [ ] Similar job search returns relevant results
- [ ] Processing time: <5 minutes for 10K jobs

---

## Implementation

### File: `nlp/embeddings.py`

- `EmbeddingGenerator` class with lazy model loading
- `embed_texts(texts, batch_size=32)` — batched processing with retry logic (3 attempts, exponential backoff)
- `embed_jobs_from_bq(title, description)` — combines title + truncated description (1000 chars)
- L2 normalization for cosine similarity
- Handles empty/null descriptions gracefully
- GPU-aware (CUDA cache clearing on retry)

### File: `nlp/generate_embeddings.py`

- Queries `cleaned_jobs` from BigQuery (latest version via `ROW_NUMBER()` on append-only table)
- Filters to only new jobs (anti-join with `job_embeddings`)
- Processes in chunks of 1,000 jobs for memory management
- Writes incrementally to BigQuery `job_embeddings` table (batch size 500)
- Supports `--limit`, `--full`, `--dry-run`, `--create-table` CLI flags
- Default processes yesterday's jobs (UTC)
- Target date filtering for backfills

### File: `nlp/setup_embeddings_table.py`

- Creates `job_embeddings` table schema:
  - `job_id` STRING
  - `source` STRING
  - `embedding` FLOAT64 REPEATED (384 elements)
  - `model_name` STRING
  - `created_at` TIMESTAMP

### File: `nlp/create_vector_index.py`

- Creates BigQuery VECTOR INDEX with:
  - `distance_type='COSINE'`
  - `index_type='IVF'`
  - `ivf_options='{"num_lists": 100}'`

---

## Deployment

| Component | File | Details |
|-----------|------|---------|
| Docker | `Dockerfile.embeddings` | CPU-only PyTorch |
| Cloud Build | `cloudbuild.embeddings.yaml` | Build pipeline |
| Cloud Run Job | — | Daily incremental embeddings |
| Cloud Scheduler | `deployment/NLP_02_Create_Embeddings_Scheduler.ps1` | Triggers at 2 AM UTC |
| Deploy Script | `deployment/NLP_01_Deploy_Embeddings_CloudRun.ps1` | PowerShell deployment |

---

## Test Coverage

- `tests/genai/01_test_embed_query.py` — 8 tests:
  1. Basic query embedding (384 dims)
  2. L2 normalization check (~1.0)
  3. Consistency (same query = same embedding)
  4. Different queries produce different embeddings
  5. Empty/short query edge cases (ValueError)
  6. Special characters handling
  7. Long query truncation (>1000 chars)
  8. Singleton pattern verification

---

## CLI Usage

```bash
# Create table first
python -m nlp.setup_embeddings_table

# Generate embeddings (incremental — only new jobs)
python -m nlp.generate_embeddings --limit 1000

# Full reprocessing
python -m nlp.generate_embeddings --full

# Dry run
python -m nlp.generate_embeddings --dry-run
```
