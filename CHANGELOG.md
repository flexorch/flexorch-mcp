# Changelog

All notable changes to `flexorch-mcp` are documented here.

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
