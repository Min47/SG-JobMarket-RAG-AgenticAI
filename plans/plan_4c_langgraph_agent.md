# Plan 4C: LangGraph Agent

> **Project:** SG Job Market Intelligence Platform
> **Focus:** Conversational AI agent built on LangGraph StateGraph with retrieval, grading, rewriting, and generation nodes
> **Status:** Active

---

## [Overview]

Single sentence: Conversational agent using LangGraph StateGraph to orchestrate retrieval, relevance grading, query rewriting, and answer generation with conditional retry logic.

Multiple paragraphs:
The LangGraph agent provides the conversational interface for the SG Job Market platform. It processes user queries through a stateful graph that retrieves relevant jobs, grades their relevance, optionally rewrites vague queries, and generates cited answers.

The agent is built on a `StateGraph` with four nodes: `retrieve`, `grade`, `generate`, and `rewrite`. A conditional edge `should_rewrite()` determines whether to retry with a reformulated query when document quality is low. The graph supports up to two rewrite attempts before falling back to generation with the best available context.

Key design decisions:
- **Average scoring on all docs**: The rewrite decision uses the average relevance score across ALL retrieved documents (before filtering), not just the passing ones. This prevents the agent from accepting a small set of highly-scored but narrow results when better variety exists.
- **Context limit**: Generation receives only the top 5 graded jobs to stay within token limits while maximizing relevance.
- **Streaming support**: The `JobMarketAgent.stream()` method yields intermediate steps for real-time UI updates.

---

## [Architecture]

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ LANGGRAPH AGENT (genai/agent.py)                                            │
│ ─────────────────────────────────────────────────────────────────────────── │
│ StateGraph with nodes:                                                      │
│                                                                             │
│   ┌─────────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│   │ REP/HRASE   │───▶│ RETRIEVE │───▶│  GRADE   │───▶│ GENERATE │───▶ END │
│   │    GATE     │    └──────────┘    └──────────┘    └──────────┘          │
│   └─────────────┘         │               │                                 │
│        (if needed)        │         (if low score)                        │
│                           │               ▼                                 │
│                           │         ┌──────────┐                            │
│                           └────────▶│ REWRITE  │──────────┐                │
│                                     └──────────┘          │                │
│                                                           ▼                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### State & Graph

- `AgentState` TypedDict with 10 fields:
  - `messages`: Conversation history
  - `query`: Current query text
  - `original_query`: Preserved initial query
  - `retrieved_jobs`: Raw vector search results
  - `graded_jobs`: Filtered and scored jobs
  - `final_answer`: Generated response
  - `rewrite_count`: Number of rewrite attempts (max 2)
  - `average_relevance_score`: Average score across ALL retrieved docs
  - `metadata`: Execution metadata (latency, cost, provider)
  - `was_rephrased`: Whether query standardization was applied

### Conditional Edge Logic

`should_rewrite()` triggers a rewrite if:
- Average relevance score < 6.0 OR
- Number of jobs passing the grade threshold < 3

Maximum 2 rewrites before forcing generation.

---

## [Files]

Single sentence: 1 modified file.

### Modified Files

| File | Changes |
|------|---------|
| `genai/agent.py` | LangGraph StateGraph with retrieve/grade/generate/rewrite nodes |

---

## [Functions]

Single sentence: 4 node functions, 1 conditional edge function, 2 interface functions.

### Node Functions

```python
# genai/agent.py
def rephrase_node(state: AgentState) -> AgentState:
    """Gated query standardization. Calls Gemini 2.5 Flash to:
    - Expand abbreviations (gd → good, wfh → work from home)
    - Normalize slang and informal language
    - Preserve Singapore context
    Only rephrases if should_rephrase() returns True.
    """

def retrieve_node(state: AgentState) -> AgentState:
    """Calls retrieve_jobs() with hybrid search, tracks metrics."""

def grade_node(state: AgentState) -> AgentState:
    """Calls grade_documents(), computes avg on ALL docs for rewrite decision."""

def generate_node(state: AgentState) -> AgentState:
    """Calls generate_answer(), limits context to top 5 jobs."""

def rewrite_node(state: AgentState) -> AgentState:
    """Uses ModelGateway to reformulate query:
    - Adds keywords
    - Expands abbreviations
    - Keeps Singapore context
    """
```

