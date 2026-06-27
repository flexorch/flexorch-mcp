from __future__ import annotations

import asyncio
import os
import sys
from contextvars import ContextVar
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict

from .client import FlexOrchMCPClient
from .errors import FlexOrchAPIError
from .tools import process as tools_process
from .tools import status as tools_status
from .tools import result as tools_result
from .tools import build as tools_build
from .tools import search as tools_search
from .tools import export as tools_export


# ---------------------------------------------------------------------------
# Output models — allow extra fields so future API additions don't break tools
# ---------------------------------------------------------------------------

class _Base(BaseModel):
    model_config = ConfigDict(extra="allow")
    isError: bool | None = None
    error: str | None = None


class ProcessDocumentResult(_Base):
    job_id: int | None = None
    status: str | None = None
    poll_hint: str | None = None


class JobStatusResult(_Base):
    job_id: int | None = None
    status: str | None = None
    execution_id: int | None = None
    dataset_id: int | None = None
    dataset_name: str | None = None
    row_count: int | None = None
    quality_grade: str | None = None
    quality_score: float | None = None
    pii_found: bool | None = None
    pii_masked: bool | None = None
    pii_count: int | None = None
    has_dataset: bool | None = None
    stage: str | None = None
    reason: str | None = None
    poll_hint: str | None = None


class _QualityInfo(_Base):
    grade: str | None = None
    score: float | None = None
    warnings: list[str] = []


class _PrivacyInfo(_Base):
    pii_findings_count: int = 0
    pii_masked: bool = False


class ExtractionResult(_Base):
    execution_id: int | None = None
    document_type: str | None = None
    detected_language: str | None = None
    quality: _QualityInfo | None = None
    privacy: _PrivacyInfo | None = None
    row_count: int | None = None
    columns: list[str] = []
    fields: list[Any] | None = None
    fields_hint: str | None = None
    has_more: bool | None = None
    has_more_hint: str | None = None


class BuildDatasetResult(_Base):
    job_id: int | None = None
    status: str | None = None
    poll_hint: str | None = None


class SearchResult(_Base):
    results: list[Any] = []
    total_results: int | None = None
    mode: str | None = None
    query: str | None = None


class ExportResult(_Base):
    dataset_id: int | None = None
    format: str | None = None
    filename: str | None = None
    content: str | None = None
    byte_count: int | None = None

_TOOLS_COUNT = 6

# HTTP mode: API key set per-request by _APIKeyMiddleware.
# stdio mode: empty string — _get_client() falls back to env var singleton.
_request_api_key: ContextVar[str] = ContextVar("_request_api_key", default="")

# Singleton for stdio mode — one process, one API key.
_api_client: FlexOrchMCPClient | None = None


def _get_client() -> FlexOrchMCPClient:
    key = _request_api_key.get()
    base_url = os.environ.get("FLEXORCH_BASE_URL", "")
    if key:
        # HTTP mode: fresh client per request so each user's key is isolated.
        return FlexOrchMCPClient(key, **({} if not base_url else {"base_url": base_url + "/v1"}))
    # stdio mode: singleton initialized once from env var.
    global _api_client
    if _api_client is None:
        kwargs = {} if not base_url else {"base_url": base_url + "/v1"}
        _api_client = FlexOrchMCPClient(os.environ.get("FLEXORCH_API_KEY", ""), **kwargs)
    return _api_client

mcp = FastMCP(
    "flexorch",
    instructions=(
        "FlexOrch converts unstructured documents (PDF, DOCX, invoices, contracts, payroll, etc.) "
        "into structured, LLM-ready datasets with PII masking and quality scoring. "
        "Standard workflow (all steps are async — always poll flexorch.job.status after submitting a job): "
        "1. flexorch.document.process(file_url) → returns job_id. "
        "2. flexorch.job.status(job_id) — poll every 3–5 s until status='completed'. Response includes execution_id. "
        "3. flexorch.job.result(execution_id) — read extracted fields and quality grade. "
        "4. flexorch.dataset.build(execution_id) → returns build job_id. Poll flexorch.job.status again. "
        "5. flexorch.dataset.export(dataset_id, format) — returns full dataset content as text. "
        "To search existing datasets without processing a new document: flexorch.dataset.search(query)."
    ),
)


# ---------------------------------------------------------------------------
# Tool 1: process_document
# ---------------------------------------------------------------------------

