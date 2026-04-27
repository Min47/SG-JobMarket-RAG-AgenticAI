# Plan 4E: Tools & MCP Server

> **Project:** SG Job Market Intelligence Platform
> **Focus:** LangChain tool adapters for job search and MCP server integration for external AI assistants (Cursor IDE)
> **Status:** Active

---

## [Overview]

Single sentence: Four LangChain tool adapters for job search and statistics, exposed via MCP server for Cursor IDE integration.

Multiple paragraphs:
The tools layer provides reusable, type-safe adapters for searching jobs, retrieving job details, aggregating salary statistics, and finding similar jobs. These tools are built with LangChain's `@tool` decorator and Pydantic `args_schema` for automatic input validation.

The MCP (Model Context Protocol) server exposes these same four tools over stdio transport, enabling external AI assistants like Cursor IDE to query the SG Job Market database directly. The MCP server reuses the existing tool adapters with no code duplication.

All tools include safety measures: input validation via Pydantic, timeout handling (30s max per BigQuery query), source normalization (jobstreet/JobStreet → JobStreet, mcf/MCF → MCF), and parameterized SQL for injection safety.

---

## [Architecture]

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ TOOL ADAPTERS (genai/tools/)                                                │
│ ─────────────────────────────────────────────────────────────────────────── │
│ @tool search_jobs     → BigQuery Vector Search + filters                    │
│ @tool get_job_details → Fetch full job info by ID                           │
│ @tool aggregate_stats → Salary ranges, job counts by category               │
│ @tool similar_jobs    → Find N most similar jobs to a given job             │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ MCP SERVER (genai/mcp_server.py)                                            │
│ ─────────────────────────────────────────────────────────────────────────── │
│ • MCP SDK integration with @server.list_tools() and @server.call_tool()    │
│ • 4 tools exposed: search_jobs_tool, get_job_details_tool,                 │
│   aggregate_stats_tool, find_similar_jobs_tool                             │
│ • Stdio transport for Cursor IDE                                            │
│ • Response truncation for large payloads (>50KB)                            │
│ • Reuses genai/tools/ adapters (no code duplication)                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## [Files]

Single sentence: 4 tool files and 1 MCP server file.

### Tool Adapter Files

| File | Purpose |
|------|---------|
| `genai/tools/__init__.py` | Module exports |
| `genai/tools/_validation.py` | Shared Pydantic schemas |
| `genai/tools/search.py` | `search_jobs`, `get_job_details` |
| `genai/tools/stats.py` | `aggregate_stats` |
| `genai/tools/recommendations.py` | `find_similar_jobs` |

### MCP Server File

| File | Purpose |
|------|---------|
| `genai/mcp_server.py` | MCP SDK server with stdio transport |

---

## [Tools]

### search_jobs

- Vector search with filters (location, salary, work_type, classification)
- Wraps `retrieve_jobs()` from `genai/rag.py`
- Returns ranked job listings with metadata

### get_job_details

- BigQuery SELECT by job_id + source
- Returns full job description, salary, location, requirements

### aggregate_stats

- GROUP BY classification/location/work_type with salary percentiles
- Returns salary statistics and job counts

### find_similar_jobs

- VECTOR_SEARCH from reference job's embedding
- Returns N most similar jobs with similarity scores

---

## [Safety]

- Input validation via Pydantic (all tools)
- Timeout handling (30s max per BigQuery query)
- Source normalization (jobstreet/JobStreet → JobStreet, mcf/MCF → MCF)
- Parameterized SQL (injection-safe)
- Error responses: `{"success": false, "error": "..."}`

---

## [MCP Server Details]

### Implementation

- MCP SDK integration with `@server.list_tools()` and `@server.call_tool()` handlers
- Response truncation for large payloads (>50KB) — job descriptions capped at 500 chars
- Reuses existing `genai/tools/` adapters (no code duplication)

### Exposed Tools

| Tool | Purpose |
|------|---------|
| `search_jobs_tool` | Semantic search with filters (location, salary, work_type, classification) |
| `get_job_details_tool` | Full job info by ID + source |
| `aggregate_stats_tool` | Salary statistics grouped by classification/location/work_type |
| `find_similar_jobs_tool` | Semantic similarity from a reference job |

### Cursor IDE Configuration

```json
{
  "mcpServers": {
    "sg-job-market": {
      "command": "python",
      "args": ["-m", "genai.mcp_server"],
      "cwd": "/path/to/SG_Job_Market"
    }
  }
}
```

Windows config path: `%APPDATA%\Claude\claude_desktop_config.json`

### Usage

```bash
# Stdio mode (default for Cursor)
python -m genai.mcp_server

# HTTP mode (optional)
python -m genai.mcp_server --transport http --port 8001
```

---

## [Testing]

### MCP Server Tests (7 tests)

| Test | Tool | Target | Details |
|------|------|--------|---------|
| 1 | Server Config | ✅ | Server name + 4 tools registered |
| 2 | Tool Discovery | ✅ | All tools discovered |
| 3 | Search Jobs | ✅ | Jobs found with model load |
| 4 | Get Job Details | ✅ | Job details retrieved correctly |
| 5 | Aggregate Stats | ⚠️ | Working but JSON parse issue in test |
| 6 | Find Similar | ✅ | Similar jobs with similarity score |
| 7 | Error Handling | ✅ | Invalid ID handled gracefully |

### Tool Adapter Tests

| File | Tests |
|------|-------|
| `tests/genai/test_tools.py` | Tool adapters (4 tests) |

---

## [Acceptance Criteria]

| Criterion | Target | How to Measure |
|-----------|--------|----------------|
| All 4 tools discoverable | MCP server lists all tools | Test #2 |
| search_jobs returns results | Jobs found with valid query | Test #3 |
| get_job_details correct | Full details by ID | Test #4 |
| aggregate_stats working | Stats returned, JSON issue tracked | Test #5 |
| find_similar correct | Similarity scores present | Test #6 |
| Error handling graceful | Invalid IDs handled | Test #7 |
| No code duplication | MCP reuses tool adapters | Code review |
| Response truncation | Large payloads capped at 500 chars | Code review |

---

*Document version: 1.0*
