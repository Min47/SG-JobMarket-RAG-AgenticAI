# Plan 4G: Testing & Evaluation

> **Project:** SG Job Market Intelligence Platform
> **Focus:** Golden test set evaluation, LLM-as-judge scoring, retrieval metrics, CI/CD regression gates, and comprehensive test coverage
> **Status:** Active

---

## [Overview]

Single sentence: Systematic evaluation framework with a 50-query golden test set, LLM-as-judge scoring, retrieval metrics, and CI/CD regression gates.

Multiple paragraphs:
The current GenAI stack has 13 passing tests but lacks systematic quality measurement. Agent performance is measured anecdotally rather than with a standardized benchmark. This plan introduces a golden test evaluation framework that scores the RAG pipeline across multiple dimensions: retrieval quality, answer relevance, and end-to-end correctness.

The evaluation uses a 50-query golden test set covering multiple languages (English, Chinese, Malay) and query categories (job-specific, salary-based, vague, filtered, edge cases). Each query has flexible relevance criteria and optional expected job IDs for computing Recall@N.

LLM-as-judge scoring uses Gemini via the ModelGateway to rate answer relevance on a 0-10 scale. A PASS threshold of ≥ 8.0/10 ensures high-quality responses. Retrieval metrics include Recall@10 (what fraction of expected jobs appear in top 10) and NDCG@10 (normalized discounted cumulative gain).

CI/CD integration ensures regressions are caught before merge. The GitHub Actions workflow runs all tests on every PR and blocks merge if golden tests fail or the pass rate drops below 80%.

---

## [Types]

Single sentence: Three new data structures for evaluation caching and dashboard metrics.

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
```

---

## [Files]

Single sentence: 6 new test/evaluation files, 1 CI config, 1 modified API file.

### New Files

| File | Purpose |
|------|---------|
| `tests/evaluation/golden_queries.json` | 50 curated golden test queries with expected relevance criteria |
| `tests/evaluation/test_golden_set.py` | Pytest suite: run golden queries through RAG → output evaluation report |
| `tests/evaluation/evaluator.py` | Core evaluation logic: Recall@10, NDCG@10, LLM-as-judge scorer |
| `tests/evaluation/metrics.py` | Metric computation: recall, NDCG, precision, MAP |
| `tests/test_cache.py` | TTL cache unit tests |
| `tests/test_metrics.py` | Metric computation unit tests |
| `.github/workflows/ci.yml` | GitHub Actions: run golden tests + unit tests on PR |

### Modified Files

| File | Changes |
|------|---------|
| `genai/api.py` | Add `/admin/evaluate` admin endpoint for running golden tests |

---

## [Functions]

Single sentence: 6 new evaluation functions.

```python
# tests/evaluation/evaluator.py
def run_golden_query(query: GoldenQuery, rag_pipeline) -> EvaluationResult:
    """Run a single golden query through the full RAG pipeline and compute metrics."""

def compute_recall_at_k(retrieved_jobs: List[Dict], expected_job_ids: List[str], k: int = 10) -> float:
    """Compute Recall@K: what fraction of expected jobs appear in top-K results."""

def compute_ndcg_at_k(relevance_scores: List[float], k: int = 10) -> float:
    """Compute Normalized Discounted Cumulative Gain at K."""

def llm_judge_answer_relevance(query: str, answer: str, context_jobs: List[Dict]) -> Dict[str, float]:
    """Use Gemini to score answer relevance 0-10 and flag hallucinations.
    Returns {score, explanation}."""

def generate_evaluation_report(results: List[EvaluationResult]) -> Dict[str, Any]:
    """Aggregate results into a pass/fail report with per-category breakdown."""
```

---

## [Classes]

Single sentence: 1 new evaluator class.

```python
# tests/evaluation/evaluator.py
class RAGEvaluator:
    """Orchestrates golden test evaluation: runs queries, computes metrics, judges answers."""
    
    def __init__(self, golden_queries: List[GoldenQuery])
    def evaluate_single(self, query: GoldenQuery) -> EvaluationResult
    def evaluate_all(self) -> List[EvaluationResult]
    def generate_report(self) -> Dict[str, Any]
```

---

## [Test Inventory]

Current: 13 test files

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

### New Tests

| File | Tests |
|------|-------|
| `tests/test_cache.py` | TTL expiry, hit/miss, embedding cache, thread safety, maxsize eviction |
| `tests/test_metrics.py` | Recall@K, NDCG@K computation with known inputs |
| `tests/test_guardrails_semantic.py` | Intent check, output moderation, rate limit |
| `tests/test_grading_parallel.py` | Parallel vs sequential grading produces same results |
| `tests/evaluation/test_golden_set.py` | Run all 50 golden queries, assert ≥ 80% pass rate (40/50) |
| `tests/evaluation/test_evaluator.py` | LLM judge scoring consistency, metric computation |

### Not Yet Implemented

- Golden test set (50 queries with expected results) — IN PROGRESS
- RAG evaluation metrics (Retrieval Recall@10, Answer relevance LLM judge) — IN PROGRESS
- Load testing (Locust/k6 scripts)
- Regression suite on every PR — IN PROGRESS

---

## [Golden Test Set Design]

- 50 curated queries
- Categories:
  - 30 English job-specific queries
  - 10 Chinese queries
  - 5 Malay queries
  - 5 Edge cases (abbreviations, typos, slang)

Each query includes:
- Flexible relevance criteria (must_contain_keywords, must_contain_classifications)
- Optional expected_job_ids for Recall@N computation
- Optional expected_classification for category validation

---

## [CI/CD Integration]

### GitHub Actions Workflow

File: `.github/workflows/ci.yml`

Steps:
1. Checkout code
2. Install dependencies
3. Run `pytest tests/genai/` (unit + integration tests)
4. Run `pytest tests/evaluation/` (golden test suite)
5. Block merge if:
   - Any unit/integration test fails
   - Golden test pass rate < 80%

---

## [Manual / Smoke Tests]

| Test | How |
|------|-----|
| Cache effectiveness | Run same query 3 times → 1st miss, 2nd/3rd hit; check /metrics for CACHE_HIT_COUNT |
| Cost tracking | Run benchmark query → check metadata.cost_usd is populated |
| Dashboard | `streamlit run dashboard/app.py` → verify all widgets load with live data |
| CI | Open a PR → verify GitHub Actions runs all tests, blocks merge if golden tests fail |

---

## [Dependencies]

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest-asyncio` | `>=0.21.0` | Async test support for parallel grading tests |

---

## [Acceptance Criteria]

| Criterion | Target | How to Measure |
|-----------|--------|----------------|
| Golden test pass rate | ≥ 80% (40/50 queries) | `pytest tests/evaluation/test_golden_set.py` |
| LLM judge threshold | Avg ≥ 8.0/10 | Report from evaluator |
| Regression | Zero breakage of existing 13 tests | `pytest tests/genai/` all green |
| CI gate | Blocks merge on test failure | Open test PR with failing golden test |
| Metric correctness | Recall@K and NDCG@K validated | `pytest tests/test_metrics.py` |
| Cache tests | TTL, hit/miss, thread safety | `pytest tests/test_cache.py` |

---

*Document version: 1.0*