### Conditional Edge

```python
def should_rewrite(state: AgentState) -> Literal["rewrite", "generate"]:
    """Returns 'rewrite' if avg_score < 6.0 OR passed_count < 3, else 'generate'.
    Max 2 rewrites enforced via rewrite_count."""
```

### High-Level Interface

```python
class JobMarketAgent:
    def run(query, conversation_history, filters) -> AgentState:
        """Full graph execution. Returns final state with answer."""
    
    def stream(query, filters) -> Generator[Dict[str, Any], None, None]:
        """Yields intermediate steps for real-time UI."""
```

---

## [Classes]

Single sentence: 2 classes — AgentState TypedDict and JobMarketAgent orchestrator.

### AgentState

```python
class AgentState(TypedDict):
    messages: List[Dict[str, str]]
    query: str
    original_query: str
    retrieved_jobs: List[Dict[str, Any]]
    graded_jobs: List[Dict[str, Any]]
    final_answer: str
    rewrite_count: int
    average_relevance_score: float
    metadata: Dict[str, Any]
    was_rephrased: bool
```

### JobMarketAgent

```python
class JobMarketAgent:
    """Orchestrates the full LangGraph workflow."""
    
    def __init__(self, settings: Optional[Settings] = None)
    def run(self, query: str, conversation_history: List[Dict] = None, 
            filters: Optional[Dict[str, Any]] = None) -> AgentState
    def stream(self, query: str, filters: Optional[Dict[str, Any]] = None) 
            -> Generator[Dict[str, Any], None, None]
```

---

## [Integration Points]

| Component | Integration |
|-----------|-------------|
| **RAG Pipeline** (Plan 4B) | Agent calls `retrieve_jobs()`, `grade_documents()`, `generate_answer()` |
| **Model Gateway** (Plan 4F) | `rewrite_node()` and `generate_node()` use `genai/gateway.py` for LLM calls |
| **Observability** (Plan 4H) | Each node emits trace spans and metrics |
| **Guardrails** (Plan 4D) | Input validated before agent execution; output validated after generation |

---

## [Testing]

Single sentence: Integration tests for graph structure, node execution, and full agent workflow.

### Agent Execution Tests (7 tests)

| Test | Scenario | Target |
|------|----------|--------|
| 1 | High-quality query (no rewrites) | Full execution, high relevance score |
| 2 | Vague query triggers rewrite | Rewrite improves relevance |
| 3 | Query with filters | Metadata preserved through graph |
| 4 | Niche edge case | Graceful handling with limited sources |
| 5 | Performance benchmark | Acceptable average latency |
| 6 | Streaming interface | Real-time step updates |
| 7 | Graph structure validation | All nodes and edges correct |

### Test Files

| File | Tests |
|------|-------|
| `tests/genai/test_agent_graph.py` | Graph structure (3 tests) |
| `tests/genai/test_agent_nodes.py` | Node implementations (integration) |
| `tests/genai/test_agent_execution.py` | Full agent workflow (7 tests) |

---

## [Acceptance Criteria]

| Criterion | Target | How to Measure |
|-----------|--------|----------------|
| Graph structure | All 4 nodes + conditional edges | `test_agent_graph.py` |
| Rewrite logic | Triggers when avg < 6.0 or passed < 3 | `test_agent_execution.py` |
| Max rewrites | Never exceeds 2 | `test_agent_execution.py` |
| Streaming | Yields intermediate steps | `test_agent_execution.py` |
| Context limit | Top 5 jobs sent to generation | Code review |
| Average scoring | Computed on ALL docs pre-filter | Code review |
| Rephrase gate | Triggers on abbreviations/slang | `test_agent_execution.py` |

---

*Document version: 1.0*
