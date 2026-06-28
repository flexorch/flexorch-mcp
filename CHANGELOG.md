# Changelog

All notable changes to `flexorch-mcp` are documented here.

---

## [0.1.9] — 2026-06-28

### Fixed
- `__init__.py` now reads `__version__` from package metadata via `importlib.metadata` — eliminates manual version sync and the 0.1.6/0.1.8 mismatch bugs
- Add `scripts/bump_version.py`: single command updates pyproject.toml, server.json, server-card.json atomically

---

## [0.1.8] — 2026-06-28

### Fixed
- Add `outputSchema` and `annotations` to all 6 tools in `server-card.json` — Smithery reads this file as fallback and was scoring output_scheme and annotation as failing because they were absent

---

## [0.1.7] — 2026-06-28

### Changed
- Remove `flexorch.` root prefix from all 6 tool names — tools are now `document.process`, `job.status`, `job.result`, `dataset.build`, `dataset.search`, `dataset.export`
- Fixes Smithery naming score: all tools previously shared a single root node (`flexorch`), which Smithery treats as a flat list; two-level tree (`document.*`, `job.*`, `dataset.*`) satisfies the navigable-tree criterion
- Update README tool table and example workflow, server-card.json, and server instructions to reflect new names

---

## [0.1.6] — 2026-06-27

### Changed
- Rename all 6 MCP tools to dot-notation tree format for Smithery naming convention
  (`flexorch.document.process`, `flexorch.job.status`, `flexorch.job.result`,
  `flexorch.dataset.build`, `flexorch.dataset.search`, `flexorch.dataset.export`)

---

## [0.1.5] — 2026-06-27

### Changed
- Rename all 6 MCP tools with `flexorch_` prefix for Smithery naming convention (e.g. `flexorch_process_document`)
- Update server instructions and docstring cross-references to use prefixed names

---

## [0.1.4] — 2026-06-26

### Added
- `FLEXORCH_BASE_URL` environment variable support: set a custom API base URL (e.g. staging or self-hosted) via env var; server passes it to the HTTP client automatically
- `smithery.yaml`: optional `baseUrl` configSchema field surfaces `FLEXORCH_BASE_URL` to Smithery's UI installer

---

## [0.1.3] — 2026-06-25

### Added
- HTTP transport mode: `MCP_TRANSPORT=http` starts a Streamable HTTP server with per-request API key isolation via `ContextVar` (`Authorization: Bearer`, `X-API-KEY`, `?api_key=` all accepted)
- `Dockerfile` for containerized HTTP deployment

---

## [0.1.2] — 2026-06-25

### Changed
- Add MCP Registry ownership token to README (required for `registry.modelcontextprotocol.io` listing)
- Update `server.json` to reference v0.1.2

---

## [0.1.1] — 2026-06-25

### Changed
- Tool descriptions rewritten for Anthropic MCP marketplace quality standards: explicit step numbers (Step 1–5), mandatory polling guidance, parameter constraints, and next-step routing in every docstring
- Server instructions expanded with numbered workflow steps and async reminder
- Error messages improved: `TRIAL_EXPIRED` now includes actionable link, `NOT_FOUND` lists all ID types
- `get_job_status` poll_hint corrected to list only MCP-supported text formats (jsonl/csv/json/xml/md/rag), removing xlsx and hf which are binary-only

### Added
- Error codes: `UNAUTHORIZED`, `PROCESSING_FAILED`, `VALIDATION_ERROR` added to error map
- `process_document` ValueError (invalid URL scheme) now returns a user-friendly message instead of the raw exception string

### Fixed
- `process_document` ValueError message no longer leaks internal exception text

---

## [0.1.0] — 2026-06-24

### Added
- `process_document` tool — download from URL and process via FlexOrch pipeline (PDF, DOCX, TXT, XLSX, HTML, XML, EML, JPG, PNG, TIFF); 50 MB limit
- `get_job_status` tool — poll job status until completed or failed; handles data_process and dataset_build job types
- `get_extraction_result` tool — retrieve all extracted records directly from execution response; up to 100 records inline, `has_more` hint for larger sets
- `build_dataset` tool — build a structured dataset from a completed execution
- `search_documents` tool — full-text and semantic search across indexed datasets; supports auto/structured/semantic/hybrid modes (semantic/hybrid requires Pro+)
- `export_dataset` tool — export datasets as inline text content; supported formats: JSONL, CSV, JSON, MD, XML, RAG (LangChain/LlamaIndex chunks)
- `flexorch-mcp --check` CLI command for API key validation and connection verification
- Structured error messages for all FlexOrch API error codes (QUOTA_EXCEEDED, RATE_LIMIT_EXCEEDED, INVALID_API_KEY, etc.)
- Claude Desktop and Cursor configuration examples
