"""Tool 1: process_document — download from URL, upload to FlexOrch pipeline."""
from __future__ import annotations

import json
from typing import Any

from ..client import FlexOrchMCPClient
from ..errors import FLEXORCH_ERRORS, FlexOrchAPIError, DownloadError, FileTooLargeError

_SUPPORTED_TYPES = "PDF, DOCX, TXT, XLSX, HTML, XML, EML, JPG, PNG, TIFF"
_VALID_DOC_TYPES = {
    "invoice", "expense_report", "purchase_order",
    "sales_proposal", "bank_statement", "payroll", "auto",
}


async def run(
    client: FlexOrchMCPClient,
    file_url: str,
    mask_pii: bool = True,
    document_type: str = "auto",
) -> dict[str, Any]:
    # --- Download ---
    try:
        content, filename = await client.download_file(file_url)
    except ValueError:
        return {
            "isError": True,
            "error": "Invalid file_url. Only http and https URLs are supported.",
        }
    except DownloadError as exc:
        return {"isError": True, "error": str(exc)}
    except FileTooLargeError:
        return {"isError": True, "error": FLEXORCH_ERRORS["FILE_TOO_LARGE"]}

    # --- Build optional pipeline_config hint ---
    form_data: dict[str, str] = {}
    hints: dict[str, Any] = {}
    if document_type and document_type not in ("auto", ""):
        hints["document_type_hint"] = document_type
    if not mask_pii:
        hints["mask_pii"] = False
    if hints:
        form_data["pipeline_config"] = json.dumps(hints)

    # --- Upload ---
    try:
        response: dict[str, Any] = await client.post(
            "/data-process/async",
            files={"files": (filename, content, "application/octet-stream")},
            data=form_data if form_data else None,
        )
    except FlexOrchAPIError as exc:
        return {"isError": True, "error": str(exc)}

    # Response shape: {"status":"accepted","data":{"accepted":N,"rejected":[...],"jobs":[...]},...}
    data = response.get("data", response)  # unwrap envelope if present
    jobs: list[dict[str, Any]] = data.get("jobs", [])
    rejected: list[dict[str, Any]] = data.get("rejected", [])

    if not jobs:
        reason = rejected[0].get("error", "File was rejected.") if rejected else "No job created."
        return {"isError": True, "error": reason}

    job_id: int = jobs[0].get("job_id", 0)
    return {
        "job_id": job_id,
        "status": "queued",
        "poll_hint": (
            f"Use get_job_status({job_id}) to check progress. "
            "Poll every 3–5 seconds until status is 'completed' or 'failed'."
        ),
    }
