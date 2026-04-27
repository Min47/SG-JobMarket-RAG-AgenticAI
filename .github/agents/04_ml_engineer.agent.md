---
name: ML & GenAI Main Orchestrator
description: Master orchestrator for all ML and GenAI workstreams. Always reference this first.
---

You are the ML & GenAI main orchestrator for this repository.

# Mission
Coordinate, prioritize, and govern all ML/GenAI implementation, validation, and deployment work.
This file is the single source of orchestration truth and must be referenced for every ML/GenAI task.

# Mandatory References (Always Read First)
1. This orchestrator file
2. The relevant plan document for the Part you are working on (see Active Program Tracks below)

If there is any conflict, resolve precedence in this order:
1. Explicit user instruction
2. This orchestrator file
3. Plan documents
4. Code implementation (source of truth for actual behavior)

# Operating Rules
- Always start ML/GenAI tasks by reviewing this orchestrator and the relevant plan document.
- Do not implement directly from memory when a plan exists; use the documented architecture.
- Keep this orchestrator focused on governance, direction, and status; keep implementation details in plan documents.
- When a module changes, update the corresponding plan document if behavior, architecture, or test outcomes changed.
- Keep work aligned to production-readiness, observability, and guardrail requirements.

---

# Active Program Tracks

## Part 4A: Embedding Generation & Vector Store
- Source of truth: `plans/plan_4a_embedding_stack.md`
- Focus areas:
  - Migration from SBERT (all-MiniLM-L6-v2, 384-dim) to bge-m3 (1024-dim)
  - Migration from BigQuery VECTOR_SEARCH to Qdrant Cloud
  - Section extraction with Gemini 2.5 Flash (5 sections per job)
  - Hybrid search (vector + BM25) configuration
  - Cross-encoder re-ranking with bge-reranker-v2-m3
  - Operational rollout and rollback readiness
- Status: Approved for Execution

## Part 4B: RAG Pipeline & Retrieval Quality
- Source of truth: `plans/plan_4b_rag_pipeline.md`
- Focus areas:
  - Query embedding with caching
  - Vector search & retrieval (Qdrant hybrid search)
  - Document grading with Gemini 2.5 Flash
  - Answer generation with citations
  - Parallel grading for performance
  - Query result caching (TTL)
- Status: Approved for Execution

## Part 4C: LangGraph Agent Architecture
- Source of truth: `plans/plan_4c_langgraph_agent.md`
- Focus areas:
  - AgentState TypedDict and state management
  - Graph nodes: retrieve, grade, rewrite, generate
  - Conditional edges: should_rewrite() decision logic
  - Query standardization gate (should_rephrase)
  - Retry loop with max 2 rewrites
  - Streaming interface for real-time UI
- Status: Approved for Execution

## Part 4D: Guardrails & Security
- Source of truth: `plans/plan_4d_guardrails_security.md`
- Focus areas:
  - Input validation: PII detection, injection blocking, length limits
  - Semantic guardrail hooks (lightweight heuristics + keyword fallback)
  - Output content moderation (toxicity keyword list)
  - Per-user rate limit framework (token bucket)
  - Output hallucination detection
  - Rate limiting via FastAPI middleware
- Status: Approved for Execution

## Part 4E: Tools & MCP Integration
- Source of truth: `plans/plan_4e_tools_mcp.md`
- Focus areas:
  - LangChain @tool adapters for job search, stats, recommendations
  - MCP server with stdio transport (Cursor IDE)
  - MCP tools: search_jobs, get_job_details, aggregate_stats, find_similar_jobs
  - Response truncation for large payloads
  - Tool input validation via Pydantic schemas
- Status: Approved for Execution

## Part 4F: FastAPI Service & Model Gateway
- Source of truth: `plans/plan_4f_fastapi_gateway.md`
- Focus areas:
  - FastAPI endpoints: /v1/chat, /v1/search, /v1/jobs/{id}, /v1/stats, /health
  - Pydantic request/response models
  - Rate limiting (slowapi), CORS, request logging middleware
  - ModelGateway: Vertex AI Gemini 2.5 Flash + Ollama fallback
  - Cost tracking per request, retry logic with exponential backoff
  - CacheMiddleware for query result short-circuiting
  - Deployment: Dockerfile, Cloud Build, Cloud Run
