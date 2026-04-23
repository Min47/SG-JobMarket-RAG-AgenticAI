# Phase 2.8: GenAI Testing Results

> Reference this file when working on: tests, debugging failures, or adding new test scenarios.

---

## Test Inventory (13 test files)

| File | Task | Status |
|------|------|--------|
| `01_test_embed_query.py` | Query embedding | ✅ 8 tests |
| `02_test_retrieve_jobs.py` | Vector search | ✅ Integration |
| `03_test_grade_documents.py` | Document grading | ✅ Integration |
| `04_test_generate_answer.py` | Answer generation | ✅ 5 scenarios |
| `05_test_agent_graph.py` | Graph structure | ✅ 3 tests |
| `06_test_agent_nodes.py` | Node implementations | ✅ Integration |
| `07_test_agent_execution.py` | Full agent workflow | ✅ 7 tests |
| `08_test_tools.py` | Tool adapters | ✅ 4 tests |
| `09_test_api.py` | FastAPI endpoints | ✅ 8 tests |
| `10_test_model_gateway.py` | Gateway & fallback | ✅ 6 tests |
| `11_test_guardrails.py` | Security validation | ✅ 10 tests |
| `12_test_observability.py` | Metrics & tracing | ✅ 7 tests |
| `13_test_mcp_server.py` | MCP protocol | ✅ 7 tests (6/7 passing) |

---

## Agent Execution Tests (7 tests)

| Test | Scenario | Result |
|------|----------|--------|
| 1 | High-quality query (no rewrites) | ✅ 45s, 8.55/10 relevance |
| 2 | Vague query triggers rewrite | ✅ 26s, 8.80/10 after rewrite |
| 3 | Query with filters | ✅ Metadata preserved |
| 4 | Niche edge case | ✅ 131s, 5 sources, graceful |
| 5 | Performance benchmark | ✅ Avg 31s, Gemini API bottleneck |
| 6 | Streaming interface | ✅ Real-time step updates |
| 7 | Graph structure validation | ✅ All nodes and edges correct |

---

## Guardrails Tests (10 tests)

| Test | Type | Endpoint | Result |
|------|------|----------|--------|
| 1 | PII Detection | Core | ✅ NRIC/phone/email detected, redacted |
| 2 | Injection Detection | Core | ✅ Prompt + SQL injection blocked |
| 3 | Input Guardrails | Core | ✅ Length/PII/injection validation |
| 4 | Output Guardrails | Core | ✅ Hallucination detection, structure validation |
| 5 | Chat Blocks Malicious | API POST /v1/chat | ✅ Returns 400 for PII/injection |
| 6 | Chat Allows Normal | API POST /v1/chat | ✅ 200 OK, full agent (61s) |
| 7 | Search Blocks Malicious | API POST /v1/search | ✅ Returns 400 for PII/injection |
| 8 | Search Allows Normal | API POST /v1/search | ✅ 200 OK, 5 jobs (3s) |
| 9 | Pydantic Validation | API POST /v1/chat | ✅ Returns 422 for empty/long queries |
| 10 | Health Unaffected | API GET /health | ✅ 200 OK, no guardrail interference |

---

## MCP Server Tests (7 tests)

| Test | Tool | Result | Details |
|------|------|--------|---------|
| 1 | Server Config | ✅ | Server name + 4 tools registered |
| 2 | Tool Discovery | ✅ | All tools discovered |
| 3 | Search Jobs | ✅ | 3 jobs found (9.1s with model load) |
| 4 | Get Job Details | ✅ | Job details retrieved correctly |
| 5 | Aggregate Stats | ⚠️ | Working but JSON parse issue in test |
| 6 | Find Similar | ✅ | 3 similar jobs (similarity 0.759) |
| 7 | Error Handling | ✅ | Invalid ID handled gracefully |

---

## Gateway Tests (6 tests)
1. Provider detection
2. Simple generation
3. Specific provider selection
4. Fallback logic
5. Cost tracking
6. Configuration options

---

## Observability Tests (7 tests)
1. Initialization (local mode)
2. Tracing decorators & span attributes
3. All 21 Prometheus metrics tracked
4. RAG pipeline integration (retrieve + grade)
5. Gateway LLM tracking
6. FastAPI /metrics endpoint
7. Error handling in traces

---

## Not Yet Implemented
- Golden test set (50 queries with expected results)
- RAG evaluation metrics (Retrieval Recall@10, Answer relevance LLM judge)
- Load testing (Locust/k6 scripts)
- Regression suite on every PR
