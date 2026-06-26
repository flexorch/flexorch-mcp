# flexorch-mcp

<!-- mcp-name: io.github.dev-flexorch/flexorch-mcp -->

[![PyPI version](https://badge.fury.io/py/flexorch-mcp.svg)](https://pypi.org/project/flexorch-mcp/)
[![CI](https://github.com/flexorch/flexorch-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/flexorch/flexorch-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**MCP server for FlexOrch — SDK for machines.**

Connect Claude and other MCP-compatible agents to the [FlexOrch](https://flexorch.com) document intelligence pipeline. Process documents, extract structured data, detect PII, and export LLM-ready datasets — all through natural language tool calls.

---

## What this is

`flexorch-mcp` is a thin proxy that exposes the FlexOrch API as MCP tools. All processing happens on FlexOrch's managed infrastructure. A FlexOrch account and API key are required.

**For humans writing code:** use [flexorch-sdk](https://github.com/flexorch/flexorch-sdk) (Python) or [flexorch-sdk-js](https://github.com/flexorch/flexorch-sdk-js) (TypeScript).  
**For agents:** use this package.

---

## Tools

| Tool | Description |
|------|-------------|
| `process_document` | Upload and process a document (PDF, DOCX, TXT, XLSX, HTML, XML, EML, JPG, PNG, TIFF) |
| `get_job_status` | Poll a processing job until completed or failed |
| `get_extraction_result` | Get structured extracted fields from a completed job |
| `build_dataset` | Build a structured dataset from a completed execution |
| `search_documents` | Semantic search across indexed datasets (Pro+) |
| `export_dataset` | Export a dataset as JSONL, CSV, JSON, XML, MD, or RAG (LangChain/LlamaIndex chunks) |

---

## Installation

```bash
pip install flexorch-mcp
```

Requires Python 3.10+.

---

## Configuration

### Claude Desktop

Add to `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "flexorch": {
      "command": "flexorch-mcp",
      "env": {
        "FLEXORCH_API_KEY": "dfx_your_key_here"
      }
    }
  }
}
```

### Cursor

Add to your Cursor MCP config:

```json
{
  "flexorch": {
    "command": "flexorch-mcp",
    "env": {
      "FLEXORCH_API_KEY": "dfx_your_key_here"
    }
  }
}
```

Get your API key from [app.flexorch.com/settings](https://app.flexorch.com/settings).

---

## Verify connection

```bash
flexorch-mcp --check
# → FlexOrch API key: dfx_xxx*** ✓
# → Connection: OK (api.flexorch.com)
# → Plan: Starter (1,200 credits/mo)
# → Tools: 6 registered
```

---

## Example agent workflow

```
User: "Process this invoice and export it as JSONL for fine-tuning."

Agent:
  1. process_document(file_url="https://...")   → job_id: 1234
  2. get_job_status(1234)                        → completed, execution_id: 567
  3. get_extraction_result(567)                  → vendor, total, date, PII masked
  4. build_dataset(execution_id=567)             → job_id: 1235
  5. get_job_status(1235)                        → completed, dataset_id: 89
  6. export_dataset(89, format="jsonl")          → inline JSONL content
```

---

## Plan limits

All FlexOrch plan limits apply to MCP tool calls. Credits are consumed per document processed.

| Plan | Credits/mo | Semantic search |
|------|-----------|----------------|
| Trial | 1,200 (30 days) | — |
| Starter | 1,200 | — |
| Pro | 6,000 | ✓ |
| Enterprise | Custom | ✓ |

---

## Security

- API key is read from the `FLEXORCH_API_KEY` environment variable — never passed as a tool argument
- No data is stored or cached by this server — stateless proxy
- PII masking is applied by FlexOrch's pipeline before results are returned
- All communication with `api.flexorch.com` uses HTTPS

---

## Related

- [flexorch-audit](https://github.com/flexorch/flexorch-audit) — Standalone PII detection and document quality scoring (no account required)
- [flexorch-sdk](https://github.com/flexorch/flexorch-sdk) — Python SDK for developers
- [flexorch-sdk-js](https://github.com/flexorch/flexorch-sdk-js) — TypeScript SDK for developers
- [docs.flexorch.com](https://docs.flexorch.com) — Full documentation

---

## License

MIT — see [LICENSE](LICENSE).
