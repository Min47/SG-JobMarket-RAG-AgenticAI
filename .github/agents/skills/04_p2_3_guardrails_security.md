# Phase 2.5: Guardrails & Security

> Reference this file when working on: input/output validation, PII detection, injection blocking, or modifying security policies.

---

## Input Guards (`InputGuardrails`)

File: `genai/guardrails.py`

| Guard | Patterns | Action |
|-------|----------|--------|
| PII Detection | Singapore NRIC (S/T/F/G + 7 digits + checksum), phone (+65/8-9xxxxxxx), email, credit cards | Block + redact |
| Prompt Injection | "ignore previous instructions", "forget everything", system prompt overrides, override commands | Block |
| SQL Injection | `; UNION/SELECT/DROP`, `--` comments, `' OR '1'='1'`, `OR 1=1` | Block |
| Length Limits | Min 3 chars, max 1000 chars | Block |

## Output Guards (`OutputGuardrails`)

| Guard | Check | Action |
|-------|-------|--------|
| Hallucination | Verify cited `job_id`s exist in context jobs | Warning (logged) |
| Empty Response | Answer is empty/whitespace | Block |
| Length | Response > 5000 chars | Warning |

## Architecture Decision: Custom Regex

- **Considered**: `rebuff`, `sqlparse`
- **Chosen**: Custom regex (industry standard for production)
- **Reasons**: Lightweight, no dependencies, <5ms, full control, auditable
- Enterprise solutions (AWS Bedrock Guardrails, Azure Content Safety) also use rule-based systems

## Severity Levels

- `BLOCKED` → HTTP 400/500 (request rejected)
- `WARNING` → logged but allowed through
