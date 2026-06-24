from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from .client import FlexOrchMCPClient
from .errors import FlexOrchAPIError
from .tools import process as tools_process
from .tools import status as tools_status
from .tools import result as tools_result
from .tools import build as tools_build
from .tools import search as tools_search
from .tools import export as tools_export

_TOOLS_COUNT = 6

# Shared async client — created once per process, reuses connection pool.
_api_client: FlexOrchMCPClient | None = None


def _get_client() -> FlexOrchMCPClient:
    global _api_client
    if _api_client is None:
        api_key = os.environ.get("FLEXORCH_API_KEY", "")
        _api_client = FlexOrchMCPClient(api_key)
    return _api_client

mcp = FastMCP(
    "flexorch",
    instructions=(
        "FlexOrch processes documents through an AI pipeline: "
        "classify → extract structured fields → detect & mask PII → score quality. "
        "Typical workflow: process_document → get_job_status (poll) → "
        "get_extraction_result → build_dataset → export_dataset."
    ),
)


# ---------------------------------------------------------------------------
# Tool 1: process_document
# ---------------------------------------------------------------------------

@mcp.tool()
async def process_document(
    file_url: str,
    mask_pii: bool = True,
    document_type: str = "auto",
) -> dict[str, Any]:
    """Upload and process a document through the FlexOrch pipeline.

    Downloads the document from file_url, then sends it to FlexOrch for
    classification, structured extraction, PII detection/masking and quality
    scoring. Returns a job_id — poll with get_job_status until completed.

    Args:
        file_url: Publicly accessible URL of the document (http/https only).
                  Supports PDF, DOCX, TXT, XLSX, HTML, XML, EML, JPG, PNG, TIFF.
        mask_pii: Mask detected PII in output. Default: true.
        document_type: Classification hint. Auto-detected if omitted.
                       Values: invoice, expense_report, purchase_order,
                       sales_proposal, bank_statement, payroll, auto.
    """
    return await tools_process.run(_get_client(), file_url, mask_pii, document_type)


# ---------------------------------------------------------------------------
# Tool 2: get_job_status
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_job_status(job_id: int) -> dict[str, Any]:
    """Check the status of a document processing job.

    Poll every 3–5 seconds until status is 'completed' or 'failed'.

    Args:
        job_id: Job ID returned by process_document or build_dataset.
    """
    return await tools_status.run(_get_client(), job_id)


# ---------------------------------------------------------------------------
# Tool 3: get_extraction_result
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_extraction_result(execution_id: int) -> dict[str, Any]:
    """Return the structured extracted fields from a completed processing job.

    Use execution_id from the get_job_status completed response.
    Masked fields are returned as [MASKED_TYPE] placeholders — raw PII is
    never exposed.

    Args:
        execution_id: Execution ID from get_job_status output.
    """
    return await tools_result.run(_get_client(), execution_id)


# ---------------------------------------------------------------------------
# Tool 4: build_dataset
# ---------------------------------------------------------------------------

@mcp.tool()
async def build_dataset(
    execution_id: int,
    name: str = "",
    description: str = "",
) -> dict[str, Any]:
    """Build a structured dataset from a completed processing execution.

    Returns a job_id to poll with get_job_status. Once completed, the response
    includes dataset_id — use export_dataset to retrieve all records.

    Args:
        execution_id: Execution ID from get_job_status or get_extraction_result.
        name: Dataset name. Auto-generated if omitted.
        description: Optional dataset description.
    """
    return await tools_build.run(_get_client(), execution_id, name, description)


# ---------------------------------------------------------------------------
# Tool 5: search_documents
# ---------------------------------------------------------------------------

@mcp.tool()
async def search_documents(
    query: str,
    top_k: int = 5,
    mode: str = "auto",
    document_type: str = "",
    language: str = "",
    quality_grade: str = "",
) -> dict[str, Any]:
    """Search across all indexed datasets using structured or semantic search.

    Structured search (all plans): keyword/field matching.
    Semantic/hybrid search (Pro+): vector similarity via pgvector.
    mode='auto' selects automatically based on document type and plan.

    Args:
        query: Natural language or keyword search query (max 1000 chars).
        top_k: Number of results to return. Default: 5, max: 50.
        mode: Search mode — auto, structured, semantic, hybrid. Default: auto.
        document_type: Filter by document type (optional).
        language: Filter by language ISO 639-1 code (optional).
        quality_grade: Filter by quality grade A/B/C/D (optional).
    """
    return await tools_search.run(
        _get_client(), query, top_k, mode, document_type, language, quality_grade
    )


# ---------------------------------------------------------------------------
# Tool 6: export_dataset
# ---------------------------------------------------------------------------

@mcp.tool()
async def export_dataset(
    dataset_id: int,
    format: str = "jsonl",
) -> dict[str, Any]:
    """Export a built dataset and return its full content as text.

    Text formats (jsonl, csv, json, md, xml, rag) are returned inline.
    Binary formats (parquet, hf) are not supported via MCP — download
    them directly from the FlexOrch API.

    rag format returns LangChain/LlamaIndex-compatible chunked JSON.
    jsonl format is optimized for LLM fine-tuning.

    Args:
        dataset_id: Dataset ID from get_job_status (dataset_build completed).
        format: Export format — jsonl, csv, json, md, xml, rag. Default: jsonl.
    """
    return await tools_export.run(_get_client(), dataset_id, format)


# ---------------------------------------------------------------------------
# --check helper
# ---------------------------------------------------------------------------

async def _run_check() -> int:
    """Validate API key and connectivity; print status report. Returns exit code."""
    api_key = os.environ.get("FLEXORCH_API_KEY", "")
    if not api_key:
        print("✗ FLEXORCH_API_KEY is not set.", file=sys.stderr)
        return 1

    print(f"FlexOrch API key : {_mask(api_key)}")

    client = FlexOrchMCPClient(api_key)
    try:
        data: dict[str, Any] = await client.get("/usage/current")
        plan: str = data.get("plan", "unknown")
        limit: int = data.get("credits_limit", 0)
        print("Connection       : OK (api.flexorch.com) ✓")
        print(f"Plan             : {plan.capitalize()} ({limit:,} credits/mo)")
        print(f"Tools            : {_TOOLS_COUNT} registered")
        return 0
    except FlexOrchAPIError as exc:
        print(f"Connection       : FAILED — {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Connection       : FAILED — {type(exc).__name__}", file=sys.stderr)
        return 1
    finally:
        await client.aclose()


def _mask(key: str) -> str:
    if len(key) <= 7:
        return "***"
    return key[:7] + "***"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if "--check" in sys.argv:
        code = asyncio.run(_run_check())
        sys.exit(code)

    api_key = os.environ.get("FLEXORCH_API_KEY", "")
    if not api_key:
        print(
            "Error: FLEXORCH_API_KEY environment variable is not set.\n"
            "Add it to your MCP client config and restart.",
            file=sys.stderr,
        )
        sys.exit(1)

    mcp.run()
