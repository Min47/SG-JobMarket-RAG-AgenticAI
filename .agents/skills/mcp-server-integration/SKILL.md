---
name: mcp-server-integration
description: Reference this file when working on MCP protocol, Cursor IDE integration, or external AI assistant connectivity.
---

# Phase 2.7: MCP Server Integration

## Implementation

File: `genai/mcp_server.py`

- MCP SDK integration with `@server.list_tools()` and `@server.call_tool()` handlers
- 4 tools exposed: `search_jobs_tool`, `get_job_details_tool`, `aggregate_stats_tool`, `find_similar_jobs_tool`
- Stdio transport for Cursor IDE
- Response truncation for large payloads (>50KB) — job descriptions capped at 500 chars
- Reuses existing `genai/tools/` adapters (no code duplication)

## Tools

| Tool | Purpose |
|------|---------|
| `search_jobs_tool` | Semantic search with filters (location, salary, work_type, classification) |
| `get_job_details_tool` | Full job info by ID + source |
| `aggregate_stats_tool` | Salary statistics grouped by classification/location/work_type |
| `find_similar_jobs_tool` | Semantic similarity from a reference job |

## Cursor IDE Configuration

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

## Test Results (7 tests)

| Test | Tool | Result | Details |
|------|------|--------|---------|
| 1 | Server Config | ✅ | Server name + 4 tools registered |
| 2 | Tool Discovery | ✅ | All tools discovered |
| 3 | Search Jobs | ✅ | 3 jobs found (9.1s with model load) |
| 4 | Get Job Details | ✅ | Job details retrieved correctly |
| 5 | Aggregate Stats | ⚠️ | Working but JSON parse issue in test |
| 6 | Find Similar | ✅ | 3 similar jobs (similarity 0.759) |
| 7 | Error Handling | ✅ | Invalid ID handled gracefully |

## Usage

```bash
# Stdio mode (default for Cursor)
python -m genai.mcp_server

# HTTP mode (optional)
python -m genai.mcp_server --transport http --port 8001
```