@mcp.tool(
    name="flexorch.document.process",
    title="Process Document",
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
    structured_output=True,
)
async def process_document(
    file_url: str,
    mask_pii: bool = True,
    document_type: str = "auto",
) -> ProcessDocumentResult:
    """Submit a document for processing — this is always the first step (Step 1 of 5).

    Downloads the file from file_url, then submits it to FlexOrch for automatic
    classification, structured field extraction, PII detection/masking, and quality
    scoring. Processing is asynchronous — this tool returns immediately with a
    job_id. You MUST call flexorch.job.status(job_id) every 3–5 seconds until
    status='completed' before calling flexorch.job.result.

    Args:
        file_url: Publicly accessible URL of the document (http/https only, max 50 MB).
                  Supported: PDF, DOCX, TXT, XLSX, HTML, XML, EML, JPG, PNG, TIFF.
        mask_pii: Replace detected PII (names, IDs, emails, phone numbers) with
                  [MASKED_TYPE] placeholders in all output. Default: true.
        document_type: Optional classification hint — FlexOrch auto-detects if omitted.
                       Values: invoice, expense_report, purchase_order,
                       sales_proposal, bank_statement, payroll.
    """
    data = await tools_process.run(_get_client(), file_url, mask_pii, document_type)
    return ProcessDocumentResult.model_validate(data)


# ---------------------------------------------------------------------------
# Tool 2: get_job_status
# ---------------------------------------------------------------------------

@mcp.tool(
    name="flexorch.job.status",
    title="Get Job Status",
    annotations=ToolAnnotations(
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=False,
    ),
    structured_output=True,
)
async def get_job_status(job_id: int) -> JobStatusResult:
    """Poll a job until it finishes — call this after flexorch.document.process or flexorch.dataset.build (Step 2).

    Call repeatedly every 3–5 seconds until status is 'completed' or 'failed'.
    For data_process jobs: the completed response includes execution_id — pass it to
    flexorch.job.result. For dataset_build jobs: the completed response includes
    dataset_id — pass it to flexorch.dataset.export.

    Args:
        job_id: Job ID returned by flexorch.document.process or flexorch.dataset.build.
    """
    data = await tools_status.run(_get_client(), job_id)
    return JobStatusResult.model_validate(data)


# ---------------------------------------------------------------------------
# Tool 3: get_extraction_result
# ---------------------------------------------------------------------------

@mcp.tool(
    name="flexorch.job.result",
    title="Get Extraction Result",
    annotations=ToolAnnotations(
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=False,
    ),
    structured_output=True,
)
async def get_extraction_result(execution_id: int) -> ExtractionResult:
    """Read structured fields extracted from a completed document (Step 3).

    Use the execution_id from a completed data_process job (flexorch.job.status response).
    Returns document type, detected language, quality grade (A–D), PII summary,
    column list, and extracted field values. If no dataset has been built yet, the
    response includes a fields_hint guiding you to call flexorch.dataset.build next.
    To retrieve all rows as a file, proceed to flexorch.dataset.build → flexorch.dataset.export.

    Note: Masked fields appear as [MASKED_TYPE] placeholders — raw PII is never returned.
    Note: execution_id comes from data_process jobs only; dataset_build jobs use dataset_id.

    Args:
        execution_id: Execution ID from the flexorch.job.status completed response.
    """
    data = await tools_result.run(_get_client(), execution_id)
    return ExtractionResult.model_validate(data)


# ---------------------------------------------------------------------------
# Tool 4: build_dataset
# ---------------------------------------------------------------------------

@mcp.tool(
    name="flexorch.dataset.build",
    title="Build Dataset",
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    ),
    structured_output=True,
)
async def build_dataset(
    execution_id: int,
    name: str = "",
    description: str = "",
) -> BuildDatasetResult:
    """Package extracted records into a dataset for export (Step 4).

    Triggers an async dataset build from a completed execution. Returns a job_id
    immediately — poll with flexorch.job.status until status='completed'. The completed
    response includes dataset_id, which you pass to flexorch.dataset.export to retrieve all
    records as text. This step is required before calling flexorch.dataset.export.

    Args:
        execution_id: Execution ID from a completed data_process job
                      (from flexorch.job.status or flexorch.job.result).
        name: Dataset name. Auto-generated from the source filename if omitted.
        description: Optional description for this dataset.
    """
    data = await tools_build.run(_get_client(), execution_id, name, description)
    return BuildDatasetResult.model_validate(data)


# ---------------------------------------------------------------------------
# Tool 5: search_documents
# ---------------------------------------------------------------------------

