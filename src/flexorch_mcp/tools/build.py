"""Tool 4: build_dataset — create a structured dataset from a completed execution."""
from __future__ import annotations

from typing import Any

from ..client import FlexOrchMCPClient
from ..errors import FlexOrchAPIError


async def run(
    client: FlexOrchMCPClient,
    execution_id: int,
    name: str = "",
    description: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if name:
        payload["name"] = name
    if description:
        payload["description"] = description

    try:
        response: dict[str, Any] = await client.post(
            f"/datasets/build-from-execution/{execution_id}",
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
            f"Use get_job_status({job_id}) to check build progress. "
            "When status is 'completed', the response includes dataset_id — "
            "use export_dataset(dataset_id, format='jsonl') to retrieve all records."
        ),
    }