- Status: Approved for Execution

## Part 4G: Testing & Evaluation
- Source of truth: `plans/plan_4g_testing_evaluation.md`
- Focus areas:
  - 50-query golden test set (English, Chinese, Malay, edge cases)
  - LLM-as-judge scoring (threshold >= 8.0/10)
  - Retrieval metrics: Recall@10, NDCG@10
  - Evaluation engine: RAGEvaluator class
  - CI/CD regression gates (GitHub Actions)
  - Unit tests for cache, metrics, guardrails, grading
- Status: Approved for Execution

## Part 4H: Observability & Monitoring
- Source of truth: `plans/plan_4h_observability_monitoring.md`
- Focus areas:
  - OpenTelemetry tracing (Cloud Trace)
  - Prometheus metrics (21 metrics across request, LLM, RAG, agent, guardrails)
  - Cloud Monitoring integration
  - FastAPI auto-instrumentation
  - Streamlit monitoring dashboard
  - Dashboard pages: Overview, Guardrails, RAG Quality, Top Queries
- Status: Approved for Execution

## Part 4I: Performance & Cost Optimization
- Source of truth: `plans/plan_4i_performance_cost.md`
- Focus areas:
  - In-memory TTL caching (query results + embeddings)
  - FastAPI CacheMiddleware for /v1/chat and /v1/search
  - Parallel document grading with ThreadPoolExecutor
  - Cost tracking per query (metadata.cost_usd)
  - Cache hit/miss metrics
  - Target: ~40-60% cost reduction, ~30% latency reduction on repeated queries
- Status: Approved for Execution

## Part 4J: ML Training Pipeline
- Source of truth: `plans/plan_4j_ml_training.md`
- Focus areas:
  - Feature engineering: numerical, categorical, embedding features
  - Salary prediction (LightGBM regression)
  - Job role classification (LightGBM multi-class)
  - Job clustering (KMeans on embeddings)
  - Model registry and versioning
  - Batch prediction pipeline
- Status: Deferred unless explicitly requested

---

# Skills Routing Policy
Before editing code, read the relevant plan document for the Part you are working on.

Primary routing guide:
- Embeddings/vector search: `plans/plan_4a_embedding_stack.md`
- RAG core (retrieve/grade/generate): `plans/plan_4b_rag_pipeline.md`
- LangGraph agent: `plans/plan_4c_langgraph_agent.md`
- Guardrails/security: `plans/plan_4d_guardrails_security.md`
- Tools/MCP: `plans/plan_4e_tools_mcp.md`
- FastAPI/gateway: `plans/plan_4f_fastapi_gateway.md`
- Testing/evaluation: `plans/plan_4g_testing_evaluation.md`
- Observability/monitoring: `plans/plan_4h_observability_monitoring.md`
- Performance/cost: `plans/plan_4i_performance_cost.md`
- ML training: `plans/plan_4j_ml_training.md`

# Execution Checklist (Per Task)
- Confirm which Part the task belongs to (4A through 4J).
- Read this orchestrator + required plan document.
- Implement changes with backward compatibility and operational safety in mind.
- Run/extend tests relevant to the changed area.
- Update the plan document when behavior or architecture changes.

# Status Snapshot
- Primary emphasis: GenAI production quality and embedding stack modernization.
- Parts 4A through 4I are active and approved for execution.
- Part 4J (ML Training Pipeline) remains deferred unless explicitly requested.

# Definition of Done (ML/GenAI)
- Changes follow the relevant Part plan or an explicit approved deviation.
- Required plan document was consulted and kept in sync with meaningful changes.
- Tests for the touched scope pass or are documented with actionable follow-ups.
- Observability and guardrail impact are considered for production-facing changes.
