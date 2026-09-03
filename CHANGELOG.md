# Changelog

All notable changes to `flexorch-mcp` are documented here.

---

## [0.2.3] — 2026-09-03

### Added
- `get_job_status` and `get_extraction_result` now include `pii_type_summary` — a per-type breakdown of detected PII (e.g. `{"email": 2, "national_id_tr": 1}`), covering all 47 PII types the platform detects. Previously only aggregate `pii_found`/`pii_masked`/`pii_count` were surfaced; the type-level detail was already on the API (`output_summary.pii_type_summary` on `GET /executions/{id}`) but neither tool read it. `get_job_status` needed a companion backend fix (`execution_summary.privacy.pii_type_summary` on `GET /jobs/{id}`, `flexorch-core` 2026-09-03) since the job endpoint never had this field to relay at all.

---

## [0.2.2] — 2026-08-26

### Fixed
- `--check` — was calling a non-existent endpoint (`/usage/current`) and always failed with a 404, even with a valid API key and working connection. Now calls the correct `GET /usage`.
- `--check` — even past the wrong path, the response envelope was never unwrapped and `plan`/`credits_limit` were read from the wrong (non-existent) keys, so a successful call still printed `Plan: Unknown (0 credits/mo)`. Now reads `data.plan` and `data.usage.credits.limit` correctly.
- `--check` — printing the ✓/✗ status glyphs crashed with `UnicodeEncodeError` on Windows terminals using a non-UTF-8 codepage (the common default). `--check` now reconfigures stdout/stderr to UTF-8 before printing.

## [0.2.1] — 2026-08-06

### Added
- `get_job_status` (Tool 2) — `degraded` field on completed `data_process` results. `true` when the underlying pipeline execution completed but structured extraction found no table/schema in the document (e.g. a short or non-tabular document). Quality/PII results are still meaningful. `poll_hint` now includes a note that `build_dataset()` doesn't apply when degraded.
- `get_extraction_result` (Tool 3) — `degraded` field on the response. When degraded and there are no records, `fields_hint` explains why instead of suggesting `build_dataset()` (which would fail with `NO_OUTPUT_DATA`).

---

## [0.2.0] — 2026-07-05

### Added
- `dataset.index` (Tool 7) — trigger semantic vector indexing for a dataset (Pro+ plan required); returns status + `index_hint` prompt for next step
- `dataset.chunks` (Tool 8) — retrieve paginated RAG-ready text chunks from an indexed dataset; supports `min_quality` (A/B/C/D), `pii_masked_only`, `page`, `page_size` (max 100); Pro+ plan required
- `IndexResult` and `ChunksResult` Pydantic output models for structured MCP responses
- `server-card.json` updated to reflect 8 tools and v0.2.0
- Total tool count: **8** (was 6)

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
