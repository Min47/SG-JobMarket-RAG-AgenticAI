# Phase 2.1 - 2.3: GenAI Architecture & Core Implementation

> Reference this file when working on: RAG pipeline, LangGraph agent, tool adapters, or query flow logic.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          USER QUERY                                         │
│                    "Find data scientist jobs with Python"                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ FASTAPI GATEWAY (genai/api.py)                                              │
│ ─────────────────────────────────────────────────────────────────────────── │
│ POST /chat      → Conversational RAG                                        │
│ POST /search    → Direct vector search                                      │
│ GET  /jobs/{id} → Job details with similar recommendations                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LANGGRAPH AGENT (genai/agent.py)                                            │
│ ─────────────────────────────────────────────────────────────────────────── │
│ StateGraph with nodes:                                                      │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│   │ RETRIEVE │───▶│  GRADE   │───▶│ GENERATE│───▶│   END   │              │
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘              │
│         │               │                                                   │
│         │         (if low score)                                            │
│         │               ▼                                                   │
│         │         ┌──────────┐                                              │
│         └────────▶│ REWRITE  │──────────┐                                  │
│                   └──────────┘          │ (retry with rewritten query)      │
│                                         ▼                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ TOOL ADAPTERS (genai/tools/)                                                │
│ @tool search_jobs     → BigQuery Vector Search + filters                    │
│ @tool get_job_details → Fetch full job info by ID                           │
│ @tool aggregate_stats → Salary ranges, job counts by category               │
│ @tool similar_jobs    → Find N most similar jobs to a given job             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ RAG PIPELINE (genai/rag.py)                                                 │
│ retrieve_jobs()    → Embed query → Vector Search → Top-K results            │
│ grade_documents()  → LLM relevance scoring → Filter irrelevant              │
│ generate_answer()  → Context + Query → Gemini 2.5 Flash → Response          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ MODEL GATEWAY (genai/gateway.py)                                            │
│ Vertex AI Gemini 2.5 Flash (default) → fallback → Ollama deepseek-r1:8b    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2.1: RAG Pipeline

File: `genai/rag.py`

### 2.1.1: Query Embedding
- `embed_query()` — 384-dim SBERT embedding, L2-normalized for cosine similarity
- Singleton pattern to avoid model reload
- Input validation: empty, short (<3 chars), long (>1000 chars) queries handled

### 2.1.2: Vector Search & Retrieval
- `retrieve_jobs()` — BigQuery VECTOR_SEARCH with COSINE distance
- [Concept] Hybrid scoring: 70% vector similarity + 30% keyword matching (BM25-style)
- [Concept] Filters: location (LIKE), min/max salary, work_type, classification
- Deduplication via `ROW_NUMBER()` on append-only `cleaned_jobs`
- Returns: job metadata + `vector_distance`, `keyword_score`, `hybrid_score`

### 2.1.3: Document Grading
- `grade_documents()` — Gemini 2.5 Flash scores each job 0-10 for relevance
- Threshold filtering (default ≥5.0)
- JSON parsing with regex fallback for malformed responses
- Average score computed on ALL retrieved docs (before filtering) for rewrite decisions
- Re-ranks by relevance score descending

### 2.1.4: Answer Generation
- `generate_answer()` — Context + Query → Gemini 2.5 Flash
- Structured output with citations [1], [2], etc.
- Empty context handling with graceful error message
- Response truncated to 4096 chars safety limit
- Cost and latency metadata returned

### 2.1.5: Orchestration
- `rag_pipeline()` — Complete Retrieve → Grade → Generate entry point

---

## 2.2: LangGraph Agent

File: `genai/agent.py`

### 2.2.1: State & Graph
- `AgentState` TypedDict with 9 fields: messages, query, original_query, retrieved_jobs, graded_jobs, final_answer, rewrite_count, average_relevance_score, metadata
- `StateGraph` with nodes: retrieve → grade → [decision] → generate → END
- Conditional edge `should_rewrite()`: triggers if avg_score < 6.0 OR passed_count < 3, max 2 rewrites
- Retry loop: grade → rewrite → retrieve → grade

### 2.2.2: Nodes
- `retrieve_node` — Calls `retrieve_jobs()` with hybrid search, tracks metrics
- `grade_node` — Calls `grade_documents()`, computes avg on ALL docs for decision
- `generate_node` — Calls `generate_answer()`, limits context to top 5 jobs
- `rewrite_node` — Uses ModelGateway to reformulate query (adds keywords, expands abbreviations, keeps Singapore context)

### 2.2.3: High-Level Interface
- `JobMarketAgent` class:
  - `run(query, conversation_history, filters)` — Full graph execution
  - `stream(query, filters)` — Yields intermediate steps for real-time UI

---

## 2.3: Tool Adapters

Files:
- `genai/tools/__init__.py` — Module exports
- `genai/tools/_validation.py` — Shared Pydantic schemas
- `genai/tools/search.py` — `search_jobs`, `get_job_details`
- `genai/tools/stats.py` — `aggregate_stats`
- `genai/tools/recommendations.py` — `find_similar_jobs`

Implementation:
- 4 LangChain `@tool` decorators with Pydantic `args_schema`
- `search_jobs` — Vector search with filters (wraps `retrieve_jobs`)
- `get_job_details` — BigQuery SELECT by job_id + source
- `aggregate_stats` — GROUP BY classification/location/work_type with salary percentiles
- `find_similar_jobs` — VECTOR_SEARCH from reference job's embedding

Safety:
- Input validation via Pydantic (all tools)
- Timeout handling (30s max per BigQuery query)
- Source normalization (jobstreet/JobStreet → JobStreet, mcf/MCF → MCF)
- Parameterized SQL (injection-safe)
- Error responses: `{"success": false, "error": "..."}`
