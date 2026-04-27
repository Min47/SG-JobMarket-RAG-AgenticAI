# Plan 4D: Guardrails & Security

> **Project:** SG Job Market Intelligence Platform
> **Focus:** Input validation, PII detection, injection blocking, output hallucination checking, and semantic guardrail hooks
> **Status:** Active

---

## [Overview]

Single sentence: Multi-layer guardrail system protecting the GenAI pipeline from malicious input, data leakage, and hallucinated output.

Multiple paragraphs:
The guardrails system provides defense-in-depth for the GenAI stack. Input guardrails validate user queries before they reach the RAG pipeline, blocking PII, prompt injection, SQL injection, and invalid-length inputs. Output guardrails verify generated answers for hallucinations, empty responses, and excessive length.

The current implementation uses custom regex-based guards. This is an intentional architecture decision: custom regex is lightweight (<5ms), has no external dependencies, and is fully auditable. Enterprise solutions like AWS Bedrock Guardrails and Azure Content Safety also use rule-based systems as their foundation.

A semantic guardrail layer (`SemanticGuardrails`) provides future-proof hooks for intent-based input checking and output content moderation. The current implementation uses lightweight keyword heuristics as a fallback, with the ability to swap in LLM-based or enterprise guardrail APIs later.

---

## [Architecture]

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ INPUT GUARDRAILS (genai/guardrails.py)                                      │
│ ─────────────────────────────────────────────────────────────────────────── │
│ 1. PII Detection        → Singapore NRIC, phone, email, credit cards       │
│ 2. Prompt Injection     → "ignore previous", system overrides              │
│ 3. SQL Injection        → UNION/SELECT/DROP, OR 1=1                        │
│ 4. Length Limits        → Min 3 chars, max 1000 chars                      │
│ 5. Semantic Intent      → Lightweight keyword heuristics (new)             │
│ 6. Rate Limit           → Per-user token bucket (new)                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
                         [BLOCKED or ALLOWED]
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ RAG PIPELINE → GENERATION                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ OUTPUT GUARDRAILS (genai/guardrails.py)                                     │
│ ─────────────────────────────────────────────────────────────────────────── │
│ 1. Hallucination        → Verify cited job_ids exist in context            │
│ 2. Empty Response       → Block empty/whitespace answers                   │
│ 3. Length               → Warn if response > 5000 chars                    │
│ 4. Content Moderation   → Toxicity keyword check (new)                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## [Files]

Single sentence: 1 new file, 1 modified file.

### New Files

| File | Purpose |
|------|---------|
| `genai/guardrails_semantic.py` | Semantic guardrail hooks + output content moderation |

### Modified Files

| File | Changes |
|------|---------|
| `genai/guardrails.py` | Call semantic guardrail hooks after regex checks; add output content moderation step |

---

## [Input Guards]

File: `genai/guardrails.py`

| Guard | Patterns | Action |
|-------|----------|--------|
| PII Detection | Singapore NRIC (S/T/F/G + 7 digits + checksum), phone (+65/8-9xxxxxxx), email, credit cards | Block + redact |
| Prompt Injection | "ignore previous instructions", "forget everything", system prompt overrides, override commands | Block |
| SQL Injection | `; UNION/SELECT/DROP`, `--` comments, `' OR '1'='1'`, `OR 1=1` | Block |
| Length Limits | Min 3 chars, max 1000 chars | Block |
| Semantic Intent | Lightweight keyword heuristics for intent beyond regex | Block |
| Rate Limit | Per-user token bucket (in-memory) | Block |

---

## [Output Guards]

File: `genai/guardrails.py`

| Guard | Check | Action |
|-------|-------|--------|
| Hallucination | Verify cited `job_id`s exist in context jobs | Warning (logged) |
| Empty Response | Answer is empty/whitespace | Block |
| Length | Response > 5000 chars | Warning |
| Content Moderation | Toxicity keyword list | Block |

---

## [Severity Levels]

- `BLOCKED` → HTTP 400/500 (request rejected)
- `WARNING` → logged but allowed through

---

## [Architecture Decision: Custom Regex]

- **Considered**: `rebuff`, `sqlparse`
- **Chosen**: Custom regex (industry standard for production)
- **Reasons**: Lightweight, no dependencies, <5ms execution, full control, auditable
- Enterprise solutions (AWS Bedrock Guardrails, Azure Content Safety) also use rule-based systems

