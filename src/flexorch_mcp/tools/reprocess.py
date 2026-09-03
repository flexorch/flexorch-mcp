"""Tool 9: reprocess_document — re-queue an already-uploaded document."""
from __future__ import annotations

from typing import Any

from ..client import FlexOrchMCPClient
from ..errors import FlexOrchAPIError


async def run(
    client: FlexOrchMCPClient,
    document_id: int,
    pipeline_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if pipeline_config:
        payload["pipeline_config"] = pipeline_config

    try:
        response: dict[str, Any] = await client.post(
            f"/documents/{document_id}/reprocess",
            json=payload if payload else None,
        )
    except FlexOrchAPIError as exc:
        return {"isError": True, "error": str(exc)}

    data = response.get("data", response)
    job_id: int = data["job_id"]
    return {
        "job_id": job_id,
        "status": "queued",
        "poll_hint": (
            f"Use get_job_status({job_id}) to check progress. "
            "Poll every 3–5 seconds until status is 'completed' or 'failed'."
        ),
    }
