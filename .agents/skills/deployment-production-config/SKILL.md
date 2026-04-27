---
name: deployment-production-config
description: Reference this file when working on Docker builds, Cloud Run deployment, CI/CD pipelines, or infrastructure changes.
---

# Deployment & Production Config

## GenAI API Service

### Dockerfile
- **File:** `Dockerfile.api`
- Optimized to ~1.8GB (CPU-only PyTorch, down from 5GB)
- Multi-stage build with dependency caching

### Cloud Build
- **File:** `cloudbuild.api.yaml`
- Trivy vulnerability scanning added
- Scans Python packages for HIGH/CRITICAL CVEs before deployment
- Ignores unfixed OS vulnerabilities (focus on application layer)
- Build fails automatically if fixable vulnerabilities detected

### Cloud Run
- Region: asia-southeast1
- Instances: 0-10 (auto-scaling)
- CPU: 2 vCPU
- RAM: 4GB
- IAM: roles/aiplatform.user for Vertex AI

### Service URL
- `https://genai-api-[hash]-as.a.run.app`

---

## Embeddings Service

### Dockerfile
- **File:** `Dockerfile.embeddings`
- CPU-only PyTorch for Cloud Run Job

### Cloud Build
- **File:** `cloudbuild.embeddings.yaml`

### Cloud Run Job
- Daily incremental embeddings
- Triggered by Cloud Scheduler at 2 AM UTC

### Deployment Scripts
- `deployment/API_01_Deploy_FastAPI.ps1`
- `deployment/NLP_01_Deploy_Embeddings_CloudRun.ps1`
- `deployment/NLP_02_Create_Embeddings_Scheduler.ps1`

---

## Security Hardening

- Trivy vulnerability scanning on all 4 cloudbuild pipelines
- Scans Python packages for HIGH/CRITICAL CVEs
- Ignores unfixed OS vulnerabilities
- Build fails on fixable vulnerabilities

---

## Phase 3 Upgrade (Planned)

> See `plan_embedding_stack_upgrade.md` for full architecture, phases, and specs.

### New Infrastructure

| Service | Provider | Purpose |
|---------|----------|---------|
| **Qdrant Cloud** | Managed (AWS) | Vector database — hybrid search, 1024-dim, BM25 payload |
| **Cloud SQL PostgreSQL** | GCP | Structured metadata, filters, 30-day active listings |

### Environment Variables (New)

```bash
# Qdrant
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-api-key
QDRANT_COLLECTION=sg_job_market

# PostgreSQL
POSTGRES_HOST=/cloudsql/...
POSTGRES_DB=jobmarket
POSTGRES_USER=embedding_service
POSTGRES_PASSWORD=[SECRET]

# Models
EMBEDDING_MODEL=BAAI/bge-m3
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
EMBEDDING_DIMENSIONS=1024
```

### Updated Components

| Component | Changes |
|-----------|---------|
| `Dockerfile.embeddings` | Add `bge-m3` + `bge-reranker-v2-m3` dependencies; increase base image if needed |
| `cloudbuild.embeddings.yaml` | Updated build pipeline with new packages |
| Cloud Run Job (embeddings) | Now runs section extraction → embedding → Qdrant upsert |
| Cloud SQL | New `cleaned_jobs` table with 5 section columns |

### Deployment Scripts

- `deployment/NLP_01_Deploy_Embeddings_CloudRun.ps1` — Update for Qdrant + PostgreSQL connectivity
- `cloudbuild.embeddings.yaml` — Add `qdrant-client`, `transformers>=4.36` to build
