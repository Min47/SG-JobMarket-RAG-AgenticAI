# Deployment & Production Config

> Reference this file when working on: Docker builds, Cloud Run deployment, CI/CD pipelines, or infrastructure changes.

---

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