---

## [Functions]

Single sentence: 2 new functions, 2 modified class methods.

### New Functions

```python
# genai/guardrails_semantic.py
def semantic_input_check(query: str) -> Optional[str]:
    """Placeholder semantic guardrail: checks intent beyond regex patterns.
    Returns violation type or None."""

def moderate_output(answer: str) -> Dict[str, Any]:
    """Lightweight keyword-based output moderation.
    Returns {safe: bool, flagged_categories: List[str]}."""
```

### Modified Class Methods

```python
# genai/guardrails.py — InputGuardrails
class InputGuardrails:
    """Add semantic check after existing regex checks."""
    
    def validate(self, query: str) -> ValidationResult:
        # Existing: regex PII, injection, length checks
        # NEW: call SemanticGuardrails.check_input_intent()
        # NEW: call SemanticGuardrails.check_rate_limit()

# genai/guardrails.py — OutputGuardrails
class OutputGuardrails:
    """Add output moderation after hallucination check."""
    
    def validate(self, answer: str, context_jobs: List[Dict]) -> ValidationResult:
        # Existing: hallucination, empty, length checks
        # NEW: call SemanticGuardrails.check_output_safety()
```

---

## [Classes]

Single sentence: 1 new class, 2 modified classes.

### New Classes

```python
# genai/guardrails_semantic.py
class SemanticGuardrails:
    """Future-proof semantic guardrail layer.
    Currently uses lightweight heuristics + keyword fallback.
    Can be swapped for LLM-based or enterprise guardrail API later."""
    
    def check_input_intent(self, query: str) -> Optional[str]
    def check_output_safety(self, text: str) -> Dict[str, Any]
    def check_rate_limit(self, user_id: str, endpoint: str) -> bool
```

### Modified Classes

See [Functions] section above for `InputGuardrails.validate()` and `OutputGuardrails.validate()` modifications.

---

## [Integration with FastAPI]

Guardrails are integrated into the FastAPI layer (see Plan 4F):
- Input validation before agent execution (PII, injection)
- Output validation after generation (hallucination check)
- `BLOCKED` severity → HTTP 400/500
- `WARNING` severity → logged but allowed through

API test coverage:
- Chat blocks malicious → Returns 400 for PII/injection
- Chat allows normal → 200 OK, full agent response
- Search blocks malicious → Returns 400 for PII/injection
- Search allows normal → 200 OK, job results
- Pydantic validation → Returns 422 for empty/long queries
- Health unaffected → 200 OK, no guardrail interference

---

## [Testing]

Single sentence: 10 guardrail tests covering input/output validation and API integration.

### Guardrails Tests (10 tests)

| Test | Type | Endpoint | Target |
|------|------|----------|--------|
| 1 | PII Detection | Core | NRIC/phone/email detected, redacted |
| 2 | Injection Detection | Core | Prompt + SQL injection blocked |
| 3 | Input Guardrails | Core | Length/PII/injection validation |
| 4 | Output Guardrails | Core | Hallucination detection, structure validation |
| 5 | Chat Blocks Malicious | API POST /v1/chat | Returns 400 for PII/injection |
| 6 | Chat Allows Normal | API POST /v1/chat | 200 OK, full agent response |
| 7 | Search Blocks Malicious | API POST /v1/search | Returns 400 for PII/injection |
| 8 | Search Allows Normal | API POST /v1/search | 200 OK, job results |
| 9 | Pydantic Validation | API POST /v1/chat | Returns 422 for empty/long queries |
| 10 | Health Unaffected | API GET /health | 200 OK, no guardrail interference |

### New Tests

| File | Tests |
|------|-------|
| `tests/test_guardrails_semantic.py` | Intent check, output moderation, rate limit |

---

## [Acceptance Criteria]

| Criterion | Target | How to Measure |
|-----------|--------|----------------|
| PII detection | NRIC, phone, email blocked | Test #1-3 |
| Injection blocking | Prompt + SQL injection blocked | Test #2 |
| Input length | Min 3, max 1000 enforced | Test #3, #9 |
| Hallucination detection | Cited job_ids verified | Test #4 |
| API integration | 400 for blocked, 200 for valid | Test #5-8 |
| Semantic hooks | Intent and moderation called | `test_guardrails_semantic.py` |
| Performance | <5ms per guard check | Benchmark |

---

*Document version: 1.0*
