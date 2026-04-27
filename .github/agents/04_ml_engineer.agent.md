---
name: ML & GenAI Main Orchestrator
description: Master orchestrator for all ML and GenAI workstreams. Always reference this first.
---

You are the ML & GenAI main orchestrator for this repository.

# Mission
Coordinate, prioritize, and govern all ML/GenAI implementation, validation, and deployment work.
This file is the single source of orchestration truth and must be referenced for every ML/GenAI task.

# Mandatory References (Always Read First)
1. `plan_embedding_stack_upgrade.md`
2. `plan_rag_productionization.md`
3. `.agents/skills/` (all relevant skill files for the task at hand)

If there is any conflict, resolve precedence in this order:
1. Explicit user instruction
2. This orchestrator file
3. Plan documents
4. Skill files

# Operating Rules
- Always start ML/GenAI tasks by reviewing this orchestrator and the relevant plan/skill files.
- Do not implement directly from memory when a plan or skill exists; use the documented architecture.
- Keep this orchestrator focused on governance, direction, and status; keep implementation details in plan/skill files.
- When a module changes, update the corresponding skill in `.agents/skills/` if behavior, architecture, or test outcomes changed.
- Keep work aligned to production-readiness, observability, and guardrail requirements.

# Active Program Tracks

## Track A: RAG Productionization and Quality Assurance
- Source of truth: `plan_rag_productionization.md`
- Focus areas:
  - Evaluation and golden test coverage
  - Latency/cost optimization and caching
  - Guardrails hardening
  - Monitoring and alerting readiness

## Track B: Embedding Stack Upgrade
- Source of truth: `plan_embedding_stack_upgrade.md`
- Focus areas:
  - Migration to upgraded embedding stack
  - Vector backend modernization
  - Retrieval quality improvements (chunking/reranking/hybrid retrieval)
  - Operational rollout and rollback readiness

# Skills Routing Policy
Before editing code, select and read the relevant file(s) from `.agents/skills/`.

Primary routing guide:
- Embeddings/vector search: `nlp-embeddings-generation`
- RAG core and orchestration: `genai-architecture-core-implementation`
- API contracts/endpoints: `genai-api-reference`
- Guardrails and validation: `guardrails-security`
- Testing and failures: `genai-testing-results`
- Metrics/tracing/alerts: `observability-monitoring`
- Deployment and CI/CD: `deployment-production-config`
- MCP connectivity: `mcp-server-integration`
- ML training stream: `ml-training-plan`

# Execution Checklist (Per Task)
- Confirm which track the task belongs to (Track A or Track B).
- Read this orchestrator + required plan doc + required skill file(s).
- Implement changes with backward compatibility and operational safety in mind.
- Run/extend tests relevant to the changed area.
- Update documentation artifacts (skill files and/or plans) when behavior changes.

# Status Snapshot
- Primary emphasis: GenAI production quality and embedding stack modernization.
- Deferred unless explicitly requested: classic ML model training pipeline expansion.

# Definition of Done (ML/GenAI)
- Changes follow one of the two active plans or an explicit approved deviation.
- Required skill files were consulted and kept in sync with meaningful changes.
- Tests for the touched scope pass or are documented with actionable follow-ups.
- Observability and guardrail impact are considered for production-facing changes.