@mcp.tool(
    name="flexorch.dataset.search",
    title="Search Documents",
    annotations=ToolAnnotations(
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=False,
    ),
    structured_output=True,
)
async def search_documents(
    query: str,
    top_k: int = 5,
    mode: str = "auto",
    document_type: str = "",
    language: str = "",
    quality_grade: str = "",
) -> SearchResult:
    """Search across all indexed FlexOrch datasets by keyword or meaning.

    Use this to find specific documents or records without processing a new file.
    Requires at least one dataset to exist. Structured search works on all plans.
    Semantic and hybrid modes require a Pro plan — a clear upgrade message is returned
    if the plan is insufficient. mode='auto' picks structured on free plans, hybrid on Pro+.

    Args:
        query: Search query — natural language or keyword. Max 1000 characters.
        top_k: Number of results to return. Default: 5, max: 50.
        mode: Search strategy — auto (default), structured, semantic, hybrid.
              semantic and hybrid require Pro plan.
        document_type: Filter to a specific document type, e.g. invoice (optional).
        language: Filter by document language, ISO 639-1 code, e.g. en, de, tr (optional).
        quality_grade: Filter by quality grade: A, B, C, or D (optional).
    """
    data = await tools_search.run(
        _get_client(), query, top_k, mode, document_type, language, quality_grade
    )
    return SearchResult.model_validate(data)


# ---------------------------------------------------------------------------
# Tool 6: export_dataset
# ---------------------------------------------------------------------------

@mcp.tool(
    name="flexorch.dataset.export",
    title="Export Dataset",
    annotations=ToolAnnotations(
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=False,
    ),
    structured_output=True,
)
async def export_dataset(
    dataset_id: int,
    format: str = "jsonl",
) -> ExportResult:
    """Download all records from a built dataset as text (Step 5 — final step).

    Returns the complete dataset content as a UTF-8 string directly in the response —
    no file download or separate URL needed. Call get_job_status after build_dataset
    and wait for status='completed' before calling this tool. Use the dataset_id from
    that completed response.

    Format guide: jsonl = LLM fine-tuning, rag = LangChain/LlamaIndex chunks,
    csv = spreadsheets, md = human-readable, xml = structured interchange.
    Binary formats (parquet, hf) cannot be returned via MCP — export them from
    the FlexOrch dashboard directly.

    Args:
        dataset_id: Dataset ID from the get_job_status completed build response.
        format: Text export format — jsonl, csv, json, md, xml, rag. Default: jsonl.
    """
    data = await tools_export.run(_get_client(), dataset_id, format)
    return ExportResult.model_validate(data)


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
# HTTP transport helpers
# ---------------------------------------------------------------------------

class _APIKeyMiddleware:
    """ASGI middleware: extracts API key from request and stores in ContextVar."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] in ("http", "websocket"):
            headers: dict[bytes, bytes] = dict(scope.get("headers", []))
            key = ""
            auth = headers.get(b"authorization", b"").decode()
            if auth.lower().startswith("bearer "):
                key = auth[7:].strip()
            if not key:
                key = headers.get(b"x-api-key", b"").decode()
            if not key:
                qs = scope.get("query_string", b"").decode()
                for param in qs.split("&"):
                    if param.startswith("api_key="):
                        key = param[8:]
                        break
            token = _request_api_key.set(key)
            try:
                await self.app(scope, receive, send)
            finally:
                _request_api_key.reset(token)
        else:
            await self.app(scope, receive, send)


def _run_http() -> None:
    import uvicorn

    starlette_app = mcp.streamable_http_app()
    wrapped = _APIKeyMiddleware(starlette_app)
    port = int(os.environ.get("PORT", "8080"))
    print(f"FlexOrch MCP HTTP server starting on 0.0.0.0:{port}", file=sys.stderr)
    uvicorn.run(wrapped, host="0.0.0.0", port=port, log_level="info")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if "--check" in sys.argv:
        code = asyncio.run(_run_check())
        sys.exit(code)

    transport = os.environ.get("MCP_TRANSPORT", "stdio")

    if transport == "http":
        _run_http()
        return

    api_key = os.environ.get("FLEXORCH_API_KEY", "")
    if not api_key:
        print(
            "Error: FLEXORCH_API_KEY environment variable is not set.\n"
            "Add it to your MCP client config and restart.",
            file=sys.stderr,
        )
        sys.exit(1)

    mcp.run()
